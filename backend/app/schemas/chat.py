from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class ChatSessionIn(BaseModel):
    customer_id: Optional[int] = None
    title: Optional[str] = None


class ChatSessionRename(BaseModel):
    title: Optional[str] = None


class ChatSessionOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    customer_id: Optional[int] = None
    title: Optional[str] = None
    created_at: Optional[str] = None


class ChatMessageIn(BaseModel):
    role: str = "user"
    content: str


class ChatMessageOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    role: str
    content: str
    meta: Optional[str] = None
    created_at: Optional[str] = None


class ChatReplyOut(BaseModel):
    session_id: int
    message: ChatMessageOut
    trace_id: str
    source_cards: Optional[List[Dict[str, Any]]] = None
    source_refs: Optional[List[str]] = None
