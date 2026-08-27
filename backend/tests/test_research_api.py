import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.core.domain.services.research_service import ingest_text, delete_chunk

client = TestClient(app)

MARKER = "api检索唯一标记_qw12"


@pytest.fixture(scope="module")
def tokens():
    init_db()
    admin = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"}).json()["access_token"]
    sales = client.post("/api/v1/auth/login", json={"username": "sales", "password": "sales123"}).json()["access_token"]
    return {"admin": admin, "sales": sales}


@pytest.fixture(scope="module")
def seeded(tokens):
    db = SessionLocal()
    made = ingest_text(db, f"{MARKER} 电解质水销量翻倍增长记录。", source_type="doc", title=MARKER, industry="饮料")
    yield made
    for c in made:
        delete_chunk(db, c.id)
    db.close()


def test_search_requires_login(seeded):
    assert client.get("/api/v1/research", params={"q": MARKER}).status_code == 401


def test_search_hit(tokens, seeded):
    r = client.get("/api/v1/research", params={"q": MARKER.split()[0], "industry": "饮料"},
                   headers={"authorization": f"Bearer {tokens['admin']}"})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert any(MARKER in (item.get("title") or "") for item in body["data"])
    item = next(i for i in body["data"] if MARKER in (i.get("title") or ""))
    assert {"source_type", "url", "source_name", "fetched_at"} <= set(item.keys())  # 可追溯字段齐全


def test_delete_admin_only(tokens, seeded):
    cid = seeded[0].id
    r_sales = client.delete(f"/api/v1/research/chunks/{cid}", headers={"authorization": f"Bearer {tokens['sales']}"})
    assert r_sales.status_code == 403
    r_admin = client.delete(f"/api/v1/research/chunks/{cid}", headers={"authorization": f"Bearer {tokens['admin']}"})
    assert r_admin.status_code == 200
    r_admin_again = client.delete(f"/api/v1/research/chunks/{cid}", headers={"authorization": f"Bearer {tokens['admin']}"})
    assert r_admin_again.status_code == 404


def test_search_k_out_of_range_rejected(tokens, seeded):
    # k 必须在 [1,50] 内：超界（如 -1）直接 422，防止 SQLite LIMIT -1 全库倾泻
    r = client.get("/api/v1/research", params={"q": MARKER, "k": -1},
                   headers={"authorization": f"Bearer {tokens['admin']}"})
    assert r.status_code == 422


def test_search_requires_admin(tokens, seeded):
    # 检索端点收为管理端调试工具：普通用户（sales）一律 403，防止越权读取他人客户背调分块
    r = client.get("/api/v1/research", params={"q": MARKER},
                   headers={"authorization": f"Bearer {tokens['sales']}"})
    assert r.status_code == 403
