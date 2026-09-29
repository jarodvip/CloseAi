from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session

from app.schemas.auth import (
    LoginIn, TokenOut, ChangePasswordIn,
    UserCreateIn, UserResetPasswordIn, UserStatusIn,
)
from app.core.domain.services import auth_service
from app.core.deps import get_db, require_user, require_admin, get_current_user

router = APIRouter()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "-"


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db)):
    client_ip = _client_ip(request)
    auth_service.check_login_rate(payload.username, client_ip)
    user = auth_service.authenticate_user(db, payload.username, payload.password)
    if not user:
        auth_service.record_failed_login(payload.username, client_ip)
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已禁用，请联系管理员")
    auth_service.clear_failed_logins(payload.username, client_ip)
    token = auth_service.build_token(user)
    return TokenOut(access_token=token, role=user.role)


@router.get("/me")
def me(user: dict = Depends(require_user)):
    return {"code": 0, "message": "ok", "data": {"username": user.get("username"), "role": user.get("role")}}


@router.post("/change-password")
def change_password(payload: ChangePasswordIn, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    auth_service.change_own_password(db, user["username"], payload.old_password, payload.new_password)
    return {"code": 0, "message": "ok"}


# ── 用户管理（admin） ──

def _user_dict(u) -> dict:
    return {"id": u.id, "username": u.username, "role": u.role, "is_active": bool(u.is_active)}


@router.get("/users")
def list_users(db: Session = Depends(get_db), user: dict = Depends(require_admin)):
    return {"code": 0, "message": "ok", "data": [_user_dict(u) for u in auth_service.list_users(db)]}


@router.post("/users")
def create_user(payload: UserCreateIn, db: Session = Depends(get_db), user: dict = Depends(require_admin)):
    record = auth_service.create_user(db, payload.username, payload.password, payload.role)
    return {"code": 0, "message": "ok", "data": _user_dict(record)}


@router.patch("/users/{user_id}/status")
def set_user_status(user_id: int, payload: UserStatusIn, db: Session = Depends(get_db), user: dict = Depends(require_admin)):
    record = auth_service.set_user_active(db, user_id, payload.is_active, user["username"])
    return {"code": 0, "message": "ok", "data": _user_dict(record)}


@router.post("/users/{user_id}/reset-password")
def reset_password(user_id: int, payload: UserResetPasswordIn, db: Session = Depends(get_db), user: dict = Depends(require_admin)):
    record = auth_service.reset_user_password(db, user_id, payload.new_password)
    return {"code": 0, "message": "ok", "data": _user_dict(record)}
