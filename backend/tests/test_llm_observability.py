# backend/tests/test_llm_observability.py
"""LLM 调用观测：成功/降级均落库 llm_call_logs，且观测失败不影响业务。"""
import httpx
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.llm_log import LLMCallLog
from app.core.domain.services import llm_service
from app.core.domain.services.llm_service import generate_text

MARKER = "obs_9x7"  # ≤20 字符：_record_call 会按列宽截断 scene


class _FakeResp:
    def __init__(self, json_data):
        self._json = json_data

    def raise_for_status(self):
        pass

    def json(self):
        return self._json


def _latest_log(db: Session, scene: str) -> LLMCallLog:
    return (db.query(LLMCallLog)
            .filter(LLMCallLog.scene == scene)
            .order_by(LLMCallLog.id.desc())
            .first())


def _cleanup(db: Session, log_id):
    if log_id:
        row = db.query(LLMCallLog).filter(LLMCallLog.id == log_id).first()
        if row:
            db.delete(row)
            db.commit()


def test_success_call_logged_with_usage(monkeypatch):
    monkeypatch.setattr(llm_service, "LLM_API_KEY", "fake-key")
    monkeypatch.setattr(llm_service.httpx.Client, "post", lambda self, url, json=None, headers=None, timeout=None: _FakeResp({
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7},
    }))
    db = SessionLocal()
    log_id = None
    try:
        result = generate_text("prompt", scene=MARKER)
        assert result == "ok"
        log = _latest_log(db, MARKER)
        assert log is not None
        log_id = log.id
        assert log.success is True
        assert log.degraded is False
        assert log.prompt_tokens == 11
        assert log.completion_tokens == 7
        assert log.latency_ms is not None
    finally:
        _cleanup(db, log_id)
        db.close()


def test_no_key_degrade_logged(monkeypatch):
    monkeypatch.setattr(llm_service, "LLM_API_KEY", "")
    monkeypatch.setattr(llm_service, "LLM_BASE_URL", "https://api.openai.com")

    def fake_post(self, url, json=None, headers=None, timeout=None):
        raise httpx.ConnectError("no network")

    monkeypatch.setattr(llm_service.httpx.Client, "post", fake_post)
    db = SessionLocal()
    log_id = None
    try:
        result = generate_text("prompt", scene=MARKER)
        assert "[LLM模拟]" in result
        log = _latest_log(db, MARKER)
        assert log is not None
        log_id = log.id
        assert log.success is False
        assert log.degraded is True
        assert log.degrade_reason == "no_api_key"
    finally:
        _cleanup(db, log_id)
        db.close()


def test_request_error_with_key_logged_and_raised(monkeypatch):
    monkeypatch.setattr(llm_service, "LLM_API_KEY", "real-key")

    def fake_post(self, url, json=None, headers=None, timeout=None):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(llm_service.httpx.Client, "post", fake_post)
    db = SessionLocal()
    log_id = None
    try:
        try:
            generate_text("prompt", scene=MARKER)
            raised = False
        except httpx.ConnectError:
            raised = True
        assert raised
        log = _latest_log(db, MARKER)
        assert log is not None
        log_id = log.id
        assert log.degrade_reason == "request_error"
        assert "boom" in (log.error or "")
    finally:
        _cleanup(db, log_id)
        db.close()


def test_scene_passed_by_services(monkeypatch):
    """各业务 service 调用都带 scene 标识，观测可按场景聚合"""
    monkeypatch.setattr(llm_service, "LLM_API_KEY", "fake-key")
    monkeypatch.setattr(llm_service.httpx.Client, "post",
                        lambda self, url, json=None, headers=None, timeout=None: (_ for _ in ()).throw(httpx.ConnectError("x")))

    from app.core.domain.services.research_service import run_backdossier

    class FakeCustomer:
        id = 1
        name = "观测客户"
        industry = "测试"

    db = SessionLocal()
    log_id = None
    try:
        # 背调走 call_llm_with_search(scene="research")：请求失败时降级返回空报告，不抛错
        assert run_backdossier(db, FakeCustomer()) == []
        log = _latest_log(db, "research")
        assert log is not None
        log_id = log.id
        assert log.degraded is True
    finally:
        _cleanup(db, log_id)
        db.close()
