from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.schemas.briefing import BriefingOut
from app.core.domain.services.briefing_service import build_briefing, list_briefings
from app.core.deps import get_current_user
from app.db.session import SessionLocal

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/{customer_id}/briefing", response_model=dict)
def generate_briefing(customer_id: int, session_id: int | None = None, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    payload = build_briefing(db, customer_id, session_id=session_id)
    if not payload:
        raise HTTPException(status_code=404, detail="customer not found")
    return {
        "code": 0,
        "message": "ok",
        "data": payload,
        "trace_id": f"briefing-{customer_id}-{payload.get('id', 'latest')}",
    }


@router.get("/{customer_id}/history", response_model=dict)
def get_briefing_history(customer_id: int, limit: int = 20, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    customer = None
    from app.core.domain.services.customer_service import get_customer
    customer = get_customer(db, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="customer not found")
    return {"code": 0, "message": "ok", "data": list_briefings(db, customer_id, limit)}
