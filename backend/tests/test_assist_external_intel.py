# 会中辅助接入外部情报：命中时 external_intel 与来源卡并入；无命中时行为与结构不变。
# 数据清理遵循硬约束：finally 删尽全部创建行（含失败路径），含 ResearchChunk 与 Customer。
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.core.domain.services.research_service import ingest_text, delete_chunk
from app.core.domain.services.assist_service import build_assist
from app.core.domain.services.customer_service import create_customer
from app.schemas.customer import CustomerIn
from sqlalchemy.orm import Session

ASSIST_MARK = "会中标记_am55"


def _cleanup(db: Session, cust=None, made_chunks=()):
    """删尽本次创建的行：研究分块 → 客户"""
    from app.models.customer import Customer

    for c in made_chunks:
        delete_chunk(db, c.id)
    if cust is not None:
        obj = db.query(Customer).filter(Customer.id == cust.id).first()
        if obj:
            db.delete(obj)
    db.commit()


def test_assist_contains_external_intel(monkeypatch):
    """命中时 external_intel 非空，source_cards 含 cards_from_intel 产物"""
    init_db()
    db = SessionLocal()
    made = []
    cust = None
    try:
        cust = create_customer(db, CustomerIn(name=f"会中助手客户_{ASSIST_MARK}", industry="饮料"), owner_id=1)
        # 「饮料」独立成词才能被 FTS 命中（jieba 不拆复合词，参考 briefing 用例注释）
        made = ingest_text(db, f"{ASSIST_MARK} 饮料 赛道新品铺货节奏加快。",
                           source_type="research", title=f"{cust.name} 背调报告",
                           customer_id=cust.id, industry="饮料")
        # 屏蔽真实 LLM，保证断言只针对外部情报管道
        monkeypatch.setattr("app.core.domain.services.assist_service.generate_text", lambda *a, **k: "模拟输出")
        result = build_assist(db, cust.id, {"current_stage": "听", "transcript": "你们怎么收费"})
        assert isinstance(result.get("external_intel"), list)
        assert any(ASSIST_MARK in (i.get("title") or "") or ASSIST_MARK in (i.get("snippet") or "")
                   for i in result["external_intel"])
        # 来源卡并入 source_cards：cards_from_intel 产物 label 含「背调」或「资料」字样
        assert any(("背调" in (c.get("label") or "")) or ("资料" in (c.get("label") or ""))
                   for c in result["source_cards"])
    finally:
        _cleanup(db, cust=cust, made_chunks=made)
        db.close()


def test_assist_no_intel_unchanged(monkeypatch):
    """无命中时行为不变：external_intel 为空列表，既有结构不受影响"""
    init_db()
    db = SessionLocal()
    cust = None
    try:
        cust = create_customer(db, CustomerIn(name=f"无情报会中客户_{ASSIST_MARK}", industry="未知行业zzz"), owner_id=1)
        monkeypatch.setattr("app.core.domain.services.assist_service.generate_text", lambda *a, **k: "模拟输出")
        result = build_assist(db, cust.id, {"current_stage": "听", "transcript": "你们怎么收费"})
        assert result.get("external_intel") == []
        # 既有结构保持
        assert "stage_guidance" in result
        assert "source_cards" in result
        assert "source_refs" in result
    finally:
        _cleanup(db, cust=cust)
        db.close()
