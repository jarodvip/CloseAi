from typing import Optional
import os
import json

from app.core.config import settings
import httpx


LLM_BASE_URL = os.getenv("LLM_BASE_URL", settings.LLM_BASE_URL)
LLM_API_KEY = os.getenv("LLM_API_KEY", settings.LLM_API_KEY)
LLM_MODEL = os.getenv("LLM_MODEL", settings.LLM_MODEL)
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", settings.LLM_TIMEOUT))
LLM_SEARCH_PAYLOAD = os.getenv("LLM_SEARCH_PAYLOAD", settings.LLM_SEARCH_PAYLOAD)


def generate_text(prompt: str, system: Optional[str] = None, extra_payload: Optional[dict] = None) -> str:
    headers = {"content-type": "application/json"}
    if LLM_API_KEY:
        headers["authorization"] = f"Bearer {LLM_API_KEY}"
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = {"model": LLM_MODEL, "messages": messages, "temperature": 0.4}
    if extra_payload:
        payload.update(extra_payload)  # 联网参数等扩展项整体并入
    try:
        with httpx.Client(timeout=LLM_TIMEOUT) as client:
            resp = client.post(f"{LLM_BASE_URL}/v1/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except Exception as exc:
        if not LLM_API_KEY:
            return f"[LLM模拟回复] {prompt[:120]}...（未配置 LLM_API_KEY）"
        raise exc


def call_llm_with_search(prompt: str, system: Optional[str] = None) -> str:
    """带联网能力的生成：LLM_SEARCH_PAYLOAD 未配置时降级为普通生成"""
    extra: dict = {}
    if LLM_SEARCH_PAYLOAD:
        try:
            extra = json.loads(LLM_SEARCH_PAYLOAD)
        except Exception:
            extra = {}
    return generate_text(prompt, system=system, extra_payload=extra or None)
