from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session
from db.database import get_db
from schemas.upload import UploadResponse
from services.auth import get_current_user
from services.documents import process_upload
from routers.files import list_files, delete_file

router = APIRouter(prefix='/upload', tags=['Upload'])

@router.post('/{room_id}', response_model=UploadResponse)
def upload_file(room_id: int, file: UploadFile = File(...), db: Session = Depends(get_db),
                current_user=Depends(get_current_user)):
    return process_upload(db, room_id, current_user.id, file)

# Compatibility aliases for the Week 4 API plan.
router.add_api_route('/{room_id}', list_files, methods=['GET'])
router.add_api_route('/{room_id}/{file_id}', delete_file, methods=['DELETE'])
