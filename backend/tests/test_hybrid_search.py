# backend/tests/test_hybrid_search.py
"""混合检索：FTS + 向量 RRF 融合、embedding 不可用降级、入库向量化回填。"""
import pytest
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core.domain.services import embedding_service, research_service
from app.core.domain.services.research_service import (
    delete_chunk,
    ensure_fts,
    ingest_text,
    search_research,
)

MARKER = "混合检索_隔离标记_8x3"
INDUSTRY = "融合隔离业"


def _db() -> Session:
    return SessionLocal()


# ── 单元：向量工具 ──

def test_blob_roundtrip_and_cosine():
    vec = [0.5, -1.25, 2.0, 0.0]
    blob = embedding_service.to_blob(vec)
    assert embedding_service.from_blob(blob) == pytest.approx(vec)
    assert embedding_service.cosine([1, 0], [1, 0]) == pytest.approx(1.0)
    assert embedding_service.cosine([1, 0], [0, 1]) == pytest.approx(0.0)
    assert embedding_service.cosine([1, 0], []) == 0.0
    assert embedding_service.from_blob(b"") == []


def test_embed_texts_unavailable_without_key(monkeypatch):
    """无 key 且指向默认 openai.com：直接判定不可用，不发网络请求"""
    monkeypatch.setattr(embedding_service.llm_service, "LLM_API_KEY", "")
    monkeypatch.setattr(embedding_service.llm_service, "LLM_BASE_URL", "https://api.openai.com")
    assert embedding_service.embed_texts(["测试"]) is None
    assert embedding_service.embed_query("测试") is None


def test_embed_texts_returns_none_on_error(monkeypatch):
    monkeypatch.setattr(embedding_service.llm_service, "LLM_API_KEY", "fake-key")

    class _Boom:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, *a, **kw):
            raise RuntimeError("接口挂了")

    monkeypatch.setattr(embedding_service.httpx, "Client", _Boom)
    assert embedding_service.embed_texts(["测试"]) is None


# ── 入库向量化回填 ──

def test_ingest_backfills_embedding(monkeypatch):
    db = _db()
    try:
        ensure_fts(db)
        monkeypatch.setattr(embedding_service, "embed_texts",
                            lambda texts: [[1.0, 0.0] for _ in texts])
        made = ingest_text(db, f"{MARKER} 向量化回填内容", source_type="doc",
                           title=f"{MARKER}_回填", industry=INDUSTRY)
        assert made[0].embedding is not None
        assert embedding_service.from_blob(made[0].embedding) == pytest.approx([1.0, 0.0])
        delete_chunk(db, made[0].id)
    finally:
        db.close()


def test_ingest_survives_embedding_failure(monkeypatch):
    db = _db()
    try:
        ensure_fts(db)
        monkeypatch.setattr(embedding_service, "embed_texts", lambda texts: None)
        made = ingest_text(db, f"{MARKER} 向量化失败仍入库", source_type="doc",
                           title=f"{MARKER}_失败", industry=INDUSTRY)
        assert len(made) == 1
        assert made[0].embedding is None
        delete_chunk(db, made[0].id)
    finally:
        db.close()


# ── 混合检索与降级 ──

def test_vector_hit_joins_fts_results(monkeypatch):
    """向量召回能带回 FTS 完全命不中的语义相关块；embedding 不可用时行为与纯 FTS 一致"""
    db = _db()
    chunk_a = chunk_b = None
    try:
        ensure_fts(db)
        vectors = {"a": [1.0, 0.0], "b": [0.0, 1.0]}

        def fake_embed_for_ingest(texts):
            return [vectors["a"] if "增长" in t else vectors["b"] for t in texts]

        monkeypatch.setattr(embedding_service, "embed_texts", fake_embed_for_ingest)
        chunk_a = ingest_text(db, f"{MARKER} 奶茶 品牌增长打法核心论述", source_type="doc",
                              title=f"{MARKER}_a", industry=INDUSTRY)[0]
        chunk_b = ingest_text(db, f"{MARKER} 完全无关词汇量子蛙跳", source_type="doc",
                              title=f"{MARKER}_b", industry=INDUSTRY)[0]

        # 查询向量贴近 b：FTS 只命中 a，向量只命中 b，融合后两者都应出现
        monkeypatch.setattr(embedding_service, "embed_query", lambda text: [0.0, 1.0])
        hits = search_research(db, "奶茶 品牌", industry=INDUSTRY, k=5)
        hit_ids = {h.id for h in hits}
        assert chunk_a.id in hit_ids
        assert chunk_b.id in hit_ids

        # embedding 不可用（embed_query → None）：退回纯 FTS，只返回 a
        monkeypatch.setattr(embedding_service, "embed_query", lambda text: None)
        hits = search_research(db, "奶茶 品牌", industry=INDUSTRY, k=5)
        assert [h.id for h in hits] == [chunk_a.id]
    finally:
        for c in (chunk_a, chunk_b):
            if c is not None:
                delete_chunk(db, c.id)
        db.close()


def test_rrf_prefers_chunks_hit_by_both_paths(monkeypatch):
    """两路都命中的块在融合排序中应优于单路命中的块"""
    db = _db()
    chunk_both = chunk_vec_only = None
    try:
        ensure_fts(db)

        def fake_embed_for_ingest(texts):
            return [[1.0, 0.0] for _ in texts]

        monkeypatch.setattr(embedding_service, "embed_texts", fake_embed_for_ingest)
        chunk_both = ingest_text(db, f"{MARKER} 奶茶 品牌双路命中内容", source_type="doc",
                                 title=f"{MARKER}_双路", industry=INDUSTRY)[0]
        chunk_vec_only = ingest_text(db, f"{MARKER} 无关键词语义相似块", source_type="doc",
                                     title=f"{MARKER}_仅向量", industry=INDUSTRY)[0]

        monkeypatch.setattr(embedding_service, "embed_query", lambda text: [1.0, 0.0])
        hits = search_research(db, "奶茶 品牌", industry=INDUSTRY, k=5)
        assert hits[0].id == chunk_both.id
        assert {chunk_vec_only.id} <= {h.id for h in hits}
    finally:
        for c in (chunk_both, chunk_vec_only):
            if c is not None:
                delete_chunk(db, c.id)
        db.close()


def test_ilike_fallback_path_unaffected(monkeypatch):
    """FTS 关闭（ILIKE 兜底）路径不做向量融合，行为与升级前一致"""
    db = _db()
    chunk = None
    try:
        ensure_fts(db)
        chunk = ingest_text(db, f"{MARKER} 奶茶 兜底路径内容", source_type="doc",
                            title=f"{MARKER}_兜底", industry=INDUSTRY)[0]
        monkeypatch.setattr(research_service, "_fts_enabled", lambda d: False)
        monkeypatch.setattr(embedding_service, "embed_query", lambda text: [1.0, 0.0])
        hits = search_research(db, "奶茶", industry=INDUSTRY, k=5)
        assert chunk.id in {h.id for h in hits}
    finally:
        monkeypatch.undo()
        if chunk is not None:
            delete_chunk(db, chunk.id)
        db.close()
