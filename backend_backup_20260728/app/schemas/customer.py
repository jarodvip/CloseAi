from pydantic import BaseModel
from typing import Optional


class CustomerIn(BaseModel):
    model_config = {"from_attributes": True}

    name: str
    industry: Optional[str] = None
    revenue_range: Optional[str] = None
    stage: Optional[str] = None
    region: Optional[str] = None


class CustomerOut(CustomerIn):
    model_config = {"from_attributes": True}

    id: int
    primary_type: Optional[str] = None
    secondary_type: Optional[str] = None
    type_confidence: Optional[float] = None
    type_evidence: Optional[str] = None


class CustomerTypeUpdate(BaseModel):
    primary_type: Optional[str] = None
    secondary_type: Optional[str] = None
    type_confidence: Optional[float] = None
    type_evidence: Optional[str] = None
