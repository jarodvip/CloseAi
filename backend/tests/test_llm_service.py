"""LLM 服务单元测试：覆盖正常调用、空 key 降级、异常传播、联网参数。"""
import json

import pytest
import httpx

from app.core.domain.services.llm_service import (
    generate_text,
    call_llm_with_search,
)


class _FakeResp:
    def __init__(self, json_data):
        self._json = json_data

    def raise_for_status(self):
        pass

    def json(self):
        return self._json


# ---------------------------------------------------------------------------
# 正常调用
# ---------------------------------------------------------------------------
def test_generate_text_returns_content(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "fake-key")

    import app.core.domain.services.llm_service as llm_mod
    monkeypatch.setattr(llm_mod, "LLM_API_KEY", "fake-key")
    monkeypatch.setattr(llm_mod, "LLM_MODEL", "test-model")

    captured = {}

    def fake_post(self, url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["payload"] = json
        return _FakeResp({
            "choices": [{"message": {"content": "增强后的内容"}}]
        })

    monkeypatch.setattr(llm_mod.httpx.Client, "post", fake_post)

    result = generate_text("用户提问", system="你是助手")
    assert result == "增强后的内容"
    assert captured["payload"]["model"] == "test-model"
    assert captured["payload"]["messages"][0]["role"] == "system"
    assert captured["payload"]["messages"][1]["role"] == "user"


def test_generate_text_no_key_returns_mock(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)

    import app.core.domain.services.llm_service as llm_mod
    monkeypatch.setattr(llm_mod, "LLM_API_KEY", "")
    monkeypatch.setattr(llm_mod, "LLM_BASE_URL", "https://api.openai.com")

    result = generate_text("测试 prompt")
    assert "[LLM模拟]" in result


def test_generate_text_network_error_no_key(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.openai.com")

    import app.core.domain.services.llm_service as llm_mod
    monkeypatch.setattr(llm_mod, "LLM_API_KEY", "")

    result = generate_text("测试 prompt")
    assert "[LLM模拟]" in result


def test_generate_text_network_error_with_key_raises(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "real-key")

    import app.core.domain.services.llm_service as llm_mod
    monkeypatch.setattr(llm_mod, "LLM_API_KEY", "real-key")

    def fake_post(self, url, json=None, headers=None, timeout=None):
        raise httpx.ConnectError("connection failed")

    monkeypatch.setattr(llm_mod.httpx.Client, "post", fake_post)

    with pytest.raises(httpx.ConnectError):
        generate_text("测试 prompt")


def test_generate_text_malformed_response(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "fake-key")

    import app.core.domain.services.llm_service as llm_mod
    monkeypatch.setattr(llm_mod, "LLM_API_KEY", "fake-key")

    def fake_post(self, url, json=None, headers=None, timeout=None):
        return _FakeResp({"choices": []})

    monkeypatch.setattr(llm_mod.httpx.Client, "post", fake_post)

    with pytest.raises(IndexError):
        generate_text("测试 prompt")


# ---------------------------------------------------------------------------
# 联网搜索
# ---------------------------------------------------------------------------
def test_call_llm_with_search_no_payload(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "fake-key")
    monkeypatch.setenv("LLM_SEARCH_PAYLOAD", "")

    import app.core.domain.services.llm_service as llm_mod
    monkeypatch.setattr(llm_mod, "LLM_API_KEY", "fake-key")
    monkeypatch.setattr(llm_mod, "LLM_SEARCH_PAYLOAD", "")

    def fake_post(self, url, json=None, headers=None, timeout=None):
        return _FakeResp({"choices": [{"message": {"content": "搜索结果"}}]})

    monkeypatch.setattr(llm_mod.httpx.Client, "post", fake_post)

    result = call_llm_with_search("搜索一下")
    assert result == "搜索结果"


def test_call_llm_with_search_with_payload(monkeypatch):
    search_payload = {"web_search": {"enable": True}}
    monkeypatch.setenv("LLM_API_KEY", "fake-key")
    monkeypatch.setenv("LLM_SEARCH_PAYLOAD", json.dumps(search_payload))

    import app.core.domain.services.llm_service as llm_mod
    monkeypatch.setattr(llm_mod, "LLM_API_KEY", "fake-key")
    monkeypatch.setattr(llm_mod, "LLM_SEARCH_PAYLOAD", json.dumps(search_payload))

    captured = {}

    def fake_post(self, url, json=None, headers=None, timeout=None):
        captured["payload"] = json
        return _FakeResp({"choices": [{"message": {"content": "联网结果"}}]})

    monkeypatch.setattr(llm_mod.httpx.Client, "post", fake_post)

    result = call_llm_with_search("搜索一下")
    assert result == "联网结果"
    assert captured["payload"].get("web_search") == {"enable": True}


def test_call_llm_with_search_invalid_json_payload(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "fake-key")
    monkeypatch.setenv("LLM_SEARCH_PAYLOAD", "not-json")

    import app.core.domain.services.llm_service as llm_mod
    monkeypatch.setattr(llm_mod, "LLM_API_KEY", "fake-key")
    monkeypatch.setattr(llm_mod, "LLM_SEARCH_PAYLOAD", "not-json")

    def fake_post(self, url, json=None, headers=None, timeout=None):
        return _FakeResp({"choices": [{"message": {"content": "降级结果"}}]})

    monkeypatch.setattr(llm_mod.httpx.Client, "post", fake_post)

    result = call_llm_with_search("搜索一下")
    assert result == "降级结果"


def test_call_llm_with_search_non_dict_json(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "fake-key")
    monkeypatch.setenv("LLM_SEARCH_PAYLOAD", "true")

    import app.core.domain.services.llm_service as llm_mod
    monkeypatch.setattr(llm_mod, "LLM_API_KEY", "fake-key")
    monkeypatch.setattr(llm_mod, "LLM_SEARCH_PAYLOAD", "true")

    def fake_post(self, url, json=None, headers=None, timeout=None):
        return _FakeResp({"choices": [{"message": {"content": "降级结果"}}]})

    monkeypatch.setattr(llm_mod.httpx.Client, "post", fake_post)

    result = call_llm_with_search("搜索一下")
    assert result == "降级结果"


# ---------------------------------------------------------------------------
# 环境变量覆盖
# ---------------------------------------------------------------------------
def test_generate_text_uses_env_overrides(monkeypatch):
    import app.core.domain.services.llm_service as llm_mod
    monkeypatch.setattr(llm_mod, "LLM_API_KEY", "env-key")
    monkeypatch.setattr(llm_mod, "LLM_BASE_URL", "https://custom.example.com")
    monkeypatch.setattr(llm_mod, "LLM_MODEL", "custom-model")
    monkeypatch.setattr(llm_mod, "LLM_TIMEOUT", 60)

    captured = {}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            captured["client_kwargs"] = kwargs

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, json=None, headers=None, timeout=None):
            captured["url"] = url
            captured["timeout"] = timeout
            return _FakeResp({"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr(llm_mod.httpx, "Client", FakeClient)

    result = generate_text("test")
    assert result == "ok"
    assert captured["url"] == "https://custom.example.com/v1/chat/completions"
    assert captured["client_kwargs"]["timeout"] == 60