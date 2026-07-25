# 自我进化 Agent — PRD

> 目标：交付一个能在持续循环中自我进化以达成目标的自主 Agent。Agent 是 Claude Code，由 ai-coworker 驱动。Agent 采取真实行动 — 监控、编排 — 基于真实来源。

## 状态

| 状态 | 日期 | 作者 |
|------|------|------|
| 🚧 草案 v2 | 2026-07-24 | cicidi + Claude |

## 变更日志

| 日期 | 变更 |
|------|------|
| 2026-07-24 | v2：新增安全架构（第5.6节）、循环状态机规范（第2.1节）、hook可靠性缓解措施（第3.3节）、成本模型（第6.6节）、错误处理（第6.7节）、质量指标（第5.2节）、Guild评估（附录A）。解决3个开放问题。 |
| 2026-07-24 | 初稿 |

---

## 1. 概述

### 1.1 愿景

一个通过完成真实任务持续自我改进的 Claude Code Agent。每个 session、每个 turn、每个错误都会反馈回系统——技能自动创建、记忆持久化、行为不断进化。越用越聪明。

### 1.2 实现参考

**当前选择：** [Hermes Agent](https://github.com/NousResearch/hermes-agent)（Nous Research，MIT，v0.18.2）作为记忆架构和自我进化模式的实现基础。Hermes 的闭环学习——自动技能创建、技能修补、持久化 MEMORY.md——直接映射到我们的需求。我们只适配触发机制（hook/插件 替代内置 agent loop），其余部分如果以后有更好的替代方案可随时替换。

> **关于 Hermes-EvoMap 争议（2026年4月）：** Hermes 被指控未标注署名引用了 EvoMap 的 Evolver 引擎。我们的使用受保护：Hermes 是 MIT 许可（宽松、不可撤销），而且 ai-coworker 重新实现的是架构模式（§分隔符记忆文件、FTS5 schema、sidecar JSON使用追踪），不是复制代码。所有模块均可替换（见第6.5节）。关于 Guild Agent 作为替代后端的评估，见附录A。

### 1.3 关键决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 循环架构 | 混合：ai-coworker = 控制平面，Claude Code = 执行平面 | ai-coworker 已管理上下文；Claude Code 负责执行 |
| 目标模型 | 元目标：自我改进为主要驱动力，真实工作为训练场 | Mode C —— agent 在使用中进化 |
| 进化范围 | Skills + Context + Code + Config（全范围） | Mode D —— agent 触及的一切都可以改进 |
| 记忆架构 | MEMORY.md + FTS5 + Curator | 每 turn 同步、跨 IDE/跨项目搜索、定期清理 |
| 后台 LLM | DeepSeek Flash（主） + 备用（Gemini Flash 或 Claude Haiku） | 便宜、快；备用防止单点故障 |
| 后台 LLM 成本注 | DeepSeek Flash 高峰定价（北京时间 9-12, 14-18）= 基准价 2 倍 | 高峰时段自主运行需要预算限制 |
| 技能创建 | 复用现有 `skill-create` / `skill-edit` | 不重复造轮子——自动触发 |
| 编排 | Claude Code 自行决定如何分解任务 | ai-coworker 不硬编码工作流 |
| 实现基础 | Hermes Agent（MIT）用于记忆+技能生命周期 | 可复用、被验证、可替换 |
| 原则 | 优先复用 → 不够改造 → 没轮子造轮子 | 务实，不教条 |

### 1.4 知识分类法

Agent 生成三种类型的知识。每种有不同的存储、生命周期和触发方式：

| 类型 | 定义 | 示例 | 存储 | 触发条件 |
|------|------|------|------|----------|
| **SOP** | 可重复的操作流程 | "修复 lint 错误的标准流程"、"部署到 production 的检查清单" | `SKILL.md`（本地 `~/.coworker/skills/`） | 复杂任务完成后自动判断 → `skill-create` |
| **经验总结** | 对/错的教训、发现的模式、坑点 | "MCP 首次请求总是 403 超时，需重试"、"ruff E501 在这个项目被忽略" | `MEMORY.md`（§ 条目，`~/.coworker/memory/<project>/`） | 每 turn sync 自动提取 + session 结束 LLM 总结 |
| **State / 进度** | 当前状态追踪 | "Dashboard 5 页完成 2 页 pending，blocker 是数据源 API 未就绪" | State 文件（`docs/<initiative>/state/YYYY-MM-DD-state.md`） | 每 turn / 每个 phase 完成 |

**SOP vs 经验：** SOP 是"怎么做"，经验是"发生了什么"。SOP 晋升到 skill-factory 分享给其他项目，经验留在项目 MEMORY.md 作为 context 参考。

**经验总结的提取：** LLM（DeepSeek Flash）分析每 turn 对话内容，识别：新发现的规则/约定、修正了之前的认知、可以复用的模式。提取结果写入 MEMORY.md 的对应项目条目。

---

## 2. 核心循环

```
┌─────────────────────────────────────────────────────────┐
│                ai-coworker (控制平面)                     │
│                                                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────────┐      │
│  │  观察    │ →  │   决策   │ →  │   更新上下文  │      │
│  │ 分析数据 │    │ 评估差距 │    │ CLAUDE.md     │      │
│  │ 状态文件 │    │          │    │ skills/memory │      │
│  └──────────┘    └──────────┘    └──────────────┘      │
│       ↑                              │                  │
│       │                              ↓                  │
│  ┌──────────┐                  ┌──────────────┐        │
│  │   记录   │ ←─────────────── │  启动 Claude  │        │
│  │   状态   │   执行平面        │  Code session │        │
│  │   记忆   │                  └──────────────┘        │
│  └──────────┘                                          │
└─────────────────────────────────────────────────────────┘
```

### 2.1 `coworker run` — 循环状态机

```bash
coworker run --goal "修复此项目中所有 lint 错误" [--loop] \
    --max-iterations 20 --max-cost 10.00 --max-time 4h
```

#### 2.1.1 循环定义

一个循环 = **观察 → 决策 → 启动 Claude Code → 记录**。每个循环产生具体输出或明确的无操作决策。

**状态：**

```
                    ┌──────────────────────┐
                    │    初始化            │
                    │  加载快照            │
                    │  解析目标+预算       │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
              ┌────→│    观察              │
              │     │  读取分析数据        │
              │     │  读取状态文件        │
              │     │  读取记忆快照        │
              │     └──────────┬───────────┘
              │                │
              │                ▼
              │     ┌──────────────────────┐
              │     │    决策              │
              │     │  对照目标评估        │
              │     │  检查终止条件        │
              │     │  规划下一步          │
              │     └──────────┬───────────┘
              │                │
              │        ┌───────┴───────┐
              │        │               │
              │        ▼               ▼
              │ ┌──────────┐   ┌──────────────┐
              │ │  终止    │   │    启动       │
              │ │ (成功,   │   │  Claude Code  │
              │ │  停滞,   │   │  携带子目标   │
              │ │  预算)   │   └──────┬─────────┘
              │ └──────────┘          │
              │                       ▼
              │              ┌──────────────────────┐
              └──────────────│    记录              │
                             │  同步记忆            │
                             │  更新状态文件        │
                             │  更新 CLAUDE.md      │
                             └──────────────────────┘
```

#### 2.1.2 终止条件

满足以下任一条件时循环终止：

| # | 条件 | 检测方式 |
|---|------|----------|
| 1 | **目标达成** | 用户提供的成功标准评估为 true（如 `pytest --exitfirst` 返回 0，`ruff check` 返回 0） |
| 2 | **停滞** | 连续 3 个循环无任何新变化（无代码 diff、无技能创建/修补、无记忆条目新增） |
| 3 | **预算耗尽** | 达到 `--max-iterations`、超过 `--max-cost` 或超过 `--max-time` |
| 4 | **人工停止** | Stop hook 触发；人工在提示中确认"done"或"stop" |

终止时：写入关闭状态、运行 session 后总结（第5.4节）、将 initiative 状态标记为完成或暂停。

#### 2.1.3 错误恢复

| 故障 | 恢复方式 |
|------|----------|
| Claude Code session 错误（API 超时、速率限制） | 指数退避重试最多 3 次；全部失败则在状态中记录错误，继续下一循环 |
| PostToolUse hook 未触发 | Stop hook fallback 捕获 session 摘要；文件审计日志（`~/.coworker/memory/audit.log`）提供第三层保障 |
| DeepSeek Flash API 中断 | 切换到备用 provider（Gemini Flash 或 Claude Haiku）；两者都断则推迟同步到下一循环 |
| FTS5 索引损坏 | 从 MEMORY.md 源数据自动重建；记录事件 |
| 并发 session 冲突 | MEMORY.md 文件锁（fcntl）；第二个 session 排队或跳过 |

#### 2.1.4 预算护栏

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--max-iterations` | 20 | 最大循环次数 |
| `--max-cost` | $5.00 | 最大 API 总费用（Claude Code + DeepSeek Flash） |
| `--max-time` | 4h | 最大墙钟时间 |

不带 `--loop` 时，`coworker run` 执行一次循环后退出（启动 → 记录）。

### 2.2 MVP 不包含 Publish / Transact

- `publish` 和 `transact` 不在 MVP 范围内
- `orchestrate` 委托给 Claude Code——ai-coworker 不硬编码任务分解

---

## 3. 记忆

### 3.1 需求

Agent 必须在 session、项目和 IDE 之间持久化所学内容：

- **R1 — IDE 无关：** 记忆在 Claude Code 和 OpenCode 之间共享。不锁定到任何单一 IDE 的配置目录。
- **R2 — 每 turn 持久化：** 每个 turn 的关键信息无需 agent 手动调用保存命令即可持久化。
- **R3 — 跨 session 搜索：** 跨所有历史 session 搜索，不限项目或 IDE。基于关键词，快速，无外部依赖。
- **R4 — Agent 管理笔记：** Agent 可以编写、修补和删除自己关于项目的笔记（约定、工具怪癖、经验教训）和关于用户的笔记（偏好、工作流习惯）。
- **R5 — 冻结快照：** 每个 session 以累积知识的稳定快照启动。Session 中的写入保存到磁盘但不影响活跃 session 的上下文。
- **R6 — 定期清理：** 过期和未使用的条目自动归档。手写条目永不触碰。
- **R7 — 轻量级：** 无向量数据库、无后台服务进程。LLM 仅用于摘要/检索（一次性），不持续运行。

### 3.2 实现：Hermes 记忆架构

我们使用 Hermes Agent 的记忆设计作为实现基础。核心组件：

**MEMORY.md + USER.md** — Agent 管理的笔记文件，条目以 `§` 分隔。Session 启动时冻结快照，session 中通过 `coworker memory add|replace|remove` 写入（立即写磁盘，快照不变）。

**存储布局：**

```
~/.coworker/memory/
├── fts5_index.db              ← 跨所有项目和 IDE 的统一搜索
├── audit.log                  ← 基于文件的审计日志，用于 hook 故障恢复
├── <project>/
│   ├── MEMORY.md              ← Agent 关于该项目的笔记
│   └── USER.md                ← Agent 对用户的理解
└── curator/
    └── REPORT.md              ← 整理运行报告
```

存储在 `~/.coworker/`（非 IDE 特定目录），确保 Claude Code 和 OpenCode 均能访问相同记忆。

### 3.3 同步流程 — 双触发 + 备用机制

**已知 PostToolUse hook 限制（Claude Code）：** PostToolUse hook 存在已记录的故障模式：跨 session 全局回归（v2.1.119+）、对 MCP/Agent/Skill 工具调用不触发、stdout 被静默丢弃、Windows 间歇性故障（Edit 工具 14% 失败率）。此外，subagent 发现（Agent 工具）在结构上对 PostToolUse 不可见——是信息最丰富的工具调用的盲区。

**缓解措施：双触发 + 审计日志。**

```
┌──────────────┐        ┌──────────────┐
│  Claude Code  │        │   OpenCode    │
│              │        │              │
│ PostToolUse  │        │ tool.execute │
│    hook      │        │   .after     │
│              │        │              │
│ SessionStop  │        │ session.end  │
│    hook      │        │              │
└──────┬───────┘        └──────┬───────┘
       │                       │
       └───────────┬───────────┘
                   │
                   ▼
    ┌──────────────────────────────┐
    │  coworker memory sync        │
    │  --session-id $SESSION_ID    │
    │  --ide claude|opencode       │
    └──────────────┬───────────────┘
                   │
                   ▼
    ┌──────────────────────────────┐
    │  DeepSeek Flash（主）        │
    │  ↓ 备用                      │
    │  Gemini Flash / Claude Haiku │
    │  提取关键信息                 │
    │  → MEMORY.md（项目）         │
    │  → FTS5 索引（全局）         │
    │  → audit.log（时间戳）       │
    └──────────────────────────────┘
```

- **触发器 1（PostToolUse）：** 对支持的工具类型执行每次工具调用的同步。覆盖大部分工具调用。
- **触发器 2（SessionStop）：** Session 结束时全量同步作为备用。捕获 PostToolUse 遗漏的内容（Agent 工具结果、Skill 调用、MCP 调用）。同时触发 session 后总结（第5.4节）。
- **审计日志：** 每次同步向 `~/.coworker/memory/audit.log` 写入带时间戳的记录。便于检测缺失：如果 session 中超过 N 个 turn 无同步记录，标记待调查。
- **Subagent 盲区：** Agent 工具的发现对 PostToolUse 不可见。缓解措施：SessionStop 摘要捕获聚合后的 subagent 结果。对于关键 subagent 工作，驱动 agent 应显式调用 `coworker memory add` 记录关键发现。

备用 LLM：如果 DeepSeek Flash 不可用（速率限制、服务中断），切换到 Gemini Flash 或 Claude Haiku。两个 provider 都失败则推迟同步到下一循环（无数据丢失——原始 turn 内容保留在 session 记录中）。

### 3.4 跨 Session 检索

```
coworker memory search "state engine 设计决策"
```

- SQLite FTS5 全文索引位于 `~/.coworker/memory/fts5_index.db`
- 每条记录标记：`session_id`、`project`、`ide`、`timestamp`、`content`
- 搜索：FTS5 关键词匹配 → 候选 session → LLM（DeepSeek Flash）合成答案
- 范围：所有项目、所有 session、两种 IDE
- MVP 不包含向量数据库（FTS5 对基于关键词的检索已足够；混合 BM25+向量搜索推迟到 v2）

### 3.5 Curator（后台维护）

- **触发：** 每 7 天一次，agent 空闲 2 小时以上后执行
- **FTS5 维护：** `PRAGMA optimize` 每天运行（非每周），防止因每 turn 写入负载导致索引碎片化。启用 WAL 模式以支持并发访问。`automerge` 用于后台增量合并。
- **操作：**
  - 追踪每条记忆条目的 `view_count`、`use_count`
  - 30 天未使用 → `stale` → 90 天未使用 → `archived`
  - 高频保护：使用 50 次以上的条目被钉住（永不被归档）
  - 季节性分析：此条目在闲置前是否被大量使用？若 `historical_use_count > 20`，延长 stale 阈值 2 倍
  - 合并重复/重叠条目
  - 在 `~/.coworker/memory/curator/` 生成 `REPORT.md`
  - 仅触碰 agent 创建的条目（手写的永不触碰）
- **取消归档：** `coworker memory unarchive <id>` 恢复已归档条目
- **LLM：** DeepSeek Flash（带 provider 备用）

### 3.6 快照注入

两种 IDE 在 session 启动时读取 CLAUDE.local.md。记忆快照注于其中：

```markdown
<!-- MEMORY:ai-coworker START -->
## 记忆快照（在 session 启动时冻结）

### 项目：ai-coworker
§ 项目使用 ruff linter，E501 忽略
§ 所有 PR 需通过 CI 才能合并
§ 上次 dashboard 开发在 session 71979623，5 页完成 2 页 pending

### 用户偏好
§ 偏好中文交流
§ 喜欢先讨论再实现
§ 优先复用现有方案
<!-- MEMORY:ai-coworker END -->
```

- 快照仅在 session 启动时更新（session 期间不更新）
- Session 中的写入保存到磁盘但不刷新快照
- 旧的快照行在下次 session 启动时整体替换
- **Session 中刷新：** `coworker memory refresh` 从磁盘重新加载快照到活跃上下文。Agent 怀疑上下文过时时可主动调用（例如超过 2 小时的长 session）。默认行为仍为冻结快照。

---

## 4. State Engine（状态引擎）

### 4.1 触发

每个 turn → `PostToolUse` hook → 异步 subagent 写入状态文件。

### 4.2 状态文件

```
docs/<initiative>/state/YYYY-MM-DD-state.md
```

- 实时文档，持续更新（非每日快照）
- 后台 subagent 追加新事件并修改之前条目（如 `🚧 → ✅`）
- Phase 完成（PRD/spec/design/plan/test）强制触发状态更新

### 4.3 记录标准

三个维度——满足任一即记录：

| 维度 | 含义 |
|------|------|
| **做了什么** | 具体产出：代码、文档、配置、研究结论、外部操作、自动化 |
| **对/错** | 经验教训：什么有效、什么无效、发现的 bug、暴露的盲区、压缩风险 |
| **进度** | 追踪：完成/未完成/谁在做/何时完成/依赖关系 |

**始终记录：**
- 代码更改、文档创建、配置更改
- 系统事件：MCP 设置、模型配置、备份/恢复、worktree、压缩、INDEX 更新
- 有结论的研究、失败的尝试、盲区发现
- Initiative 生命周期、约定创建过程
- Subagent 探索结果（记录结论，中间过程可选）

**永不记录：**
- 即时查询（只是看看，无产出）
- 单命令原子操作（一个 `git commit` 完事）
- 纯聊天/好奇/未做决定
- 瞬态状态检查（只是读一个数字）

---

## 5. 自我进化引擎

### 5.1 自动技能创建

**触发：** 完成一个工具调用较多的任务。默认阈值：10+ 次工具调用（针对 ai-coworker 多 agent 模式校准；Hermes 的 5+ 阈值太低——单个 Claude Code 任务可能产生 50+ 次工具调用）。阈值可通过 `coworker config set skill.create.threshold` 配置。

**CLAUDE.md 中的规则：**
```markdown
## 自我进化规则

当你使用大量工具调用完成复杂任务时：
1. 评估该工作流/模式/知识是否可复用
2. 若是 → 调用 `skill-create` 自动生成 SKILL.md
```

**审批模式：**

| 模式 | 行为 |
|------|------|
| **审查模式**（`auto_approve: false`，默认） | 技能暂存到 `~/.coworker/pending/skills/`——用户通过 `coworker skill pending` 审查 |
| **自动模式**（`auto_approve: true`） | 技能无需确认自动创建（主动选择开启） |

- 记忆写入：轻量级，内联审查
- 技能写入：始终暂存（太大不宜内联预览）
- 后台创建：始终暂存（无用户在场）
- 暂存存储：`~/.coworker/pending/{memory,skills}/<id>.json`，跨重启持久化
- **安全门禁**（完整安全架构见第5.6节）：
  - 熔断机制：24小时内创建或修补超过3个技能则暂停所有自动进化并通知用户
  - 沙箱测试：自动创建的技能在从 pending 提升前必须通过一次空跑
  - 回滚：任何自动修补的技能均可通过 `coworker skill rollback <name>` 回退到上一版本

### 5.2 技能生命周期与晋升

技能**先本地创建**，不直接进入 skill-factory。凭实力晋升。

```
Agent 创建 skill
       │
       ▼
~/.coworker/skills/<name>/SKILL.md    ← 共享存储（IDE 无关）
       │
       │  coworker sync
       ├──────────────→ ~/.claude/skills/<name>/        (Claude Code)
       │
       └──────────────→ ~/.config/opencode/skills/<name>/  (OpenCode)
```

**规则：**
- **0-9 次使用：** 共享存储中，两个 IDE 都能通过 sync 获取
- **10+ 次使用：** 自动标记晋升 → 复制到 `skill-factory/personal-skills/` → 人工审查并提交
- **使用追踪：** Sidecar JSON 位于 `~/.coworker/skills/.usage.json`。原子写入（tempfile + os.replace + fcntl lock）。失败为尽力而为——损坏的计数器绝不阻塞技能调用。追踪：`use_count`、`view_count`、`patch_count`、`error_rate`、`last_invoked`、`state`、`provenance`
- **质量指标（不止使用次数）：**
  - `error_rate`：用户拒绝或纠正技能输出的调用比例
  - `patch_frequency`：每月修补次数。高频（>3次/月）标志质量问题 → 标记审查
  - `user_override_rate`：用户覆盖技能行为的频率
  - **回归检测：** 技能被修补后，对比修补前后 `error_rate`。若修补后更高 → 自动回滚并标记
- **生命周期：** active → stale（30天未使用）→ archived（90天，移至 `.archive/`）。钉住的技能豁免。闲置前高历史使用（>20次）延长 stale 阈值 2 倍。`coworker skill unarchive <name>` 恢复已归档技能
- **来源：** agent-created / bundled（ai-coworker 核心）/ skill-factory / hub。Curator 仅触碰 agent-created

### 5.3 自动技能修补

**触发：** 使用已有技能时发现其过时、不完整或错误

**CLAUDE.md 中的规则：**
```markdown
使用技能时发现其不正确或过时：
→ 调用 `skill-edit` 修补（外科手术式编辑：old_string → new_string）
```

- `patch_count` 按技能追踪——输入 Curator 和晋升决策
- 修补遵循与创建相同的审批模式和安全门禁（默认模式需审查）
- 回滚可用：`coworker skill rollback <name>` 回到上一良好版本
- 熔断机制适用（第5.6节）

### 5.4 Session 后总结

**触发：** Session Stop hook

**操作：** DeepSeek Flash 总结 session → 写入 MEMORY.md → 索引到 FTS5。Provider 备用生效。

### 5.5 Curator

**触发：** Cron 每 7 天一次（空闲 2h+）。FTS5 OPTIMIZE 每天运行。

**操作：**
- 追踪技能和记忆条目的 `view_count`、`use_count`、`patch_count`、`error_rate`
- 30 天未使用 → `stale` → 90 天 → `archived`
- 高频保护：使用 50 次以上的条目/技能被钉住
- 季节性分析：历史高使用条目延长 stale 阈值
- 合并重复/重叠条目
- 生成 `REPORT.md`
- 仅触碰 agent 创建条目（手写或 skill-factory 捆绑的永不触碰）
- `coworker memory unarchive <id>` 和 `coworker skill unarchive <name>` 用于恢复

### 5.6 安全与对齐架构

> **为什么存在这一节：** 上海 AI Lab 研究（2026）记录了四种自我进化途径的安全侵蚀：模型进化导致钓鱼风险触发率从 18.2% 跃升至 71.4%；记忆进化导致恶意代码拒绝率从 99.4% 降至 54.4%；工具进化显示自动创建工具的不安全率达 65.5%；工作流进化将恶意请求拒绝率从 46.3% 压垮到 6.3%。AgentWorm（北京大学，2026）展示了对自我进化 agent 生态 63% 的攻击成功率。没有安全基础设施的自我修改自主 agent 是不可接受的。

#### 5.6.1 默认值

所有自我进化操作默认为**审查模式**（`auto_approve: false`）。自动批准需主动选择开启，并按操作类型限定范围。

| 操作 | 默认 | 可主动开启自动？ |
|------|------|-----------------|
| 技能创建 | 审查（pending 队列） | 是，按技能域 |
| 技能修补 | 审查（pending 队列） | 是，按技能 |
| 记忆写入 | 内联审查 | 不适用（轻量级） |
| 后台创建 | 始终暂存 | 否 |

#### 5.6.2 熔断机制

若 **24 小时内创建或修补超过 3 个技能**，系统暂停所有自动进化：

1. 自动创建和自动修补暂停
2. 所有 pending 技能保留在队列中（无数据丢失）
3. 通知用户："自动进化已暂停：24h 内修改了 4 个技能。审查 pending 队列并运行 `coworker skill resume` 重新启用。"
4. `coworker skill resume` 经用户审查后重新启用

#### 5.6.3 沙箱测试

Pending 技能在被提升（批准使用）之前：

1. 在沙箱 session 中空跑技能（无副作用）
2. 对照最低安全检查验证输出：无 `rm -rf` shell 命令、无凭据暴露、无未授权网络调用
3. 沙箱通过 → 技能进入活跃池
4. 沙箱失败 → 技能保留在 pending 并记录失败原因

#### 5.6.4 回滚

每个自动创建或自动修补的技能支持回滚：

- `coworker skill rollback <name>` 恢复到上一已知良好版本
- 若修补后 `error_rate` 比修补前高 50%+ 则自动回滚
- 每个技能保留最近 5 个版本的版本历史

#### 5.6.5 安全监控

按 session 追踪以下指标并输入 Curator 决策：

| 指标 | 信号 |
|------|------|
| `refusal_rate` | Agent 拒绝不安全请求（应保持高位） |
| `unsafe_output_rate` | Agent 产生潜在有害输出（应保持接近 0） |
| `skill_error_rate` | 自动创建技能产生错误结果 |
| `circuit_breaker_trips` | 熔断机制触发次数 |

---

## 6. 架构

### 6.1 新模块

```
src/coworker/memory/
├── __init__.py
├── memory_store.py     # MEMORY.md + USER.md 读写，使用 atomic_replace + 文件锁
├── fts5_index.py       # SQLite FTS5 全文索引，覆盖 session 内容
├── curator.py          # 定期清理（7天周期，每天 OPTIMIZE）
└── sync.py             # 双触发同步：PostToolUse + SessionStop，带 provider 备用

src/coworker/skills/
├── __init__.py
├── lifecycle.py        # 使用追踪（.usage.json），质量指标，晋升标记，回滚，归档
└── pending.py          # 暂存技能/记忆审批队列，含沙箱测试
```

### 6.2 新存储位置

```
~/.coworker/
├── memory/              # 跨 IDE 记忆（见第3节）
│   ├── fts5_index.db
│   ├── audit.log        # 基于文件的审计日志
│   └── <project>/
│       ├── MEMORY.md
│       └── USER.md
├── skills/              # 共享技能存储（source of truth）
│   ├── <name>/SKILL.md
│   └── .archive/
├── pending/             # 审批队列
│   ├── memory/<id>.json
│   └── skills/<id>.json
└── curator/
    └── REPORT.md
```

### 6.3 Hooks 和插件（两种 IDE）

**Claude Code：**
```json
// ~/.claude/settings.json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "",
        "command": "coworker memory sync --session-id $SESSION_ID --ide claude"
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "command": "coworker memory close --session-id $SESSION_ID --ide claude"
      }
    ]
  }
}
```

**OpenCode：**
```typescript
// .opencode/coworker-analytics/ 插件（扩展现有）
tool.execute.after → spawnSync('coworker', ['memory', 'sync', '--session-id', sessionId, '--ide', 'opencode'])
session.end        → spawnSync('coworker', ['memory', 'close', '--session-id', sessionId, '--ide', 'opencode'])
```

**已知限制（已记录）：**
- PostToolUse 对以下情况不触发：MCP 工具调用、Agent 工具完成、Skill 调用。SessionStop 备用部分缓解。
- OpenCode hook 可靠性未评估——生产使用前需分析。基于文件的审计日志为跨 IDE 对比提供真实依据。
- Hook 命令的 stdout 在 Claude Code 中被丢弃——同步输出不能注入活跃上下文。这是有意设计：同步写入磁盘供下次 session 使用（第3.6节）。

### 6.4 Cron 任务

```cron
# Curator：每 7 天
0 3 * * 1 coworker memory curator run

# FTS5 OPTIMIZE：每天（防止每 turn 写入导致的索引碎片化）
0 4 * * * coworker memory optimize

# 记忆整理：每天 10am, 8pm——整理并合并条目
0 10,20 * * * coworker memory organize
```

### 6.5 OpenCode 插件扩展

现有 OpenCode 分析插件（`.opencode/coworker-analytics/`）已经 hook 了 `tool.execute.before/after` 和 `session.compacting`。扩展增加：

| 事件 | 操作 |
|------|------|
| `tool.execute.after` | `coworker memory sync --ide opencode` |
| `session.end` | `coworker memory close --ide opencode` |

**OpenCode hook 可靠性：** 生产使用前需分析。OpenCode 的 `tool.execute.after` 事件可能与 Claude Code PostToolUse 覆盖范围不同（需验证：所有工具类型是否触发？子进程工具调用呢？）。在评估完成前，将 OpenCode 记忆视为尽力而为，通过审计日志验证。

### 6.6 成本模型

**DeepSeek Flash（主后台 LLM）：**

| 指标 | 非高峰 | 高峰（北京时间 9-12, 14-18） |
|------|--------|------------------------------|
| 输入（每 1M token） | $0.14 | $0.28 |
| 输出（每 1M token） | $0.28 | $0.56 |

**每操作估算：**

| 操作 | Token（入/出） | 非高峰成本 | 高峰成本 |
|------|---------------|-----------|----------|
| 每 turn 同步 | ~2K / ~500 | ~$0.0004 | ~$0.0008 |
| Session 后总结 | ~8K / ~1K | ~$0.0014 | ~$0.0028 |
| Curator 运行（每周） | ~20K / ~2K | ~$0.0034 | ~$0.0067 |
| 记忆搜索（LLM 合成） | ~4K / ~500 | ~$0.0007 | ~$0.0014 |

**Session/月估算（100 turn/session，20 session/月）：**

| 场景 | 月成本 |
|------|--------|
| 轻度使用（10 session，每 session 50 turn，非高峰） | ~$0.25 |
| 中度使用（20 session，每 session 100 turn，混合高峰/非高峰） | ~$2-5 |
| 重度自主循环（8h 运行，500+ turn，混合） | ~$15-30 |

**预算执行：** `coworker run --max-cost $X.XX` 限制每次调用的 API 总开支。CLI 在 50%、80%、95% 阈值时警告。超出预算触发优雅终止（保存状态、运行总结、退出）。

**Provider 备用定价：** Gemini Flash 和 Claude Haiku 与非高峰 DeepSeek Flash 相当或更便宜。备用在中断场景中增加的成本可忽略不计。

### 6.7 错误处理和降级模式

| 组件 | 故障 | 降级行为 |
|------|------|----------|
| PostToolUse hook | 单个 turn 未触发 | 无立即操作；SessionStop 在 session 结束时捕获。审计日志记录缺口。 |
| PostToolUse hook | 全局回归（所有 hook 失效） | SessionStop 备用捕获全量 session 摘要。基于文件的审计日志提供恢复依据。 |
| DeepSeek Flash | 速率限制或不可用 | 切换到 Gemini Flash 或 Claude Haiku。两者都失败 → 推迟同步到下一循环（无数据丢失；原始 turn 内容保留在 session 记录中）。 |
| FTS5 索引 | 损坏（断电、磁盘满） | 下次访问时从 MEMORY.md 源数据自动重建。记录事件。 |
| MEMORY.md | 文件锁争用（并发 session） | 第二个 session 排队写入；以 1s 退避重试 3 次。3 次失败后写入单独冲突文件待后续合并。 |
| Curator | 运行中途失败 | 部分结果持久化。下次运行从上次检查点继续。REPORT.md 注明未完成运行。 |
| 技能存储 | `.usage.json` 损坏 | 从技能目录列表重建。使用计数重置为 0（有损但非阻塞）。 |
| Claude Code session | API 超时/速率限制 | 指数退避重试 3 次（1s, 2s, 4s）。全部失败 → 在状态文件中记录错误，继续下一循环。 |

**FTS5 重建策略（解决开放问题 2）：** 增量更新为主路径。仅在索引损坏时触发全量重建（通过 `PRAGMA integrity_check` 检测）。重建读取所有 MEMORY.md 文件并重新索引——典型项目语料约 100ms。

### 6.8 实现基础

记忆、技能生命周期和 Curator 实现遵循 Hermes Agent 的模式（MIT 许可）。关键模块映射：

- `memory_store.py` ← Hermes `tools/memory_tool.py`（§ 分隔符、atomic_replace、文件锁）
- `fts5_index.py` ← Hermes FTS5 查询 + schema 模式
- `curator.py` ← Hermes 整理生命周期规则（30d stale → 90d archived，扩展了质量指标和季节性分析）
- `lifecycle.py` ← Hermes `skill_usage.py`（sidecar JSON、原子写入，扩展了 error_rate 和回归检测）

这些实现选择不是锁定的——如果有更好的替代方案出现，任何模块都可以替换。

---

## 7. 集成点

### 7.1 复用的现有 ai-coworker 基础设施

| 模块 | 复用目的 |
|------|----------|
| `coworker skill new` | 自动技能创建触发 |
| `skill-create` / `skill-edit` skills | 自我进化操作 |
| 分析管道（hooks、DB） | FTS5 数据源 |
| `analytics/knowledge.py` | 记忆条目的 LLM 去重逻辑 |
| `session-memory` skill | LLM 摘要管道（适配 Claude Code + DeepSeek Flash，移除 Ollama 依赖） |
| OpenCode 分析插件（`.opencode/coworker-analytics/`） | 扩展记忆同步 hook |

### 7.2 新增内容

| 组件 | 为什么新增 |
|------|-----------|
| `coworker run` | ai-coworker 目前无循环驱动 |
| `memory_store.py` | MEMORY.md 读写尚不存在 |
| `fts5_index.py` | 跨 session 搜索尚不存在 |
| `curator.py` | 定期清理尚不存在 |
| `sync.py` | 双触发同步，带 provider 备用 |
| `pending.py` | 暂存技能的沙箱测试 |
| 安全架构 | 熔断、回滚、监控 |
| CLAUDE.md 自我进化规则 | Claude Code 需要行为指令 |

---

## 8. MVP 不包含

- Publish / Transact 操作
- 基于嵌入/向量的长期记忆（FTS5 对 MVP 已足够；混合 BM25+向量搜索推迟到 v2）
- GEPA/DSPy prompt 进化（v2）
- 多 agent 委托网格（v2）
- Guild Agent 集成（附录A 已评估——互补的任务协调层，v2 候选）

---

## 9. 开放问题

### 已解决

1. ✅ **循环终止检测：** 定义了四种条件（第 2.1.2 节）：目标标准、停滞（3 个循环无变化）、预算耗尽、人工停止。
2. ✅ **FTS5 重建策略：** 增量更新为主；`integrity_check` 失败时从 MEMORY.md 源数据全量重建（第 6.7 节）。
3. ✅ **MEMORY.md 快照注入：** CLAUDE.local.md 中独立的 `<!-- MEMORY:project-name -->` 块。可通过 `coworker memory refresh` 进行 mid-session 刷新（第 3.6 节）。

### 新问题（v2+）

4. **OpenCode hook 可靠性：** OpenCode 的 `tool.execute.after` 是否像 Claude Code PostToolUse 一样覆盖所有工具类型？需要实证验证才能声明生产可用的跨 IDE 一致性。
5. **技能质量自动检测：** 能否在无需用户覆盖信号的情况下自动检测技能退化？对技能输出模式的异常检测？
6. **跨项目技能晋升：** 一个项目中创建的技能何时应晋升到 skill-factory vs 保持项目本地化？
7. **循环停滞灵敏度：** 3 个循环是正确的阈值吗？需要基于真实自主运行数据的实证调优。

---

## 附录A：Guild Agent 评估

*遵循"优先复用"原则——造轮子前先评估现有工具。*

### A.1 Guild Agent 概要

[Guild Agent](https://github.com/mathomhaus/guild)（Apache 2.0）是一个包含 MCP 服务器和嵌入式 SQLite 的单 Go 二进制文件。四个原语：Quests（带原子声明的任务）、Lore（按类型分类的知识条目）、Oaths（项目原则）、Briefs（session 交接笔记）。通过倒数排列融合（reciprocal-rank fusion）实现混合 BM25 + 向量搜索。通过 MCP 协议跨 IDE。状态存储在 `~/.guild/`。

### A.2 对照 PRD 记忆需求的对比

| 需求 | PRD 方式 | Guild 方式 | 评估 |
|------|----------|-----------|------|
| R1（IDE 无关） | 记忆在 `~/.coworker/`，按 IDE 配置 hook | MCP 服务器——任何 MCP 客户端都可连接 | Guild IDE 覆盖更广。PRD 需要按 IDE 配置 hook。 |
| R2（无手动保存） | 无条件 PostToolUse hook → 自动同步 | Agent 必须显式调用 `lore_inscribe` | **Guild 不满足 R2。** `lore_inscribe` 就是手动保存命令。R2 明确要求"无需 agent 手动调用保存命令"的持久化。 |
| R3（跨 session 搜索） | FTS5 关键词 → LLM 合成 | 混合 BM25 + 向量，通过倒数排列融合 | Guild 的搜索客观上更强。PRD 在查询时的 LLM 合成是更轻量的语义层。Windows 上向量搜索被禁用。 |
| R4（Agent 管理笔记） | MEMORY.md 带 § 条目，`add|replace|remove` | `lore_inscribe` 带 kind/summary/topic | 权衡：Guild 结构更好（SQLite 行，按类型 TTL）。PRD 透明度更好（人类可读、可 git diff、可直接注入 LLM 上下文）。 |
| R5（冻结快照） | Session 启动时 CLAUDE.local.md 注入 | `guild_session_start` 返回 oath + brief + quest | 都满足。PRD 快照零工具调用（立即在上下文中）。Guild 需要工具调用但更自包含。 |
| R6（定期清理） | 基于使用的 staleness（30d → 90d）+ curator 合并 | 按类型 TTL（30d/180d/永久） | Guild 按类型 TTL 更优雅。PRD curator 处理更广范围（技能 + 记忆 + 合并 + 报告）。 |
| R7（无后台服务） | Hooks → CLI 命令（运行即退出） | MCP 服务器（持久进程）+ 嵌入式 ONNX 运行时 | **Guild 不满足 R7。** MCP 服务器就是后台进程。ONNX 运行时相当于向量数据库。R7 明确排除两者。 |

### A.3 Guild 不提供的功能

Guild 是一个**任务协调基板**。它不提供 PRD 的任何自我进化功能：

- ❌ 自动技能创建（无技能概念）
- ❌ 自动技能修补（无原地编辑知识的机制）
- ❌ CLAUDE.md 修改（仅为注册写入 AGENTS.md）
- ❌ 三层知识分类法（lore 种类 ≠ SOP/经验/State）
- ❌ 状态引擎（quests 追踪任务完成，不追踪 initiative 进展）
- ❌ `coworker run` 循环驱动
- ❌ 带沙箱测试和熔断机制的审批模型

### A.4 决定

**Guild 不是 PRD 记忆架构的替代品。** Guild 不满足 R2 和 R7，且不提供作为 PRD 核心目的的任何自我进化功能。

**Guild 是互补的 v2 候选。** Guild 的任务面板、级联解锁和混合搜索可以作为 PRD 任务协调层的补充（MVP 不包含）。当 v2 考虑向量搜索时也值得评估作为 FTS5 的替代方案。
