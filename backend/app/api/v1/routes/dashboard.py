from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.deps import get_db, get_current_user
from app.models.customer import Customer
from app.models.briefing import BriefingHistory
from app.models.interaction import Interaction
from app.models.feedback import Feedback
from app.models.llm_log import LLMCallLog
from app.core.domain.services.feedback_service import feedback_stats

router = APIRouter()


def _llm_stats(db: Session) -> dict:
    """近7天 LLM 调用观测：成功率、降级、token、耗时、场景分布"""
    since = datetime.utcnow() - timedelta(days=7)
    rows = db.query(LLMCallLog).filter(LLMCallLog.created_at >= since).all()
    total = len(rows)
    success = sum(1 for r in rows if r.success)
    degraded = sum(1 for r in rows if r.degraded)
    tokens = sum((r.prompt_tokens or 0) + (r.completion_tokens or 0) for r in rows)
    latencies = [r.latency_ms for r in rows if r.latency_ms]
    by_scene: dict = {}
    for r in rows:
        item = by_scene.setdefault(r.scene, {"scene": r.scene, "total": 0, "degraded": 0})
        item["total"] += 1
        item["degraded"] += 1 if r.degraded else 0
    return {
        "total": total,
        "success": success,
        "degraded": degraded,
        "success_rate": round(success / total, 4) if total else None,
        "degrade_rate": round(degraded / total, 4) if total else None,
        "total_tokens": tokens,
        "avg_latency_ms": int(sum(latencies) / len(latencies)) if latencies else None,
        "by_scene": sorted(by_scene.values(), key=lambda x: -x["total"]),
    }


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

    # 知识飞轮：来源卡反馈采纳率 + LLM 调用观测（近7天）
    feedback = feedback_stats(db)
    llm = _llm_stats(db)

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
            "feedback": feedback,
            "llm": llm,
        },
    }
