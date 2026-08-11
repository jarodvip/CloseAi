from pydantic import BaseModel, Field
from typing import Optional


class InteractionIn(BaseModel):
    model_config = {"from_attributes": True}

    stage: Optional[str] = Field(default=None, max_length=50)
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
    current_stage: Optional[str] = Field(default=None, max_length=50)
    transcript: Optional[str] = None
    customer_type: Optional[str] = Field(default=None, max_length=100)


class AssistOut(BaseModel):
    current_stage: Optional[str] = None
    detected_stage: Optional[str] = None
    stage_guidance: Optional[str] = None
    suggested_response: Optional[str] = None
    objection_detected: Optional[str] = None
    objection_response: Optional[str] = None
    notes: Optional[list[str]] = None
    source_cards: Optional[list[dict]] = None
    source_refs: Optional[list[str]] = None
    llm_text: Optional[str] = None


class FollowupIn(BaseModel):
    summary: Optional[str] = None
    decisions: Optional[list[str]] = None
    pending_actions: Optional[list[str]] = None
    transcript: Optional[str] = None
    customer_type: Optional[str] = Field(default=None, max_length=100)


class FollowupOut(BaseModel):
    summary: Optional[str] = None
    decisions: Optional[list[str]] = None
    pending_actions: Optional[list[str]] = None
    tasks: Optional[list[dict[str, str]]] = None
    followup_email: Optional[str] = None
    followup_wechat: Optional[str] = None
    knowledge_update_suggestion: Optional[str] = None
    source_cards: Optional[list[dict]] = None
    source_refs: Optional[list[str]] = None
    llm_text: Optional[str] = None
