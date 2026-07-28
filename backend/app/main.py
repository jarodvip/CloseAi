"""主应用入口 - 简化重构版"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints import main_router as api_router
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models.chat import ChatSession, ChatMessage


app = FastAPI(title="客户攻单AI", version="0.7.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
            session = ChatSession(title="欢迎会话", customer_id=None, created_at=datetime.now().isoformat())
            db.add(session)
            db.flush()
            db.add_all([
                ChatMessage(role="assistant", content="欢迎使用客户攻单AI。你可以新建会话、绑定客户，我会结合知识库来源给出攻单建议。", session_id=session.id, created_at=datetime.now().isoformat()),
                ChatMessage(role="user", content="我想准备品牌野心型客户的会前简报。", session_id=session.id, created_at=datetime.now().isoformat()),
                ChatMessage(role="assistant", content="建议先明确增长瓶颈，再给一句场景化切入话术和低门槛测试方案。", session_id=session.id, created_at=datetime.now().isoformat()),
            ])
        db.commit()
    finally:
        db.close()
