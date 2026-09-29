"""LLM 调用适配层：统一封装生成与联网搜索，并记录调用观测日志。"""
import json
import logging
import os
import time
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

LLM_BASE_URL = os.getenv("LLM_BASE_URL", settings.LLM_BASE_URL)
LLM_API_KEY = os.getenv("LLM_API_KEY", settings.LLM_API_KEY)
LLM_MODEL = os.getenv("LLM_MODEL", settings.LLM_MODEL)
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", settings.LLM_TIMEOUT))
LLM_SEARCH_PAYLOAD = os.getenv("LLM_SEARCH_PAYLOAD", settings.LLM_SEARCH_PAYLOAD)
LLM_EMBEDDING_MODEL = os.getenv("LLM_EMBEDDING_MODEL", settings.LLM_EMBEDDING_MODEL)


def _record_call(*, scene: str, model: Optional[str], success: bool, degraded: bool,
                 degrade_reason: Optional[str], latency_ms: Optional[int],
                 prompt_tokens: Optional[int] = None, completion_tokens: Optional[int] = None,
                 error: Optional[str] = None) -> None:
    """落库 LLM 调用观测；观测写入失败只打日志，绝不影响业务调用"""
    try:
        from datetime import datetime

        from app.db.session import SessionLocal
        from app.models.llm_log import LLMCallLog

        db = SessionLocal()
        try:
            db.add(LLMCallLog(
                scene=(scene or "unknown")[:20], model=model, success=success,
                degraded=degraded, degrade_reason=degrade_reason,
                prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
                latency_ms=latency_ms, error=(error or None) and str(error)[:255],
                created_at=datetime.utcnow(),
            ))
            db.commit()
        finally:
            db.close()
    except Exception as log_exc:  # pragma: no cover - 观测兜底，无法覆盖所有 DB 故障
        logger.warning("llm call log write failed: %s", log_exc)


def generate_text(prompt: str, system: Optional[str] = None, extra_payload: Optional[dict] = None,
                  scene: Optional[str] = None) -> str:
    headers = {"content-type": "application/json"}
    if LLM_API_KEY:
        headers["authorization"] = f"Bearer {LLM_API_KEY}"
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = {"model": LLM_MODEL, "messages": messages, "temperature": 0.4}
    if extra_payload:
        payload.update(extra_payload)
    started = time.monotonic()
    try:
        with httpx.Client(timeout=LLM_TIMEOUT) as client:
            resp = client.post(f"{LLM_BASE_URL}/v1/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            usage = data.get("usage") or {}
            _record_call(scene=scene, model=LLM_MODEL, success=True, degraded=False,
                         degrade_reason=None, latency_ms=int((time.monotonic() - started) * 1000),
                         prompt_tokens=usage.get("prompt_tokens"),
                         completion_tokens=usage.get("completion_tokens"))
            return data["choices"][0]["message"]["content"]
    except Exception as exc:
        if not LLM_API_KEY:
            _record_call(scene=scene, model=LLM_MODEL, success=False, degraded=True,
                         degrade_reason="no_api_key", latency_ms=int((time.monotonic() - started) * 1000),
                         error=exc)
            return "[LLM模拟] 未配置 LLM_API_KEY，以下为规则引擎生成的建议。"
        _record_call(scene=scene, model=LLM_MODEL, success=False, degraded=True,
                     degrade_reason="request_error", latency_ms=int((time.monotonic() - started) * 1000),
                     error=exc)
        raise exc


def call_llm_with_search(prompt: str, system: Optional[str] = None, scene: Optional[str] = None) -> str:
    """带联网能力的生成：LLM_SEARCH_PAYLOAD 未配置时降级为普通生成"""
    extra: dict = {}
    if LLM_SEARCH_PAYLOAD:
        try:
            extra = json.loads(LLM_SEARCH_PAYLOAD)
        except Exception:
            extra = {}
        if not isinstance(extra, dict):
            extra = {}
    return generate_text(prompt, system=system, extra_payload=extra or None, scene=scene)
