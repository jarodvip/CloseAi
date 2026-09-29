# 背调（backdossier）：LLM 联网生成报告入库 + 本人客户专属刷新端点。
# 注：customers 创建接口实际返回裸 CustomerOut（无 data 包装），取 id 用 ["id"]。
from fastapi.testclient import TestClient

from app.main import app
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.core.domain.services import research_service

client = TestClient(app)

REPORT_FAKE = "主营业务：气泡水；近半年动态：推出联名款（待确认）；广告投放：电梯媒体为主。"


def _mk_customer(token_suffix: str, name: str):
    tok = client.post("/api/v1/auth/login", json={"username": "sales", "password": "sales123"}).json()["access_token"]
    cid = client.post("/api/v1/customers", json={"name": name},
                      headers={"authorization": f"Bearer {tok}"}).json()["id"]
    return tok, cid


def _del_customers_by_name(name: str):
    """删尽指定名字的全部客户行，防止断言中途失败给 dev DB 留脏数据"""
    db = SessionLocal()
    try:
        from app.models.customer import Customer
        rows = db.query(Customer).filter(Customer.name == name).all()
        for obj in rows:
            db.delete(obj)
        db.commit()
    finally:
        db.close()


def test_run_backdossier_ingests_report(monkeypatch):
    init_db()
    db = SessionLocal()
    made = []
    try:
        monkeypatch.setattr(research_service, "call_llm_with_search", lambda prompt, system=None, **kwargs: REPORT_FAKE)
        # 直接构造内存对象即可验证逻辑
        class _Cust:
            id = None
            name = "单元测试客户_bd1"
            industry = "饮料"

        made = research_service.run_backdossier(db, _Cust())
        assert len(made) >= 1
        first = made[0]
        assert first.source_type == "research"
        assert first.title == "单元测试客户_bd1 背调报告"
        assert first.source_name == "LLM联网调研"
    finally:
        # 断言失败也必须清理已入库的分块
        for c in made:
            research_service.delete_chunk(db, c.id)
        db.close()


def test_refresh_endpoint_owner_isolation(monkeypatch):
    init_db()
    sales_tok, sales_cid = _mk_customer("s", "归属隔离客户_so1")
    admin_tok = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"}).json()["access_token"]

    called = {}
    monkeypatch.setattr(
        "app.api.v1.routes.research.run_backdossier",
        lambda db, customer: called.update({"name": customer.name}) or [],
    )
    try:
        # 本人 OK
        r_ok = client.post(f"/api/v1/customers/{sales_cid}/research/refresh",
                           headers={"authorization": f"Bearer {sales_tok}"})
        assert r_ok.status_code == 200
        assert called["name"] == "归属隔离客户_so1"
        # 他人 404
        r_other = client.post(f"/api/v1/customers/{sales_cid}/research/refresh",
                              headers={"authorization": f"Bearer {admin_tok}"})
        assert r_other.status_code == 404
    finally:
        _del_customers_by_name("归属隔离客户_so1")


def test_refresh_endpoint_llm_failure_degrades(monkeypatch):
    # 已配置 LLM_API_KEY 时联网失败也不得向客户端抛 500，须降级为空结果
    init_db()
    sales_tok, sales_cid = _mk_customer("f", "背调降级客户_sf1")

    def _boom(prompt, system=None):
        raise RuntimeError("模拟联网故障")

    monkeypatch.setattr(research_service, "call_llm_with_search", _boom)
    try:
        r = client.post(f"/api/v1/customers/{sales_cid}/research/refresh",
                        headers={"authorization": f"Bearer {sales_tok}"})
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 0
        assert body["data"] == []
    finally:
        _del_customers_by_name("背调降级客户_sf1")
