from typing import Any, Dict, List, Optional
from datetime import datetime
import json as _json

from sqlalchemy.orm import Session
from app.core.domain.services.common import build_source_cards_for_cases, build_system_prompt, to_code
from app.core.domain.services.customer_service import get_customer
from app.core.domain.services.knowledge_service import get_customer_type_by_code, list_cases, list_evidence
from app.core.domain.services.llm_service import generate_text
from app.models.briefing import BriefingHistory

def build_briefing(db: Session, customer_id: int, session_id: Optional[int] = None) -> Dict[str, Any]:
    customer = get_customer(db, customer_id)
    if not customer:
        return {}
    primary_type = customer.primary_type
    type_info = None
    if primary_type:
        type_info = get_customer_type_by_code(db, to_code(primary_type))
    cases = [{"code": item.code, "title": item.title, "type": item.type, "industry": item.industry, "stage": item.stage, "result": item.result, "source": item.source} for item in list_cases(db, primary_type or "")][:3]
    evidence = list_evidence(db)[:3]
    evidence_text = "；".join([f"{e.source}: {e.metric}={e.value}" for e in evidence if e.source and e.value])
    prompt = f"""请根据客户资料生成销售会前简报。
客户：{customer.name}
行业：{customer.industry or '未知'}
阶段：{customer.stage or '未知'}
客户类型：{primary_type or '待判断'}
类型策略：{type_info.strategy if type_info else '先判断客户类型与增长瓶颈'}
禁忌：{type_info.taboo if type_info else '避免空泛承诺'}
权威证据：{evidence_text or '暂无'}
请输出：判断依据、破冰话术、重点方向、推荐案例要点、潜在异议、下一步动作、来源说明。"""
    llm_text = ""
    try:
        llm_text = generate_text(prompt, system=build_system_prompt("briefing", primary_type or "待判断", type_info, evidence, customer=customer))
    except Exception:
        llm_text = ""
    source_cards = build_source_cards_for_cases(type_info, cases, evidence)
    source_refs = [card["source"] for card in source_cards]
    payload = {
        "customer_id": customer_id,
        "session_id": session_id,
        "customer_name": customer.name,
        "primary_type": primary_type,
        "secondary_type": customer.secondary_type,
        "confidence": customer.type_confidence,
        "evidence": customer.type_evidence,
        "opening_line": type_info.opening_line if type_info else None,
        "focus": type_info.strategy if type_info else "先明确客户增长瓶颈与决策链。",
        "recommended_cases": cases,
        "potential_objections": type_info.objections.split(",") if type_info and type_info.objections else ["太贵了", "我们再看看"],
        "next_step": type_info.next_step if type_info else "建议先做1个核心城市1个月品牌认知测试方案。",
        "source_refs": source_refs,
        "llm_text": llm_text or None,
        "llm_source_cards": source_cards,
        "created_at": datetime.now().isoformat(),
    }
    for key in ["recommended_cases", "potential_objections", "source_refs", "llm_source_cards"]:
        if isinstance(payload.get(key), (list, dict)):
            payload[key] = _json.dumps(payload[key], ensure_ascii=False)
    record = None
    try:
        record = BriefingHistory(
            **{k: v for k, v in payload.items() if k in {
                "customer_id", "session_id", "customer_name", "primary_type", "secondary_type",
                "confidence", "evidence", "opening_line", "focus", "next_step",
                "recommended_cases", "potential_objections", "source_refs", "llm_text",
                "llm_source_cards", "created_at",
            }},
        )
        db.add(record)
        db.commit()
        if record and record.id:
            payload["id"] = record.id
    except Exception:
        db.rollback()
    return payload

def list_briefings(db: Session, customer_id: int, limit: int = 20) -> Dict[str, Any]:
    items = (
        db.query(BriefingHistory)
        .filter(BriefingHistory.customer_id == customer_id)
        .order_by(BriefingHistory.id.desc())
        .limit(limit)
        .all()
    )
    return {"code": 0, "message": "ok", "data": [
        {
            "id": item.id,
            "customer_id": item.customer_id,
            "session_id": item.session_id,
            "customer_name": item.customer_name,
            "primary_type": item.primary_type,
            "secondary_type": item.secondary_type,
            "confidence": item.confidence,
            "evidence": item.evidence,
            "opening_line": item.opening_line,
            "focus": item.focus,
            "next_step": item.next_step,
            "recommended_cases": _safe_json(item.recommended_cases),
            "potential_objections": _safe_json(item.potential_objections, default=[]),
            "source_refs": _safe_json(item.source_refs, default=[]),
            "llm_text": item.llm_text,
            "llm_source_cards": _safe_json(item.llm_source_cards, default=[]),
            "created_at": item.created_at,
        }
        for item in items
    ]}

def _safe_json(value, default=None):
    if value is None:
        return default
    try:
        import json
        return json.loads(value)
    except Exception:
        return default
