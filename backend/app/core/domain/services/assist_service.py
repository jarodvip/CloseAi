from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.core.domain.services.common import build_source_cards, build_system_prompt, collect_source_refs, format_evidence_text, to_code
from app.core.domain.services.customer_service import get_customer
from app.core.domain.services.knowledge_service import get_customer_type_by_code, list_evidence, list_scripts
from app.core.domain.services.llm_service import generate_text


def build_assist(db: Session, customer_id: int, payload: Dict) -> Dict:
    customer = get_customer(db, customer_id)
    if not customer:
        return {}
    current_stage = payload.get("current_stage") or "听"
    transcript = (payload.get("transcript") or "").strip()
    customer_type = customer.primary_type or payload.get("customer_type") or "品牌野心型"
    type_info = get_customer_type_by_code(db, to_code(customer_type))
    detected_stage = _detect_stage(transcript) if transcript else current_stage
    objection, objection_response = _detect_objection(transcript)
    matched_script = next((item for item in list_scripts(db) if item.type in {customer_type, "通用"}), None)
    evidence = list_evidence(db)[:3]
    evidence_text = format_evidence_text(evidence)
    prompt = f"""请基于销售五步法生成会中辅助建议。
当前阶段：{detected_stage}
客户类型：{customer_type}
客户输入：{transcript or '暂无输入'}
识别到的异议：{objection or '无'}
权威证据：{evidence_text or '暂无'}
请输出：阶段提示、可执行话术、异议应答、2条操作提醒、来源说明。"""
    llm_text = ""
    try:
        llm_text = generate_text(prompt, system=build_system_prompt("assist", customer_type, type_info, evidence))
    except Exception:
        llm_text = ""
    source_cards = build_source_cards(type_info, matched_script, evidence)
    source_refs = collect_source_refs(type_info, matched_script, evidence)
    return {
        "current_stage": current_stage,
        "detected_stage": detected_stage,
        "stage_guidance": _stage_guidance(detected_stage, customer_type),
        "suggested_response": matched_script.template if matched_script else None,
        "objection_detected": objection,
        "objection_response": objection_response,
        "notes": [
            "继续用具体行业事实代替空洞共情。",
            "如果客户提到预算，优先给低门槛测试方案。",
        ],
        "source_cards": source_cards,
        "source_refs": source_refs,
        "llm_text": llm_text or None,
    }


def _detect_stage(transcript: str) -> str:
    text = transcript.lower()
    if any(k in text for k in ["为什么", "目前最大的问题是", "你们现在的目标"]):
        return "听"
    if any(k in text for k in ["总结一下", "你的意思是", "核心问题是"]):
        return "认"
    if any(k in text for k in ["xx也做过", "有没有类似", "参考"]):
        return "比"
    if any(k in text for k in ["多久能见效", "回报", "数据", "预期"]):
        return "算"
    if any(k in text for k in ["那就先测", "下一步", "下周", "对接"]):
        return "定"
    return "听"


def _detect_objection(transcript: str):
    objections = {
        "太贵了": "先拆单次触达成本，再给同量级案例。",
        "我们再看看": "协助梳理决策链，锁定关键人诉求。",
        "投过线上，效果不好": "说明线上线下互补逻辑，优化投放模型。",
        "我们品牌太小": "提供小预算区域化测试方案。",
        "老板不同意": "挖掘老板关心的经营指标，重构方案。",
    }
    for key, value in objections.items():
        if key in transcript.lower():
            return key, value
    return None, None


def _stage_guidance(stage, customer_type):
    base = {
        "听": "继续问行业现状、增长目标和决策链，少讲分众资源。",
        "认": "用一句话点破客户核心瓶颈，建立专业信任。",
        "比": "引用同类型同阶段案例，说明为什么可行。",
        "算": "给出测试方案、时间周期、可量化预期。",
        "定": "把下一步变成具体动作，比如试点城市或对接人。",
    }
    return base.get(stage, base["听"])
