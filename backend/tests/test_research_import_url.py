# 内网页面抓取 import-url 测试（Task 6）
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.core.domain.services import research_service

client = TestClient(app)

HTML_SAMPLE = """
<html><head><title>内部wiki页面</title></head><body>
<nav>导航 导航 导航</nav>
<article><h1>-Cola</h1><p>{}</p></article>
<footer>页脚信息</footer></body></html>
""".format("可口可乐近期推出低糖新品线，聚焦便利店渠道。" * 5)

INGEST_MARK = "import_url_wiki_zz9"


@pytest.fixture()
def admin_token():
    from app.db.init_db import init_db
    init_db()
    return client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"}).json()["access_token"]


def test_extract_readable_html():
    title, text = research_service.extract_readable_html(HTML_SAMPLE.replace("nav>导航 导航 导航<", ""))
    assert "wiki" in title or "Cola" in text
    assert "低糖新品线" in text


def test_ingest_url_stores_chunks(admin_token, monkeypatch):
    class _R:
        status_code = 200

        def __init__(self):
            self.text = HTML_SAMPLE

    monkeypatch.setattr(research_service, "_http_get_raw", lambda url: _R())
    r = client.post("/api/v1/research/import-url",
                    json={"url": "https://intra.example.com/wiki/cola", "industry": "饮料", "source_name": "内部wiki"},
                    headers={"authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert len(data) >= 1
    assert data[0]["source_type"] == "web"
    assert data[0]["url"].startswith("https://intra.example.com")
    db = SessionLocal()
    try:
        for c in data:
            research_service.delete_chunk(db, c["id"])
    finally:
        db.close()


def test_import_url_requires_admin(admin_token):
    sales = client.post("/api/v1/auth/login", json={"username": "sales", "password": "sales123"}).json()["access_token"]
    r = client.post("/api/v1/research/import-url", json={"url": "https://intra.example.com/x"},
                    headers={"authorization": f"Bearer {sales}"})
    assert r.status_code == 403
