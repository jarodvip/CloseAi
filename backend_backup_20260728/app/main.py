import json
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.routes import auth, customers, briefing, interactions, knowledge
from app.routes import chat
from app.core.deps import get_current_user
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models.customer import Customer
from app.schemas.customer import CustomerOut
from app.models.chat import ChatSession, ChatMessage
from app.models.briefing import BriefingHistory
from app.services.briefing_service import list_briefings


app = FastAPI(title="客户攻单AI", version="0.7.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(customers.router, prefix="/api/v1/customers", tags=["customers"])
app.include_router(briefing.router, prefix="/api/v1/customers", dependencies=[Depends(get_current_user)], tags=["briefing"])
app.include_router(interactions.router, prefix="/api/v1/customers", dependencies=[Depends(get_current_user)], tags=["interactions"])
app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["knowledge"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/api/v1/customers/{customer_id}", response_model=CustomerOut, tags=["customers"])
def get_customer_detail(customer_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    customer = customers.get_customer(db, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="customer not found")
    return CustomerOut.from_orm(customer)


@app.get("/api/v1/customers/{customer_id}/briefing-history", tags=["briefing"])
def get_customer_briefing_history(customer_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    customer = customers.get_customer(db, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="customer not found")
    return {"code": 0, "message": "ok", "data": list_briefings(db, customer_id)}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.on_event("startup")
def startup():
    init_db()
    from app.db.session import Base, engine
    Base.metadata.create_all(bind=engine)
    from sqlalchemy.orm import Session
    from app.db.session import SessionLocal
    from app.models.user import User
    from app.services.auth_service import create_user
    from app.models.knowledge import CustomerTypeKnowledge, Case, Script, Evidence
    from app.models.chat import ChatSession, ChatMessage
    from app.models.briefing import BriefingHistory
    db = SessionLocal()
    if not db.query(User).filter(User.username == "admin").first():
        create_user(db, "admin", "admin123", role="admin")
        create_user(db, "sales", "sales123", role="user")
    else:
        admin = db.query(User).filter(User.username == "admin").first()
        if admin.role != "admin":
            admin.role = "admin"
            db.add(admin)
    if not db.query(CustomerTypeKnowledge).first():
        db.add_all([
            CustomerTypeKnowledge(code="BRAND_AMBITION", name="品牌野心型", signal="我要做行业第一", pain="担心品牌投入没有长期回报", strategy="把投放定义为品牌资产投资", opening_line="老板，您投入的不是单纯的广告费，而是在为企业构建品牌资产。", taboo="只谈CPM/短期流量成本", case_code="FEIHE", source="分众客户七大类型 · 识别与攻单策略.pptx", objections="太贵了,我们再看看", next_step="建议先做1个核心城市1个月品牌认知测试方案，用历史品牌资产案例测算长期溢价。"),
            CustomerTypeKnowledge(code="POSITIONING", name="定位卡位型", signal="这个位置我先占", pain="担心消费者优先选择竞品", strategy="提炼15秒心智超级话语", opening_line="我发现你们在XX细分领域的体验做得特别好，但消费者还没真正意识到这种价值。", taboo="只求规模声量", case_code="MIAOKELD", source="分众销售作战速查卡片.pptx", objections="我们已经有定位了,消费者记不住", next_step="建议先提炼一句场景化超级话语，再选3城做电梯高频触达验证。"),
        ])
        db.add_all([
            Case(code="FEIHE", title="飞鹤奶粉", type="品牌野心型", industry="母婴", stage="全国化扩张", result="营收从35亿提升到200亿+", source="分众客户七大类型 · 识别与攻单策略.pptx"),
            Case(code="MIAOKELD", title="妙可蓝多", type="定位卡位型", industry="食品", stage="心智抢占", result="市场份额从3.9%提升到30.9%", source="分众销售作战速查卡片.pptx"),
        ])
        db.add_all([
            Script(scene="破冰", type="品牌野心型", template="老板，您投入的不是单纯的广告费，是在为企业构建品牌资产。", source="分众客户七大类型 · 识别与攻单策略.pptx"),
            Script(scene="破冰", type="定位卡位型", template="你不需要让所有人喜欢你，你只需要让消费者在某个特定场景下第一个想起你。", source="分众销售作战速查卡片.pptx"),
        ])
        db.add_all([
            Evidence(source="凯度", metric="一抖一书一分众", value="品牌资产提升从7%跃升到11%", scene="媒介组合论证", source_ref="分众客户七大类型 · 识别与攻单策略.pptx"),
            Evidence(source="电梯广告", metric="日到达率/主动观看率", value="79% / 45%", scene="触达强度论证", source_ref="分众客户七大类型 · 识别与攻单策略.pptx"),
        ])
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
    db.close()
