from typing import Optional
import os
from typing import Optional

from app.core.config import settings
import httpx


LLM_BASE_URL = os.getenv("LLM_BASE_URL", settings.LLM_BASE_URL)
LLM_API_KEY = os.getenv("LLM_API_KEY", settings.LLM_API_KEY)
LLM_MODEL = os.getenv("LLM_MODEL", settings.LLM_MODEL)
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", settings.LLM_TIMEOUT))


def generate_text(prompt: str, system: Optional[str] = None) -> str:
    headers = {"content-type": "application/json"}
    if LLM_API_KEY:
        headers["authorization"] = f"Bearer {LLM_API_KEY}"
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = {"model": LLM_MODEL, "messages": messages, "temperature": 0.4}
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
