from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy import or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.knowledge import CustomerTypeKnowledge, Case, Script, Evidence, KnowledgeSuggestion
from fastapi import HTTPException


def _visibility_filter(model, username: Optional[str], role: Optional[str]):
    """知识可见性：admin 全量；普通用户可见 共享项 + 本人创建项 + 全局种子(owner NULL)"""
    if role == "admin" or not username:
        return []
    return [or_(model.is_shared.is_(True),
                model.owner_username == username,
                model.owner_username.is_(None))]


def list_customer_types(db: Session) -> List[CustomerTypeKnowledge]:
    return db.query(CustomerTypeKnowledge).order_by(CustomerTypeKnowledge.id.asc()).all()


def get_customer_type_by_code(db: Session, code: str) -> Optional[CustomerTypeKnowledge]:
    return db.query(CustomerTypeKnowledge).filter(CustomerTypeKnowledge.code == code).first()


def list_cases(db: Session, query: str = "", username: Optional[str] = None,
               role: Optional[str] = None) -> List[Case]:
    q = db.query(Case)
    for cond in _visibility_filter(Case, username, role):
        q = q.filter(cond)
    if query:
        like = f"%{query}%"
        q = q.filter((Case.title.ilike(like)) | (Case.type.ilike(like)) | (Case.industry.ilike(like)))
    return q.order_by(Case.id.asc()).all()


def list_scripts(db: Session, username: Optional[str] = None, role: Optional[str] = None,
                 shared_only: bool = False) -> List[Script]:
    """shared_only=True 供简报/会中/会后检索池使用：个人未共享话术不进检索"""
    q = db.query(Script)
    if shared_only:
        q = q.filter(or_(Script.is_shared.is_(True), Script.owner_username.is_(None)))
    else:
        for cond in _visibility_filter(Script, username, role):
            q = q.filter(cond)
    return q.order_by(Script.id.asc()).all()


def list_evidence(db: Session) -> List[Evidence]:
    return db.query(Evidence).order_by(Evidence.id.asc()).all()


def create_case(db: Session, payload: dict, owner: Optional[str] = None,
                is_shared: bool = False) -> Case:
    record = Case(**payload, owner_username=owner, is_shared=is_shared)
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="案例编码已存在")
    db.refresh(record)
    return record


def create_script(db: Session, payload: dict, owner: Optional[str] = None,
                  is_shared: bool = False) -> Script:
    record = Script(**payload, owner_username=owner, is_shared=is_shared)
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="话术已存在")
    db.refresh(record)
    return record


def _get_shareable(db: Session, model, item_id: int, username: str, role: str):
    record = db.query(model).filter(model.id == item_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="条目不存在")
    if role != "admin" and record.owner_username != username:
        raise HTTPException(status_code=403, detail="仅创建者或管理员可修改共享状态")
    return record


def set_case_shared(db: Session, item_id: int, is_shared: bool, username: str, role: str) -> Case:
    record = _get_shareable(db, Case, item_id, username, role)
    record.is_shared = is_shared
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def set_script_shared(db: Session, item_id: int, is_shared: bool, username: str, role: str) -> Script:
    record = _get_shareable(db, Script, item_id, username, role)
    record.is_shared = is_shared
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ── 知识沉淀建议（会后生成 → admin 审核入库） ──

def suggestion_dict(s: KnowledgeSuggestion) -> Dict:
    return {
        "id": s.id,
        "customer_id": s.customer_id,
        "customer_name": s.customer_name,
        "username": s.username,
        "suggestion_type": s.suggestion_type,
        "scene": s.scene,
        "ktype": s.ktype,
        "title": s.title,
        "industry": s.industry,
        "content": s.content,
        "status": s.status,
        "note": s.note,
        "reviewed_by": s.reviewed_by,
        "reviewed_at": s.reviewed_at,
        "created_at": s.created_at,
    }


def create_suggestion(db: Session, payload: dict) -> KnowledgeSuggestion:
    content = (payload.get("content") or "").strip()
    if not content:
        raise HTTPException(status_code=422, detail="建议内容不能为空")
    record = KnowledgeSuggestion(
        customer_id=payload.get("customer_id"),
        customer_name=payload.get("customer_name"),
        username=payload.get("username"),
        suggestion_type=payload.get("suggestion_type") or "script",
        scene=payload.get("scene"),
        ktype=payload.get("ktype"),
        title=payload.get("title"),
        industry=payload.get("industry"),
        content=content,
        status="pending",
        created_at=datetime.utcnow().isoformat(timespec="seconds"),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_suggestions(db: Session, status: Optional[str] = None) -> List[KnowledgeSuggestion]:
    q = db.query(KnowledgeSuggestion)
    if status:
        q = q.filter(KnowledgeSuggestion.status == status)
    return q.order_by(KnowledgeSuggestion.id.desc()).limit(200).all()


def _get_pending(db: Session, suggestion_id: int) -> KnowledgeSuggestion:
    record = db.query(KnowledgeSuggestion).filter(KnowledgeSuggestion.id == suggestion_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="知识建议不存在")
    if record.status != "pending":
        raise HTTPException(status_code=409, detail=f"该建议已处理（{record.status}）")
    return record


def approve_suggestion(db: Session, suggestion_id: int, edits: Optional[dict], reviewer: str):
    """审核通过：应用编辑后写入对应知识表，建议标记 approved"""
    record = _get_pending(db, suggestion_id)
    edits = edits or {}
    content = (edits.get("content") or record.content or "").strip()
    if not content:
        raise HTTPException(status_code=422, detail="建议内容不能为空")
    scene = edits.get("scene", record.scene)
    ktype = edits.get("ktype", record.ktype)
    title = edits.get("title", record.title)
    industry = edits.get("industry", record.industry)
    source = f"会后沉淀·{record.customer_name}" if record.customer_name else "会后沉淀"

    stype = edits.get("suggestion_type", record.suggestion_type)
    if stype == "case":
        knowledge = create_case(db, {
            "code": f"CASE_{datetime.utcnow().strftime('%y%m%d%H%M%S')}_{record.id}",
            "title": title or (record.title or f"{record.customer_name or '客户'}案例"),
            "type": ktype,
            "industry": industry,
            "stage": None,
            "result": content,
            "source": source,
        })
    elif stype == "evidence":
        knowledge = Evidence(
            source=record.customer_name or "会后沉淀",
            metric=title or "待补充指标",
            value=content[:150],
            scene=scene,
            source_ref=source,
        )
        db.add(knowledge)
        db.commit()
        db.refresh(knowledge)
    else:
        knowledge = create_script(db, {
            "scene": scene or "异议应答",
            "type": ktype,
            "template": content,
            "source": source,
        })

    record.status = "approved"
    record.content = content
    record.scene, record.ktype, record.title, record.industry = scene, ktype, title, industry
    record.note = edits.get("note") or record.note
    record.reviewed_by = reviewer
    record.reviewed_at = datetime.utcnow().isoformat(timespec="seconds")
    db.add(record)
    db.commit()
    db.refresh(record)
    return record, knowledge


def reject_suggestion(db: Session, suggestion_id: int, reason: Optional[str], reviewer: str) -> KnowledgeSuggestion:
    record = _get_pending(db, suggestion_id)
    record.status = "rejected"
    record.note = reason or "未通过审核"
    record.reviewed_by = reviewer
    record.reviewed_at = datetime.utcnow().isoformat(timespec="seconds")
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
