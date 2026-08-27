# backend/tests/test_research_model.py
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.research import ResearchChunk


def test_create_and_query_chunk():
    """模型能正常建表、写入、按来源类型查询"""
    db: Session = SessionLocal()
    try:
        chunk = ResearchChunk(
            source_type="doc",
            title="行业报告_测试marker_T1",
            url="https://example.com/t1",
            source_name="测试源",
            industry="食品饮料",
            customer_id=None,
            content="测试正文内容，用于验证存储。",
            chunk_index=0,
        )
        db.add(chunk)
        db.commit()
        db.refresh(chunk)
        assert chunk.id is not None
        found = (
            db.query(ResearchChunk)
            .filter(ResearchChunk.title == "行业报告_测试marker_T1")
            .first()
        )
        assert found is not None
        # 清理
        db.delete(found)
        db.commit()
    finally:
        db.close()
