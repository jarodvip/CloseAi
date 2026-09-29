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


class KnowledgeSuggestion(Base):
    """知识沉淀建议草稿：会后跟进自动生成，admin 审核通过后进入知识库"""

    __tablename__ = "knowledge_suggestions"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, nullable=True, index=True)
    customer_name = Column(String(150), nullable=True)
    username = Column(String(50), nullable=True)          # 生成跟进包的销售
    suggestion_type = Column(String(20), default="script")  # script / case / evidence
    scene = Column(String(100), nullable=True)            # 话术场景 / 证据场景
    ktype = Column(String(100), nullable=True)            # 对应 Script.type 客户类型
    title = Column(String(200), nullable=True)
    industry = Column(String(100), nullable=True)
    content = Column(Text, nullable=False)                # 草稿正文（话术模板/案例结果）
    status = Column(String(20), default="pending", index=True)  # pending / approved / rejected
    note = Column(String(255), nullable=True)             # 驳回原因或审核备注
    reviewed_by = Column(String(50), nullable=True)
    reviewed_at = Column(String(30), nullable=True)
    created_at = Column(String(30), nullable=True)
