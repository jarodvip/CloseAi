# backend/app/models/research.py
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, LargeBinary

from app.db.session import Base


class ResearchChunk(Base):
    """外部数据文本块：文档导入 / 内网页面 / 联网背调统一存储，保证来源可追溯"""

    __tablename__ = "research_chunks"

    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String(20), nullable=False)  # doc / web / research
    title = Column(String(200), nullable=True)
    url = Column(String(500), nullable=True)
    source_name = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    customer_id = Column(Integer, nullable=True, index=True)  # 背调结果挂具体客户
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, default=0)
    fetched_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    embedding = Column(LargeBinary, nullable=True)  # 预留：二期语义检索升级
