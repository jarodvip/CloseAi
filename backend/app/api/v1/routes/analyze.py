from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.domain.services.analysis_service import analyze_customer
from app.core.deps import get_db, require_user, assert_owner
from app.core.domain.services.customer_service import get_customer
from app.schemas.customer import CustomerIn

router = APIRouter()


class AnalyzeIn(BaseModel):
    name: str
    industry: str = ""
    revenue_range: str = ""
    stage: str = ""
    region: str = ""


@router.post("/analyze")
def analyze_route(payload: AnalyzeIn, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    from app.models.user import User
    owner_id = db.query(User.id).filter(User.username == user.get("username")).scalar()
    result = analyze_customer(db, payload.model_dump(), owner_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"code": 0, "message": "ok", "data": result}
