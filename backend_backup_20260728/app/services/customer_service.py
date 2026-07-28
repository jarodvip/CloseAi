from typing import Optional
from sqlalchemy.orm import Session
from app.schemas.customer import CustomerIn, CustomerOut, CustomerTypeUpdate
from app.models.customer import Customer


def get_customer(db: Session, customer_id: int) -> Optional[Customer]:
    return db.query(Customer).filter(Customer.id == customer_id).first()


def list_customers(db: Session) -> list:
    return db.query(Customer).order_by(Customer.id.asc()).all()


def create_customer(db: Session, customer_in: CustomerIn) -> Customer:
    customer = Customer(**customer_in.dict())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def update_customer_type(db: Session, customer_id: int, payload: CustomerTypeUpdate) -> Optional[Customer]:
    customer = get_customer(db, customer_id)
    if not customer:
        return None
    if payload.primary_type is not None:
        customer.primary_type = payload.primary_type
    if payload.secondary_type is not None:
        customer.secondary_type = payload.secondary_type
    if payload.type_confidence is not None:
        customer.type_confidence = payload.type_confidence
    if payload.type_evidence is not None:
        customer.type_evidence = payload.type_evidence
    db.commit()
    db.refresh(customer)
    return customer
