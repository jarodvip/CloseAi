from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.schemas.interaction import InteractionIn, InteractionOut, AssistIn, AssistOut, FollowupIn, FollowupOut
from app.core.domain.services.interaction_service import create_interaction, list_interactions
from app.core.domain.services.customer_service import get_customer
from app.core.domain.services.assist_service import build_assist
from app.core.domain.services.followup_service import build_followup
from app.core.deps import get_current_user, require_user
from app.db.session import SessionLocal

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/{customer_id}/interactions", response_model=InteractionOut)
def create_interaction_route(customer_id: int, payload: InteractionIn, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    customer = get_customer(db, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="customer not found")
    return create_interaction(db, customer_id, payload)


@router.get("/{customer_id}/interactions", response_model=list[InteractionOut])
def list_interactions_route(customer_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return list_interactions(db, customer_id)


@router.post("/{customer_id}/assist")
def assist_route(customer_id: int, payload: AssistIn, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    customer = get_customer(db, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="customer not found")
    result = build_assist(db, customer_id, {
        "current_stage": payload.current_stage,
        "transcript": payload.transcript,
        "customer_type": customer.primary_type or payload.customer_type or "品牌野心型",
    })
    return {
        "code": 0,
        "message": "ok",
        "data": result,
        "trace_id": f"assist-{customer_id}",
    }


@router.post("/{customer_id}/followup")
def followup_route(customer_id: int, payload: FollowupIn, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    customer = get_customer(db, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="customer not found")
    result = build_followup(db, customer_id, {
        "summary": payload.summary,
        "decisions": payload.decisions or [],
        "pending_actions": payload.pending_actions or [],
        "transcript": payload.transcript,
        "customer_type": customer.primary_type or payload.customer_type or "品牌野心型",
    })
    return {
        "code": 0,
        "message": "ok",
        "data": result,
        "trace_id": f"followup-{customer_id}",
    }
