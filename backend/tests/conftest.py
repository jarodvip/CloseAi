import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import Base, engine
from app.core.domain.services.auth_service import create_user

client = TestClient(app)


def pytest_sessionstart(session):
    Base.metadata.create_all(bind=engine)
    from sqlalchemy.orm import Session
    from app.db.session import SessionLocal
    from app.models.user import User
    db = SessionLocal()
    try:
        for username in ["admin", "sales"]:
            if not db.query(User).filter(User.username == username).first():
                create_user(db, username, f"{username}123", role="admin" if username == "admin" else "user")
        db.commit()
    finally:
        db.close()
