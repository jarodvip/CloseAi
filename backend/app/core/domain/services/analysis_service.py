from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from app.core.domain.services.common import to_code
from app.core.domain.services.customer_service import get_customer, list_customers
from app.core.domain.services.knowledge_service import get_customer_type_by_code, list_cases, list_evidence
from app.core.domain.services.briefing_service import build_briefing
from app.schemas.customer import CustomerIn


def analyze_customer(db: Session, payload: dict) -> Dict[str, Any]:
    name = (payload.get("name") or "").strip()
    if not name:
        return {"error": "客户名称不能为空"}

    existing = list_customers(db)
    matched = next((c for c in existing if c.name == name), None)

    if matched:
        customer_id = matched.id
        customer = matched
    else:
        customer = create_customer(db, CustomerIn(**{k: v for k, v in payload.items() if k in {"name", "industry", "revenue_range", "stage", "region"}}))
        customer_id = customer.id

    # 如果客户还没有类型，基于 LLM 推断
    if not customer.primary_type:
        customer = _infer_type(db, customer, payload)

    # 生成会前简报
    briefing = build_briefing(db, customer_id)
    return {
        "customer_id": customer_id,
        "customer_name": customer.name,
        "primary_type": customer.primary_type,
        "secondary_type": customer.secondary_type,
        "type_confidence": customer.type_confidence,
        "type_evidence": customer.type_evidence,
        "is_new": matched is None,
        "briefing": briefing,
    }


def _infer_type(db: Session, customer, payload: dict) -> Any:
    """根据客户名称和已有知识库做简单类型推断"""
    from app.core.domain.services.llm_service import generate_text
    from app.core.domain.services.common import format_evidence_text
    from app.models.knowledge import CustomerTypeKnowledge

    types = db.query(CustomerTypeKnowledge).all()
    type_list = "\n".join([f"- {t.name}: 信号={t.signal}, 痛点={t.pain}" for t in types])
    evidence = list_evidence(db)[:3]
    evidence_text = format_evidence_text(evidence)

    stage_info = f"行业={customer.industry or '未知'}, 阶段={customer.stage or '未知'}"
    prompt = f"""请根据客户名称判断其最可能的客户类型。
客户名称：{customer.name}
{stage_info}
可选类型：
{type_list}
权威证据：{evidence_text or '暂无'}
请只输出最匹配的类型名称，例如：品牌野心型"""

    try:
        result = generate_text(prompt)
        predicted = result.strip().split("\n")[0].strip()
        matched_type = next((t for t in types if predicted in t.name or t.name in predicted), None)
        if matched_type:
            customer.primary_type = matched_type.name
            customer.type_confidence = 0.7
            customer.type_evidence = f"基于LLM推断：{predicted}"
        else:
            customer.primary_type = predicted
            customer.type_confidence = 0.5
            customer.type_evidence = f"基于LLM推断：{predicted}"
    except Exception:
        if types:
            customer.primary_type = types[0].name
            customer.type_confidence = 0.3
            customer.type_evidence = "LLM 不可用，使用默认类型"

    db.commit()
    db.refresh(customer)
    return customer
