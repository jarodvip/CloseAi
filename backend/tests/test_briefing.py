from fastapi.testclient import TestClient
from app.main import app
from app.db.session import Base, engine
from app.core.domain.services.auth_service import create_user
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User

client = TestClient(app)
token = None


def test_login():
    global token
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    for username in ["admin", "sales"]:
        if not db.query(User).filter(User.username == username).first():
            create_user(db, username, f"{username}123", role="admin" if username == "admin" else "user")
    db.commit()
    db.close()
    token = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"}).json()["access_token"]


def test_generate_and_history_briefing():
    customer = client.post("/api/v1/customers/", json={"name": "示例客户A"}, headers={"authorization": f"Bearer {token}"}).json()
    customer_id = customer["id"]
    session = client.post("/api/v1/chat/sessions", json={"customer_id": customer_id}, headers={"authorization": f"Bearer {token}"}).json()
    response = client.post(f"/api/v1/customers/{customer_id}/briefing?session_id={session['id']}", headers={"authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["customer_name"] == "示例客户A"
    assert data["data"]["session_id"] == session["id"]
    history = client.get(f"/api/v1/customers/{customer_id}/briefing-history", headers={"authorization": f"Bearer {token}"}).json()
    assert history["code"] == 0
    assert len(history["data"]) >= 1
    assert history["data"][0]["id"] == data["data"]["id"]
    assert isinstance(history["data"][0]["source_refs"], list)
    assert isinstance(history["data"][0]["llm_source_cards"], list)
