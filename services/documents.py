import hashlib
import logging
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from db.models import ChatRoom, UploadedFile
from services.config import UPLOAD_DIR, MAX_UPLOAD_BYTES
from services.ingestion.chunker import chunk_text
from services.qdrant import embed_and_store, delete_vectors

logger = logging.getLogger(__name__)
SUPPORTED_TYPES = {'pdf', 'csv', 'txt', 'md', 'png', 'jpg', 'jpeg', 'docx', 'pptx', 'wav', 'mp3', 'm4a', 'flac', 'ogg', 'mp4', 'mov', 'webm'}

def require_room(db, room_id, user_id):
    room = db.query(ChatRoom).filter(ChatRoom.id == room_id, ChatRoom.owner_id == user_id).first()
    if room is None:
        raise HTTPException(404, 'Room not found')
    return room

def safe_filename(filename):
    # Treat both Windows and POSIX separators consistently.
    name = (filename or '').replace('\\', '/').rsplit('/', 1)[-1].strip()
    if not name or len(name) > 255 or any(ord(c) < 32 for c in name) or ':' in name:
        raise HTTPException(400, 'Invalid filename')
    extension = Path(name).suffix.lower().lstrip('.')
    if extension not in SUPPORTED_TYPES:
        raise HTTPException(415, 'Unsupported file type')
    return name, extension

def extract_document(path, extension):
    if extension == 'pdf':
        from services.ingestion.pdf import extract_pdf
        return extract_pdf(str(path))
    if extension in {'png', 'jpg', 'jpeg'}:
        from services.ingestion.image import extract_image_text
        from services.ingestion.vision import extract_visual_description
        try:
            text = extract_image_text(str(path))
        except (RuntimeError, FileNotFoundError):
            text = ''
        # Spatial OCR remains primary for certificates; vision handles visual-only images.
        if len(text.split()) >= 8:
            return text
        return 'Generated visual description (unverified):\n' + extract_visual_description(str(path))
    if extension == 'csv':
        from services.ingestion.csv import extract_csv
        return extract_csv(str(path))
    if extension == 'docx':
        from services.ingestion.docx import extract_docx
        return extract_docx(path)
    if extension == 'pptx':
        from services.ingestion.pptx import extract_pptx
        return extract_pptx(path)
    if extension in {'wav', 'mp3', 'm4a', 'flac', 'ogg'}:
        from services.ingestion.audio import extract_audio
        return extract_audio(path)
    if extension in {'mp4', 'mov', 'webm'}:
        from services.ingestion.video import extract_video
        return extract_video(path)
    from services.ingestion.text import extract_text
    from services.ingestion.markdown import extract_markdown
    return extract_markdown(str(path)) if extension == 'md' else extract_text(str(path))

def document_chunks(path, extension):
    text = extract_document(path, extension)
    if extension in {'png', 'jpg', 'jpeg'}:
        from services.ingestion.image import chunk_image_text
        return chunk_image_text(text)
    return chunk_text(text)

def remove_physical_file(db, uploaded_file):
    path = Path(uploaded_file.file_path).resolve()
    if not path.is_relative_to(UPLOAD_DIR.resolve()):
        raise ValueError('Stored file path is outside the upload directory')
    # Legacy uploads can share a physical path; retain it until the last reference.
    others = db.query(UploadedFile).filter(UploadedFile.id != uploaded_file.id).all()
    if not any(Path(other.file_path).resolve() == path for other in others):
        path.unlink(missing_ok=True)

def remove_document(db, uploaded_file):
    delete_vectors(room_id=uploaded_file.room_id, file_id=uploaded_file.id)
    remove_physical_file(db, uploaded_file)
    db.delete(uploaded_file)
    db.flush()

def process_upload(db, room_id, user_id, upload):
    require_room(db, room_id, user_id)
    filename, extension = safe_filename(upload.filename)
    content = upload.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, 'File exceeds the upload size limit')
    if not content:
        raise HTTPException(400, 'Uploaded file is empty')
    digest = hashlib.sha256(content).hexdigest()
    duplicate = db.query(UploadedFile).filter(
        UploadedFile.room_id == room_id, UploadedFile.file_hash == digest,
        UploadedFile.status.in_(['processing', 'ready', 'completed'])
    ).first()
    if duplicate:
        raise HTTPException(409, 'This file has already been uploaded to this room')
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOAD_DIR / f'{uuid4().hex}.{extension}'
    record = UploadedFile(room_id=room_id, filename=filename, file_type=extension,
                          file_path=str(path), file_hash=digest, status='processing')
    try:
        path.write_bytes(content)
        db.add(record)
        db.commit()
        db.refresh(record)
    except Exception:
        db.rollback()
        path.unlink(missing_ok=True)
        logger.exception('Could not save upload')
        raise HTTPException(500, 'Could not save upload')
    file_id = record.id
    try:
        chunks = document_chunks(path, extension)
        if not chunks:
            raise HTTPException(422, 'No readable text was found in the document')
        count = embed_and_store(chunks=chunks, room_id=room_id, file_id=file_id,
                               filename=filename, file_type=extension)
        if count == 0:
            raise HTTPException(422, 'No document chunks were indexed')
        record.status = 'ready'
        db.commit()
        logger.info('Indexed file %s: %s chunks', file_id, count)
        return {'file_id': file_id, 'filename': filename, 'chunks_created': count,
                'chunks': count, 'status': 'ready'}
    except Exception as exc:
        db.rollback()
        # Preserve a visible failed record so a failed attempt can be deleted or retried.
        failed = db.get(UploadedFile, file_id)
        failed.status = 'failed'
        db.commit()
        try:
            delete_vectors(room_id=room_id, file_id=file_id)
        except Exception:
            logger.exception('Cleanup failed for file %s; deletion can be retried', file_id)
        try:
            path.unlink(missing_ok=True)
        except OSError:
            logger.exception('File cleanup failed for file %s', file_id)
        logger.exception('Processing failed for file %s', file_id)
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(422 if isinstance(exc, ValueError) else 500,
                            str(exc) if isinstance(exc, ValueError) else 'File processing failed; check the format and API configuration, then retry') from exc


def reindex_document(db, record):
    path = Path(record.file_path)
    if not path.is_absolute():
        from services.config import BASE_DIR
        path = BASE_DIR / path
    path = path.resolve()
    if not path.is_relative_to(UPLOAD_DIR.resolve()):
        raise HTTPException(400, 'Stored file path is outside the upload directory')
    if not path.is_file():
        raise HTTPException(404, 'The original uploaded file is missing; upload it again')
    file_id, room_id = record.id, record.room_id
    try:
        chunks = document_chunks(path, record.file_type)
        if not chunks:
            raise HTTPException(422, 'No readable text was found')
        record.status = 'processing'
        db.commit()
        delete_vectors(room_id=room_id, file_id=file_id)
        count = embed_and_store(chunks=chunks, room_id=room_id, file_id=file_id,
                                filename=record.filename, file_type=record.file_type)
        if not count:
            raise HTTPException(422, 'No document chunks were indexed')
        record.status = 'ready'
        db.commit()
        return {'file_id': file_id, 'chunks_created': count, 'status': 'ready'}
    except Exception as exc:
        db.rollback()
        # Retain the original image so a failed reindex can be retried.
        db.get(UploadedFile, file_id).status = 'failed'
        db.commit()
        try:
            delete_vectors(room_id=room_id, file_id=file_id)
        except Exception:
            logger.exception('Reindex cleanup failed for file %s', file_id)
        logger.exception('Reindex failed for file %s', file_id)
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(500, 'Reindex failed; the original file was retained for retry') from exc
