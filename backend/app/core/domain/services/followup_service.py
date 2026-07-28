from typing import Dict, List
from sqlalchemy.orm import Session
from app.core.domain.services.customer_service import get_customer
from app.core.domain.services.knowledge_service import get_customer_type_by_code, list_scripts, list_evidence
from app.core.domain.services.llm_service import generate_text

def build_followup(db: Session, customer_id: int, payload: Dict) -> Dict:
    customer = get_customer(db, customer_id)
    if not customer:
        return {}
    summary = payload.get("summary") or "本次拜访待进一步结构化。"
    decisions = payload.get("decisions") or []
    pending_actions = payload.get("pending_actions") or []
    customer_type = customer.primary_type or payload.get("customer_type") or "品牌野心型"
    type_info = get_customer_type_by_code(db, _to_code(customer_type))
    matched_script = next((item for item in list_scripts(db) if item.type in {customer_type, "通用"}), None)
    evidence = list_evidence(db)[:3]
    evidence_text = "；".join([f"{e.source}: {e.metric}={e.value}" for e in evidence if e.source and e.value])
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
        llm_text = generate_text(prompt, system=_system_prompt(customer_type, type_info, evidence))
    except Exception:
        llm_text = ""
    source_cards = _build_source_cards(type_info, matched_script, evidence)
    source_refs = [card["source"] for card in source_cards]
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

def _to_code(name: str) -> str:
    mapping = {
        "品牌野心型": "BRAND_AMBITION",
        "定位卡位型": "POSITIONING",
        "品类开创者型": "CATEGORY_CREATOR",
        "竞争突围型": "COMPETITIVE_BREAKOUT",
        "资本叙事型": "CAPITAL_NARRATIVE",
        "全国化扩张型": "NATIONAL_EXPANSION",
        "品牌焕新型": "BRAND_REJUVENATION",
    }
    return mapping.get(name, name.upper())

def _system_prompt(customer_type, type_info, evidence) -> str:
    ctype = type_info.name if type_info else customer_type
    evidence_text = "；".join([f"{e.source}: {e.metric}={e.value}" for e in evidence[:3] if e.source and e.value])
    return (
        "你是销售助理，输出简洁中文，可直接用于会后跟进。"
        f"客户类型：{ctype}。"
        f"权威证据：{evidence_text or '暂无'}。"
        "请在建议中明确引用来源。"
    )

def _collect_source_refs(type_info, matched_script, evidence) -> List[str]:
    cards = _build_source_cards(type_info, matched_script, evidence)
    refs: List[str] = []
    seen = set()
    for card in cards:
        source = card.get("source")
        if not source or source in seen:
            continue
        seen.add(source)
        refs.append(source)
    return refs


def _build_source_cards(type_info, matched_script, evidence) -> List[Dict[str, Optional[str]]]:
    cards: List[Dict[str, Optional[str]]] = []
    seen = set()

    def add(source: Optional[str], label: str, detail: Optional[str] = None, scene: Optional[str] = None):
        if not source:
            return
        key = (source, label, detail or "")
        if key in seen:
            return
        seen.add(key)
        cards.append({"source": source, "label": label, "detail": detail, "scene": scene})

    if type_info and type_info.source:
        add(type_info.source, "客户类型策略", type_info.strategy, type_info.name)
    if matched_script and matched_script.source:
        add(matched_script.source, "话术", matched_script.template, matched_script.scene)
    for item in evidence:
        if item.source_ref or item.source:
            add(item.source_ref or item.source, f"证据：{item.metric}", item.value, item.scene)
    return cards


def _collect_source_refs(type_info, matched_script, evidence) -> List[str]:
    refs: List[str] = []
    seen = set()

    def add(item):
        if not item:
            return
        key = str(item)
        if key in seen:
            return
        seen.add(key)
        refs.append(item)

    if type_info and type_info.source:
        add(type_info.source)
    if matched_script and matched_script.source:
        add(matched_script.source)
    for item in evidence:
        if item.source_ref or item.source:
            add(item.source_ref or item.source)
    return refs

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
