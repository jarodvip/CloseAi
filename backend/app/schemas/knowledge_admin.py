from pydantic import BaseModel, Field
from typing import Optional


class CaseIn(BaseModel):
    code: str = Field(max_length=50)
    title: str = Field(max_length=150)
    type: Optional[str] = Field(default=None, max_length=100)
    industry: Optional[str] = Field(default=None, max_length=100)
    stage: Optional[str] = Field(default=None, max_length=100)
    result: Optional[str] = None
    source: Optional[str] = Field(default=None, max_length=255)


class ScriptIn(BaseModel):
    scene: Optional[str] = Field(default=None, max_length=100)
    type: str = Field(max_length=100)
    template: str
    source: Optional[str] = Field(default=None, max_length=255)
