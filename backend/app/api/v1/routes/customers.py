from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.customer import CustomerIn, CustomerOut, CustomerTypeUpdate
from app.core.domain.services.customer_service import get_customer, list_customers, create_customer, update_customer_type
from app.core.deps import get_current_user, require_user
from app.db.session import SessionLocal

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=list[CustomerOut])
def get_customers(db: Session = Depends(get_db), user: dict = Depends(require_user)):
    return [CustomerOut.from_orm(item) for item in list_customers(db)]


@router.post("/", response_model=CustomerOut)
def create_customer_route(customer: CustomerIn, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    return CustomerOut.from_orm(create_customer(db, customer))


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer_route(customer_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    customer = get_customer(db, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="customer not found")
    return CustomerOut.from_orm(customer)


@router.patch("/{customer_id}/type", response_model=CustomerOut)
def update_customer_type_route(customer_id: int, payload: CustomerTypeUpdate, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    customer = update_customer_type(db, customer_id, payload)
    if not customer:
        raise HTTPException(status_code=404, detail="customer not found")
    return CustomerOut.from_orm(customer)
