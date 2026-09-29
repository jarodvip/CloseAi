import sys
import logging
import os
from pathlib import Path
import json

from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.db.session import engine, Base
from app.models.user import User
from app.models.knowledge import CustomerTypeKnowledge, Case, Script, Evidence, KnowledgeSuggestion
from app.models.research import ResearchChunk  # noqa: F401 显式导入确保 create_all 建表
from app.models.feedback import Feedback  # noqa: F401 显式导入确保 create_all 建表
from app.models.llm_log import LLMCallLog  # noqa: F401 显式导入确保 create_all 建表
from app.models.crm import CrmPushLog  # noqa: F401 显式导入确保 create_all 建表
from app.core.domain.services.auth_service import create_user
from app.core.domain.services.research_service import ensure_fts

logger = logging.getLogger(__name__)

DATA_DIR = ROOT / "data" / "knowledge"


def _load_json(filename: str):
    path = DATA_DIR / filename
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _bulk_insert(db: Session, model, records: list, unique_field: str = None):
    if not records:
        return
    for record in records:
        if unique_field:
            if db.query(model).filter(getattr(model, unique_field) == record[unique_field]).first():
                continue
        data = {}
        for k, v in record.items():
            if isinstance(v, (list, dict)):
                v = json.dumps(v, ensure_ascii=False)
            data[k] = v
        db.add(model(**data))


def _ensure_columns(db: Session) -> None:
    """轻量迁移：create_all 不会给既有表补列，这里幂等补充 v1.0 新列"""
    from sqlalchemy import text
    stmts = [
        ("cases", "owner_username", "VARCHAR(50)"),
        ("cases", "is_shared", "BOOLEAN DEFAULT 0"),
        ("scripts", "owner_username", "VARCHAR(50)"),
        ("scripts", "is_shared", "BOOLEAN DEFAULT 0"),
    ]
    for table, col, ddl in stmts:
        try:
            db.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}"))
            db.commit()
        except Exception:
            db.rollback()  # 列已存在，跳过


def init_db():
    Base.metadata.create_all(bind=engine, checkfirst=True)
    db = Session(bind=engine)
    ensure_fts(db)  # 启动时建 FTS5 虚表；不支持时静默退化为 ILIKE
    _ensure_columns(db)
    try:
        if not db.query(User).first():
            # 仅首次初始化引导 admin；生产部署必须设置 ADMIN_INITIAL_PASSWORD
            admin_password = os.getenv("ADMIN_INITIAL_PASSWORD", "admin123")
            if not os.getenv("ADMIN_INITIAL_PASSWORD"):
                logger.warning(
                    "ADMIN_INITIAL_PASSWORD 未设置：使用默认密码 admin123 引导 admin 账号，"
                    "仅限本地开发。生产部署请通过环境变量设置强密码。"
                )
            create_user(db, "admin", admin_password, role="admin")
            logger.info("已创建初始 admin 账号（密码来自 ADMIN_INITIAL_PASSWORD 或默认值）")
        else:
            admin = db.query(User).filter(User.username == "admin").first()
            if admin and admin.role != "admin":
                admin.role = "admin"
                db.add(admin)

        _bulk_insert(db, CustomerTypeKnowledge, _load_json("customer_types.json"), "code")
        _bulk_insert(db, Case, _load_json("cases.json"), "code")
        _bulk_insert(db, Script, _load_json("scripts.json"))
        _bulk_insert(db, Evidence, _load_json("evidence.json"))

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    print("initialized")
