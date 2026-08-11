from fastapi.testclient import TestClient
from app.main import app
from app.db.session import Base, engine
from app.core.domain.services.auth_service import create_user
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User
from app.models.customer import Customer

client = TestClient(app)
admin_token = None


def test_login():
    global admin_token
    # 确保测试所需的客户存在
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
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    admin_token = response.json()["access_token"]


def test_create_customer():
    response = client.post("/api/v1/customers/", json={"name": "测试客户", "industry": "食品"}, headers={"authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "测试客户"
    assert data["id"] >= 1


def test_get_customer():
    response = client.get("/api/v1/customers/1", headers={"authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "示例客户A"
