from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.domain.services.analysis_service import analyze_customer
from app.core.deps import get_current_user, require_user
from app.db.session import SessionLocal


router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class AnalyzeIn(BaseModel):
    name: str
    industry: str = ""
    revenue_range: str = ""
    stage: str = ""
    region: str = ""


@router.post("/analyze")
def analyze_route(payload: AnalyzeIn, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    result = analyze_customer(db, payload.model_dump())
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"code": 0, "message": "ok", "data": result}
