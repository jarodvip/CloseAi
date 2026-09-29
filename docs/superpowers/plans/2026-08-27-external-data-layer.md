# 外部数据层实施计划（Implementation Plan）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为客户攻单AI补齐外部数据底座——统一文本块存储 + SQLite FTS5 中文检索 + 联网背调 + 简报/会中助手 RAG 集成。

**Architecture:** 新增 `ResearchChunk` 单表承载三类来源（文档导入/内网页面/联网背调），jieba 分词写入 FTS5 虚表做全文检索，现有 4 张知识表与接口行为不变；业务侧在简报与会中对话两个入口注入检索结果并复用来源卡展示。

**Tech Stack:** FastAPI + SQLAlchemy + SQLite(FTS5) + jieba、pypdf、python-docx、readability-lxml。

**Spec:** [docs/外部数据层设计.md](../../外部数据层设计.md)

## Global Constraints

- 只用 SQLite，禁止引入向量库或额外服务进程；新依赖仅限 pypdf / python-docx / readability-lxml / jieba（纯 Python）
- API 响应统一信封：`{"code": 0, "message": "ok", "data": ...}`（沿用 routes/knowledge.py 模式）
- 权限：检索 `require_user`；import-url 与删除 `require_admin`；客户背调刷新用 `deps.assert_owner` 做数据归属隔离
- 追溯原则：每个文本块必须落库 source_type + url/source_name + fetched_at
- 降级策略：检索无命中时现有流程行为完全不变；FTS 不可用时退化为 ILIKE 兜底
- 全部中文注释；commit 消息英文 conventional 风格；每个 task 独立可提交
- 测试环境注意：tests 直连开发库（无 fixture 隔离，沿现有 conftest 约定），测试数据用独特 marker 字符串并在 finally 中清理

---

### Task 1: 数据模型与依赖

**Files:**
- Create: `backend/app/models/research.py`
- Modify: `backend/app/db/init_db.py`（显式 import，确保 create_all 建表）
- Create: `backend/requirements.txt`
- Test: `backend/tests/test_research_model.py`

**Interfaces:**
- Produces: `ResearchChunk` ORM 模型（字段见下方代码），后续所有任务通过它读写

- [ ] **Step 1: 安装新依赖**

在**项目实际使用的解释器**下安装（先用 `pip show fastapi` 确认当前解释器已装 fastapi，避免装错环境）：

```bash
pip install pypdf python-docx readability-lxml jieba
```

创建 `backend/requirements.txt`（仓库没有依赖清单文件，只登记本次新增，不动存量安装方式）：

```text
# 外部数据层新增依赖（存量依赖安装方式见 docs/项目初始化与运行.md）
pypdf
python-docx
readability-lxml
jieba
```

- [ ] **Step 2: 写失败测试**

```python
# backend/tests/test_research_model.py
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.research import ResearchChunk


def test_create_and_query_chunk():
    """模型能正常建表、写入、按来源类型查询"""
    db: Session = SessionLocal()
    try:
        chunk = ResearchChunk(
            source_type="doc",
            title="行业报告_测试marker_T1",
            url="https://example.com/t1",
            source_name="测试源",
            industry="食品饮料",
            customer_id=None,
            content="测试正文内容，用于验证存储。",
            chunk_index=0,
        )
        db.add(chunk)
        db.commit()
        db.refresh(chunk)
        assert chunk.id is not None
        found = (
            db.query(ResearchChunk)
            .filter(ResearchChunk.title == "行业报告_测试marker_T1")
            .first()
        )
        assert found is not None
        # 清理
        db.delete(found)
        db.commit()
    finally:
        db.close()
```

- [ ] **Step 3: 运行确认失败**

Run: `cd backend && python -m pytest tests/test_research_model.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models.research'`

- [ ] **Step 4: 写模型**

```python
# backend/app/models/research.py
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, LargeBinary

from app.db.session import Base


class ResearchChunk(Base):
    """外部数据文本块：文档导入 / 内网页面 / 联网背调统一存储，保证来源可追溯"""

    __tablename__ = "research_chunks"

    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String(20), nullable=False)  # doc / web / research
    title = Column(String(200), nullable=True)
    url = Column(String(500), nullable=True)
    source_name = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    customer_id = Column(Integer, nullable=True, index=True)  # 背调结果挂具体客户
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, default=0)
    fetched_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    embedding = Column(LargeBinary, nullable=True)  # 预留：二期语义检索升级
```

修改 `backend/app/db/init_db.py` 的 import 区：

```python
from app.models.research import ResearchChunk  # noqa: F401 显式导入确保 create_all 建表
```

- [ ] **Step 5: 运行确认通过**

Run: `cd backend && python -m pytest tests/test_research_model.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/research.py backend/app/db/init_db.py backend/requirements.txt backend/tests/test_research_model.py docs/外部数据层设计.md
git commit -m "feat(research): add ResearchChunk model and data-layer dependencies"
```

---

### Task 2: 分块与分词纯函数

**Files:**
- Create: `backend/app/core/domain/services/research_service.py`
- Test: `backend/tests/test_research_chunks.py`

**Interfaces:**
- Produces:
  - `split_into_chunks(text: str, max_chars: int = 500) -> List[str]` — 按段落聚合分块，超长段落硬切
  - `tokenize_for_fts(text: str) -> str` — jieba 分词后空格连接，供 FTS 索引与查询共用

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_research_chunks.py
from app.core.domain.services.research_service import split_into_chunks, tokenize_for_fts


def test_split_empty_and_short():
    assert split_into_chunks("") == []
    text = "短文本一段。\n第二段也不长。"
    chunks = split_into_chunks(text, max_chars=500)
    assert len(chunks) == 1
    assert "第二段" in chunks[0]


def test_split_by_max_chars():
    paras = ["甲" * 300, "乙" * 300, "丙" * 100]
    chunks = split_into_chunks("\n".join(paras), max_chars=500)
    # 前两段共600字超500必须分开；第三段与前一块合计400字可合并
    assert len(chunks) == 2
    assert max(len(c.replace("\n", "")) for c in chunks) <= 500


def test_tokenize_chinese():
    result = tokenize_for_fts("奶茶行业竞争激烈")
    assert isinstance(result, str)
    assert " " in result  # 词之间有空格
    tokens = result.split()
    assert "奶茶" in tokens or "行业" in tokens
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && python -m pytest tests/test_research_chunks.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现**

```python
# backend/app/core/domain/services/research_service.py
"""外部数据服务：摄取、检索、背调。所有文本入库前必经此处，保证来源可追溯。"""
from typing import Dict, List, Optional, Tuple


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
```

- [ ] **Step 4: 运行确认通过**

Run: `cd backend && python -m pytest tests/test_research_chunks.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/domain/services/research_service.py backend/tests/test_research_chunks.py
git commit -m "feat(research): add chunk splitting and jieba tokenization helpers"
```

---

### Task 3: 摄取与 FTS5 检索（含 ILIKE 兜底）

**Files:**
- Modify: `backend/app/core/domain/services/research_service.py`
- Modify: `backend/app/db/init_db.py`（启动时调用 `ensure_fts`）
- Test: `backend/tests/test_research_search.py`

**Interfaces:**
- Consumes: Task 1 `ResearchChunk`；Task 2 两个纯函数
- Produces:
  - `ensure_fts(db) -> bool` — 建 FTS5 虚表（幂等）；返回 False 表示当前 SQLite 不支持 FTS5
  - `ingest_text(db, content: str, *, source_type: str, title: str = None, url: str = None, source_name: str = None, industry: str = None, customer_id: int = None, fetched_at=None) -> List[ResearchChunk]`
  - `search_research(db, query: str, *, industry: str = None, customer_id: int = None, k: int = 5) -> List[ResearchChunk]`
  - `delete_chunk(db, chunk_id: int) -> bool`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_research_search.py
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core.domain.services.research_service import (
    delete_chunk,
    ensure_fts,
    ingest_text,
    search_research,
)

MARKER = "青栀气泡水_九乘七唯一标记"


def _db() -> Session:
    return SessionLocal()


def test_ingest_creates_multiple_chunks_with_metadata():
    from app.models.research import ResearchChunk
    db = _db()
    try:
        ensure_fts(db)
        long_text = "\n\n".join([f"{MARKER} 第{i}段。" + "详" * 300 for i in range(3)])
        chunks = ingest_text(db, long_text, source_type="doc", title=f"{MARKER}_t", industry="饮料")
        assert len(chunks) == 3
        assert {c.chunk_index for c in chunks} == {0, 1, 2}
        for c in chunks:
            assert delete_chunk(db, c.id) is True
        assert db.query(ResearchChunk).filter(ResearchChunk.title == f"{MARKER}_t").count() == 0
    finally:
        db.close()


def test_search_hits_tokenized_content():
    db = _db()
    try:
        ensure_fts(db)
        made = ingest_text(
            db,
            f"{MARKER} 奶茶行业进入存量竞争，头部品牌加速下沉开店。",
            source_type="doc",
            title=f"{MARKER}_搜索",
            industry="茶饮",
        )
        hits = search_research(db, "奶茶 行业", k=10)
        assert any(h.id == made[0].id for h in hits)
        # industry 过滤生效
        assert all(h.industry == "茶饮" for h in search_research(db, "奶茶", industry="茶饮", k=20) if h.id == made[0].id)
        # 无命中返回空且不抛异常
        assert search_research(db, "完全无关查询量子膨胀") == [] or all(h.id != made[0].id for h in search_research(db, "完全无关查询量子膨胀"))
        delete_chunk(db, made[0].id)
    finally:
        db.close()


def test_delete_chunk_removes_row_and_fts():
    db = _db()
    try:
        ensure_fts(db)
        made = ingest_text(db, f"{MARKER} 待删除内容", source_type="web", url="https://example.com/x")
        cid = made[0].id
        assert delete_chunk(db, cid) is True
        assert delete_chunk(db, cid) is False
    finally:
        db.close()
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && python -m pytest tests/test_research_search.py -v`
Expected: FAIL — `ImportError: cannot import name 'ensure_fts'`

- [ ] **Step 3: 实现摄取/删除/检索**

追加到 `research_service.py`：

```python
from datetime import datetime

from sqlalchemy import text as _sqltext
from sqlalchemy.orm import Session

from app.models.research import ResearchChunk

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
        base = base.filter(ResearchChunk.customer_id == customer_id)
    if _fts_enabled(db):
        quoted = " ".join(f'"{t}"' for t in tokenize_for_fts(query).split())
        sql = _sqltext(
            "SELECT rc.* FROM research_chunks_fts f "
            "JOIN research_chunks rc ON rc.id = f.chunk_id "
            "WHERE research_chunks_fts MATCH :m "
            "AND (:i IS NULL OR rc.industry = :i) "
            "AND (:cu IS NULL OR rc.customer_id = :cu) "
            "ORDER BY rank LIMIT :k"
        )
        rows = db.execute(sql, {"m": quoted, "i": industry, "cu": customer_id, "k": k}).fetchall()
        ids = [row[0] for row in rows]
        if not ids:
            return []
        return base.filter(ResearchChunk.id.in_(ids)).all()
    # ILIKE 兜底
    like = f"%{query.strip()}%"
    return base.filter(ResearchChunk.content.ilike(like)).limit(k).all()
```

同时修改 `init_db()` 的 `init_db()` 函数体，在 `Base.metadata.create_all(...)` 之后加一行：

```python
from app.core.domain.services.research_service import ensure_fts  # 文件顶部
# init_db() 内 create_all 之后：
ensure_fts(Session(bind=engine))
```

- [ ] **Step 4: 运行确认通过**

Run: `cd backend && python -m pytest tests/test_research_chunks.py tests/test_research_model.py tests/test_research_search.py -v`
Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/domain/services/research_service.py backend/app/db/init_db.py backend/tests/test_research_search.py
git commit -m "feat(research): ingest pipeline with FTS5 index and ILIKE fallback"
```

---

### Task 4: LLM 联网适配层

**Files:**
- Modify: `backend/app/core/config.py`（新增 `LLM_SEARCH_PAYLOAD`）
- Modify: `backend/app/core/domain/services/llm_service.py`
- Test: `backend/tests/test_llm_search_adapter.py`

**Interfaces:**
- Produces:
  - `generate_text(prompt: str, system: Optional[str] = None, extra_payload: Optional[dict] = None) -> str`（原签名向后兼容，仅加第三参）
  - `call_llm_with_search(prompt: str, system: Optional[str] = None) -> str`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_llm_search_adapter.py
import json

from app.core.domain.services import llm_service


class _FakeResp:
    def raise_for_status(self):
        pass

    def json(self):
        return {"choices": [{"message": {"content": "联网结果"}}]}


class _FakeClient:
    """捕获请求体的假 httpx.Client"""

    last_payload = {}

    def __init__(self, *a, **kw):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def post(self, url, json=None, headers=None):
        _FakeClient.last_payload = json
        return _FakeResp()


def test_extra_payload_merged(monkeypatch):
    monkeypatch.setattr(llm_service.httpx, "Client", _FakeClient)
    out = llm_service.generate_text("你好", extra_payload={"tools": [{"type": "web_search"}]})
    assert out == "联网结果"
    assert _FakeClient.last_payload["tools"] == [{"type": "web_search"}]


def test_call_llm_with_search_reads_config(monkeypatch):
    monkeypatch.setattr(llm_service.httpx, "Client", _FakeClient)
    monkeypatch.setattr(llm_service, "LLM_SEARCH_PAYLOAD", '{"enable_search": true}')
    out = llm_service.call_llm_with_search("调研喜茶")
    assert out == "联网结果"
    assert _FakeClient.last_payload["enable_search"] is True


def test_call_llm_without_config_falls_back(monkeypatch):
    # 未配置联网参数时应等价于普通调用，不抛错
    monkeypatch.setattr(llm_service, "LLM_SEARCH_PAYLOAD", "")
    monkeypatch.setattr(llm_service, "generate_text", lambda *a, **k: "plain")
    assert llm_service.call_llm_with_search("q") == "plain"
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && python -m pytest tests/test_llm_search_adapter.py -v`
Expected: FAIL — `AttributeError: ... has no attribute 'LLM_SEARCH_PAYLOAD'` 或 ImportError

- [ ] **Step 3: 实现**

config.py 的 LLM 配置区追加：

```python
    LLM_SEARCH_PAYLOAD: str = ""  # 联网参数 JSON 串（内部API语义不同，经环境变量注入后整体 merge 进请求体；留空=不联网）
```

llm_service.py 改造（保持原有代码风格，最小改动）：

```python
import json

LLM_SEARCH_PAYLOAD = os.getenv("LLM_SEARCH_PAYLOAD", settings.LLM_SEARCH_PAYLOAD)


def generate_text(prompt: str, system: Optional[str] = None, extra_payload: Optional[dict] = None) -> str:
    headers = {"content-type": "application/json"}
    if LLM_API_KEY:
        headers["authorization"] = f"Bearer {LLM_API_KEY}"
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = {"model": LLM_MODEL, "messages": messages, "temperature": 0.4}
    if extra_payload:
        payload.update(extra_payload)  # 联网参数等扩展项整体并入
    try:
        with httpx.Client(timeout=LLM_TIMEOUT) as client:
            resp = client.post(f"{LLM_BASE_URL}/v1/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except Exception as exc:
        if not LLM_API_KEY:
            return f"[LLM模拟回复] {prompt[:120]}...（未配置 LLM_API_KEY）"
        raise exc


def call_llm_with_search(prompt: str, system: Optional[str] = None) -> str:
    """带联网能力的生成：LLM_SEARCH_PAYLOAD 未配置时降级为普通生成"""
    extra: dict = {}
    if LLM_SEARCH_PAYLOAD:
        try:
            extra = json.loads(LLM_SEARCH_PAYLOAD)
        except Exception:
            extra = {}
    return generate_text(prompt, system=system, extra_payload=extra or None)
```

- [ ] **Step 4: 运行确认通过（含全量回归，防止签名变更破坏既有调用）**

Run: `cd backend && python -m pytest tests/test_llm_search_adapter.py tests/test_briefing.py tests/test_chat.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/config.py backend/app/core/domain/services/llm_service.py backend/tests/test_llm_search_adapter.py
git commit -m "feat(llm): web-search adapter via configurable extra payload"
```

---

### Task 5: Research 检索与管理 API

**Files:**
- Create: `backend/app/schemas/research.py`
- Create: `backend/app/api/v1/routes/research.py`
- Modify: `backend/app/api/v1/endpoints.py:1-24`（注册路由）
- Test: `backend/tests/test_research_api.py`

**Interfaces:**
- Consumes: Task 3 的 `search_research / delete_chunk / chunk_dict`
- Produces:
  - `GET /api/v1/research?q=&industry=&customer_id=&k=` （登录用户）
  - `DELETE /api/v1/research/chunks/{chunk_id}` （admin）
  - 后续任务把更多端点加进同文件的 router

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_research_api.py
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.core.domain.services.research_service import ingest_text, delete_chunk

client = TestClient(app)

MARKER = "api检索唯一标记_qw12"


@pytest.fixture(scope="module")
def tokens():
    init_db()
    admin = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"}).json()["access_token"]
    sales = client.post("/api/v1/auth/login", json={"username": "sales", "password": "sales123"}).json()["access_token"]
    return {"admin": admin, "sales": sales}


@pytest.fixture(scope="module")
def seeded(tokens):
    db = SessionLocal()
    made = ingest_text(db, f"{MARKER} 电解质水销量翻倍增长记录。", source_type="doc", title=MARKER, industry="饮料")
    yield made
    for c in made:
        delete_chunk(db, c.id)
    db.close()


def test_search_requires_login(seeded):
    assert client.get("/api/v1/research", params={"q": MARKER}).status_code == 401


def test_search_hit(tokens, seeded):
    r = client.get("/api/v1/research", params={"q": MARKER.split()[0], "industry": "饮料"},
                   headers={"authorization": f"Bearer {tokens['sales']}"})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert any(MARKER in (item.get("title") or "") for item in body["data"])
    item = next(i for i in body["data"] if MARKER in (i.get("title") or ""))
    assert {"source_type", "url", "source_name", "fetched_at"} <= set(item.keys())  # 可追溯字段齐全


def test_delete_admin_only(tokens, seeded):
    cid = seeded[0].id
    r_sales = client.delete(f"/api/v1/research/chunks/{cid}", headers={"authorization": f"Bearer {tokens['sales']}"})
    assert r_sales.status_code == 403
    r_admin = client.delete(f"/api/v1/research/chunks/{cid}", headers={"authorization": f"Bearer {tokens['admin']}"})
    assert r_admin.status_code == 200
    r_admin_again = client.delete(f"/api/v1/research/chunks/{cid}", headers={"authorization": f"Bearer {tokens['admin']}"})
    assert r_admin_again.status_code == 404
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && python -m pytest tests/test_research_api.py -v`
Expected: FAIL — 404（路由不存在）

- [ ] **Step 3: 实现**

`backend/app/schemas/research.py`：

```python
from typing import Optional

from pydantic import BaseModel


class ImportUrlIn(BaseModel):
    """内网页面抓取入参"""
    url: str
    industry: Optional[str] = None
    source_name: Optional[str] = None
```

`backend/app/api/v1/routes/research.py`（本任务先落检索与删除，Task 6/7 继续在此文件追加）：

```python
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_user, require_admin
from app.core.domain.services.research_service import chunk_dict, delete_chunk, search_research

router = APIRouter()


@router.get("")
def search(q: str = "", industry: Optional[str] = None, customer_id: Optional[int] = None,
           k: int = 5, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    data = [chunk_dict(c) for c in search_research(db, q, industry=industry, customer_id=customer_id, k=k)]
    return {"code": 0, "message": "ok", "data": data}


@router.delete("/chunks/{chunk_id}")
def remove_chunk(chunk_id: int, db: Session = Depends(get_db), user: dict = Depends(require_admin)):
    if not delete_chunk(db, chunk_id):
        raise HTTPException(status_code=404, detail="chunk not found")
    return {"code": 0, "message": "ok", "data": {"deleted": chunk_id}}
```

在同文件追加（供 Task 6/7 使用，但本任务就位）：序列化助手放 service 层更合适——`research_service.py` 加：

```python
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
```

`backend/app/api/v1/endpoints.py` 注册（导入区 + 尾部各一行）：

```python
from app.api.v1.routes.research import router as research_router
...
main_router.include_router(research_router, prefix="/api/v1/research", tags=["research"])
```

- [ ] **Step 4: 运行确认通过**

Run: `cd backend && python -m pytest tests/test_research_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/research.py backend/app/api/v1/routes/research.py backend/app/api/v1/endpoints.py backend/tests/test_research_api.py backend/app/core/domain/services/research_service.py
git commit -m "feat(api): research search and chunk management endpoints"
```

---

### Task 6: 内网页面抓取 import-url

**Files:**
- Modify: `backend/app/core/domain/services/research_service.py`
- Modify: `backend/app/api/v1/routes/research.py`
- Test: `backend/tests/test_research_import_url.py`

**Interfaces:**
- Produces:
  - `extract_readable_html(html: str) -> Tuple[str, str]` — 返回 (标题, 正文)，便于纯函数测试
  - `ingest_url(db, url: str, *, industry=None, source_name=None) -> List[ResearchChunk]`
  - `POST /api/v1/research/import-url`（admin）

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_research_import_url.py
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.core.domain.services import research_service

client = TestClient(app)

HTML_SAMPLE = """
<html><head><title>内部wiki页面</title></head><body>
<nav>导航 导航 导航</nav>
<article><h1>-Cola</h1><p>{}</p></article>
<footer>页脚信息</footer></body></html>
""".format("可口可乐近期推出低糖新品线，聚焦便利店渠道。" * 5)

INGEST_MARK = "import_url_wiki_zz9"


@pytest.fixture()
def admin_token():
    from app.db.init_db import init_db
    init_db()
    return client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"}).json()["access_token"]


def test_extract_readable_html():
    title, text = research_service.extract_readable_html(HTML_SAMPLE.replace("nav>导航 导航 导航<", ""))
    assert "wiki" in title or "Cola" in text
    assert "低糖新品线" in text


def test_ingest_url_stores_chunks(admin_token, monkeypatch):
    class _R:
        status_code = 200

        def __init__(self):
            self.text = HTML_SAMPLE

    monkeypatch.setattr(research_service, "_http_get_raw", lambda url: _R())
    r = client.post("/api/v1/research/import-url",
                    json={"url": "https://intra.example.com/wiki/cola", "industry": "饮料", "source_name": "内部wiki"},
                    headers={"authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert len(data) >= 1
    assert data[0]["source_type"] == "web"
    assert data[0]["url"].startswith("https://intra.example.com")
    db = SessionLocal()
    try:
        for c in data:
            research_service.delete_chunk(db, c["id"])
    finally:
        db.close()


def test_import_url_requires_admin(admin_token):
    sales = client.post("/api/v1/auth/login", json={"username": "sales", "password": "sales123"}).json()["access_token"]
    r = client.post("/api/v1/research/import-url", json={"url": "https://intra.example.com/x"},
                    headers={"authorization": f"Bearer {sales}"})
    assert r.status_code == 403
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && python -m pytest tests/test_research_import_url.py -v`
Expected: FAIL — `ImportError` / 404

- [ ] **Step 3: 实现**

`research_service.py` 追加：

```python
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


def ingest_url(db: Session, url: str, *, industry: Optional[str] = None,
               source_name: Optional[str] = None) -> List[ResearchChunk]:
    """抓取内网页面 → 提取正文 → 分块入库"""
    resp = _http_get_raw(url)
    title, body = extract_readable_html(resp.text)
    if not body:
        return []
    return ingest_text(db, body, source_type="web", title=title or url, url=url,
                       source_name=source_name, industry=industry,
                       fetched_at=datetime.utcnow())
```

`routes/research.py` 追加：

```python
from fastapi import HTTPException
from app.schemas.research import ImportUrlIn
from app.core.domain.services.research_service import ingest_url


@router.post("/import-url")
def import_url(payload: ImportUrlIn, db: Session = Depends(get_db), user: dict = Depends(require_admin)):
    try:
        made = ingest_url(db, str(payload.url), industry=payload.industry, source_name=payload.source_name)
    except Exception:
        raise HTTPException(status_code=502, detail="页面抓取失败，请检查 URL 是否可达")
    return {"code": 0, "message": "ok", "data": [chunk_dict(c) for c in made]}
```

- [ ] **Step 4: 运行确认通过**

Run: `cd backend && python -m pytest tests/test_research_import_url.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/domain/services/research_service.py backend/app/api/v1/routes/research.py backend/tests/test_research_import_url.py
git commit -m "feat(research): ingest intranet pages via readability extraction"
```

---

### Task 7: 联网背调与客户刷新端点

**Files:**
- Modify: `backend/app/core/domain/services/research_service.py`
- Modify: `backend/app/api/v1/routes/research.py`
- Test: `backend/tests/test_research_backdossier.py`

**Interfaces:**
- Consumes: Task 4 `call_llm_with_search`；Task 3 `ingest_text`
- Produces:
  - `run_backdossier(db, customer) -> List[ResearchChunk]`
  - `POST /api/v1/customers/{customer_id}/research/refresh`（本人客户的登录用户）
  - 第二个路由实例挂到 `/api/v1/customers` 前缀（模式参考 briefing_router）

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_research_backdossier.py
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.core.domain.services import research_service

client = TestClient(app)

REPORT_FAKE = "主营业务：气泡水；近半年动态：推出联名款（待确认）；广告投放：电梯媒体为主。"


def _mk_customer(token_suffix: str, name: str):
    tok = client.post("/api/v1/auth/login", json={"username": "sales", "password": "sales123"}).json()["access_token"]
    cid = client.post("/api/v1/customers", json={"name": name},
                      headers={"authorization": f"Bearer {tok}"}).json()["data"]["id"]
    return tok, cid


def test_run_backdossier_ingests_report(monkeypatch):
    init_db()
    db = SessionLocal()
    try:
        monkeypatch.setattr(research_service, "call_llm_with_search", lambda prompt, system=None: REPORT_FAKE)
        from app.core.domain.services.customer_service import list_customers
        customer = list_customers(db, 0) or []
        # 直接构造内存对象即可验证逻辑
        class _Cust:
            id = None
            name = "单元测试客户_bd1"
            industry = "饮料"

        made = research_service.run_backdossier(db, _Cust())
        assert len(made) >= 1
        first = made[0]
        assert first.source_type == "research"
        assert first.title == "单元测试客户_bd1 背调报告"
        assert first.source_name == "LLM联网调研"
        for c in made:
            research_service.delete_chunk(db, c.id)
    finally:
        db.close()


def test_refresh_endpoint_owner_isolation(monkeypatch):
    init_db()
    sales_tok, sales_cid = _mk_customer("s", "归属隔离客户_so1")
    admin_tok = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"}).json()["access_token"]

    called = {}
    monkeypatch.setattr(
        "app.api.v1.routes.research.run_backdossier",
        lambda db, customer: called.update({"name": customer.name}) or [],
    )
    # 本人 OK
    r_ok = client.post(f"/api/v1/customers/{sales_cid}/research/refresh",
                       headers={"authorization": f"Bearer {sales_tok}"})
    assert r_ok.status_code == 200
    assert called["name"] == "归属隔离客户_so1"
    # 他人 404
    r_other = client.post(f"/api/v1/customers/{sales_cid}/research/refresh",
                          headers={"authorization": f"Bearer {admin_tok}"})
    assert r_other.status_code == 404
    # 清理
    db = SessionLocal()
    try:
        from app.models.customer import Customer
        obj = db.query(Customer).filter(Customer.name == "归属隔离客户_so1").first()
        if obj:
            db.delete(obj)
            db.commit()
    finally:
        db.close()
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && python -m pytest tests/test_research_backdossier.py -v`
Expected: FAIL — `AttributeError: ... has no attribute 'run_backdossier'`

- [ ] **Step 3: 实现**

`research_service.py` 追加：

```python
BACKDOSSIER_PROMPT = """请联网调研以下客户，输出销售拜访用的背景调查简报。
客户名称：{name}
所属行业：{industry}
要求覆盖：主营业务与规模、近半年动态（融资/新品/组织变动）、营销与广告投放现状、可能切入的业务痛点。
不确定的信息必须标注"待确认"，不得编造。"""


def run_backdossier(db: Session, customer) -> List[ResearchChunk]:
    """联网生成客户背调报告并存库（source_type=research）"""
    from app.core.domain.services.llm_service import call_llm_with_search

    prompt = BACKDOSSIER_PROMPT.format(name=customer.name, industry=customer.industry or "未知")
    report = call_llm_with_search(prompt)
    if not report:
        return []
    return ingest_text(db, report, source_type="research",
                       title=f"{customer.name} 背调报告",
                       source_name="LLM联网调研",
                       industry=customer.industry,
                       customer_id=getattr(customer, "id", None),
                       fetched_at=datetime.utcnow())
```

`routes/research.py` 追加：

```python
from app.core.deps import assert_owner
from app.core.domain.services.customer_service import get_customer
from app.core.domain.services.research_service import run_backdossier

customer_router = APIRouter()  # 第二个实例，注册到 /api/v1/customers 前缀


@customer_router.post("/{customer_id}/research/refresh")
def refresh_research(customer_id: int, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    assert_owner(db, customer_id, user)
    customer = get_customer(db, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="customer not found")
    made = run_backdossier(db, customer)
    return {"code": 0, "message": "ok", "data": [chunk_dict(c) for c in made]}
```

`endpoints.py` 再加一行注册（观察 briefing_router 同前缀注册两次的既有写法）：

```python
main_router.include_router(research_customer_router, prefix="/api/v1/customers", tags=["research"])

# endpoints.py 内导入处改为：
from app.api.v1.routes.research import router as research_router
from app.api.v1.routes.research import customer_router as research_customer_router
```

- [ ] **Step 4: 运行确认通过**

Run: `cd backend && python -m pytest tests/test_research_backdossier.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/domain/services/research_service.py backend/app/api/v1/routes/research.py backend/app/api/v1/endpoints.py backend/tests/test_research_backdossier.py
git commit -m "feat(research): llm backdossier generation with owner-scoped refresh API"
```

---

### Task 8: 会前简报注入外部情报

**Files:**
- Modify: `backend/app/core/domain/services/research_service.py`（新增 `collect_research_cards`）
- Modify: `backend/app/core/domain/services/briefing_service.py:12-77`
- Test: `backend/tests/test_briefing_external_intel.py`

**Interfaces:**
- Consumes: Task 3 检索；common.build_source_cards_for_cases 的卡片结构 `{"source","label","detail","scene"}`
- Produces:
  - `collect_research_cards(db, *, name: str = "", industry: str = None, customer_id: int = None, k: int = 5) -> List[dict]` — 卡片结构复用来源卡形状
  - briefng 响应新增键 `"external_intel"`（全量元数据列表）；命中时同步并入 `llm_source_cards`，**前端来源卡零改动即可显示**
  - `analysis_service.analyze_customer` 因内部调用 build_briefing 自动获得同一数据（spec 第 6 节对应项由此覆盖，不单独改动 analysis）

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_briefing_external_intel.py
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.core.domain.services.research_service import ingest_text, delete_chunk
from app.core.domain.services.briefing_service import build_briefing
from app.core.domain.services.customer_service import create_customer
from app.schemas.customer import CustomerIn

client = TestClient(app)

INTEL_MARK = "情报标记_xt88"


def test_briefing_contains_external_intel(monkeypatch):
    init_db()
    db = SessionLocal()
    try:
        cust = create_customer(db, CustomerIn(name=f"情报集成客户_{INTEL_MARK}", industry="饮料"), owner_id=1)
        made = ingest_text(db, f"{INTEL_MARK} 该品牌重点布局一二线便利店渠道。",
                           source_type="research", title=f"{cust.name} 背调报告",
                           customer_id=cust.id, industry="饮料")
        # 屏蔽真实 LLM，保证断言只针对外部情报管道
        monkeypatch.setattr("app.core.domain.services.briefing_service.generate_text", lambda *a, **k: "模拟输出")
        payload = build_briefing(db, cust.id)
        assert isinstance(payload.get("external_intel"), list)
        assert any(INTEL_MARK in (i.get("title") or "") or INTEL_MARK in (i.get("snippet") or "")
                   for i in payload["external_intel"])
        # 卡片并入 llm_source_cards：label 应含"背调/资料"字样且 source 有值
        cards = payload.get("llm_source_cards") or []
        assert any(("背调" in (c.get("label") or "")) or ("资料" in (c.get("label") or "")) for c in cards)
        for c in made:
            delete_chunk(db, c.id)
        from app.models.customer import Customer
        obj = db.query(Customer).filter(Customer.name.startswith("情报集成客户_")).first()
        if obj:
            db.delete(obj)
            db.commit()
    finally:
        db.close()


def test_briefing_no_intel_unchanged(monkeypatch):
    """无命中时行为不变：external_intel 为空列表，其余结构保持"""
    init_db()
    db = SessionLocal()
    try:
        monkeypatch.setattr("app.core.domain.services.briefing_service.generate_text", lambda *a, **k: "模拟输出")
        from app.core.domain.services.customer_service import list_customers
        from app.models.user import User
        uid = db.query(User).filter(User.username == "admin").scalar()
        existing = [c.name for c in list_customers(db, uid)]
        name = f"无情报客户_{INTEL_MARK}"
        if name not in existing:
            cust = create_customer(db, CustomerIn(name=name, industry="未知行业zzz"), owner_id=uid)
        else:
            from app.models.customer import Customer
            cust = db.query(Customer).filter(Customer.name == name).first()
        payload = build_briefing(db, cust.id)
        assert payload.get("external_intel") == []
    finally:
        db.close()
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && python -m pytest tests/test_briefing_external_intel.py -v`
Expected: FAIL — KeyError `'external_intel'`

- [ ] **Step 3: 实现**

`research_service.py` 追加：

```python
def collect_research_cards(db: Session, *, name: str = "", industry: Optional[str] = None,
                           customer_id: Optional[int] = None, k: int = 5) -> List[Dict[str, object]]:
    """为简报/chat 汇总外部情报：cards 供来源卡渲染，payload 含 snippet 片段"""
    payload: List[Dict[str, object]] = []
    seen: set = set()
    queries = [q for q in [f"{name} {industry or ''}".strip(), industry or ""] if q]
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
        src = i.get("url") or i.get("source_name") or ""
        if not src:
            continue
        label = "背调资料" if i.get("source_type") == "research" else "参考资料"
        cards.append({"source": src, "label": label, "detail": i.get("snippet"), "scene": i.get("title")})
    return cards
```

`briefing_service.py` 在 `build_briefing` 中三处小改：

```python
# 导入区
from app.core.domain.services.research_service import collect_research_cards, cards_from_intel

# evidence 相关语句之后
external_intel = collect_research_cards(
    db, name=customer.name, industry=customer.industry,
    customer_id=customer.id,
)
external_cards = cards_from_intel(external_intel)

# payload 构造处新增键
"external_intel": external_intel,

# llm_source_cards 合并外部卡
"llm_source_cards": source_cards + external_cards,

# BriefingHistory 过滤白名单不含 external_intel 即可自动跳过持久化，
# 但需把 "llm_source_cards" 的 json 序列化分支无需改动（已是 list 序列化路径）
```

`list_briefings` 每个 item 增加（读取时动态汇总，不迁移表结构）：

```python
# 循环体顶部
intel = collect_research_cards(db, name=item.customer_name, customer_id=item.customer_id)
stored_cards = _safe_json(item.llm_source_cards, default=[])
# item dict 里加：
"external_intel": intel,
"llm_source_cards": stored_cards + cards_from_intel(intel),
```

- [ ] **Step 4: 运行确认通过（全量简报回归）**

Run: `cd backend && python -m pytest tests/test_briefing_external_intel.py tests/test_briefing.py tests/test_assist.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/domain/services/research_service.py backend/app/core/domain/services/briefing_service.py backend/tests/test_briefing_external_intel.py
git commit -m "feat(briefing): inject research-backed external intelligence and merged source cards"
```

---

### Task 9: 会中助手 RAG 注入

**Files:**
- Modify: `backend/app/core/domain/services/chat_service.py`（回复生成分支，约 :60-85）
- Test: `backend/tests/test_chat_rag.py`

**Interfaces:**
- Consumes: `collect_research_cards`
- Produces: 消息回复响应新增可选键 `"source_cards"`（命中时非空）。前端 [app.js:667](../../frontend/src/app.js) 已有 `if (cards.length) extraHtml = sourceCardsHtml(cards)` 通道——**执行者第一步先核实前端取的字段名**（约 :650-700 区间），若前端读的是其他键名则后端以实际键名为准返回，保持契约一致。

- [ ] **Step 1: 核实前端契约（先读代码再定字段名）**

Run: `grep -n "source_cards\|cards =" frontend/src/app.js | head -20`
记录 chat 回复处理函数里读取的确切键名（预期 `source_cards`），后续实现以此为返回键。

- [ ] **Step 2: 写失败测试**

```python
# backend/tests/test_chat_rag.py
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.core.domain.services.research_service import ingest_text, delete_chunk

client = TestClient(app)

RAG_MARK = "会中rag标记_kp55"
Q = "气泡水的旺季打法"


def test_chat_reply_carries_sources(monkeypatch):
    init_db()
    db = SessionLocal()
    try:
        from app.core.domain.services.customer_service import create_customer
        from app.schemas.customer import CustomerIn
        from app.models.user import User
        uid = db.query(User).filter(User.username == "sales").scalar()
        cust = create_customer(db, CustomerIn(name=f"会中客户_{RAG_MARK}", industry="饮料"), owner_id=uid)
        made = ingest_text(db, f"{RAG_MARK} 夏季高温期气泡水动销最佳，建议提前铺冰柜。",
                           source_type="doc", title=f"{RAG_MARK}_资料", customer_id=cust.id, industry="饮料")

        captured = {}

        def fake_generate(prompt, system=None, **kw):
            captured["prompt"] = prompt
            return "建议提前一个月锁定冰柜资源。"

        monkeypatch.setattr("app.core.domain.services.chat_service.generate_text", fake_generate)

        tok = client.post("/api/v1/auth/login", json={"username": "sales", "password": "sales123"}).json()["access_token"]
        s = client.post("/api/v1/chat/sessions", json={"customer_id": cust.id},
                        headers={"authorization": f"Bearer {tok}"}).json()["data"]
        sid = s["id"] if isinstance(s, dict) else s.get(0)["id"]  # 以实际响应结构调整
        r = client.post(f"/api/v1/chat/sessions/{sid}/messages", json={"content": Q},
                        headers={"authorization": f"Bearer {tok}"})
        assert r.status_code == 200
        body = r.json()
        msg = body.get("data", body)
        assert RAG_MARK in captured["prompt"] or RAG_MARK in (msg.get("reply") or msg.get("content") or "")
        cards = msg.get("source_cards") or []
        assert len(cards) >= 1 and cards[0].get("source")
        for c in made:
            delete_chunk(db, c.id)
    finally:
        db.close()
```

> 注意：`sid` 取值行按实际 `/chat/sessions` 响应结构改写（先跑一次看响应再固定断言）。

- [ ] **Step 3: 运行确认失败**

Run: `cd backend && python -m pytest tests/test_chat_rag.py -v`
Expected: FAIL — `source_cards` 键不存在

- [ ] **Step 4: 实现**

chat_service.py 回复生成处改造（定位 `llm_text = generate_text(content, system=...)` 所在函数）：

```python
# 导入区
from app.core.domain.services.research_service import collect_research_cards, cards_from_intel

# 回复函数内，generate_text 调用之前
hits = collect_research_cards(db, name=customer.name if customer else "",
                              industry=getattr(customer, "industry", None),
                              customer_id=getattr(customer, "id", None), k=3)
prompt_for_llm = content
if hits:
    block = "\n".join(
        f"[资料{i + 1}] {h.get('title')}（来源：{h.get('url') or h.get('source_name')}）\n{h.get('snippet')}"
        for i, h in enumerate(hits)
    )
    prompt_for_llm = f"{content}\n\n以下是内部资料，回答时可引用并在结尾标注来源：\n{block}"

# 原 generate_text(content, ...) 改为
llm_text = generate_text(prompt_for_llm, system=build_system_prompt(...))  # 参数不变

# 回复响应字典增加（找到返回 reply/message 的构造点）
if hits:
    payload_out["source_cards"] = cards_from_intel(hits)
```

- [ ] **Step 5: 运行确认通过（聊天回归）**

Run: `cd backend && python -m pytest tests/test_chat_rag.py tests/test_chat.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/domain/services/chat_service.py backend/tests/test_chat_rag.py
git commit -m "feat(chat): retrieve research context into replies with source cards"
```

---

### Task 10: 存量文档导入脚本

**Files:**
- Create: `backend/scripts/import_docs.py`
- Test: `backend/tests/test_import_docs_script.py`

**Interfaces:**
- Consumes: `ingest_text`
- Produces: CLI `python scripts/import_docs.py <路径> --industry <行业> --source-name <名称>`；`read_docx(path) -> str`、`read_pdf(path) -> str`、`parse_any(path) -> str`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_import_docs_script.py
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from scripts.import_docs import parse_any, read_docx  # noqa: E402


def _make_docx(tmp_path: Path) -> Path:
    from docx import Document

    doc = Document()
    doc.add_paragraph("第一段：气泡水行业景气度高。" )
    doc.add_paragraph("第二段：" + "渠道下沉" * 150)
    p = tmp_path / "sample.docx"
    doc.save(str(p))
    return p


def test_read_docx(tmp_path):
    p = _make_docx(tmp_path)
    text = read_docx(p)
    assert "气泡水行业景气度高" in text
    assert "渠道下沉" in text


def test_parse_any_dispatch_and_bad_file(tmp_path):
    p = _make_docx(tmp_path)
    assert "气泡水" in parse_any(p)
    bad = tmp_path / "broken.docx"
    bad.write_bytes(b"not-a-real-docx")
    assert parse_any(bad) == ""  # 解析失败返回空串而非抛出


def test_parse_unsupported_ext(tmp_path):
    f = tmp_path / "x.exe"
    f.write_bytes(b"\x00")
    assert parse_any(f) == ""
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && python -m pytest tests/test_import_docs_script.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts'` 或缺 `scripts/__init__.py`

- [ ] **Step 3: 实现**

新建 `backend/scripts/__init__.py`（空文件，使 scripts 成为包以便 pytest 导入）。

```python
# backend/scripts/import_docs.py
"""存量 PDF/Word 批量导入脚本（容错：单文件失败不中断批量）"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.db.session import SessionLocal  # noqa: E402
from app.core.domain.services.research_service import ingest_text  # noqa: E402


def read_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def read_docx(path: Path) -> str:
    from docx import Document

    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def parse_any(path: Path) -> str:
    """按扩展名分发解析；任何失败都返回空串"""
    suffix = path.suffix.lower()
    try:
        if suffix == ".pdf":
            return read_pdf(path)
        if suffix in {".docx"}:
            return read_docx(path)
        return ""
    except Exception:
        print(f"[warn] 解析失败: {path}")
        return ""


def main(argv=None):
    parser = argparse.ArgumentParser(description="批量导入 PDF/Word 到外部数据层")
    parser.add_argument("path", help="文件或目录")
    parser.add_argument("--industry", default=None, help="行业标签")
    parser.add_argument("--source-name", dest="source_name", default=None, help="来源名称")
    parser.add_argument("--max-chars", type=int, default=500)
    args = parser.parse_args(argv)

    root = Path(args.path)
    files = sorted(root.rglob("*")) if root.is_dir() else [root]
    total = 0
    ok_files = 0
    db = SessionLocal()
    try:
        for f in files:
            if not f.is_file() or f.suffix.lower() not in {".pdf", ".docx"}:
                continue
            text = parse_any(f)
            if not text:
                continue
            made = ingest_text(db, text, source_type="doc", title=f.stem,
                               source_name=args.source_name or f.parent.name,
                               industry=args.industry)
            total += len(made)
            ok_files += 1
            print(f"[ok] {f.name}: {len(made)} chunks")
    finally:
        db.close()
    print(f"完成：{ok_files} 个文件，共 {total} 个文本块")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 手工冒烟（PDF 真实解析无法脚本造数，人工验一次）**

随便找一份 PDF（没有就用 docs 目录任意 md 先跳过 pdf）：

```bash
cd backend && python scripts/import_docs.py <你的pdf路径> --industry 测试 --source-name 冒烟
```

Expected: 输出 `[ok] xxx.pdf: N chunks` 且 N ≥ 1

- [ ] **Step 5: 运行测试并提交**

Run: `cd backend && python -m pytest tests/test_import_docs_script.py -v`
Expected: PASS

```bash
git add backend/scripts/__init__.py backend/scripts/import_docs.py backend/tests/test_import_docs_script.py
git commit -m "feat(scripts): tolerant batch importer for legacy pdf/docx corpus"
```

---

### Task 11: 前端接入（简报外部情报 + 会中来源核对）

**Files:**
- Modify: `frontend/src/app.js`（renderBriefing 约 :346 起、简报详情 ：430 附近、历史列表 ：529 附近）

**Interfaces:**
- Consumes: 后端契约 `briefing.external_intel: [{title,url,source_name,source_type,snippet}]`；`llm_source_cards` 已含外部卡（Task 8 合并）→ 大部分来源展示零改动

- [ ] **Step 1: 摸清渲染点**

Run: `grep -n "renderBriefing\|openBriefing\|external\|llm_source_cards" frontend/src/app.js | head`

- [ ] **Step 2: renderBriefing（live 视图）插入外部情报区块**

在 `renderBriefing` 拿到 `payload` 后、拼模板字符串前加：

```javascript
// 外部情报区块：有数据才渲染，不占空态版面
const intel = Array.isArray(payload.external_intel) ? payload.external_intel : [];
const intelHtml = intel.length ? `
  <div class="card intel-block">
    <div class="source-card-title">外部情报</div>
    <ul class="source-list">
      ${intel.map((i) => `<li>${escapeHtml(i.title || '')}${i.url ? ` · <a href="${escapeHtml(i.url)}" target="_blank" rel="noopener">${escapeHtml(i.source_name || '链接')}</a>` : ''}<div class="intel-snippet">${escapeHtml(i.snippet || '')}</div></li>`).join('')}
    </ul>
  </div>` : '';
```

模板里 `${sourceCards}` 相邻处插入 `${intelHtml}`。若还没有 `.intel-snippet/.intel-block` 样式，往 `frontend/src/index.html` 的 `<style>` 里补两条最简样式（灰字、左缩进）。

- [ ] **Step 3: 详情弹窗与历史列表同样接入**

对 ：433-447（详情）与 ：529-543（历史行）两处 `sourceCardsHtml(b.llm_source_cards || [])` 上方加同样的 `const intel = ...` 逻辑并插 `${intelHtml}`；历史表格列宽紧张的话，历史行可以只在 `intel.length` 时显示计数徽标（如 `外情×N`），点击进详情看全量——执行者自行判断保持布局不被撑爆。

- [ ] **Step 4: 会中消息来源确认**

Task 9 已让回复携带 `source_cards`；浏览器实测一次会话提问，确认助签下方出现「引用来源」卡（这是既有通道，应已生效）。若无：对照 app.js 处理 chat 响应处（约 ：650-700）的键名与后端对齐修复。

- [ ] **Step 5: 浏览器验收 + 冒烟回归**

```bash
bash scripts/run_tests_with_restart.sh
```

Expected: 全量 pytest 通过；随后浏览器走一遍：登录 → 录客户 → 触发一次背调刷新 → 打开会前简报看到「外部情报」与合并后的引用来源 → 会中提问答案附来源。前端控制台无报错。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/app.js frontend/src/index.html
git commit -m "feat(frontend): external intelligence block and source card parity across briefing views"
```

---

### Task 12: 全量回归与验收清单

**Files:** 无新改动，只验证与收尾

- [ ] **Step 1: 后端全量测试**

```bash
bash scripts/run_tests_with_restart.sh
```

Expected: 全绿。若有失败，逐个修完再继续（不改本计划之外的行为）。

- [ ] **Step 2: 端到端手工链路**

依次验证并记录结果：
1. `curl -X POST /api/v1/customers/<id>/research/refresh`（本地某测试客户）→ 返回 research 类型块
2. 往 `backend/data` 放一份真实行业 PDF，跑导入脚本 → chunks 计数合理
3. `GET /api/v1/research?q=<行业关键词>` → 命中且带 url/source
4. 页面生成该客户简报 → 「外部情报」出现且来源可点击
5. 删除一条 chunk（admin）→ 检索不再返回

- [ ] **Step 3: 更新文档索引**

在 [docs/README.md](../README.md) 的文档清单补一行 `外部数据层设计.md`（若有此清单；没有就在文末合理位置补充一句导航）。

- [ ] **Step 4: 收尾提交**

```bash
git add docs/
git commit -m "docs: register external data layer design in docs index"
```

---

## Spec ↔ 任务映射自查

| Spec 章节 | 覆盖任务 |
|---|---|
| §3 数据模型 ResearchChunk | Task 1 |
| §4.1 存量文档导入 | Task 10 |
| §4.2 内网页面抓取 | Task 6 |
| §4.3 联网背调适配层+兜底 | Task 4、7 |
| §5 FTS5+jieba 检索、ILIKE 兜底 | Task 2、3 |
| §6 简报集成（分析链路经 build_briefing 传递） | Task 8 |
| §6 会中助手 RAG | Task 9 |
| §7 四个 API + 权限矩阵 | Task 5、6、7 |
| §8 依赖清单 | Task 1 |
| §9 测试计划 + 手动验收 | 各任务内嵌 + Task 12 |
| §10 二期演进 | 不在本期（明确出栈） |
