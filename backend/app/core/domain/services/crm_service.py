"""CRM 集成（v1.0）：通用 webhook 推送跟进包。

不绑定具体 CRM：配置 CRM_WEBHOOK_URL 后，跟进包以 JSON POST 到该地址，
约定负载形如 {customer_id, customer_name, summary, tasks, email, wechat, pushed_by}。
推送结果落 crm_push_logs；webhook 未配置/失败不影响跟进包主流程。
"""
import logging
from datetime import datetime
from typing import Dict, Optional

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.crm import CrmPushLog

logger = logging.getLogger(__name__)


def crm_webhook_enabled() -> bool:
    return bool(settings.CRM_WEBHOOK_URL.strip())


def push_followup(db: Session, *, username: str, customer_id: int, customer_name: str,
                  payload: Dict) -> Dict:
    """推送跟进包到 CRM webhook。返回 {success, http_status, error}"""
    body = {
        "customer_id": customer_id,
        "customer_name": customer_name,
        "summary": payload.get("summary") or "",
        "tasks": payload.get("tasks") or [],
        "email": payload.get("email") or "",
        "wechat": payload.get("wechat") or "",
        "decisions": payload.get("decisions") or [],
        "pending_actions": payload.get("pending_actions") or [],
        "pushed_by": username,
        "pushed_at": datetime.utcnow().isoformat(timespec="seconds"),
    }
    success, http_status, error = False, None, None
    try:
        resp = httpx.post(settings.CRM_WEBHOOK_URL.strip(), json=body, timeout=10,
                          headers={"content-type": "application/json"})
        http_status = resp.status_code
        resp.raise_for_status()
        success = True
    except Exception as exc:
        error = str(exc)[:255]
        logger.warning("CRM 推送失败 customer_id=%s: %s", customer_id, error)

    try:
        db.add(CrmPushLog(
            username=username, customer_id=customer_id, customer_name=customer_name,
            success=success, http_status=http_status, error=error,
            payload_summary=(body.get("summary") or "")[:500],
            created_at=datetime.utcnow(),
        ))
        db.commit()
    except Exception as log_exc:  # 日志失败不影响推送结果返回
        logger.warning("crm push log 写入失败: %s", log_exc)
        db.rollback()

    return {"success": success, "http_status": http_status, "error": error}
