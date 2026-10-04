import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import UploadedFile
from services.auth import get_current_user
from services.documents import require_room, remove_document, reindex_document

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/files', tags=['Files'])

@router.get('/{room_id}')
def list_files(room_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    require_room(db, room_id, current_user.id)
    files = db.query(UploadedFile).filter(UploadedFile.room_id == room_id).order_by(UploadedFile.id.desc()).all()
    return [{'file_id': f.id, 'filename': f.filename, 'file_type': f.file_type, 'status': f.status} for f in files]

@router.delete('/{room_id}/{file_id}')
def delete_file(room_id: int, file_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    require_room(db, room_id, current_user.id)
    record = db.query(UploadedFile).filter(UploadedFile.id == file_id, UploadedFile.room_id == room_id).first()
    if record is None:
        raise HTTPException(404, 'File not found')
    filename = record.filename
    try:
        remove_document(db, record)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception('Deletion failed for file %s', file_id)
        raise HTTPException(500, 'File deletion failed; retry deletion') from exc
    return {'message': 'File deleted successfully', 'file_id': file_id, 'filename': filename}


@router.post('/{room_id}/{file_id}/reindex')
def reindex_file(room_id: int, file_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    require_room(db, room_id, current_user.id)
    record = db.query(UploadedFile).filter(UploadedFile.id == file_id, UploadedFile.room_id == room_id).first()
    if record is None:
        raise HTTPException(404, 'File not found')
    return reindex_document(db, record)
