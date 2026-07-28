from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.schemas.auth import LoginIn, TokenOut
from app.services.auth_service import authenticate_user, build_token
from app.db.session import SessionLocal
from app.core.deps import require_user

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = build_token(user)
    return TokenOut(access_token=token, role=user.role)


@router.get("/me")
def me(user: dict = Depends(require_user)):
    return {"code": 0, "message": "ok", "data": {"username": user.get("username"), "role": user.get("role")}}
