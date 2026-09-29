from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.feedback import Feedback

VALID_RATINGS = {"up", "down"}
VALID_SCENES = {"briefing", "assist", "followup", "chat"}


def create_feedback(db: Session, payload: dict, username: str) -> Feedback:
    rating = (payload.get("rating") or "").strip()
    scene = (payload.get("scene") or "").strip()
    if rating not in VALID_RATINGS:
        raise HTTPException(status_code=422, detail="rating 仅支持 up/down")
    if scene not in VALID_SCENES:
        raise HTTPException(status_code=422, detail=f"scene 仅支持 {'/'.join(sorted(VALID_SCENES))}")
    source = (payload.get("source") or "").strip() or None
    if not source:
        raise HTTPException(status_code=422, detail="source 不能为空")
    record = Feedback(
        username=username,
        scene=scene,
        customer_id=payload.get("customer_id"),
        source=source[:255],
        label=(payload.get("label") or "")[:150] or None,
        rating=rating,
        comment=(payload.get("comment") or "") or None,
        created_at=datetime.utcnow(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def feedback_stats(db: Session) -> Dict:
    """采纳率统计：总体 + 按场景 + 最近反馈"""
    total = db.query(func.count(Feedback.id)).scalar() or 0
    up = db.query(func.count(Feedback.id)).filter(Feedback.rating == "up").scalar() or 0
    down = total - up
    by_scene_rows = db.query(Feedback.scene, Feedback.rating, func.count(Feedback.id)).group_by(
        Feedback.scene, Feedback.rating).all()
    scene_map: Dict[str, Dict] = {}
    for scene, rating, cnt in by_scene_rows:
        item = scene_map.setdefault(scene, {"scene": scene, "up": 0, "down": 0})
        item[rating] = cnt
    by_scene = []
    for scene, item in sorted(scene_map.items()):
        voted = item["up"] + item["down"]
        item["total"] = voted
        item["adoption_rate"] = round(item["up"] / voted, 4) if voted else None
        by_scene.append(item)
    recent = db.query(Feedback).order_by(Feedback.id.desc()).limit(20).all()
    return {
        "total": total,
        "up": up,
        "down": down,
        "adoption_rate": round(up / total, 4) if total else None,
        "by_scene": by_scene,
        "recent": [_brief(f) for f in recent],
    }


def _brief(f: Feedback) -> Dict:
    return {
        "id": f.id,
        "username": f.username,
        "scene": f.scene,
        "customer_id": f.customer_id,
        "source": f.source,
        "label": f.label,
        "rating": f.rating,
        "created_at": f.created_at.isoformat() if f.created_at else None,
    }
