import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.db.session import engine, Base
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.knowledge import CustomerTypeKnowledge, Case, Script, Evidence
from app.models.chat import ChatSession, ChatMessage
from app.core.domain.services.auth_service import create_user


def init_db():
    Base.metadata.create_all(bind=engine, checkfirst=True)
    db = Session(bind=engine)
    try:
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
        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    print("initialized")
