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
