from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class InteractionIn(BaseModel):
    model_config = {"from_attributes": True}

    stage: Optional[str] = None
    transcript: Optional[str] = None
    summary: Optional[str] = None
    decisions: Optional[str] = None
    pending_actions: Optional[str] = None


class InteractionOut(InteractionIn):
    model_config = {"from_attributes": True}

    id: int
    customer_id: int
    created_at: Optional[str] = None


class AssistIn(BaseModel):
    current_stage: Optional[str] = None
    transcript: Optional[str] = None
    customer_type: Optional[str] = None


class AssistOut(BaseModel):
    current_stage: Optional[str] = None
    detected_stage: Optional[str] = None
    stage_guidance: Optional[str] = None
    suggested_response: Optional[str] = None
    objection_detected: Optional[str] = None
    objection_response: Optional[str] = None
    notes: Optional[List[str]] = None
    source_cards: Optional[List[Dict[str, Any]]] = None
    source_refs: Optional[List[str]] = None
    llm_text: Optional[str] = None


class FollowupIn(BaseModel):
    summary: Optional[str] = None
    decisions: Optional[List[str]] = None
    pending_actions: Optional[List[str]] = None
    transcript: Optional[str] = None
    customer_type: Optional[str] = None


class FollowupOut(BaseModel):
    summary: Optional[str] = None
    decisions: Optional[List[str]] = None
    pending_actions: Optional[List[str]] = None
    tasks: Optional[List[Dict[str, str]]] = None
    followup_email: Optional[str] = None
    followup_wechat: Optional[str] = None
    knowledge_update_suggestion: Optional[str] = None
    source_cards: Optional[List[Dict[str, Any]]] = None
    source_refs: Optional[List[str]] = None
    llm_text: Optional[str] = None
