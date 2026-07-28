from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.schemas.interaction import InteractionIn, InteractionOut
from app.models.interaction import Interaction


def create_interaction(db: Session, customer_id: int, payload: InteractionIn) -> Interaction:
    record = Interaction(
        customer_id=customer_id,
        **payload.model_dump(),
        created_at=datetime.now().isoformat(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_interactions(db: Session, customer_id: int) -> list:
    return db.query(Interaction).filter(Interaction.customer_id == customer_id).order_by(Interaction.id.asc()).all()
