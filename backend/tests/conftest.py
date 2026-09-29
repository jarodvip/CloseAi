import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models.user import User
from app.core.domain.services.auth_service import get_user_by_username, create_user

# TestClient 不会触发 startup 事件：测试前显式建表+种子，保证新增表在测试库可用
init_db()

# v1.0 起不再硬编码种子账号：测试需要普通用户时在此处确保存在
_db = SessionLocal()
try:
    if not get_user_by_username(_db, "sales"):
        create_user(_db, "sales", "sales123", role="user")
finally:
    _db.close()

client = TestClient(app)
