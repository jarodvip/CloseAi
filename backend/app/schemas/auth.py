from pydantic import BaseModel
from typing import Optional


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Optional[str] = None
