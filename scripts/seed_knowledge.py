from pathlib import Path
import json


knowledge_dir = Path("/Users/jarod/Dev/sales/backend/data/knowledge")
knowledge_dir.mkdir(parents=True, exist_ok=True)

sample_types = [
    {"code": "BRAND_AMBITION", "name": "品牌野心型", "signal": "我要做行业第一", "pain": "担心品牌投入没有长期回报", "strategy": "把投放定义为品牌资产投资", "taboo": "只谈CPM/短期流量成本", "case_code": "FEIHE"},
    {"code": "POSITIONING", "name": "定位卡位型", "signal": "这个位置我先占", "pain": "担心消费者优先选择竞品", "strategy": "提炼15秒心智超级话语", "taboo": "只求规模声量", "case_code": "MIAOKELD"},
]

sample_cases = [
    {"code": "FEIHE", "title": "飞鹤奶粉", "type": "品牌野心型", "industry": "母婴", "stage": "全国化扩张", "result": "营收从35亿提升到200亿+"},
    {"code": "MIAOKELD", "title": "妙可蓝多", "type": "定位卡位型", "industry": "食品", "stage": "心智抢占", "result": "市场份额从3.9%提升到30.9%"},
]

(knowledge_dir / "customer_types.json").write_text(json.dumps(sample_types, ensure_ascii=False, indent=2), encoding="utf-8")
(knowledge_dir / "cases.json").write_text(json.dumps(sample_cases, ensure_ascii=False, indent=2), encoding="utf-8")
print("knowledge seeded")
