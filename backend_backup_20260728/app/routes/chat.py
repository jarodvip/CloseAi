from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.schemas.chat import ChatSessionIn, ChatMessageIn, ChatSessionOut, ChatMessageOut, ChatReplyOut, ChatSessionRename
from app.services.chat_service import create_session, list_sessions, list_messages, create_message, build_reply, rename_session, get_session
from app.models.chat import ChatSession, ChatMessage
from app.core.deps import get_current_user, require_user
from app.db.session import SessionLocal

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/sessions", response_model=ChatSessionOut)
def create_chat_session(payload: ChatSessionIn, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    return create_session(db, payload.dict())


@router.get("/sessions", response_model=list[ChatSessionOut])
def get_chat_sessions(customer_id: int | None = None, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return list_sessions(db, customer_id)


@router.patch("/sessions/{session_id}", response_model=ChatSessionOut)
def rename_chat_session(session_id: int, payload: ChatSessionRename, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    session = rename_session(db, session_id, payload.title)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return session


@router.delete("/sessions/{session_id}")
def delete_chat_session(session_id: int, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete(synchronize_session=False)
    db.delete(session)
    db.commit()
    return {"code": 0, "message": "ok", "data": None}


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageOut])
def get_chat_messages(session_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    messages = list_messages(db, session_id)
    if not messages:
        return []
    return messages


@router.post("/sessions/{session_id}/messages", response_model=ChatReplyOut)
def send_chat_message(session_id: int, payload: ChatMessageIn, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    create_message(db, session_id, {"role": payload.role, "content": payload.content})
    result = build_reply(db, session_id, payload.content)
    try:
        meta = {}
        if result["message"].meta:
            import json
            meta = json.loads(result["message"].meta)
    except Exception:
        meta = {}
    return ChatReplyOut(
        session_id=session_id,
        message=result["message"],
        trace_id=result["trace_id"],
        source_cards=meta.get("source_cards") or [],
        source_refs=meta.get("source_refs") or [],
    )
