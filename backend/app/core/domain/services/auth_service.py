import threading
import time
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.user import User
from app.core.security import hash_password, verify_password, create_access_token

PASSWORD_MIN_LENGTH = 8

# 登录限速：内存态（单进程部署足够；多副本部署需换 Redis）。
# 同一 用户名+IP 在 15 分钟内失败 5 次后锁定，成功登录即清零。
FAILED_LOGIN_WINDOW_SECONDS = 15 * 60
FAILED_LOGIN_MAX_ATTEMPTS = 5
_failed_logins: dict = {}
_failed_lock = threading.Lock()


def _failed_key(username: str, client_ip: str) -> str:
    return f"{(username or '').lower()}|{client_ip or '-'}"


def check_login_rate(username: str, client_ip: str) -> None:
    """失败次数超限时抛 429，携带需等待的秒数"""
    key = _failed_key(username, client_ip)
    now = time.monotonic()
    with _failed_lock:
        stamps = [t for t in _failed_logins.get(key, []) if now - t < FAILED_LOGIN_WINDOW_SECONDS]
        _failed_logins[key] = stamps
        if len(stamps) >= FAILED_LOGIN_MAX_ATTEMPTS:
            wait = int(FAILED_LOGIN_WINDOW_SECONDS - (now - stamps[0])) + 1
            raise HTTPException(status_code=429, detail=f"登录失败次数过多，请 {wait} 秒后重试")


def record_failed_login(username: str, client_ip: str) -> None:
    key = _failed_key(username, client_ip)
    with _failed_lock:
        _failed_logins.setdefault(key, []).append(time.monotonic())


def clear_failed_logins(username: str, client_ip: str) -> None:
    with _failed_lock:
        _failed_logins.pop(_failed_key(username, client_ip), None)


def validate_password(password: str) -> str:
    """新密码策略：非空且 ≥8 位。返回去空格后的密码，不合法抛 422"""
    password = (password or "").strip()
    if len(password) < PASSWORD_MIN_LENGTH:
        raise HTTPException(status_code=422, detail=f"密码长度至少 {PASSWORD_MIN_LENGTH} 位")
    return password


def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def list_users(db: Session):
    return db.query(User).order_by(User.id.asc()).all()


def create_user(db: Session, username: str, password: str, role: str = "user") -> User:
    username = (username or "").strip()
    if not username:
        raise HTTPException(status_code=422, detail="用户名不能为空")
    if get_user_by_username(db, username):
        raise HTTPException(status_code=409, detail="用户名已存在")
    if role not in {"admin", "user"}:
        raise HTTPException(status_code=422, detail="role 仅支持 admin/user")
    password = validate_password(password)
    user = User(username=username, hashed_password=hash_password(password), role=role, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def set_user_active(db: Session, user_id: int, is_active: bool, operator: str) -> User:
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.username == operator and not is_active:
        raise HTTPException(status_code=422, detail="不能禁用自己的账号")
    user.is_active = is_active
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def reset_user_password(db: Session, user_id: int, new_password: str) -> User:
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.hashed_password = hash_password(validate_password(new_password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def change_own_password(db: Session, username: str, old_password: str, new_password: str) -> None:
    user = get_user_by_username(db, username)
    if not user or not verify_password(old_password or "", user.hashed_password):
        raise HTTPException(status_code=400, detail="原密码不正确")
    user.hashed_password = hash_password(validate_password(new_password))
    db.add(user)
    db.commit()


def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def build_token(user: User) -> str:
    return create_access_token({"sub": user.username, "role": user.role}, expires_delta=timedelta(hours=24))
