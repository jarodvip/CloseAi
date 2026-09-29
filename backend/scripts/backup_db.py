"""SQLite 数据库备份脚本（v1.0 备份策略）。

用法：
    cd backend && PYTHONPATH=. python scripts/backup_db.py [--keep 14] [--out backups]

- 使用 sqlite3 backup API 在线备份，不锁表、不影响运行中的服务
- 仅处理 SQLite 数据库；PostgreSQL 部署请使用 pg_dump（见 docs/README.md）
- --keep 保留最近 N 份，超出自动清理（默认 14）
"""
import argparse
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings  # noqa: E402


def sqlite_file_from_url(url: str) -> Path | None:
    match = re.match(r"sqlite:///(.*)", url)
    if not match:
        return None
    path = Path(match.group(1))
    return path if path.is_absolute() else ROOT / path


def main(keep: int, out_dir: str) -> int:
    db_file = sqlite_file_from_url(settings.DATABASE_URL)
    if not db_file or not db_file.exists():
        print(f"非 SQLite 或数据库文件不存在：{settings.DATABASE_URL}（PostgreSQL 请用 pg_dump）")
        return 1
    out = ROOT / out_dir
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = out / f"{db_file.stem}_{stamp}.db"

    src = sqlite3.connect(str(db_file))
    dst = sqlite3.connect(str(target))
    with dst:
        src.backup(dst)
    src.close()
    dst.close()
    print(f"[backup] 已备份 {db_file} -> {target}")

    backups = sorted(out.glob(f"{db_file.stem}_*.db"))
    for old in backups[:-keep] if keep > 0 else []:
        old.unlink()
        print(f"[backup] 清理过期备份 {old.name}")
    print(f"[backup] 当前保留 {min(len(backups), keep)} 份")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", type=int, default=14, help="保留最近 N 份备份")
    parser.add_argument("--out", type=str, default="backups", help="备份输出目录（相对 backend/）")
    args = parser.parse_args()
    sys.exit(main(args.keep, args.out))
