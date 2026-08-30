from typing import Any, Dict, List, Optional
from datetime import datetime
import json as _json

from sqlalchemy.orm import Session
from app.core.domain.services.common import build_source_cards_for_cases, build_system_prompt, to_code
from app.core.domain.services.customer_service import get_customer
from app.core.domain.services.knowledge_service import get_customer_type_by_code, list_cases, list_evidence
from app.core.domain.services.llm_service import generate_text
from app.core.domain.services.research_service import cards_from_intel, collect_research_cards
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
    prompt = f"""你是销售作战助手。请根据以下客户资料生成会前简报，输出简洁、可执行、专业的中文建议。

客户：{customer.name}
行业：{customer.industry or '未知'}
阶段：{customer.stage or '未知'}
客户类型：{primary_type or '待判断'}
类型策略：{type_info.strategy if type_info else '先判断客户类型与增长瓶颈'}
禁忌：{type_info.taboo if type_info else '避免空泛承诺'}
权威证据：{evidence_text or '暂无'}

请按以下格式输出：
【判断依据】客户属于什么类型，判断理由
【破冰话术】第一句如何切入
【重点方向】本次拜访应聚焦的核心议题
【推荐案例要点】匹配案例的启示
【潜在异议】客户可能提出的顾虑及预应对话术
【下一步动作】会后要跟进的具体事项
【来源说明】引用知识的来源"""
    llm_text = ""
    try:
        llm_text = generate_text(prompt, system=build_system_prompt("briefing", primary_type or "待判断", type_info, evidence, customer=customer))
    except Exception:
        llm_text = ""
    source_cards = build_source_cards_for_cases(type_info, cases, evidence)
    source_refs = [card["source"] for card in source_cards]
    # 外部情报：按行业+客户检索研究分块，仅存在于响应态（BriefingHistory 白名单会自动跳过 external_intel）
    external_intel = collect_research_cards(
        db, name=customer.name, industry=customer.industry,
        customer_id=customer.id,
    )
    external_cards = cards_from_intel(external_intel)
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
        "external_intel": external_intel,
        "llm_source_cards": source_cards + external_cards,
        "created_at": datetime.now().isoformat(),
    }
    db_payload = {**payload}
    # 持久化仅保留内部来源卡：外部情报卡与 external_intel 同属响应态，读取时由 list_briefings 实时补算，避免叠加重复
    db_payload["llm_source_cards"] = _json.dumps(source_cards, ensure_ascii=False)
    for key in ["recommended_cases", "potential_objections", "source_refs", "llm_source_cards"]:
        if isinstance(db_payload.get(key), (list, dict)):
            db_payload[key] = _json.dumps(db_payload[key], ensure_ascii=False)
    record = None
    try:
        record = BriefingHistory(
            **{k: v for k, v in db_payload.items() if k in {
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
    data = []
    for item in items:
        # 外部情报不入库：每次读取按当前客户名实时补算，不迁移表结构
        intel = collect_research_cards(db, name=item.customer_name, customer_id=item.customer_id)
        stored_cards = _safe_json(item.llm_source_cards, default=[])
        data.append({
            "id": item.id,
            "customer_id": item.customer_id,
            "session_id": item.session_id,
            "customer_name": item.customer_name,
            "primary_type": item.primary_type,
            "secondary_type": item.secondary_type,
            "confidence": float(item.confidence) if item.confidence else None,
            "evidence": item.evidence,
            "opening_line": item.opening_line,
            "focus": item.focus,
            "next_step": item.next_step,
            "recommended_cases": _safe_json(item.recommended_cases),
            "potential_objections": _safe_json(item.potential_objections, default=[]),
            "source_refs": _safe_json(item.source_refs, default=[]),
            "llm_text": item.llm_text,
            "external_intel": intel,
            "llm_source_cards": stored_cards + cards_from_intel(intel),
            "created_at": item.created_at,
        })
    return {"code": 0, "message": "ok", "data": data}

def _safe_json(value, default=None):
    if value is None:
        return default
    try:
        import json
        return json.loads(value)
    except Exception:
        return default
