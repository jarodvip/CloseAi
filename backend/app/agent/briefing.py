from typing import Dict


def build_briefing(customer: Dict) -> Dict:
    industry = customer.get("industry") or "未填写行业"
    return {
        "customer_name": customer.get("name"),
        "likely_type": customer.get("primary_type") or "待判断",
        "confidence": customer.get("type_confidence") or 0.0,
        "opening_line": "老板，我关注你们很久了，我觉得你们有成为行业第一的基因。",
        "focus": f"围绕 {industry} 的品牌资产沉淀与增长瓶颈展开。",
        "next_step": "建议先做1个核心城市1个月品牌认知测试方案。",
    }
