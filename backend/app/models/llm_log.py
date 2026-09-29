from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.db.session import Base


class LLMCallLog(Base):
    """LLM 调用观测：成功/降级、token、耗时。写入失败绝不影响业务"""

    __tablename__ = "llm_call_logs"

    id = Column(Integer, primary_key=True, index=True)
    scene = Column(String(20), nullable=False, index=True)  # briefing/assist/followup/chat/analyze/research/embedding
    model = Column(String(100), nullable=True)
    success = Column(Boolean, default=False)
    degraded = Column(Boolean, default=False)          # 无 key 降级 / 请求失败
    degrade_reason = Column(String(100), nullable=True)  # no_api_key / request_error
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    error = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
