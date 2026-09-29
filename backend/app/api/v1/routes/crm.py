from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.domain.services import crm_service
from app.core.domain.services.customer_service import get_customer
from app.core.deps import get_db, require_user, assert_owner
from app.models.crm import CrmPushLog

router = APIRouter()


@router.get("/config")
def get_app_config(user: dict = Depends(require_user)):
    """前端功能开关：CRM webhook 是否已配置"""
    return {"code": 0, "message": "ok",
            "data": {"crm_webhook_enabled": crm_service.crm_webhook_enabled()}}


class CrmPushIn(BaseModel):
    summary: Optional[str] = None
    tasks: list = Field(default_factory=list)
    email: Optional[str] = None
    wechat: Optional[str] = None
    decisions: list = Field(default_factory=list)
    pending_actions: list = Field(default_factory=list)


@router.post("/customers/{customer_id}/crm-push")
def crm_push(customer_id: int, payload: CrmPushIn, db: Session = Depends(get_db),
             user: dict = Depends(require_user)):
    assert_owner(db, customer_id, user)
    customer = get_customer(db, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="customer not found")
    if not crm_service.crm_webhook_enabled():
        raise HTTPException(status_code=400, detail="未配置 CRM_WEBHOOK_URL，无法推送")
    result = crm_service.push_followup(
        db, username=user["username"], customer_id=customer_id,
        customer_name=customer.name, payload=payload.model_dump(),
    )
    if not result["success"]:
        raise HTTPException(status_code=502, detail=f"CRM 推送失败：{result['error'] or result['http_status']}")
    return {"code": 0, "message": "ok", "data": result}


@router.get("/crm/push-logs")
def crm_push_logs(db: Session = Depends(get_db), user: dict = Depends(require_user)):
    logs = (db.query(CrmPushLog)
            .order_by(CrmPushLog.id.desc())
            .limit(50).all())
    return {"code": 0, "message": "ok", "data": [{
        "id": l.id, "username": l.username, "customer_id": l.customer_id,
        "customer_name": l.customer_name, "success": bool(l.success),
        "http_status": l.http_status, "error": l.error,
        "created_at": l.created_at.isoformat() if l.created_at else None,
    } for l in logs]}
