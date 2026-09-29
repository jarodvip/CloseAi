import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.init_db import init_db

# TestClient 不会触发 startup 事件：测试前显式建表+种子，保证新增表在测试库可用
init_db()

client = TestClient(app)
