from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional, Dict

from app.core.config import settings
from app.core.security import decode_access_token
from app.models.customer import Customer
from sqlalchemy.orm import Session
from app.db.session import SessionLocal

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login", auto_error=False)


async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[Dict]:
    """从 Authorization: Bearer <token> 解析用户信息（含 role）。
    校验数据库中的账号状态：被禁用账号即使 token 未过期也立即失效"""
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    username = payload.get("sub") or payload.get("username")
    if not username:
        return None
    from app.models.user import User
    db = SessionLocal()
    try:
        row = db.query(User).filter(User.username == username).first()
        if not row or not row.is_active:
            return None
    finally:
        db.close()
    return {"username": username, "role": payload.get("role")}


async def require_user(user: Optional[Dict] = Depends(get_current_user)) -> Dict:
    """校验：必须已登录"""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录或登录已过期"
        )
    return user


async def require_admin(user: Dict = Depends(require_user)) -> Dict:
    """校验：必须是 admin 角色"""
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足：需要 admin 角色"
        )
    return user


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def assert_owner(db: Session, customer_id: int, user: Dict):
    """校验当前用户是否为客户的 owner，不是则返回 404"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer or customer.owner_id != _user_id(db, user):
        raise HTTPException(status_code=404, detail="customer not found")


def _user_id(db: Session, user: Dict) -> int:
    from app.models.user import User
    return db.query(User.id).filter(User.username == user.get("username")).scalar()