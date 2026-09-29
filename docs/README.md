# 客户攻单AI — 项目状态

> 最后更新：2026-09-29
> 当前版本：v1.0.0

## 已实现

- FastAPI 后端，含 CORS、请求大小限制、全局异常处理
- JWT 认证（登录），默认账号 admin/admin123 / sales/sales123
- 客户 CRUD + 客户类型自动标注（7 类），owner 级数据隔离
- 会前简报生成（基于客户类型 + 知识库，含历史记录）
- 会中辅助（实时话术/异议应答，含来源追溯）
- 会后跟进包生成（跟进话术 + 任务建议 + 知识更新建议）
- 会话/消息管理（多会话、消息历史、来源卡）
- 知识库管理（客户类型、案例、话术、数据证言，管理员可写）
- 客户分析（快速分析并创建客户）
- 外部数据层（Research）：文档导入、内网页面抓取、联网背调、FTS5 中文全文检索
- 数据看板（客户总数、类型分布、简报趋势、阶段分布）
- 智能类型检测（根据客户名称/行业自动推断类型）
- LLM 增强生成（会前简报、会中辅助、会后跟进、聊天均已接入 LLM，无 key 时自动降级为规则引擎）
- 前端页面（登录、客户列表/详情、会前简报、会中辅助、会后跟进、知识库管理、数据看板）
- 种子数据脚本 + 前端冒烟测试 + 重启测试脚本
- 完整测试覆盖（99 个后端测试：含反馈/建议审核/观测/混合检索专项）
- **v0.8 知识飞轮**：来源卡反馈（👍/👎 采纳率看板）、知识沉淀建议审核流（会后自动生成 → admin 一键入库）、LLM 调用观测（成功率/降级/token/耗时）、混合检索（FTS5 + embedding 向量 RRF 融合，embedding 不可用自动降级纯 FTS）
- **v0.9 现场可用**：会中实时辅助模式（语音转写 → 停顿 2.5s 自动生成建议，阶段实时显示，异常优雅降级）、PWA（manifest + Service Worker App Shell 缓存 + 图标，可安装到主屏）、移动端适配（弹窗近全屏、44px 触控目标、防 iOS 聚焦缩放）、离线兜底（简报/会中建议 localStorage 缓存，断网显示离线缓存版本）
- **v1.0 团队与集成**：用户管理（admin 创建/禁用/重置密码，禁用即失效，登录限速 5 次/15 分钟，密码 ≥8 位，去除硬编码种子账号）、团队知识共享（销售可建个人案例/话术，一键共享进入团队检索池，admin 聚合视图）、CRM 集成（CRM_WEBHOOK_URL 通用 webhook 推送跟进包 + 推送日志 + 前端 CSV 导出）、数据库升级选项（DATABASE_URL 直接切换 PostgreSQL，psycopg2-binary 依赖）+ SQLite 在线备份脚本

## 待实现

- 后端 ASR 接入（当前用浏览器 Web Speech API，依赖 Chrome/Edge + 网络）
- 多端同步

## 项目结构

```
backend/
  app/
    api/v1/routes/     # REST 端点
    core/
      domain/services/ # 业务服务层
      security.py      # JWT / 密码哈希
      deps.py          # 登录态/权限依赖
      config.py        # 环境变量配置
    models/            # SQLAlchemy 模型（9 个）
    schemas/           # Pydantic schemas
    db/                # 数据库会话与初始化
    agent/             # Agent 模块
  tests/               # 测试套件（22 个测试文件）
  scripts/             # 演示与种子数据脚本
frontend/
  src/
    index.html         # 单页应用
    app.js             # 前端逻辑
    manifest.webmanifest # PWA 清单（v0.9）
    sw.js              # Service Worker：App Shell 离线缓存（v0.9）
    icons/             # PWA 图标 192/512
    prototype.html     # 原型页面
docs/                  # 设计文档
scripts/               # 项目级脚本
```

## 技术栈

- 后端：Python 3.11 + FastAPI + SQLAlchemy
- 数据库：SQLite + FTS5 全文检索
- 认证：JWT
- LLM：接口预留（OpenAI / Claude / 国产大模型）
- 前端：原生 HTML/JS
- 测试：pytest + Playwright（前端冒烟）

## API 文档

启动后端后访问：`http://localhost:8002/docs`

## 脚本

- `scripts/run_tests_with_restart.sh`：自动重启前后端 + 跑 pytest
- `scripts/frontend_smoke_test.py`：前端页面级冒烟测试
- `scripts/seed_knowledge.py`：初始化知识库
- `backend/scripts/import_docs.py`：导入 PDF/Word 到外部数据层
- `backend/scripts/backfill_embeddings.py`：为存量研究分块回填 embedding 向量（v0.8 混合检索）
- `backend/scripts/eval_retrieval.py`：检索相关性评测（纯 FTS vs 混合检索 hit@k/MRR）
- `backend/scripts/backup_db.py`：SQLite 在线备份（--keep 保留份数；PostgreSQL 用 pg_dump）
- `backend/scripts/demo.py`：演示脚本

## 设计文档导航

- `开发文档总览.md`：导航、范围、阅读顺序
- `技术架构.md`：总体架构、模块职责、部署架构
- `数据模型设计.md`：业务表结构、索引
- `接口设计.md`：API 清单、请求响应、错误码
- `Agent工作流设计.md`：会前/会中/会后的状态流转与工具调用
- `知识库设计.md`：客户类型、案例库、话术库、数据证言
- `外部数据层设计.md`：客户背调、内网页面与存量文档导入、FTS 中文检索及简报/会中集成
- `核心代码示例.md`：最小可运行示例与关键代码片段
- `项目初始化与运行.md`：环境、依赖、启动、调试
- `产品路线图.md`：v0.8 → v1.0 版本规划、指标体系、决策点
