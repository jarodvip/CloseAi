# 攻单 AI Agent API 文档

> 当前实现：React + tRPC + Express + Manus OAuth 基础设施。所有业务调用通过 `/api/trpc` 进入，前端应优先使用项目生成的 `trpc` 客户端，而不是自行拼接请求。

## 1. 文档范围与接口约定

本文档覆盖当前代码中 `appRouter.gongdan` 与 `appRouter.auth` 的路由、输入约束、输出结构、鉴权要求和知识库行为。路由定义以 [`server/routers.ts`][1] 为准，前端调用入口为 [`client/src/lib/trpc.ts`][2]。

| 项目 | 当前值 |
|---|---|
| RPC 前缀 | `/api/trpc` |
| 协议 | tRPC 11 over HTTP |
| 数据序列化 | SuperJSON，由项目模板负责 |
| AI 模型 | `gpt-5-mini`，服务端通过 `invokeLLM` 调用 |
| AI 输出格式 | 诊断接口使用严格 JSON Schema；聊天接口返回文本 |
| 当前匿名能力 | `gongdan.diagnose`、`gongdan.chat`、`gongdan.knowledge` |
| 当前受保护能力 | `gongdan.save`、`gongdan.list`、`gongdan.get` |
| 前端默认保存 | 浏览器 `localStorage`，不依赖登录 |

> 重要：当前免登录前端默认不调用受保护的 `save/list/get` 数据库接口，而是使用本地记录模块。后端受保护接口仍保留，适合后续启用团队云端同步。

## 2. 调用方式

### 2.1 前端推荐方式

项目内使用 tRPC React 客户端：

```ts
import { trpc } from "@/lib/trpc";

const knowledge = trpc.gongdan.knowledge.useQuery();
const diagnose = trpc.gongdan.diagnose.useMutation();

diagnose.mutate({
  industry: "美妆个护",
  scale: "区域龙头",
  keywords: "我要出省",
  competition: "区域强、出省弱",
  goal: "拓展全国市场",
  background: "老板希望先在北上广深打样",
});
```

### 2.2 HTTP 形态

tRPC 的实际 HTTP URL 通常按以下形式组织：

```text
POST /api/trpc/gongdan.diagnose
POST /api/trpc/gongdan.chat
GET  /api/trpc/gongdan.knowledge
```

不同客户端的 batch、输入编码和响应封装由 tRPC 客户端处理。若从非 TypeScript 客户端接入，建议先参考 tRPC 11 的 HTTP 链路和项目网关配置，不要把上述示例当成传统 REST JSON 响应格式。

## 3. 数据类型

### 3.1 客户输入 `ClientInput`

```ts
export type ClientInput = {
  brandName?: string;      // 最长 240 字符，默认 ""
  industry?: string;      // 最长 1200 字符，默认 ""
  scale?: string;         // 最长 1200 字符，默认 ""
  keywords?: string;      // 最长 1200 字符，默认 ""
  competition?: string;   // 最长 1200 字符，默认 ""
  goal?: string;          // 最长 1200 字符，默认 ""
  background?: string;    // 最长 8000 字符，默认 ""
};
```

字段允许为空，是因为诊断过程支持销售逐步补充。但为了获得可靠的主次类型与行动计划，集成方应尽量提供六个维度，尤其是老板原话、竞争状态和本次目标。

### 3.2 攻单结论 `Playbook`

```ts
export type Playbook = {
  primaryType: string;
  secondaryType: string;
  confidence: string;
  evidence: string[];
  diagnosis: string;
  strategy: string;
  steps: Array<{
    name: string;
    action: string;
    output: string;
  }>;
  breakIce: string;
  coreTalk: string;
  objections: Array<{
    objection: string;
    concern: string;
    response: string;
  }>;
  nextAction: string;
  matchedCases: string[];
};
```

`matchedCases` 不信任模型自由生成的案例名称。服务端会读取模型返回的 `primaryType` 与 `secondaryType`，再通过 `getMatchedCases` 从内置案例库程序化匹配，确保案例名称属于知识库。若两个类型都没有命中，当前实现会回退到案例库的前两个案例，因此调用方应把它视为“候选佐证”，而不是事实断言。

## 4. 路由详细说明

### 4.1 `auth.me`

| 属性 | 说明 |
|---|---|
| 方法 | Query |
| 输入 | 无 |
| 鉴权 | Public procedure |
| 返回 | 当前会话用户对象或 `null/undefined` |

当前免登录前端不依赖该接口。登录基础设施仍可用于后续云端记录和团队身份管理。

### 4.2 `auth.logout`

| 属性 | 说明 |
|---|---|
| 方法 | Mutation |
| 输入 | 无 |
| 鉴权 | Public procedure |
| 返回 | `{ success: true }` |

接口会清除项目会话 Cookie。它不清除浏览器中的 `gongdan-ai-local-records`，因为本地记录属于独立存储。

### 4.3 `gongdan.knowledge`

| 属性 | 说明 |
|---|---|
| 方法 | Query |
| 输入 | 无 |
| 鉴权 | Public procedure |
| 返回 | `{ customerTypes, cases, fiveSteps, objections }` |

返回内容来自 [`shared/gongdanKnowledge.ts`][3]，是前端“七大类型”“异议速查”等页面的唯一业务来源。

`customerTypes` 每项包含：

```ts
{
  id: string;
  name: string;
  short: string;
  dimension: string;
  signals: string[];
  entry: string;
  taboo: string;
  breakIce: string;
  coreTalk: string;
  strategy: string;
  caseIds: string[];
}
```

`cases` 每项包含 `id`、`name`、`type`、`summary`、`metric`、`fit`；`fiveSteps` 每项包含 `id`、`name`、`title`、`text`；`objections` 每项包含 `label`、`concern`、`response`。

### 4.4 `gongdan.diagnose`

| 属性 | 说明 |
|---|---|
| 方法 | Mutation |
| 输入 | `ClientInput` |
| 鉴权 | Public procedure |
| 主要用途 | 生成结构化客户画像和攻单结论 |

处理流程如下：

1. 服务端使用系统提示词注入七大客户类型、经典案例、异议库和攻单五步法。
2. 调用 `gpt-5-mini`，要求严格按照 `gongdan_playbook` JSON Schema 输出。
3. 解析模型 JSON，并提取 `primaryType`、`secondaryType`。
4. 服务端执行 `getMatchedCases(primaryType, secondaryType)`，覆盖模型自由生成的 `matchedCases`。
5. 返回完整 `Playbook`。

请求示例：

```json
{
  "brandName": "花西子",
  "industry": "美妆个护",
  "scale": "区域龙头",
  "keywords": "我要出省、要打爆一个市场",
  "competition": "区域强、出省弱；线上流量变贵",
  "goal": "拓展全国市场、核心城市打样",
  "background": "老板关注北上广深，希望先小范围测试，决策链包含老板和市场负责人"
}
```

返回示例：

```json
{
  "primaryType": "全国化扩张型",
  "secondaryType": "品牌野心型",
  "confidence": "高",
  "evidence": ["区域市场基础较强", "存在明确出省诉求"],
  "diagnosis": "客户的主要矛盾不是是否增长，而是如何让新市场先建立信任。",
  "strategy": "先以核心城市打样，品牌认知先行，再让渠道承接增长。",
  "steps": [
    { "name": "听", "action": "追问全国化节奏与试点城市", "output": "确认扩张优先级" },
    { "name": "认", "action": "点破区域强、跨区认知弱的处境", "output": "建立共识" },
    { "name": "比", "action": "引用区域品牌全国化案例", "output": "降低不确定性" },
    { "name": "算", "action": "拆解试点城市、周期和预算", "output": "形成可评估方案" },
    { "name": "定", "action": "确认试点城市与下次会议关键人", "output": "锁定推进动作" }
  ],
  "breakIce": "你们在区域市场很强，想听听你们对全国化布局的规划？",
  "coreTalk": "从区域走向全国，最大的成本不是开店，而是让新市场消费者先信任你。",
  "objections": [
    { "objection": "太贵了", "concern": "担心全国化投入试错成本过高", "response": "先拆成核心城市测试，明确周期和复盘门槛。" }
  ],
  "nextAction": "约到老板和市场负责人，共同确认首个试点城市。",
  "matchedCases": ["老乡鸡", "茶颜悦色"]
}
```

如果模型返回不可解析的内容，接口会抛出“AI 返回格式异常，请重试”。调用方应提供重试入口，并保留原始输入，避免用户重新填写。

### 4.5 `gongdan.chat`

| 属性 | 说明 |
|---|---|
| 方法 | Mutation |
| 输入 | `{ messages: ChatMessage[] }` |
| 鉴权 | Public procedure |
| 数量限制 | 至少 1 条，最多 20 条 |
| 单条限制 | 内容 1—12000 字符 |
| 返回 | `{ content: string }` |

`ChatMessage` 定义如下：

```ts
type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};
```

聊天接口会把系统知识库提示词和消息数组一起发送给模型。前端建议只传递当前会话所需的上下文，并在消息过长时先做摘要。聊天接口返回文本，不保证是 JSON；如果调用方需要结构化结论，应使用 `gongdan.diagnose`。

### 4.6 `gongdan.save`

| 属性 | 说明 |
|---|---|
| 方法 | Mutation |
| 输入 | 受保护的 `DealSessionInput` |
| 鉴权 | Protected procedure |
| 当前前端是否默认使用 | 否 |

输入结构：

```ts
type DealSessionInput = {
  title: string;         // 1—180 字符
  clientSummary: string; // 非空
  primaryType: string;   // 非空
  secondaryType?: string;
  diagnosis: string;     // 非空
  playbook: string;      // 非空，通常为 Markdown
};
```

接口会将记录写入 `deal_sessions` 表，并把当前登录用户的 `id` 写入 `userId`。未登录调用会返回鉴权错误。当前免登录工作台使用 [`client/src/lib/localRecords.ts`][4] 保存本地记录，不应把两种存储误认为同一个数据源。

### 4.7 `gongdan.list`

| 属性 | 说明 |
|---|---|
| 方法 | Query |
| 输入 | 无 |
| 鉴权 | Protected procedure |
| 返回 | 当前用户的数据库攻单记录列表 |

### 4.8 `gongdan.get`

| 属性 | 说明 |
|---|---|
| 方法 | Query |
| 输入 | `{ id: number }`，必须为正整数 |
| 鉴权 | Protected procedure |
| 返回 | 当前用户对应的单条数据库攻单记录 |

服务端会校验记录归属，调用方不能通过修改 `id` 读取其他用户的记录。

## 5. 浏览器本地记录契约

当前前端本地记录类型如下：

```ts
export type StoredRecord = {
  id: string;
  title: string;
  brandName?: string;
  primaryType: string;
  secondaryType?: string;
  diagnosis: string;
  playbook: string;
  createdAt: string;
  status?: "待拜访" | "跟进中" | "已推进" | "暂缓";
  followUpDate?: string;
  visitFeedback?: string;
  objectionOutcome?: string;
};
```

本地存储接口是：

```ts
loadLocalRecords(storage): StoredRecord[];
saveLocalRecords(storage, records): void;
```

`loadLocalRecords` 在键不存在、JSON 无效或数据结构异常时返回空数组；`saveLocalRecords` 将完整数组序列化后写回 `gongdan-ai-local-records`。闭环回写字段 `status`、`followUpDate`、`visitFeedback` 和 `objectionOutcome` 用于记录拜访后的推进状态、下一次跟进日期、客户反馈与异议处理结果。

提醒与迁移工具函数如下：

```ts
getFollowUpState(record, now?): "逾期" | "今天" | "即将到期" | "已排期" | "未排期";
buildFollowUpSummary(record): string;
exportLocalRecords(records, exportedAt?): string;
importLocalRecords(raw): StoredRecord[];
```

导出格式为 `{ version, exportedAt, records }`。导入支持该对象格式，也兼容直接传入记录数组；导入前会校验 `id`、`title`、`primaryType`、`diagnosis`、`playbook` 和 `createdAt` 等必要字段，并按记录 ID 执行“导入优先、本机未冲突记录保留”的合并策略。集成方如果要增加导入/导出，应保持字段兼容，并建议在记录中增加版本号，而不是改变既有字段含义。

## 6. 客户画像契约

客户画像由前端 `buildCustomerProfile` 根据 `ClientInput` 与 `Playbook` 确定性生成，不再次调用 LLM：

```ts
export type CustomerProfile = {
  brandName: string;
  title: string;
  summary: string;
  customerStage: string;
  decisionDriver: string;
  marketTension: string;
  visitGoal: string;
  primaryType: string;
  secondaryType: string;
  evidence: string[];
  communicationFocus: string;
  watchouts: string[];
};
```

其中 `brandName` 来自诊断输入，并用于画像标题、记录标题和 PDF 报告；`watchouts` 取前三条异议的真实顾虑，`evidence` 取最多四条判断依据。输入缺失时会使用“待补充行业”“待确认发展阶段”等占位文字，便于报告明确暴露信息缺口。

## 7. PDF 报告导出

PDF 导出是纯浏览器端能力，不会调用服务端接口。实现使用 `html2canvas` 将报告模板渲染为图片，再使用 `jspdf` 生成 A4 PDF。下载文件名格式为：

```text
攻单报告-{profile.title}-{YYYY-MM-DD}.pdf
```

报告模板包含：客户画像、发展阶段、决策驱动力、市场张力、拜访目标、主次类型、判断依据、攻单策略、破冰话术、核心沟通话术、匹配案例以及会前/会中/会后计划。为避免 Tailwind 的 OKLCH 颜色影响截图兼容性，导出逻辑会把报告克隆到临时 iframe，并在隔离样式中渲染。

集成方若改造 PDF 模板，应保持以下约束：报告根节点需要可通过 `ref` 捕获；导出区域应使用稳定的内联颜色或标准 RGB/HEX；导出完成后及时释放 Blob URL；下载失败时应保留页面状态并允许用户重试。

## 8. 错误处理建议

| 场景 | 可能原因 | 调用方建议 |
|---|---|---|
| AI 返回格式异常 | 模型输出不是合法 JSON | 保留输入，提示重试，不要清空问诊内容 |
| 诊断内容不完整 | 客户输入字段缺失 | 提示补充老板原话、竞争状态和拜访目标 |
| 鉴权错误 | 调用受保护接口时无会话 | 引导登录，或改用当前免登录本地记录策略 |
| 本地记录为空 | 浏览器/设备发生变化或站点数据被清除 | 提供本地导入导出能力，减少数据丢失风险 |
| PDF 生成失败 | 浏览器下载权限、渲染兼容或资源异常 | 允许重试，并提示检查下载权限 |

## 9. 测试与运行命令

```bash
pnpm install
pnpm dev
pnpm check
pnpm test
pnpm build
pnpm start
```

当前测试覆盖认证登出、客户画像生成、知识库接口、攻单路由契约和本地记录读写。PDF 导出属于浏览器端能力，应在具备浏览器环境的端到端测试中验证 Blob 文件头、下载文件名和报告内容。

## 10. P1 复盘与迁移接口说明

### 10.1 `gongdan.recap`

`gongdan.recap` 是公开 mutation，用于将客户诊断、拜访反馈、异议结果和下一次目标转化为结构化作战卡。返回字段包括 `factualSummary`、`customerChange`、`currentBarrier`、`confidence`、`nextObjective`、`keyQuestions`、`recommendedActions`、`avoidActions`、`materialsToPrepare` 和 `followUpMessages`。

`followUpMessages` 必须包含“关系维护型”“专业推进型”“决策确认型”三种风格，每项包含 `style` 和 `message`。接口使用严格 JSON Schema，缺失事实返回“待确认”，不得补造预算、效果、竞品或决策人信息。

### 10.2 本地记录版本 2

`StoredRecord` 新增 `meetingResult`、`newSignals`、`nextGoal`、`recap` 和 `followUpMessage`。导出对象的 `version` 为 `2`，导入仍接受版本 1，并支持预览统计、冲突优先级和最近一次导入撤销。

### 10.3 ICS 日历导出

前端 `buildFollowUpCalendar(records)` 将含 `followUpDate` 的记录转换为全天 ICS 事件，支持批量和单条导出。
