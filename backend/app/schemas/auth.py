from pydantic import BaseModel, Field
from typing import Optional


class LoginIn(BaseModel):
    username: str = Field(max_length=50)
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Optional[str] = None


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str = Field(max_length=128)


class UserCreateIn(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(max_length=128)
    role: str = Field(default="user", max_length=20)


class UserResetPasswordIn(BaseModel):
    new_password: str = Field(max_length=128)


class UserStatusIn(BaseModel):
    is_active: bool
