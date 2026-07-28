from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.domain.services.knowledge_service import list_customer_types, list_cases, list_scripts, list_evidence, create_case, create_script
from app.schemas.knowledge_admin import CaseIn, ScriptIn
from app.core.deps import get_current_user, require_user
from app.db.session import SessionLocal

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/customer-types")
def get_customer_types(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return {"code": 0, "message": "ok", "data": [item.__dict__ for item in list_customer_types(db)]}


@router.get("/cases")
def get_cases(query: str = "", db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return {"code": 0, "message": "ok", "data": [item.__dict__ for item in list_cases(db, query)]}


@router.get("/scripts")
def get_scripts(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return {"code": 0, "message": "ok", "data": [item.__dict__ for item in list_scripts(db)]}


@router.get("/evidence")
def get_evidence(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return {"code": 0, "message": "ok", "data": [item.__dict__ for item in list_evidence(db)]}


@router.post("/cases")
def create_case_route(payload: CaseIn, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="权限不足")
    return {"code": 0, "message": "ok", "data": create_case(db, payload.model_dump()).model_dump()}


@router.post("/scripts")
def create_script_route(payload: ScriptIn, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="权限不足")
    return {"code": 0, "message": "ok", "data": create_script(db, payload.model_dump()).model_dump()}
