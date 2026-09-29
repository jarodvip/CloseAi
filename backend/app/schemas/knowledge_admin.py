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


class SuggestionEditIn(BaseModel):
    """审核通过时可选的编辑字段（不传则用草稿原值）"""
    suggestion_type: Optional[str] = Field(default=None, max_length=20)
    scene: Optional[str] = Field(default=None, max_length=100)
    ktype: Optional[str] = Field(default=None, max_length=100)
    title: Optional[str] = Field(default=None, max_length=200)
    industry: Optional[str] = Field(default=None, max_length=100)
    content: Optional[str] = None
    note: Optional[str] = Field(default=None, max_length=255)


class SuggestionRejectIn(BaseModel):
    note: Optional[str] = Field(default=None, max_length=255)
