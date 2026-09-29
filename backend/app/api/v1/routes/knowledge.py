from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import distinct
from app.core.domain.services.knowledge_service import (
    list_customer_types, list_cases, list_scripts, list_evidence, create_case, create_script,
    list_suggestions, approve_suggestion, reject_suggestion, suggestion_dict,
    set_case_shared, set_script_shared,
)
from app.schemas.knowledge_admin import CaseIn, ScriptIn, SuggestionEditIn, SuggestionRejectIn
from app.core.deps import get_db, get_current_user, require_admin, require_user
from app.models.knowledge import Case, Script

router = APIRouter()


@router.get("/customer-types")
def get_customer_types(db: Session = Depends(get_db), user: dict = Depends(require_user)):
    return {"code": 0, "message": "ok", "data": [item.__dict__ for item in list_customer_types(db)]}


@router.get("/cases")
def get_cases(query: str = "", db: Session = Depends(get_db), user: dict = Depends(require_user)):
    return {"code": 0, "message": "ok",
            "data": [item.__dict__ for item in list_cases(db, query, user["username"], user.get("role"))]}


@router.get("/scripts")
def get_scripts(db: Session = Depends(get_db), user: dict = Depends(require_user)):
    return {"code": 0, "message": "ok",
            "data": [item.__dict__ for item in list_scripts(db, user["username"], user.get("role"))]}


@router.get("/evidence")
def get_evidence(db: Session = Depends(get_db), user: dict = Depends(require_user)):
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


# v1.0 团队知识共享：所有登录用户可创建知识；admin 创建自动共享，销售创建为个人条目
@router.post("/cases")
def create_case_route(payload: CaseIn, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    is_shared = user.get("role") == "admin"
    record = create_case(db, payload.model_dump(), owner=user["username"], is_shared=is_shared)
    return {"code": 0, "message": "ok", "data": record.__dict__}


@router.post("/scripts")
def create_script_route(payload: ScriptIn, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    is_shared = user.get("role") == "admin"
    record = create_script(db, payload.model_dump(), owner=user["username"], is_shared=is_shared)
    return {"code": 0, "message": "ok", "data": record.__dict__}


@router.patch("/cases/{case_id}/share")
def share_case_route(case_id: int, is_shared: bool, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    record = set_case_shared(db, case_id, is_shared, user["username"], user.get("role"))
    return {"code": 0, "message": "ok", "data": record.__dict__}


@router.patch("/scripts/{script_id}/share")
def share_script_route(script_id: int, is_shared: bool, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    record = set_script_shared(db, script_id, is_shared, user["username"], user.get("role"))
    return {"code": 0, "message": "ok", "data": record.__dict__}


# ── 知识沉淀建议审核流（admin） ──

@router.get("/suggestions")
def list_suggestions_route(status: str = "pending", db: Session = Depends(get_db), user: dict = Depends(require_admin)):
    return {"code": 0, "message": "ok", "data": [suggestion_dict(s) for s in list_suggestions(db, status or None)]}


@router.post("/suggestions/{suggestion_id}/approve")
def approve_suggestion_route(suggestion_id: int, payload: SuggestionEditIn | None = None,
                             db: Session = Depends(get_db), user: dict = Depends(require_admin)):
    edits = payload.model_dump(exclude_none=True) if payload else None
    record, knowledge = approve_suggestion(db, suggestion_id, edits, user["username"])
    return {"code": 0, "message": "ok",
            "data": {"suggestion": suggestion_dict(record),
                     "knowledge_id": getattr(knowledge, "id", None)}}


@router.post("/suggestions/{suggestion_id}/reject")
def reject_suggestion_route(suggestion_id: int, payload: SuggestionRejectIn | None = None,
                            db: Session = Depends(get_db), user: dict = Depends(require_admin)):
    record = reject_suggestion(db, suggestion_id, payload.note if payload else None, user["username"])
    return {"code": 0, "message": "ok", "data": suggestion_dict(record)}
