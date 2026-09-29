"""主应用入口 - 简化重构版"""

import logging
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.endpoints import main_router as api_router
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models.chat import ChatSession, ChatMessage


logger = logging.getLogger(__name__)


# 请求体大小限制中间件 (最大 1MB)
class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 1_048_576:
            return JSONResponse(status_code=413, content={"detail": "请求体过大，请控制在 1MB 以内"})
        return await call_next(request)


app = FastAPI(title="客户攻单AI", version="0.9.0")
app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8080", "http://localhost:8080", "http://127.0.0.1:5500", "http://localhost:5500"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# 全局异常处理：隐藏内部错误详情
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误"})


# 注册所有 API 路由
app.include_router(api_router, tags=["api"])


@app.get("/health")
def health():
    """健康检查端点"""
    return {"status": "ok"}


@app.on_event("startup")
def startup():
    """初始化数据库和种子数据"""
    init_db()
    db = SessionLocal()
    try:
        session = db.query(ChatSession).first()
        if not session:
            session = ChatSession(title="欢迎会话", customer_id=None, created_at=datetime.now(timezone.utc).isoformat())
            db.add(session)
            db.flush()
            db.add_all([
                ChatMessage(role="assistant", content="欢迎使用客户攻单AI。你可以新建会话、绑定客户，我会结合知识库来源给出攻单建议。", session_id=session.id, created_at=datetime.now(timezone.utc).isoformat()),
                ChatMessage(role="user", content="我想准备品牌野心型客户的会前简报。", session_id=session.id, created_at=datetime.now(timezone.utc).isoformat()),
                ChatMessage(role="assistant", content="建议先明确增长瓶颈，再给一句场景化切入话术和低门槛测试方案。", session_id=session.id, created_at=datetime.now(timezone.utc).isoformat()),
            ])
        db.commit()
    finally:
        db.close()
