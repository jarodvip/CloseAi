from sqlalchemy import Column, Integer, String, Text, DateTime
from app.db.session import Base
from datetime import datetime


class BriefingHistory(Base):
    __tablename__ = "briefing_history"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, nullable=False, index=True)
    session_id = Column(Integer, nullable=True)
    customer_name = Column(String(120), nullable=True)
    primary_type = Column(String(100), nullable=True)
    secondary_type = Column(String(100), nullable=True)
    confidence = Column(String(50), nullable=True)
    evidence = Column(Text, nullable=True)
    opening_line = Column(Text, nullable=True)
    focus = Column(Text, nullable=True)
    next_step = Column(Text, nullable=True)
    recommended_cases = Column(Text, nullable=True)
    potential_objections = Column(Text, nullable=True)
    source_refs = Column(Text, nullable=True)
    llm_text = Column(Text, nullable=True)
    llm_source_cards = Column(Text, nullable=True)
    created_at = Column(String(50), nullable=False)
