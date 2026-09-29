from typing import Dict, List, Optional
from datetime import datetime
import re
from sqlalchemy.orm import Session
from app.core.domain.services.common import build_source_cards, build_system_prompt, collect_source_refs, format_evidence_text, to_code
from app.core.domain.services.customer_service import get_customer
from app.core.domain.services.knowledge_service import get_customer_type_by_code, list_evidence, list_scripts, create_suggestion, suggestion_dict
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
    matched_script = next((item for item in list_scripts(db, shared_only=True) if item.type in {customer_type, "通用"}), None)
    evidence = list_evidence(db)[:3]
    evidence_text = format_evidence_text(evidence)
    prompt = f"""你是销售助理，请基于会议信息生成会后跟进包，输出简洁中文，可直接使用。

客户：{customer.name}
类型：{customer_type}
会议摘要：{summary}
决策结果：{', '.join(decisions)}
待办动作：{', '.join(pending_actions)}
权威证据：{evidence_text or '暂无'}

请按以下格式输出：
【结构化摘要】本次拜访核心结论
【任务清单】3-5个具体跟进任务及优先级
【邮件草稿】正式跟进邮件正文
【微信跟进话术】简洁的消息话术
【知识沉淀建议】本次拜访是否有新模板/案例值得入库
【来源说明】引用知识的来源"""
    llm_text = ""
    try:
        llm_text = generate_text(prompt, system=build_system_prompt("followup", customer_type, type_info, evidence), scene="followup")
    except Exception:
        llm_text = ""
    source_cards = build_source_cards(type_info, matched_script, evidence)
    source_refs = collect_source_refs(type_info, matched_script, evidence)
    suggestions = _create_suggestion_drafts(db, customer, payload, customer_type,
                                            username=payload.get("username"), llm_text=llm_text)
    return {
        "summary": summary,
        "decisions": decisions,
        "pending_actions": pending_actions,
        "followup_email": _email(summary, customer_type),
        "followup_wechat": _wechat(summary),
        "tasks": _tasks(pending_actions),
        "knowledge_update_suggestion": (
            f"已生成 {len(suggestions)} 条知识沉淀建议，待管理员审核入库。" if suggestions
            else "本次暂未发现必须沉淀的新模板。"
        ),
        "knowledge_suggestions": [suggestion_dict(s) for s in suggestions],
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


def _extract_llm_suggestion(llm_text: str) -> str:
    """从 LLM 输出中提取【知识沉淀建议】段；无该段或为空则返回空串"""
    if not llm_text:
        return ""
    match = re.search(r"【知识沉淀建议】(.+?)(?=【|$)", llm_text, re.S)
    if not match:
        return ""
    text = match.group(1).strip().strip("：:")
    # LLM 无 key 时会带回模拟提示头，直接判为无效内容
    if not text or "规则引擎" in text[:20]:
        return ""
    return text[:2000]


def _create_suggestion_drafts(db: Session, customer, payload: Dict, customer_type: str,
                              username: Optional[str], llm_text: str) -> list:
    """拜访中出现异议/预算信号时，自动生成一条话术沉淀草稿（待 admin 审核）"""
    transcript = payload.get("transcript") or ""
    if "异议" not in transcript and "预算" not in transcript:
        return []
    llm_suggestion = _extract_llm_suggestion(llm_text)
    content = llm_suggestion or (
        f"客户原话：{transcript[:120]}\n"
        f"建议应答：先拆单次触达成本，再给同量级案例，落到低门槛测试方案。"
    )
    try:
        return [create_suggestion(db, {
            "customer_id": customer.id,
            "customer_name": customer.name,
            "username": username,
            "suggestion_type": "script",
            "scene": "异议应答",
            "ktype": customer_type,
            "title": f"{customer.name} 异议应答沉淀",
            "content": content,
        })]
    except Exception:
        # 草稿落库失败不影响跟进包主流程
        return []
