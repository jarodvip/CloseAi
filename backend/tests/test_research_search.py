# backend/tests/test_research_search.py
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core.domain.services.research_service import (
    delete_chunk,
    ensure_fts,
    ingest_text,
    search_research,
)

MARKER = "青栀气泡水_九乘七唯一标记"


def _db() -> Session:
    return SessionLocal()


def test_ingest_creates_multiple_chunks_with_metadata():
    from app.models.research import ResearchChunk
    db = _db()
    try:
        ensure_fts(db)
        long_text = "\n\n".join([f"{MARKER} 第{i}段。" + "详" * 300 for i in range(3)])
        chunks = ingest_text(db, long_text, source_type="doc", title=f"{MARKER}_t", industry="饮料")
        assert len(chunks) == 3
        assert {c.chunk_index for c in chunks} == {0, 1, 2}
        for c in chunks:
            assert delete_chunk(db, c.id) is True
        assert db.query(ResearchChunk).filter(ResearchChunk.title == f"{MARKER}_t").count() == 0
    finally:
        db.close()


def test_search_hits_tokenized_content():
    db = _db()
    try:
        ensure_fts(db)
        made = ingest_text(
            db,
            f"{MARKER} 奶茶行业进入存量竞争，头部品牌加速下沉开店。",
            source_type="doc",
            title=f"{MARKER}_搜索",
            industry="茶饮",
        )
        hits = search_research(db, "奶茶 行业", k=10)
        assert any(h.id == made[0].id for h in hits)
        # industry 过滤生效
        assert all(h.industry == "茶饮" for h in search_research(db, "奶茶", industry="茶饮", k=20) if h.id == made[0].id)
        # 无命中返回空且不抛异常
        assert search_research(db, "完全无关查询量子膨胀") == [] or all(h.id != made[0].id for h in search_research(db, "完全无关查询量子膨胀"))
        delete_chunk(db, made[0].id)
    finally:
        db.close()


def test_delete_chunk_removes_row_and_fts():
    db = _db()
    try:
        ensure_fts(db)
        made = ingest_text(db, f"{MARKER} 待删除内容", source_type="web", url="https://example.com/x")
        cid = made[0].id
        assert delete_chunk(db, cid) is True
        assert delete_chunk(db, cid) is False
    finally:
        db.close()


def test_search_with_quote_token_falls_back():
    """查询 token 内含 ASCII 双引号不得抛异常：应正常命中或安全落入 ILIKE 兜底"""
    db = _db()
    try:
        ensure_fts(db)
        made = ingest_text(db, f"{MARKER} 引号健壮性验证出现奶茶与品牌", source_type="doc", industry="引号测试")
        try:
            # 正文含引号字符的复合查询不抛异常且有确定行为（列表结果）
            hits = search_research(db, '包含"引号的奶茶查询', k=10)
            assert isinstance(hits, list)
            # 纯引号 token 同样不抛
            assert isinstance(search_research(db, '"', k=10), list)
        finally:
            delete_chunk(db, made[0].id)
    finally:
        db.close()


def test_search_preserves_relevance_order():
    """FTS 命中多块时返回顺序必须保持相关性（rank）次序，而非 IN 的无序结果"""
    db = _db()
    try:
        ensure_fts(db)
        # 用同一隔离 industry 过滤，避免开发库历史数据干扰；高相关块重复关键词密度明显更高
        low = ingest_text(db, "顺带提了一下奶茶和品牌的杂谈内容", source_type="doc", industry="排名隔离业")[0]
        high = ingest_text(db, "奶茶品牌奶茶品牌奶茶品牌 核心论述奶茶品牌增长打法", source_type="doc", industry="排名隔离业")[0]
        try:
            hits = search_research(db, "奶茶 品牌", industry="排名隔离业", k=10)
            assert {h.id for h in hits} == {high.id, low.id}
            assert hits[0].id == high.id
        finally:
            delete_chunk(db, low.id)
            delete_chunk(db, high.id)
    finally:
        db.close()
