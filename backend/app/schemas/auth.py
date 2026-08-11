from pydantic import BaseModel, Field
from typing import Optional


class LoginIn(BaseModel):
    username: str = Field(max_length=50)
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Optional[str] = None
