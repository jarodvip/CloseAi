# backend/tests/test_llm_search_adapter.py
from app.core.domain.services import llm_service


class _FakeResp:
    def raise_for_status(self):
        pass

    def json(self):
        return {"choices": [{"message": {"content": "联网结果"}}]}


class _FakeClient:
    """捕获请求体的假 httpx.Client"""

    last_payload = {}

    def __init__(self, *a, **kw):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def post(self, url, json=None, headers=None):
        _FakeClient.last_payload = json
        return _FakeResp()


def test_extra_payload_merged(monkeypatch):
    monkeypatch.setattr(llm_service.httpx, "Client", _FakeClient)
    out = llm_service.generate_text("你好", extra_payload={"tools": [{"type": "web_search"}]})
    assert out == "联网结果"
    assert _FakeClient.last_payload["tools"] == [{"type": "web_search"}]


def test_call_llm_with_search_reads_config(monkeypatch):
    monkeypatch.setattr(llm_service.httpx, "Client", _FakeClient)
    monkeypatch.setattr(llm_service, "LLM_SEARCH_PAYLOAD", '{"enable_search": true}')
    out = llm_service.call_llm_with_search("调研喜茶")
    assert out == "联网结果"
    assert _FakeClient.last_payload["enable_search"] is True


def test_call_llm_without_config_falls_back(monkeypatch):
    # 未配置联网参数时应等价于普通调用，不抛错
    monkeypatch.setattr(llm_service, "LLM_SEARCH_PAYLOAD", "")
    monkeypatch.setattr(llm_service, "generate_text", lambda *a, **k: "plain")
    assert llm_service.call_llm_with_search("q") == "plain"


def test_call_llm_with_invalid_json_falls_back(monkeypatch):
    # 非法 JSON 应降级为普通生成，不抛错、不带任何扩展字段
    monkeypatch.setattr(llm_service.httpx, "Client", _FakeClient)
    monkeypatch.setattr(llm_service, "LLM_SEARCH_PAYLOAD", '{"enable_search":')
    out = llm_service.call_llm_with_search("q")
    assert out == "联网结果"
    assert "enable_search" not in _FakeClient.last_payload


def test_call_llm_with_non_dict_json_falls_back(monkeypatch):
    # 合法但非对象的 JSON（如 true）同样应降级，不抛错、请求体只有基础字段
    monkeypatch.setattr(llm_service.httpx, "Client", _FakeClient)
    monkeypatch.setattr(llm_service, "LLM_SEARCH_PAYLOAD", "true")
    out = llm_service.call_llm_with_search("q")
    assert out == "联网结果"
    assert set(_FakeClient.last_payload.keys()) == {"model", "messages", "temperature"}
