from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional, Dict

from app.core.config import settings
from app.core.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login", auto_error=False)


async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[Dict]:
    """从 Authorization: Bearer <token> 解析用户信息（含 role）"""
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    username = payload.get("sub") or payload.get("username")
    if not username:
        return None
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