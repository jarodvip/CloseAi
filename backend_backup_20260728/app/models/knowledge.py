from sqlalchemy import Column, Integer, String, Text, Float
from app.db.session import Base


class CustomerTypeKnowledge(Base):
    __tablename__ = "customer_type_knowledge"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    signal = Column(String(255), nullable=True)
    pain = Column(Text, nullable=True)
    strategy = Column(Text, nullable=True)
    opening_line = Column(Text, nullable=True)
    taboo = Column(String(255), nullable=True)
    case_code = Column(String(50), nullable=True)
    source = Column(String(255), nullable=True)
    objections = Column(Text, nullable=True)
    next_step = Column(Text, nullable=True)


class Case(Base):
    __tablename__ = "cases"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False)
    title = Column(String(150), nullable=False)
    type = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    stage = Column(String(100), nullable=True)
    result = Column(Text, nullable=True)
    source = Column(String(255), nullable=True)


class Script(Base):
    __tablename__ = "scripts"
    id = Column(Integer, primary_key=True, index=True)
    scene = Column(String(100), nullable=True)
    type = Column(String(100), nullable=True)
    template = Column(Text, nullable=True)
    source = Column(String(255), nullable=True)


class Evidence(Base):
    __tablename__ = "evidence"
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(100), nullable=True)
    metric = Column(String(150), nullable=True)
    value = Column(String(150), nullable=True)
    scene = Column(String(150), nullable=True)
    source_ref = Column(String(255), nullable=True)
