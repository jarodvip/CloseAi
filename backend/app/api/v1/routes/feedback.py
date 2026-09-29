from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.domain.services.feedback_service import create_feedback, feedback_stats
from app.schemas.feedback import FeedbackIn
from app.core.deps import get_db, require_user

router = APIRouter()


@router.post("")
def create_feedback_route(payload: FeedbackIn, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    record = create_feedback(db, payload.model_dump(), user["username"])
    return {"code": 0, "message": "ok", "data": {"id": record.id, "rating": record.rating}}


@router.get("/stats")
def feedback_stats_route(db: Session = Depends(get_db), user: dict = Depends(require_user)):
    return {"code": 0, "message": "ok", "data": feedback_stats(db)}
