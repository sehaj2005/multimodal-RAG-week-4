from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
)

from schemas.room import RoomCreate
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import ChatRoom, UploadedFile, ChatMessage

from services.auth import get_current_user
import logging
from services.documents import require_room, remove_document, process_upload
from services.qdrant import delete_vectors
logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/rooms",
    tags=["Rooms"],
)





# ==================================================
# ROOM CREATE SCHEMA
# ==================================================

# ==================================================
# CREATE ROOM
# ==================================================

@router.post("/")
def create_room(
    room_data: RoomCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    room = ChatRoom(
        name=room_data.name,
        description=room_data.description,
        owner_id=current_user.id,
    )

    db.add(room)
    db.commit()
    db.refresh(room)

    return {
        "id": room.id,
        "name": room.name,
        "description": room.description,
    }


# ==================================================
# LIST ROOMS
# ==================================================

@router.get("/")
def list_rooms(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rooms = (
        db.query(ChatRoom)
        .filter(
            ChatRoom.owner_id == current_user.id
        )
        .order_by(ChatRoom.id.desc())
        .all()
    )

    return [
        {
            "id": room.id,
            "name": room.name,
            "description": room.description,
        }
        for room in rooms
    ]


# ==================================================
# GET ROOM
# ==================================================

@router.get("/{room_id}")
def get_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    room = (
        db.query(ChatRoom)
        .filter(
            ChatRoom.id == room_id,
            ChatRoom.owner_id == current_user.id,
        )
        .first()
    )

    if room is None:
        raise HTTPException(
            status_code=404,
            detail="Room not found",
        )

    return {
        "id": room.id,
        "name": room.name,
        "description": room.description,
    }


# ==================================================
# DELETE ROOM
# ==================================================


@router.delete('/{room_id}')
def delete_room(room_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    room = require_room(db, room_id, current_user.id)
    try:
        files = db.query(UploadedFile).filter(UploadedFile.room_id == room_id).all()
        for record in files:
            remove_document(db, record)
        delete_vectors(room_id=room_id)
        db.query(ChatMessage).filter(ChatMessage.room_id == room_id).delete(synchronize_session=False)
        db.delete(room)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception('Room deletion failed: %s', room_id)
        raise HTTPException(500, 'Room deletion failed; retry deletion') from exc
    return {'message': 'Room deleted successfully', 'room_id': room_id}

@router.post('/{room_id}/upload')
def upload_document(room_id: int, file: UploadFile = File(...), db: Session = Depends(get_db),
                    current_user=Depends(get_current_user)):
    return process_upload(db, room_id, current_user.id, file)
