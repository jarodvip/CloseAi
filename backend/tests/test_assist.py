from fastapi.testclient import TestClient
from app.main import app
from app.db.session import Base, engine
from app.core.domain.services.auth_service import create_user
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User
from app.models.customer import Customer
from app.db.init_db import init_db

client = TestClient(app)
token = None


def test_login():
    global token
    # 确保测试所需的客户和知识数据存在
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "admin").first():
            create_user(db, "admin", "admin123", role="admin")
        admin = db.query(User).filter(User.username == "admin").first()
        if not db.query(Customer).filter(Customer.id == 1).first():
            db.add(Customer(name="示例客户A", industry="消费", stage="全国化扩张", region="华东", owner_id=admin.id))
            db.flush()
        db.commit()
    finally:
        db.close()
    init_db()
    token = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"}).json()["access_token"]


def test_assist():
    response = client.post("/api/v1/customers/1/assist", json={"current_stage": "听", "transcript": "你们有什么预期数据？", "customer_type": "品牌野心型"}, headers={"authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert "data" in data
    assert isinstance(data["data"]["source_cards"], list)
    assert len(data["data"]["source_cards"]) >= 1
    assert any(card.get("label") == "客户类型策略" for card in data["data"]["source_cards"])
    assert any(card.get("label") == "话术" for card in data["data"]["source_cards"])
