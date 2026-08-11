from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.domain.services.common import build_source_cards, build_system_prompt, collect_source_refs, format_evidence_text, to_code
from app.core.domain.services.customer_service import get_customer
from app.core.domain.services.knowledge_service import get_customer_type_by_code, list_evidence, list_scripts
from app.core.domain.services.llm_service import generate_text


def build_followup(db: Session, customer_id: int, payload: Dict) -> Dict:
    customer = get_customer(db, customer_id)
    if not customer:
        return {}
    summary = payload.get("summary") or "本次拜访待进一步结构化。"
    decisions = payload.get("decisions") or []
    pending_actions = payload.get("pending_actions") or []
    customer_type = customer.primary_type or payload.get("customer_type") or "品牌野心型"
    type_info = get_customer_type_by_code(db, to_code(customer_type))
    matched_script = next((item for item in list_scripts(db) if item.type in {customer_type, "通用"}), None)
    evidence = list_evidence(db)[:3]
    evidence_text = format_evidence_text(evidence)
    prompt = f"""请基于会议信息生成会后跟进包。
客户：{customer.name}
类型：{customer_type}
摘要：{summary}
决策：{', '.join(decisions)}
待办：{', '.join(pending_actions)}
权威证据：{evidence_text or '暂无'}
请输出：结构化摘要、任务清单、邮件草稿、微信跟进话术、知识沉淀建议、来源说明。"""
    llm_text = ""
    try:
        llm_text = generate_text(prompt, system=build_system_prompt("followup", customer_type, type_info, evidence))
    except Exception:
        llm_text = ""
    source_cards = build_source_cards(type_info, matched_script, evidence)
    source_refs = collect_source_refs(type_info, matched_script, evidence)
    return {
        "summary": summary,
        "decisions": decisions,
        "pending_actions": pending_actions,
        "followup_email": _email(summary, customer_type),
        "followup_wechat": _wechat(summary),
        "tasks": _tasks(pending_actions),
        "knowledge_update_suggestion": _knowledge_update(payload),
        "source_cards": source_cards,
        "source_refs": source_refs,
        "llm_text": llm_text or None,
    }


def _email(summary, customer_type):
    return f"【客户攻单AI】跟进邮件草稿：围绕 {customer_type} 的下一步，建议补充品牌资产测算或试点方案，核心信息：{summary}"


def _wechat(summary):
    return f"【跟进】根据今天沟通，我整理了三项下一步：{summary}，方便时请您确认优先级。"


def _tasks(pending_actions):
    tasks = []
    if not pending_actions:
        tasks.append({"title": "发送测试方案", "deadline": "3个工作日内"})
        tasks.append({"title": "确认关键决策人", "deadline": "2个工作日内"})
        return tasks
    for item in pending_actions:
        tasks.append({"title": item, "deadline": "3个工作日内"})
    return tasks


def _knowledge_update(payload):
    transcript = payload.get("transcript") or ""
    if "异议" in transcript or "预算" in transcript:
        return "建议新增一条该客户类型的常见异议应答。"
    return "本次暂未发现必须沉淀的新模板。"
