from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from app.core.deps import get_db, get_current_user
from app.models.customer import Customer
from app.models.briefing import BriefingHistory
from app.models.interaction import Interaction

router = APIRouter()


@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    """获取看板统计数据"""
    # 客户总数
    total_customers = db.query(func.count(Customer.id)).scalar() or 0

    # 客户类型分布
    type_distribution = db.query(
        Customer.primary_type, func.count(Customer.id)
    ).group_by(Customer.primary_type).all()
    type_dist = [{"type": t[0] or "未分类", "count": t[1]} for t in type_distribution if t[0]]

    # 会前简报生成数
    total_briefings = db.query(func.count(BriefingHistory.id)).scalar() or 0

    # 互动记录数
    total_interactions = db.query(func.count(Interaction.id)).scalar() or 0

    # 会后跟进数（有summary的记录）
    followups_with_summary = db.query(func.count(Interaction.id)).filter(
        Interaction.summary.isnot(None),
        Interaction.summary != ""
    ).scalar() or 0

    # 最近7天简报生成趋势（按天）
    from datetime import datetime, timedelta
    from sqlalchemy import text
    seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
    result = db.execute(text("""
        SELECT substr(created_at, 1, 10) as date, COUNT(*) as count
        FROM briefing_history
        WHERE created_at >= :seven_days_ago
        GROUP BY substr(created_at, 1, 10)
        ORDER BY date
    """), {"seven_days_ago": seven_days_ago})
    briefing_trend = [{"date": row[0], "count": row[1]} for row in result.fetchall()]

    # 客户阶段分布
    stage_distribution = db.query(
        Customer.stage, func.count(Customer.id)
    ).group_by(Customer.stage).all()
    stage_dist = [{"stage": s[0] or "未设置", "count": s[1]} for s in stage_distribution if s[0]]

    return {
        "code": 0,
        "message": "ok",
        "data": {
            "total_customers": total_customers,
            "type_distribution": type_dist,
            "total_briefings": total_briefings,
            "total_interactions": total_interactions,
            "followups_with_summary": followups_with_summary,
            "briefing_trend": briefing_trend,
            "stage_distribution": stage_dist,
        },
    }
