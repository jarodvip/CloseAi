# 会前简报注入外部情报：命中时 external_intel 区块 + 来源卡并入；无命中时行为不变。
# 数据清理遵循硬约束：finally 删尽全部创建行（含失败路径），含 ResearchChunk 与 BriefingHistory。
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.core.domain.services.research_service import ingest_text, delete_chunk
from app.core.domain.services.briefing_service import build_briefing
from app.core.domain.services.customer_service import create_customer
from app.schemas.customer import CustomerIn

client = TestClient(app)

INTEL_MARK = "情报标记_xt88"


def _cleanup(db, cust=None, made_chunks=()):
    """删尽本次创建的行：简报历史 → 研究分块 → 客户（外键依赖顺序）"""
    from app.models.briefing import BriefingHistory
    from app.models.customer import Customer

    if cust is not None:
        db.query(BriefingHistory).filter(BriefingHistory.customer_id == cust.id).delete()
    for c in made_chunks:
        delete_chunk(db, c.id)
    if cust is not None:
        obj = db.query(Customer).filter(Customer.id == cust.id).first()
        if obj:
            db.delete(obj)
    db.commit()


def test_briefing_contains_external_intel(monkeypatch):
    init_db()
    db = SessionLocal()
    made = []
    cust = None
    try:
        cust = create_customer(db, CustomerIn(name=f"情报集成客户_{INTEL_MARK}", industry="饮料"), owner_id=1)
        made = ingest_text(db, f"{INTEL_MARK} 该品牌重点布局一二线便利店渠道。",
                           source_type="research", title=f"{cust.name} 背调报告",
                           customer_id=cust.id, industry="饮料")
        # 屏蔽真实 LLM，保证断言只针对外部情报管道
        monkeypatch.setattr("app.core.domain.services.briefing_service.generate_text", lambda *a, **k: "模拟输出")
        payload = build_briefing(db, cust.id)
        assert isinstance(payload.get("external_intel"), list)
        assert any(INTEL_MARK in (i.get("title") or "") or INTEL_MARK in (i.get("snippet") or "")
                   for i in payload["external_intel"])
        # 卡片并入 llm_source_cards：label 应含"背调/资料"字样且 source 有值
        cards = payload.get("llm_source_cards") or []
        assert any(("背调" in (c.get("label") or "")) or ("资料" in (c.get("label") or "")) for c in cards)
    finally:
        _cleanup(db, cust=cust, made_chunks=made)
        db.close()


def test_briefing_no_intel_unchanged(monkeypatch):
    """无命中时行为不变：external_intel 为空列表，其余结构保持"""
    init_db()
    db = SessionLocal()
    cust = None
    try:
        monkeypatch.setattr("app.core.domain.services.briefing_service.generate_text", lambda *a, **k: "模拟输出")
        from app.core.domain.services.customer_service import list_customers
        from app.models.user import User
        # 注意：查询返回实体而非标量，owner 需取 .id（原稿 .scalar() 直接当 id 使用会在绑定时报错）
        user = db.query(User).filter(User.username == "admin").first()
        uid = user.id
        existing = [c.name for c in list_customers(db, uid)]
        name = f"无情报客户_{INTEL_MARK}"
        if name not in existing:
            cust = create_customer(db, CustomerIn(name=name, industry="未知行业zzz"), owner_id=uid)
        else:
            from app.models.customer import Customer
            cust = db.query(Customer).filter(Customer.name == name).first()
        payload = build_briefing(db, cust.id)
        assert payload.get("external_intel") == []
    finally:
        _cleanup(db, cust=cust)
        db.close()


def test_list_briefings_recomputes_external_intel(monkeypatch):
    """历史列表实时补算：external_intel 现算注入，来源卡合并呈现"""
    init_db()
    from app.core.domain.services.briefing_service import list_briefings
    db = SessionLocal()
    made = []
    cust = None
    try:
        cust = create_customer(db, CustomerIn(name=f"列表补算客户_{INTEL_MARK}", industry="饮料"), owner_id=1)
        made = ingest_text(db, f"{INTEL_MARK} 重点观察该客户的即时零售铺货节奏。",
                           source_type="research", title=f"{cust.name} 背调报告",
                           customer_id=cust.id, industry="饮料")
        monkeypatch.setattr("app.core.domain.services.briefing_service.generate_text", lambda *a, **k: "模拟输出")
        build_briefing(db, cust.id)
        result = list_briefings(db, cust.id)
        items = result["data"]
        assert len(items) >= 1
        newest = items[0]
        assert isinstance(newest.get("external_intel"), list)
        assert any(INTEL_MARK in (i.get("title") or "") or INTEL_MARK in (i.get("snippet") or "")
                   for i in newest["external_intel"])
        assert any(("背调" in (c.get("label") or "")) or ("资料" in (c.get("label") or ""))
                   for c in newest["llm_source_cards"])
    finally:
        _cleanup(db, cust=cust, made_chunks=made)
        db.close()
