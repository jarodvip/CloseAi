import sys
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
from app.core.domain.services.auth_service import create_user
from app.core.domain.services.research_service import ensure_fts

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


def init_db():
    Base.metadata.create_all(bind=engine, checkfirst=True)
    db = Session(bind=engine)
    ensure_fts(db)  # 启动时建 FTS5 虚表；不支持时静默退化为 ILIKE
    try:
        if not db.query(User).filter(User.username == "admin").first():
            create_user(db, "admin", "admin123", role="admin")
            create_user(db, "sales", "sales123", role="user")
        else:
            admin = db.query(User).filter(User.username == "admin").first()
            if admin.role != "admin":
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
