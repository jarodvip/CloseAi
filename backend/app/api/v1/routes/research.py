from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_user, require_admin
from app.core.domain.services.research_service import chunk_dict, delete_chunk, search_research
from app.core.domain.services.research_service import ingest_url
from app.schemas.research import ImportUrlIn

router = APIRouter()


@router.get("")
def search(q: str = "", industry: Optional[str] = None, customer_id: Optional[int] = None,
           k: int = Query(5, ge=1, le=50), db: Session = Depends(get_db),
           user: dict = Depends(require_user)):
    data = [chunk_dict(c) for c in search_research(db, q, industry=industry, customer_id=customer_id, k=k)]
    return {"code": 0, "message": "ok", "data": data}


@router.delete("/chunks/{chunk_id}")
def remove_chunk(chunk_id: int, db: Session = Depends(get_db), user: dict = Depends(require_admin)):
    if not delete_chunk(db, chunk_id):
        raise HTTPException(status_code=404, detail="chunk not found")
    return {"code": 0, "message": "ok", "data": {"deleted": chunk_id}}


@router.post("/import-url")
def import_url(payload: ImportUrlIn, db: Session = Depends(get_db), user: dict = Depends(require_admin)):
    try:
        made = ingest_url(db, str(payload.url), industry=payload.industry, source_name=payload.source_name)
    except Exception:
        raise HTTPException(status_code=502, detail="页面抓取失败，请检查 URL 是否可达")
    return {"code": 0, "message": "ok", "data": [chunk_dict(c) for c in made]}
