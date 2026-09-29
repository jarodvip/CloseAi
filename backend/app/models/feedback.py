from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.db.session import Base


class Feedback(Base):
    """来源卡反馈：销售对简报/会中/会后建议的采纳标记，驱动采纳率看板"""

    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False, index=True)
    scene = Column(String(20), nullable=False, index=True)  # briefing / assist / followup / chat
    customer_id = Column(Integer, nullable=True, index=True)
    source = Column(String(255), nullable=True)   # 来源卡 source 字段
    label = Column(String(150), nullable=True)    # 来源卡 label 字段
    rating = Column(String(10), nullable=False)   # up / down
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
