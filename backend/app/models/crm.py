from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime
from app.db.session import Base


class CrmPushLog(Base):
    """CRM 推送日志：跟进包 webhook 回写的结果留痕，失败可排查"""

    __tablename__ = "crm_push_logs"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=True)
    customer_id = Column(Integer, nullable=True, index=True)
    customer_name = Column(String(150), nullable=True)
    success = Column(Boolean, default=False)
    http_status = Column(Integer, nullable=True)
    error = Column(String(255), nullable=True)
    payload_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
