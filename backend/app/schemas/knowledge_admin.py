from pydantic import BaseModel
from typing import Optional


class CaseIn(BaseModel):
    code: str
    title: str
    type: Optional[str] = None
    industry: Optional[str] = None
    stage: Optional[str] = None
    result: Optional[str] = None
    source: Optional[str] = None


class ScriptIn(BaseModel):
    scene: Optional[str] = None
    type: str
    template: str
    source: Optional[str] = None
