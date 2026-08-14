from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import distinct
from app.core.domain.services.knowledge_service import list_customer_types, list_cases, list_scripts, list_evidence, create_case, create_script
from app.schemas.knowledge_admin import CaseIn, ScriptIn
from app.core.deps import get_db, get_current_user, require_admin
from app.models.knowledge import Case, Script

router = APIRouter()


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


@router.get("/options")
def get_options(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    industries = [row[0] for row in db.query(distinct(Case.industry)).filter(Case.industry.isnot(None), Case.industry != "").order_by(Case.industry.asc()).all() if row[0]]
    stages = [row[0] for row in db.query(distinct(Case.stage)).filter(Case.stage.isnot(None), Case.stage != "").order_by(Case.stage.asc()).all() if row[0]]
    scenes = [row[0] for row in db.query(distinct(Script.scene)).filter(Script.scene.isnot(None), Script.scene != "").order_by(Script.scene.asc()).all() if row[0]]
    customer_types = [{"code": t.code, "name": t.name} for t in list_customer_types(db)]
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "industries": industries,
            "stages": stages,
            "customer_types": customer_types,
            "scenes": scenes,
            "decisions": ["确定合作", "暂缓", "需再评估", "指定负责人", "明确预算"],
            "actions": ["发方案", "约下次会议", "内部评审", "报价", "寄样品"],
        },
    }


@router.post("/cases")
def create_case_route(payload: CaseIn, db: Session = Depends(get_db), user: dict = Depends(require_admin)):
    return {"code": 0, "message": "ok", "data": create_case(db, payload.model_dump()).model_dump()}


@router.post("/scripts")
def create_script_route(payload: ScriptIn, db: Session = Depends(get_db), user: dict = Depends(require_admin)):
    return {"code": 0, "message": "ok", "data": create_script(db, payload.model_dump()).model_dump()}
