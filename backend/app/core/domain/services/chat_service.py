from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import json

from app.models.chat import ChatSession, ChatMessage
from app.core.domain.services.customer_service import get_customer
from app.core.domain.services.knowledge_service import get_customer_type_by_code, list_cases, list_evidence, list_scripts
from app.core.domain.services.llm_service import generate_text

def create_session(db: Session, payload: dict) -> ChatSession:
    customer_id = payload.get("customer_id")
    title = (payload.get("title") or "").strip() if payload.get("title") is not None else None
    if title is None:
        title = f"会话 #{_next_session_id(db)}"
    session = ChatSession(customer_id=customer_id, title=title, created_at=datetime.now().isoformat())
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

def list_sessions(db: Session, customer_id: Optional[int] = None) -> List[ChatSession]:
    query = db.query(ChatSession)
    if customer_id is not None:
        query = query.filter(ChatSession.customer_id == customer_id)
    return query.order_by(ChatSession.id.desc()).all()

def get_session(db: Session, session_id: int) -> Optional[ChatSession]:
    return db.query(ChatSession).filter(ChatSession.id == session_id).first()

def list_messages(db: Session, session_id: int) -> List[ChatMessage]:
    return db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.id.asc()).all()

def create_message(db: Session, session_id: int, payload: dict) -> ChatMessage:
    message = ChatMessage(**payload, session_id=session_id, created_at=datetime.now().isoformat())
    db.add(message)
    db.commit()
    db.refresh(message)
    return message

def rename_session(db: Session, session_id: int, title: Optional[str]) -> Optional[ChatSession]:
    session = get_session(db, session_id)
    if not session:
        return None
    if title is not None:
        title = title.strip()
        if title:
            session.title = title
    db.commit()
    db.refresh(session)
    return session

def build_reply(db: Session, session_id: int, content: str) -> dict:
    history = list_messages(db, session_id)
    chat_session = get_session(db, session_id)
    customer = get_customer(db, chat_session.customer_id) if chat_session and chat_session.customer_id else None
    context = _build_context(db, customer, history, content)
    llm_text = ""
    try:
        llm_text = generate_text(content, system=_system_prompt(customer, context))
    except Exception:
        llm_text = ""
    reply_text = llm_text or _rule_reply(customer, content)
    meta = {
        "customer_name": customer.name if customer else None,
        "primary_type": customer.primary_type if customer else None,
        "evidence_text": context.get("evidence_text", ""),
        "source_cards": context.get("source_cards", []),
        "source_refs": context.get("source_refs", []),
    }
    message = create_message(db, session_id, {"role": "assistant", "content": reply_text, "meta": _encode_meta(meta)})
    if not chat_session.title or chat_session.title.startswith("会话 #"):
        candidate = (llm_text or reply_text).strip().split("\n")[0]
        candidate = candidate.replace("【", "").replace("】", "").strip()
        if len(candidate) > 24:
            candidate = candidate[:24] + "…"
        if candidate:
            chat_session.title = candidate
            db.add(chat_session)
            db.commit()
            db.refresh(chat_session)
    return {"session_id": session_id, "message": message, "trace_id": f"chat-{session_id}-{message.id}"}

def _encode_meta(meta: Dict[str, Any]) -> str:
    try:
        return json.dumps(meta, ensure_ascii=False)
    except Exception:
        return str(meta)

def _build_context(db: Session, customer, history, user_content: str) -> dict:
    customer_type = (customer.primary_type or "") if customer else ""
    cases = list_cases(db=db, query=customer_type)[:3]
    type_info = get_customer_type_by_code(db, _to_code(customer_type)) if customer_type else None
    matched_script = next((item for item in list_scripts(db) if item.type in {customer_type, "通用"}), None)
    evidence = list_evidence(db=db)[:3]
    evidence_text = "；".join([f"{e.source}: {e.metric}={e.value}" for e in evidence if e.source and e.value])
    source_cards = _collect_source_cards(type_info, matched_script, evidence)
    source_refs = [card["source"] for card in source_cards]
    return {
        "customer_name": customer.name if customer else None,
        "customer_type": customer_type or None,
        "history": [{"role": item.role, "content": item.content} for item in history[-8:]],
        "evidence_text": evidence_text,
        "source_cards": source_cards,
        "source_refs": source_refs,
    }

def _system_prompt(customer, context) -> str:
    name = customer.name if customer else "潜在客户"
    ctype = customer.primary_type if customer else "待判断"
    evidence_text = context.get("evidence_text", "")
    return (
        "你是销售攻单AI助手，输出简洁、专业、可直接使用的中文销售建议。"
        f"客户：{name}，类型：{ctype}。"
        f"权威证据：{evidence_text or '暂无'}。"
        "请在建议中明确引用来源。"
    )

def _rule_reply(customer, content: str) -> str:
    text = content.lower()
    if "简报" in text or "会前" in text:
        return "建议先明确客户增长瓶颈，再给一句场景化切入话术和一个低门槛测试方案。"
    if "异议" in text or "太贵" in text:
        return "先把预算拆成月度触达成本，再用同类型案例降低决策风险。"
    if "跟进" in text or "会后" in text:
        return "会后跟进优先确认决策人、时间与下一步动作，避免只发感想型消息。"
    return f"我已记录：{content}。你可以继续追问客户类型、会中应对话术或会后动作。"

def _collect_source_cards(type_info, matched_script, evidence) -> List[Dict[str, Optional[str]]]:
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

def _next_session_id(db: Session) -> int:
    from sqlalchemy import func
    result = db.query(func.max(ChatSession.id)).scalar()
    return int(result or 0) + 1
