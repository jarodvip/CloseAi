"""为存量 research_chunks 回填 embedding 向量（v0.8 混合检索升级）。

用法：
    cd backend && PYTHONPATH=. python scripts/backfill_embeddings.py [--batch 32]

未配置可用的 embedding 接口时直接提示退出，不影响任何数据。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.session import SessionLocal  # noqa: E402
from app.models.research import ResearchChunk  # noqa: E402
from app.core.domain.services import embedding_service  # noqa: E402


def main(batch_size: int = 32) -> int:
    db = SessionLocal()
    try:
        rows = db.query(ResearchChunk).filter(ResearchChunk.embedding.is_(None)).all()
        if not rows:
            print("没有待回填的分块，退出。")
            return 0
        total = len(rows)
        done = failed = 0
        for start in range(0, total, batch_size):
            part = rows[start:start + batch_size]
            vectors = embedding_service.embed_texts(
                [f"{c.title or ''}\n{c.content or ''}" for c in part]
            )
            if vectors is None:
                failed += len(part)
                continue
            for chunk, vec in zip(part, vectors):
                chunk.embedding = embedding_service.to_blob(vec)
                done += 1
            db.commit()
            print(f"[backfill] {min(start + batch_size, total)}/{total}")
        if failed:
            print(f"[backfill] 完成 {done} 条，{failed} 条向量化失败（接口不可用），可稍后重跑。")
        else:
            print(f"[backfill] 全部完成：{done} 条。")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    batch = 32
    if "--batch" in sys.argv:
        batch = int(sys.argv[sys.argv.index("--batch") + 1])
    sys.exit(main(batch))
