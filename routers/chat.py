import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import ChatMessage
from schemas.chat import ChatRequest, ChatResponse
from services.auth import get_current_user
from services.documents import require_room
from services.rag import ask

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/chat', tags=['Chat'])

@router.get('/{room_id}/history')
def get_chat_history(room_id: int, skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=200),
                     db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    require_room(db, room_id, current_user.id)
    return db.query(ChatMessage).filter(ChatMessage.room_id == room_id, ChatMessage.user_id == current_user.id).order_by(
        ChatMessage.created_at.asc(), ChatMessage.id.asc()).offset(skip).limit(limit).all()

@router.delete('/{room_id}/history')
def delete_chat_history(room_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    require_room(db, room_id, current_user.id)
    db.query(ChatMessage).filter(ChatMessage.room_id == room_id, ChatMessage.user_id == current_user.id).delete(synchronize_session=False)
    db.commit()
    return {'message': 'Chat history deleted successfully'}

@router.post('/{room_id}', response_model=ChatResponse)
def chat(room_id: int, chat_data: ChatRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    require_room(db, room_id, current_user.id)
    if not chat_data.query.strip():
        raise HTTPException(422, 'Question cannot be blank')
    messages = db.query(ChatMessage).filter(ChatMessage.room_id == room_id, ChatMessage.user_id == current_user.id).order_by(
        ChatMessage.created_at.desc(), ChatMessage.id.desc()).limit(6).all()
    history = [{'role': message.role, 'content': message.content} for message in reversed(messages)]
    try:
        result = ask(query=chat_data.query, room_id=room_id, history=history)
    except Exception as exc:
        logger.exception('Answer generation failed for room %s', room_id)
        raise HTTPException(502, 'Answer generation failed; retry your question') from exc
    db.add_all([ChatMessage(room_id=room_id, user_id=current_user.id, role='user', content=chat_data.query, sources=[]),
                ChatMessage(room_id=room_id, user_id=current_user.id, role='assistant', content=result['answer'], sources=result['sources'])])
    db.commit()
    logger.info('Saved conversation turn for room %s', room_id)
    return result
