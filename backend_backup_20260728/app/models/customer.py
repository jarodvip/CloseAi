from sqlalchemy import Column, Integer, String, Float, Text
from app.db.session import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    industry = Column(String(100), nullable=True)
    revenue_range = Column(String(100), nullable=True)
    stage = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    primary_type = Column(String(100), nullable=True)
    secondary_type = Column(String(100), nullable=True)
    type_confidence = Column(Float, nullable=True)
    type_evidence = Column(Text, nullable=True)
