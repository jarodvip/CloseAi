"""公共工具函数，供各 service 层复用。"""

from typing import Any, Dict, List, Optional


# 客户类型中文名 → 英文代码映射
TYPE_CODE_MAP = {
    "品牌野心型": "BRAND_AMBITION",
    "定位卡位型": "POSITIONING",
    "品类开创者型": "CATEGORY_CREATOR",
    "竞争突围型": "COMPETITIVE_BREAKOUT",
    "资本叙事型": "CAPITAL_NARRATIVE",
    "全国化扩张型": "NATIONAL_EXPANSION",
    "品牌焕新型": "BRAND_REJUVENATION",
}


def to_code(name: str) -> str:
    return TYPE_CODE_MAP.get(name, name.upper())


def format_evidence_text(evidence: list, limit: Optional[int] = None) -> str:
    items = evidence if limit is None else evidence[:limit]
    return "；".join([f"{e.source}: {e.metric}={e.value}" for e in items if e.source and e.value])


def build_source_cards(type_info, matched_script, evidence: list) -> List[Dict[str, Optional[str]]]:
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


def build_source_cards_for_cases(type_info, cases: list, evidence: list) -> List[Dict[str, Optional[str]]]:
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
    for item in cases:
        if item.get("source"):
            add(item.get("source"), f"案例：{item.get('title')}", f"{item.get('type')} / {item.get('industry')} / {item.get('stage')}")
    for item in evidence:
        if item.source_ref or item.source:
            add(item.source_ref or item.source, f"证据：{item.metric}", item.value, item.scene)
    return cards


def collect_source_refs(type_info, matched_script, evidence: list) -> List[str]:
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


def build_system_prompt(
    role: str,
    customer_type: str,
    type_info,
    evidence: list,
    customer: Any = None,
) -> str:
    ctype = type_info.name if type_info else customer_type
    evidence_text = "；".join([f"{e.source}: {e.metric}={e.value}" for e in evidence[:3] if e.source and e.value])

    role_prompts = {
        "briefing": "你是销售作战助手，输出简洁、可执行、专业的中文建议。",
        "assist": "你是会中销售辅助助手，输出中文、可直接使用的话术与操作建议。",
        "followup": "你是销售助理，输出简洁中文，可直接用于会后跟进。",
        "chat": "你是销售攻单AI助手，输出简洁、专业、可直接使用的中文销售建议。",
    }
    intro = role_prompts.get(role, "你是销售助手，输出简洁中文。")

    if customer and hasattr(customer, "name"):
        return f"{intro}客户：{customer.name}；类型：{ctype}。权威证据：{evidence_text or '暂无'}。请在建议中明确引用来源。"
    return f"{intro}客户类型：{ctype}。权威证据：{evidence_text or '暂无'}。请在建议中明确引用来源。"
