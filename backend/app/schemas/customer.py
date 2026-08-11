from pydantic import BaseModel, Field
from typing import Optional


class CustomerIn(BaseModel):
    model_config = {"from_attributes": True}

    name: str = Field(max_length=100)
    industry: Optional[str] = Field(default=None, max_length=100)
    revenue_range: Optional[str] = Field(default=None, max_length=100)
    stage: Optional[str] = Field(default=None, max_length=100)
    region: Optional[str] = Field(default=None, max_length=100)


class CustomerOut(CustomerIn):
    model_config = {"from_attributes": True}

    id: int
    primary_type: Optional[str] = Field(default=None, max_length=100)
    secondary_type: Optional[str] = Field(default=None, max_length=100)
    type_confidence: Optional[float] = None
    type_evidence: Optional[str] = None


class CustomerTypeUpdate(BaseModel):
    primary_type: Optional[str] = Field(default=None, max_length=100)
    secondary_type: Optional[str] = Field(default=None, max_length=100)
    type_confidence: Optional[float] = None
    type_evidence: Optional[str] = None
