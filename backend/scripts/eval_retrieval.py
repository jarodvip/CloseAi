"""检索相关性评测集：对比纯 FTS 与混合检索（FTS+向量 RRF）的命中率。

用法：
    cd backend && PYTHONPATH=. python scripts/eval_retrieval.py

评测集为「查询 → 期望命中的标题关键词」的标注对，跑两类指标：
- hit@k：top-k 结果中是否包含任一期望关键词
- MRR：首个命中的倒数排名

embedding 接口不可用时，混合列与 FTS 列一致（自动降级），并在报告尾部提示。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.session import SessionLocal  # noqa: E402
from app.core.domain.services import research_service  # noqa: E402
from app.core.domain.services import embedding_service  # noqa: E402

# 标注评测集：query 与期望命中的 chunk 标题/内容关键词（人工标注，可持续扩充）
EVAL_SET = [
    {"query": "客户最近融资了，怎么切入", "expect": ["融资", "资本"]},
    {"query": "广告投放预算怎么拆", "expect": ["预算", "投放", "成本"]},
    {"query": "他们投过线上效果不好", "expect": ["线上", "投放", "效果"]},
    {"query": "竞品在做电梯广告我们要不要跟", "expect": ["竞", "电梯", "广告"]},
    {"query": "新品牌要做品类开创", "expect": ["品类", "开创", "新品"]},
    {"query": "老板担心效果没法衡量", "expect": ["效果", "衡量", "衡量", "数据"]},
    {"query": "二三线城市扩张策略", "expect": ["城市", "扩张", "区域"]},
    {"query": "品牌升级焕新案例", "expect": ["焕新", "升级", "品牌"]},
]

K = 3


def _hit_rate_and_mrr(runs):
    """runs: {mode: [[chunk, ...], ...]} → {mode: (hit@k, mrr)}"""
    stats = {}
    for mode, results in runs.items():
        hits = 0
        rr_sum = 0.0
        for result, case in zip(results, EVAL_SET):
            expect = case["expect"]
            rr = 0.0
            for rank, chunk in enumerate(result[:K], start=1):
                text = f"{chunk.title or ''} {chunk.content or ''}"
                if any(kw in text for kw in expect):
                    rr = 1.0 / rank
                    break
            if rr:
                hits += 1
            rr_sum += rr
        stats[mode] = (round(hits / len(results), 4), round(rr_sum / len(results), 4))
    return stats


def main() -> int:
    db = SessionLocal()
    try:
        # embedding 可用性探测：不可用时混合检索自动等于纯 FTS
        probe = embedding_service.embed_texts(["探测"])
        hybrid_available = probe is not None

        runs = {"fts": [], "hybrid": []}
        for case in EVAL_SET:
            # 纯 FTS：临时屏蔽向量召回
            original = research_service._vector_search_ids
            research_service._vector_search_ids = lambda *a, **kw: []
            try:
                runs["fts"].append(research_service.search_research(db, case["query"], k=5))
            finally:
                research_service._vector_search_ids = original
            runs["hybrid"].append(research_service.search_research(db, case["query"], k=5))

        stats = _hit_rate_and_mrr(runs)
        print(f"评测集：{len(EVAL_SET)} 条查询，k={K}")
        print(f"{'模式':<8}{'hit@k':<10}{'MRR':<10}")
        for mode, (hit, mrr) in stats.items():
            print(f"{mode:<8}{hit:<10}{mrr:<10}")
        if not hybrid_available:
            print("\n提示：embedding 接口不可用，hybrid 与 fts 结果一致。"
                  "配置 LLM_BASE_URL/LLM_API_KEY/LLM_EMBEDDING_MODEL 后重跑。")
        else:
            delta = stats["hybrid"][0] - stats["fts"][0]
            print(f"\n混合检索 hit@{K} 提升：{delta:+.4f}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
