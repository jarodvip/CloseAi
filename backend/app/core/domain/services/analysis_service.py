from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from app.core.domain.services.common import to_code
from app.core.domain.services.customer_service import get_customer, list_customers, create_customer
from app.core.domain.services.knowledge_service import get_customer_type_by_code, list_cases, list_evidence
from app.core.domain.services.briefing_service import build_briefing
from app.schemas.customer import CustomerIn


def analyze_customer(db: Session, payload: dict, owner_id: int = 0) -> Dict[str, Any]:
    name = (payload.get("name") or "").strip()
    if not name:
        return {"error": "客户名称不能为空"}

    existing = list_customers(db, owner_id)
    matched = next((c for c in existing if c.name == name), None)

    if matched:
        customer_id = matched.id
        customer = matched
    else:
        customer = create_customer(db, CustomerIn(**{k: v for k, v in payload.items() if k in {"name", "industry", "revenue_range", "stage", "region"}}), owner_id)
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


def _extract_keywords(text: str) -> list:
    """提取中文关键词（按标点分词，保留有意义的片段）"""
    if not text:
        return []
    # 按常见分隔符分割
    import re
    parts = re.split(r'[，,、\s]+', text)
    # 过滤掉太短的片段，保留2-6字的有意义词组
    keywords = [p.strip() for p in parts if 2 <= len(p.strip()) <= 6]
    return list(dict.fromkeys(keywords))  # 去重保持顺序


def _keyword_score(name: str, industry: str, stage: str, text: str) -> int:
    """计算关键词匹配分数（精确匹配优先）"""
    if not text:
        return 0
    combined = f"{name} {industry or ''} {stage or ''}"
    keywords = _extract_keywords(text)
    score = 0
    for kw in keywords:
        if kw in combined:
            # 长词组匹配权重更高
            score += len(kw)
    return score


def _explicit_pattern_match(name: str, industry: str) -> tuple:
    """基于客户名称和行业做显式模式匹配（高置信度）"""
    patterns = {
        "品牌野心型": {"keywords": ["品牌", "第一", "头部", "领军"], "weight": 8},
        "全国化扩张型": {"keywords": ["全国", "出省", "连锁", "扩张", "区域"], "weight": 8},
        "资本叙事型": {"keywords": ["融资", "资本", "上市", "IPO", "估值"], "weight": 8},
        "品牌焕新型": {"keywords": ["焕新", "年轻", "升级", "转型", "重构"], "weight": 8},
        "品类开创者型": {"keywords": ["首创", "新品类", "开创", "革新", "颠覆"], "weight": 8},
        "竞争突围型": {"keywords": ["突围", "翻盘", "破局", "竞争", "红海"], "weight": 8},
        "定位卡位型": {"keywords": ["定位", "卡位", "细分", "心智", "占据"], "weight": 8},
    }

    name_lower = name.lower() if name else ""
    combined = f"{name_lower} {industry or ''}".lower()

    best_type = None
    best_score = 0
    best_evidence = ""

    for type_name, config in patterns.items():
        score = 0
        evidence_parts = []
        for kw in config["keywords"]:
            if kw in combined:
                score += config["weight"]
                evidence_parts.append(f"名称包含'{kw}'")
        if score > best_score:
            best_score = score
            best_type = type_name
            best_evidence = "；".join(evidence_parts)

    return best_type, best_score, best_evidence


def _rule_match_type(db: Session, customer) -> tuple:
    """基于知识库 signal/pain 字段做规则匹配，返回 (type_name, confidence, evidence)"""
    from app.models.knowledge import CustomerTypeKnowledge, Case

    types = db.query(CustomerTypeKnowledge).all()
    if not types:
        return None, 0, ""

    name = customer.name or ""
    industry = customer.industry or ""
    stage = customer.stage or ""

    # Step 1: 显式模式匹配（高权重）
    pattern_type, pattern_score, pattern_evidence = _explicit_pattern_match(name, industry)
    if pattern_score >= 8:
        return pattern_type, 0.75, f"模式匹配：{pattern_evidence}"

    # Step 2: 基于知识库 signal/pain 的关键词匹配
    best_match = None
    best_score = 0
    best_evidence = ""

    for t in types:
        score = 0
        evidence_parts = []

        # 匹配 signal 字段（整体短语优先）
        if t.signal:
            if t.signal in name or t.signal in (industry or ""):
                score += 10
                evidence_parts.append(f"signal精确匹配:{t.signal}")
            else:
                s = _keyword_score(name, industry, stage, t.signal)
                if s > 0:
                    score += s
                    evidence_parts.append(f"signal匹配:{t.signal[:20]}...")

        # 匹配 pain 字段
        if t.pain:
            if t.pain in name or t.pain in (industry or ""):
                score += 8
                evidence_parts.append(f"pain精确匹配:{t.pain}")
            else:
                p = _keyword_score(name, industry, stage, t.pain)
                if p > 0:
                    score += p * 0.5
                    evidence_parts.append(f"pain匹配:{t.pain[:20]}...")

        # 行业案例匹配（低权重）
        if industry:
            matching_cases = db.query(Case).filter(
                Case.industry == industry
            ).count()
            if matching_cases > 0:
                score += matching_cases * 1
                evidence_parts.append(f"{industry}案例:{matching_cases}个")

        if score > best_score:
            best_score = score
            best_match = t
            best_evidence = "；".join(evidence_parts) if evidence_parts else "关键词匹配"

    if best_match and best_score >= 3:
        confidence = min(0.5 + best_score * 0.05, 0.75)
        return best_match.name, round(confidence, 2), best_evidence

    return None, 0, ""


def _infer_type(db: Session, customer, payload: dict) -> Any:
    """根据客户名称和已有知识库做类型推断（规则优先，LLM 增强）"""
    from app.core.domain.services.llm_service import generate_text
    from app.core.domain.services.common import format_evidence_text
    from app.models.knowledge import CustomerTypeKnowledge

    types = db.query(CustomerTypeKnowledge).all()

    # Step 1: 规则匹配
    rule_name, rule_confidence, rule_evidence = _rule_match_type(db, customer)

    if rule_name:
        customer.primary_type = rule_name
        customer.type_confidence = rule_confidence
        customer.type_evidence = f"规则匹配：{rule_evidence}"
        db.commit()
        db.refresh(customer)
        return customer

    # Step 2: 规则未命中，尝试 LLM
    stage_info = f"行业={customer.industry or '未知'}, 阶段={customer.stage or '未知'}"
    evidence = list_evidence(db)[:3]
    evidence_text = format_evidence_text(evidence)
    type_list = "\n".join([f"- {t.name}: 信号={t.signal}" for t in types])

    prompt = f"""请根据客户名称判断其最可能的客户类型。
客户名称：{customer.name}
{stage_info}
可选类型：
{type_list}
权威证据：{evidence_text or '暂无'}
请只输出最匹配的类型名称，例如：品牌野心型"""

    try:
        result = generate_text(prompt, scene="analyze")
        predicted = result.strip().split("\n")[0].strip()
        matched_type = next((t for t in types if predicted in t.name or t.name in predicted), None)
        if matched_type:
            customer.primary_type = matched_type.name
            customer.type_confidence = 0.7
            customer.type_evidence = f"LLM推断+规则兜底：{predicted}"
        else:
            customer.primary_type = predicted[:50]
            customer.type_confidence = 0.5
            customer.type_evidence = f"LLM推断（未匹配到知识库类型）：{predicted}"
    except Exception:
        if types:
            # LLM 也失败时，回退到规则匹配结果或默认值
            if rule_name:
                customer.primary_type = rule_name
                customer.type_confidence = rule_confidence
                customer.type_evidence = f"规则匹配（LLM不可用）：{rule_evidence}"
            else:
                customer.primary_type = types[0].name
                customer.type_confidence = 0.3
                customer.type_evidence = "LLM 不可用，使用知识库默认类型"
        else:
            customer.primary_type = "未知类型"
            customer.type_confidence = 0.1
            customer.type_evidence = "知识库为空，无法推断"

    db.commit()
    db.refresh(customer)
    return customer
