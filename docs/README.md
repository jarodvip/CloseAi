# 客户攻单AI — 项目状态

> 最后更新：2026-08-27
> 当前版本：v0.7.0

## 已实现

- FastAPI 后端，含 CORS、请求大小限制、全局异常处理
- JWT 认证（注册/登录/当前用户）
- 客户 CRUD + 客户类型自动标注（7 类）
- 会前简报生成（基于客户类型 + 知识库）
- 会话/消息管理（多会话、消息历史）
- 知识库管理（客户类型、案例、话术、数据证言的 CRUD）
- 会后跟进包生成
- 客户分析（`/analyze` 端点）
- 前端页面（客户列表、客户详情、会前简报、会中辅助、会后跟进、知识库管理）
- 种子数据脚本

## 待实现

- LLM 增强生成（当前为规则 + 检索，LLM 接口已预留）
- 会中实时语音转写
- CRM 集成
- 向量数据库检索
- 数据看板
- 多端同步

## 项目结构

```
backend/
  app/
    api/v1/routes/     # REST 端点
    core/domain/       # 业务服务层
    models/            # SQLAlchemy 模型
    schemas/           # Pydantic schemas
    db/                # 数据库会话与初始化
    agent/             # Agent 模块（briefing 等）
  tests/               # 测试套件
  scripts/             # 演示与种子数据脚本
frontend/              # 前端页面
docs/                  # 设计文档
scripts/               # 项目级脚本
```

## 技术栈

- 后端：Python 3.11 + FastAPI
- 数据库：SQLite（MVP），PostgreSQL（生产）
- 认证：JWT
- LLM：接口预留（OpenAI / Claude / 国产大模型）
- 前端：原生 HTML/JS

## 设计文档导航

本目录设计文档入口为 `开发文档总览.md`；外部数据层（客户背调、内网页面与存量文档导入、FTS 中文检索、简报/会中集成）见 `外部数据层设计.md`。
