from sqlalchemy import Column, Integer, String, Text, DateTime
from app.db.session import Base
from datetime import datetime


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, nullable=False, index=True)
    stage = Column(String(50), nullable=True)
    transcript = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    decisions = Column(Text, nullable=True)
    pending_actions = Column(Text, nullable=True)
    created_at = Column(String(50), nullable=False)
