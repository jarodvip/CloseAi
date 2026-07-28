from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class BriefingOut(BaseModel):
    model_config = {"from_attributes": True}

    id: Optional[int] = None
    customer_id: int
    session_id: Optional[int] = None
    customer_name: Optional[str] = None
    primary_type: Optional[str] = None
    secondary_type: Optional[str] = None
    confidence: Optional[float] = None
    evidence: Optional[str] = None
    opening_line: Optional[str] = None
    focus: Optional[str] = None
    next_step: Optional[str] = None
    recommended_cases: Optional[List[Dict[str, Any]]] = None
    potential_objections: Optional[List[str]] = None
    source_refs: Optional[List[str]] = None
    llm_text: Optional[str] = None
    llm_source_cards: Optional[List[Dict[str, Any]]] = None
    created_at: Optional[str] = None
