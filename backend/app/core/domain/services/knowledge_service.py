from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.knowledge import CustomerTypeKnowledge, Case, Script, Evidence
from fastapi import HTTPException


def list_customer_types(db: Session) -> List[CustomerTypeKnowledge]:
    return db.query(CustomerTypeKnowledge).order_by(CustomerTypeKnowledge.id.asc()).all()


def get_customer_type_by_code(db: Session, code: str) -> Optional[CustomerTypeKnowledge]:
    return db.query(CustomerTypeKnowledge).filter(CustomerTypeKnowledge.code == code).first()


def list_cases(db: Session, query: str = "") -> List[Case]:
    q = db.query(Case)
    if query:
        like = f"%{query}%"
        q = q.filter((Case.title.ilike(like)) | (Case.type.ilike(like)) | (Case.industry.ilike(like)))
    return q.order_by(Case.id.asc()).all()


def list_scripts(db: Session) -> List[Script]:
    return db.query(Script).order_by(Script.id.asc()).all()


def list_evidence(db: Session) -> List[Evidence]:
    return db.query(Evidence).order_by(Evidence.id.asc()).all()


def create_case(db: Session, payload: dict) -> Case:
    record = Case(**payload)
    db.add(record)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="案例编码已存在") from exc
    db.refresh(record)
    return record


def create_script(db: Session, payload: dict) -> Script:
    record = Script(**payload)
    db.add(record)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="话术已存在") from exc
    db.refresh(record)
    return record
