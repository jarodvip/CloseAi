"""Embedding 适配层：OpenAI 兼容 /v1/embeddings 接口，供混合检索使用。

无 key / 接口失败时返回 None，调用方自动退回 FTS 检索，行为与升级前一致。
"""
import logging
import math
import os
import struct
import time
from typing import List, Optional, Sequence

import httpx

from app.core.config import settings
from app.core.domain.services import llm_service

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = os.getenv("LLM_EMBEDDING_MODEL", settings.LLM_EMBEDDING_MODEL)


def _embedding_configured() -> bool:
    """未配置 key 且仍指向默认 openai.com 时视为不可用：
    避免每次入库/检索都白等一次注定失败的网络请求；自建/内部接口不受影响"""
    if not llm_service.LLM_API_KEY and "api.openai.com" in (llm_service.LLM_BASE_URL or ""):
        return False
    return True


def embed_texts(texts: Sequence[str]) -> Optional[List[List[float]]]:
    """批量向量化；任何失败返回 None（调用方降级），不抛异常"""
    if not _embedding_configured():
        return None
    texts = [t for t in texts if t and t.strip()]
    if not texts:
        return None
    headers = {"content-type": "application/json"}
    if llm_service.LLM_API_KEY:
        headers["authorization"] = f"Bearer {llm_service.LLM_API_KEY}"
    started = time.monotonic()
    try:
        with httpx.Client(timeout=llm_service.LLM_TIMEOUT) as client:
            resp = client.post(
                f"{llm_service.LLM_BASE_URL}/v1/embeddings",
                json={"model": EMBEDDING_MODEL, "input": list(texts)},
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            usage = data.get("usage") or {}
            vectors = [item["embedding"] for item in data["data"]]
            llm_service._record_call(
                scene="embedding", model=EMBEDDING_MODEL, success=True, degraded=False,
                degrade_reason=None, latency_ms=int((time.monotonic() - started) * 1000),
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("total_tokens"),
            )
            return vectors
    except Exception as exc:
        llm_service._record_call(
            scene="embedding", model=EMBEDDING_MODEL, success=False, degraded=True,
            degrade_reason="request_error",
            latency_ms=int((time.monotonic() - started) * 1000), error=exc,
        )
        return None


def embed_query(text: str) -> Optional[List[float]]:
    if not text or not text.strip():
        return None
    vectors = embed_texts([text])
    return vectors[0] if vectors else None


def to_blob(vector: Sequence[float]) -> bytes:
    return struct.pack(f"<{len(vector)}f", *vector)


def from_blob(blob: bytes) -> List[float]:
    if not blob:
        return []
    n = len(blob) // 4
    return list(struct.unpack(f"<{n}f", blob))


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
