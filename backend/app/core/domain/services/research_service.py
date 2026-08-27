"""外部数据服务：摄取、检索、背调。所有文本入库前必经此处，保证来源可追溯。"""
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def split_into_chunks(text: str, max_chars: int = 500) -> List[str]:
    """按段落聚合成 ~max_chars 的块；单段超长时硬切"""
    if not text or not text.strip():
        return []
    chunks: List[str] = []
    buf = ""
    for para in [p.strip() for p in text.split("\n") if p.strip()]:
        while len(para) > max_chars:
            if buf:
                chunks.append(buf)
                buf = ""
            chunks.append(para[:max_chars])
            para = para[max_chars:]
        if len(buf) + len(para) + 1 > max_chars and buf:
            chunks.append(buf)
            buf = para
        else:
            buf = f"{buf}\n{para}" if buf else para
    if buf:
        chunks.append(buf)
    return chunks


def tokenize_for_fts(text: str) -> str:
    """jieba 预分词：索引写入与查询两侧必须使用同一实现"""
    import jieba

    jieba.setLogLevel(60)  # 关闭构建日志刷屏
    return " ".join(jieba.cut(text or ""))


from datetime import datetime

from sqlalchemy import or_, text as _sqltext
from sqlalchemy.orm import Session

from app.models.research import ResearchChunk
from app.core.domain.services.llm_service import call_llm_with_search  # 模块级绑定：测试可 patch 本模块属性拦截联网调用

_FTS_DDL = """
CREATE VIRTUAL TABLE IF NOT EXISTS research_chunks_fts USING fts5(
    chunk_id UNINDEXED, title, body
)
"""


def ensure_fts(db: Session) -> bool:
    """创建 FTS5 虚表（幂等）。不支持 FTS5 的 SQLite 构建返回 False，检索走 ILIKE 兜底"""
    try:
        db.execute(_sqltext(_FTS_DDL))
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False


def _fts_enabled(db: Session) -> bool:
    try:
        db.execute(_sqltext("SELECT 1 FROM research_chunks_fts LIMIT 1"))
        return True
    except Exception:
        return ensure_fts(db)


def _write_fts(db: Session, chunk: ResearchChunk) -> None:
    db.execute(
        _sqltext(
            "INSERT INTO research_chunks_fts(chunk_id, title, body) VALUES (:c, :t, :b)"
        ),
        {
            "c": chunk.id,
            "t": tokenize_for_fts(chunk.title or ""),
            "b": tokenize_for_fts(chunk.content or ""),
        },
    )


def ingest_text(
    db: Session,
    content: str,
    *,
    source_type: str,
    title: Optional[str] = None,
    url: Optional[str] = None,
    source_name: Optional[str] = None,
    industry: Optional[str] = None,
    customer_id: Optional[int] = None,
    fetched_at=None,
) -> List[ResearchChunk]:
    """分块入库并同步 FTS 索引。所有来源统一走这里"""
    pieces = split_into_chunks(content)
    now = fetched_at or datetime.utcnow()
    made: List[ResearchChunk] = []
    for idx, piece in enumerate(pieces):
        chunk = ResearchChunk(
            source_type=source_type,
            title=title,
            url=url,
            source_name=source_name,
            industry=industry,
            customer_id=customer_id,
            content=piece,
            chunk_index=idx,
            fetched_at=now,
        )
        db.add(chunk)
        db.commit()
        db.refresh(chunk)
        if _fts_enabled(db):
            _write_fts(db, chunk)
            db.commit()
        made.append(chunk)
    return made


def delete_chunk(db: Session, chunk_id: int) -> bool:
    chunk = db.query(ResearchChunk).filter(ResearchChunk.id == chunk_id).first()
    if not chunk:
        return False
    if _fts_enabled(db):
        db.execute(
            _sqltext("DELETE FROM research_chunks_fts WHERE chunk_id = :c"),
            {"c": chunk_id},
        )
    db.delete(chunk)
    db.commit()
    return True


def search_research(
    db: Session,
    query: str,
    *,
    industry: Optional[str] = None,
    customer_id: Optional[int] = None,
    k: int = 5,
) -> List[ResearchChunk]:
    """FTS5 全文检索；不可用时退化为 ILIKE。过滤条件按需叠加"""
    if not query or not query.strip():
        return []
    base = db.query(ResearchChunk)
    if industry:
        base = base.filter(ResearchChunk.industry == industry)
    if customer_id is not None:
        # 纳入本客户分块与行业级(customer_id 为 NULL)分块；其他客户的私有分块仍被排除
        base = base.filter(or_(ResearchChunk.customer_id == customer_id,
                               ResearchChunk.customer_id.is_(None)))
    if _fts_enabled(db):
        # 每个 token 内部的双引号双写转义，避免构造出非法 MATCH 表达式
        quoted = " ".join('"%s"' % t.replace('"', '""') for t in tokenize_for_fts(query).split())
        sql = _sqltext(
            "SELECT rc.* FROM research_chunks_fts f "
            "JOIN research_chunks rc ON rc.id = f.chunk_id "
            "WHERE research_chunks_fts MATCH :m "
            "AND (:i IS NULL OR rc.industry = :i) "
            "AND (:cu IS NULL OR rc.customer_id = :cu OR rc.customer_id IS NULL) "
            "ORDER BY rank LIMIT :k"
        )
        try:
            rows = db.execute(sql, {"m": quoted, "i": industry, "cu": customer_id, "k": k}).fetchall()
        except Exception:
            # FTS 查询异常（如无法解析的表达式）时回滚并落入下方 ILIKE 兜底，不让异常穿透
            db.rollback()
        else:
            ids = [row[0] for row in rows]
            if not ids:
                return []
            # 用映射按 rank 次序重排，规避 SQL IN 无序保证
            chunks_by_id = {c.id: c for c in base.filter(ResearchChunk.id.in_(ids)).all()}
            return [chunks_by_id[i] for i in ids if i in chunks_by_id]
    # ILIKE 兜底
    like = f"%{query.strip()}%"
    return base.filter(ResearchChunk.content.ilike(like)).limit(k).all()


def extract_readable_html(html: str) -> Tuple[str, str]:
    """readability 提取正文；失败时降级为原始 HTML 去标签"""
    title, text = "", html or ""
    try:
        from readability import Document as _Doc

        doc = _Doc(html)
        title = doc.short_title() or ""
        text = doc.summary(html_partial=True)
    except Exception:
        pass
    if "<" in text:
        import re

        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
    return title, text.strip()


def _http_get_raw(url: str):
    import httpx

    resp = httpx.get(url, timeout=15, follow_redirects=True,
                     headers={"user-agent": "CloseAI-research-bot/0.1"})
    resp.raise_for_status()
    return resp


def fetch_extract(url: str) -> Tuple[str, str]:
    """抓取内网页面并提取（标题, 正文）。网络或解析异常向上抛出，由调用方决定降级策略"""
    resp = _http_get_raw(url)
    return extract_readable_html(resp.text)


def ingest_url(db: Session, url: str, *, industry: Optional[str] = None,
               source_name: Optional[str] = None) -> List[ResearchChunk]:
    """抓取内网页面 → 提取正文 → 分块入库"""
    title, body = fetch_extract(url)
    if not body:
        return []
    return ingest_text(db, body, source_type="web", title=title or url, url=url,
                       source_name=source_name, industry=industry,
                       fetched_at=datetime.utcnow())


def chunk_dict(chunk: ResearchChunk) -> dict:
    """统一序列化，保证前端拿到的追溯字段稳定"""
    return {
        "id": chunk.id,
        "source_type": chunk.source_type,
        "title": chunk.title,
        "url": chunk.url,
        "source_name": chunk.source_name,
        "industry": chunk.industry,
        "customer_id": chunk.customer_id,
        "content": (chunk.content or "")[:200],
        "chunk_index": chunk.chunk_index,
        "fetched_at": chunk.fetched_at.isoformat() if chunk.fetched_at else None,
        "created_at": chunk.created_at.isoformat() if chunk.created_at else None,
    }


def collect_research_cards(db: Session, *, name: str = "", industry: Optional[str] = None,
                           customer_id: Optional[int] = None, k: int = 5) -> List[Dict[str, object]]:
    """为简报/chat 汇总外部情报：cards 供来源卡渲染，payload 含 snippet 片段"""
    payload: List[Dict[str, object]] = []
    seen: set = set()
    # FTS 为全 token AND 匹配：名称+行业拼成整串查询时，正文缺任一 token 即整体落空，
    # 故拆成"名称"与"行业"两路检索再按 id 去重合并，召回更稳
    queries = [q for q in [name.strip() if name else "", industry or ""] if q]
    for q in queries:
        for hit in search_research(db, q, industry=None, customer_id=customer_id, k=k):
            if hit.id in seen:
                continue
            seen.add(hit.id)
            payload.append({
                "id": hit.id,
                "title": hit.title,
                "url": hit.url,
                "source_name": hit.source_name,
                "source_type": hit.source_type,
                "snippet": (hit.content or "")[:120],
            })
    return payload[:k]


def cards_from_intel(intel: List[Dict[str, object]]) -> List[Dict[str, Optional[str]]]:
    """转成与 common.build_source_cards 一致的卡片形状，前端零改动复用"""
    cards = []
    for i in intel:
        # source 兜底到标题：历史/手工入库的分块可能同时缺失 url 与 source_name
        src = i.get("url") or i.get("source_name") or i.get("title") or ""
        if not src:
            continue
        label = "背调资料" if i.get("source_type") == "research" else "参考资料"
        cards.append({"source": src, "label": label, "detail": i.get("snippet"), "scene": i.get("title")})
    return cards


BACKDOSSIER_PROMPT = """请联网调研以下客户，输出销售拜访用的背景调查简报。
客户名称：{name}
所属行业：{industry}
要求覆盖：主营业务与规模、近半年动态（融资/新品/组织变动）、营销与广告投放现状、可能切入的业务痛点。
不确定的信息必须标注"待确认"，不得编造。"""


def run_backdossier(db: Session, customer) -> List[ResearchChunk]:
    """联网生成客户背调报告并存库（source_type=research）；联网失败降级为空结果，不向调用方抛错"""
    prompt = BACKDOSSIER_PROMPT.format(name=customer.name, industry=customer.industry or "未知")
    try:
        report = call_llm_with_search(prompt)
    except Exception as exc:
        # 联网失败（超时/限流/上游 5xx 等）：宁缺毋滥，返回空列表而非编造
        logger.error("客户背调生成失败 customer_id=%s：%s",
                     getattr(customer, "id", None), exc, exc_info=True)
        return []
    if not report:
        return []
    return ingest_text(db, report, source_type="research",
                       title=f"{customer.name} 背调报告",
                       source_name="LLM联网调研",
                       industry=customer.industry,
                       customer_id=getattr(customer, "id", None),
                       fetched_at=datetime.utcnow())
