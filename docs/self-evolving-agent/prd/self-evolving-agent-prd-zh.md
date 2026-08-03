# Self-Evolving Agent — PRD

> 目标：交付一个在持续循环中自演化以达成目标的自主智能体。该智能体是 Claude Code（及 OpenCode），由 walter-worker 驱动。智能体执行真实动作——监控、编排——基于真实信息源。

## 状态

| 状态 | 日期 | 作者 |
|----|------|--------|
| 🚧 draft v6 | 2026-07-25 | cicidi + Claude |

## 变更记录

| 日期 | 变更 |
|------|-------|
| 2026-07-25 | v6：**仅保留需求的重构。** PRD 现在只陈述「做什么/为什么」；「怎么做」（技术、存储、schema、hook 配置、成本、复用分析）移至 [spec](../spec/self-evolving-agent-spec.md)。具体：(1) 移除 §1.4 Hermes 作为基础、§6 架构、§7 集成与实现、附录 A Guild 评估——均为方案层，现归 spec。(2) 把技术专有词（DeepSeek/Hermes/sqlite-vec/hook 名/存储路径）泛化为技术中立的需求语言。(3) 反转 §5.4 隐私模型：默认改为**远程** background LLM（v5 为本地默认）。(4) MEMORY.md 从 Tier 3 存储降级为只读 curator 导出（§3.5）。(5) 向量/embedding 记忆**移回 scope**（mem0）——从 OOS 删除。(6) 新增需求：演化有效性指标（§5.7）、pending queue 不溢出（§5.1）。 |
| 2026-07-25 | v5：修复 adversarial review 的 3 个阻塞项（async hook、Stop hook 名、隐私模型）。*（v6 反转了隐私项 #3。）* |
| 2026-07-25 | v4：重构为三层记忆架构（§3）。 |
| 2026-07-24 | v3：主体验改为 Hook 嵌入的隐式演化。 |
| 2026-07-24 | v2/v1：安全架构、loop 状态机、hook 缓解、成本模型、Guild 评估。 |

> **配套 spec：** [`../spec/self-evolving-agent-spec.md`](../spec/self-evolving-agent-spec.md)——权威的「怎么做」（mem0 基座、Hermes loop 改造、双 IDE 采集、schema、错误处理）。PRD 阐述需求（R1–R7）；spec 满足之。

---

## 1. 概览

### 1.1 愿景

一个通过做真实任务持续自我改进的 Claude Code / OpenCode 智能体。每个 session、每个 turn、每次犯错都反馈回系统——skill 自动创建、记忆持久化、行为演化。你用得越多，它越聪明。

**你的体验：** 你正常使用 Claude Code（或 OpenCode）。幕后，平台捕获发生的事，一个 background LLM 提取教训，智能体悄悄积累 skill 与记忆。一个 session 接一个 session，智能体积累知识——你喜欢的约定、踩过的坑、奏效的工作流。没有单独的「训练模式」。演化嵌入在日常使用中。

### 1.2 主体验：Hook 嵌入的隐式演化

```
你自然地使用 Claude Code / OpenCode
         │
         ▼
  每次 tool call 之后
  ─────────────────────
  平台在后台记录状态、同步记忆
  （不阻塞你的工作）
         │
         ▼
  session 结束时
  ─────────────────────
  一个 background LLM 读取完整 transcript，
  提取教训，识别可复用工作流，
  并把 skill 暂存以待 review
         │
         ▼
  下一个 session：更丰富的上下文、
  更好的 skill、更聪明的智能体
```

**没有单独的命令，没有外部驱动。** 智能体在你工作时后台演化。这是主 UX。每个 IDE 的具体 hook/event 接线见 spec（§3）。

### 1.3 SDK 模式

面向程序化场景（CI/CD、批处理、定时自主运行），以显式状态机驱动的 loop 暴露为 CLI，供脚本与自动化使用——不是主 human 体验。loop 行为见 §2.2。

### 1.4 实现选型

实现选型（记忆基座、skill 提炼模式、hook 接线、LLM/embedder 选择、成本）**不**在本 PRD 指定。它们位于 [spec](../spec/self-evolving-agent-spec.md)。PRD 刻意保持技术中立，以便基座可替换而无需改动需求。

### 1.5 关键决策

| 决策 | 选择 | 理由 |
|----------|--------|-----------|
| 主体验 | **Hook 嵌入的隐式演化**——你用 IDE，平台做其余的事 | 演化不应感觉像单独的工具或模式 |
| SDK 模式 | 显式 loop CLI，用于 CI/CD、批处理、headless 自动化 | 同一套基础设施，脚本的 CLI 入口 |
| 目标模型 | 元目标：自我改进为主驱动，真实工作为训练场 | 智能体通过使用而演化 |
| 演化范围 | Skills + Context + Code + Config（全范围） | 智能体触及的一切皆可改进 |
| 记忆架构 | 三层：Session → Project-State → Long-Term | 每 turn 同步、跨 IDE/跨项目搜索、语义+精确检索、定期清理 |
| Skill 创建 | 复用现有 `skill-create` / `skill-edit` | 不重复造轮子——自动触发 |
| 编排 | 由智能体决定如何分解任务 | walter-worker 不硬编码工作流 |
| 原则 | 优先复用 → 不够改造 → 没轮子造轮子 | 务实，不教条 |

### 1.6 知识分类

智能体生成三类知识，各映射到一个记忆层：

| 类型 | 定义 | 示例 | 记忆层 | 触发 |
|------|-----------|---------|-------------|---------|
| **SOP** | 可重复的操作流程——某任务的逐步步骤 | "修复 lint 错误的标准流程"、"部署到 production 的检查清单" | Skill 存储 → 晋升到 skill-factory | 复杂任务完成后自动判断 → `skill-create` |
| **经验总结** | 对/错的教训、发现的模式、坑点 | "MCP 首次请求总是 403 超时，需重试"、"ruff E501 在这个项目被忽略" | **Tier 3**——长期记忆存储（跨项目、永久） | 每 turn 同步 + session 结束 LLM 总结 |
| **State / 进度** | 当前状态——做了什么、对/错、done/pending、谁在做、何时完成 | "Dashboard 5 页完成 2 页 pending，blocker 是数据源 API 未就绪" | **Tier 2**——State 文件（`docs/<initiative>/state/YYYY-MM-DD-state.md`） | 每 turn / 每个 phase 完成 |

**SOP vs 经验 vs State：** SOP 是「怎么做」（可复用流程，晋升到 skill-factory 共享），经验是「发生了什么/学到了什么」（长期记忆，跨项目持久化），State 是「当前在哪」（中期记忆，项目完成即归档）。

---

## 2. 演化如何发生

### 2.1 隐式 Loop（主体验）

每个 session 就是一个演化周期。没有单独的「run」命令——演化在使用中自动发生：

```
Session N                            Session N+1
┌──────────────────────┐            ┌──────────────────────┐
│  你做真实工作         │            │  更聪明的智能体       │
│  ──────────────────── │            │                       │
│  每次 tool call 后     │            │  • 更丰富的上下文     │
│  → 记录状态           │  ──────►   │    （snapshot 有新    │
│  → 同步记忆           │  Session   │     记忆）            │
│                       │   结束     │                       │
│  session 结束时       │            │  • 更好的 skill       │
│  → 总结教训           │            │    （上个 session     │
│  → 暂存 skill         │            │     暂存）            │
└──────────────────────┘            └──────────────────────┘
```

**什么触发什么：**

| 触发 | 何时 | 发生什么 |
|---------|------|-------------|
| **每次 tool** | 每次 tool call 之后 | 记录状态。后台同步记忆到长期存储。subagent 结果也被捕获。 |
| **Session 结束** | session 结束 | 完整 transcript → background LLM → 提取教训 → 长期记忆。识别可复用工作流 → 暂存 skill 以待 review。为下个 session 更新记忆 snapshot。 |
| **Skill 使用** | session 中 | 跟踪使用。若 skill 错误/过时 → 智能体 patch 它。 |
| **Curator** | 定期（空闲） | 清理：归档过期条目、合并重复、生成报告。绝不触碰手写内容。 |

**关键洞察：** 演化不是单独的模式。你做真实工作的每个 session 都成为训练数据。用得越多，skill 与记忆积累越多。

### 2.2 SDK 模式

面向程序化使用，同一套基础设施以显式 loop 暴露为 CLI。默认最长运行：**12 小时**；到时优雅停止并保存状态。不带 loop 标志时，运行一个周期即退出。

**一个周期** = Observe → Decide → Spawn agent → Record。每个周期产出具体结果或一个刻意的 no-op。

**终止条件**（满足任一即停）：

| # | 条件 | 检测 |
|---|-----------|-----------|
| 1 | **目标达成** | 用户提供的成功标准判定为 true（如 `pytest --exitfirst` 返回 0、`ruff check` 返回 0） |
| 2 | **停滞** | 连续 3 个周期无新变更（无代码 diff、无 skill 创建/patch、无记忆条目） |
| 3 | **时间到期** | 默认 12h 到。优雅停止：保存状态、运行总结、退出。 |
| 4 | **人工 halt** | 人工确认「done」或「stop」 |

**错误恢复**（降级，不崩溃）：

| 故障 | 恢复 |
|---------|----------|
| Agent session 错误（API 超时、限流） | 指数退避重试至多 3 次；全失败则记录错误到 state 并进入下一周期 |
| 每 tool 捕获失败 | session 结束那次捕获完整 summary；audit trail 记录缺口 |
| Background LLM 宕机 | 回退到备用 provider；全挂则推迟同步到下一周期（无数据丢失——原始 transcript 保留） |
| 搜索索引损坏 | 从 source of truth 自动重建；记录事件 |
| 并发 session 冲突 | 锁定共享存储；第二个 session 排队或跳过 |

> 详细状态机图与 SDK 内部见 spec。

> **什么会被自动更新、什么不会：** 自动演化只修改 **CLAUDE.local.md**（个人、不提交）、共享 skill 存储中的 skill、长期存储中的记忆。**CLAUDE.md**（共享、提交）**绝不**被自动修改——自演化规则由人工一次性写入。此分离确保智能体演化个人上下文而不改变团队约定。

### 2.3 不做 Publish / Transact（MVP）

- `publish` 与 `transact` 在 MVP 范围外
- `orchestrate` 委派给智能体——walter-worker 不硬编码任务分解

---

## 3. 记忆——三层架构

### 3.1 需求

智能体必须跨 session、项目、IDE 持久化所学：

- **R1 — IDE 无关（双 IDE）：** 记忆由 **Claude Code 与 OpenCode** 共享，二者均为一等公民。本节每条需求都必须对每个 IDE 有可行方案。不锁定到任何单一 IDE 的配置目录。
- **R2 — 每 turn 持久化：** 每个 turn 的关键信息持久化，无需智能体手动调用 save。
- **R3 — 跨 session 搜索：** 跨所有过往 session 搜索，不论项目或 IDE。必须同时支持精确 key 查找（按 project + topic）与模糊/语义搜索（找概念相似内容）。仅关键词搜索不足。
- **R4 — 智能体管理的笔记：** 智能体可写入、patch、删除自己关于项目（约定、工具怪癖、教训）与用户（偏好、工作流习惯）的笔记。
- **R5 — 冻结 snapshot：** 每个 session 以积累知识的稳定 snapshot 开始。session 中写入落盘但不扰动当前 session 的上下文。
- **R6 — 定期清理：** 过期与未用条目自动归档。手写条目绝不触碰。
- **R7 — 轻量：** 无强制常驻后台 server 进程。LLM 用于总结/检索，不持续运行。

### 3.2 三层记忆模型

记忆按三层组织，从短命到永久：

```
┌─────────────────────────────────────────┐
│  TIER 1 — Session 记忆                  │
│  正在发生的 NOW                          │
│  生命周期：session 时长                  │
└──────────┬──────────────────┬───────────┘
           │ session 结束     │ 每 turn 同步
           ▼                  │
┌──────────────────────────┐ │
│   Session Transcript     │ │
│   （原始，保留）          │ │
└──────────┬───────────────┘ │
           │ LLM 总结        │
           ▼                  │
┌──────────────────────────┐ │
│  TIER 3 — 长期           │◄┘
│  记忆（所有项目，         │
│  永久）                  │
│  教训、模式、             │
│  约定、偏好              │
│  搜索：精确 + 语义        │
└──────────┬───────────────┘
           │ session 开始时 snapshot
           ▼
┌─────────────────────────────────────────┐
│  TIER 2 — 项目状态记忆                   │
│  做了什么 / PENDING / BLOCKED            │
│  生命周期：initiative 时长               │
│  完成时关键教训晋升到 Tier 3             │
└─────────────────────────────────────────┘
```

**数据流：**
- **Session → Tier 3（主）：** session 结束 LLM 把 transcript 总结进长期记忆。主捕获路径——每个 session 产出学习。
- **Session → Tier 2（每 turn）：** state 变更贯穿 session 写入 initiative state 文件。
- **Tier 2 → Tier 3（完成时）：** initiative 完成时，关键教训晋升到长期记忆。
- **Tier 3 → Tier 1（session 开始）：** 相关长期记忆的冻结 snapshot 注入新 session。

| 层 | 范围 | 生命周期 | 存什么 | 关键操作 |
|------|-------|----------|---------------|----------------|
| **Session** | 当前 session | session 时长 | 活跃上下文、tool call、对话 | 自动捕获 |
| **项目状态** | 当前 initiative | initiative 时长 | 进度、决策、blocker、phase 跟踪 | 每 turn 同步、phase snapshot |
| **长期** | 所有项目 | 永久（curated） | 教训、模式、约定、用户偏好 | session 结束总结、跨 session 搜索、定期策展 |

### 3.3 Tier 1 — Session 记忆

智能体的工作记忆——session 中它「看到」的东西。

- **内容：** 当前对话、tool-call 历史、session 开始时注入的长期知识冻结 snapshot（§3.8）。
- **捕获：** 自动。无需手动「save」。
- **生命周期：** session 时长。session 结束时，原始内容保留在 transcript；background LLM 提取关键教训并晋升到 Tier 2 和 Tier 3。
- **约束：** session 中向长期记忆的写入**不**刷新 session 的 snapshot。长 session（>2h）有手动刷新。

### 3.4 Tier 2 — 项目状态记忆

跟踪当前 initiative「走到哪」。中期——详细、项目特定，initiative 完成时完整。

- **内容：** 三维——做了什么（具体产出）、对/错（教训）、当前状态（done/not done/谁/何时/依赖）。
- **存储：** State 文件 `docs/<initiative>/state/YYYY-MM-DD-state.md`。持续更新的活文档。先前条目可随状态修改（如 `🚧 → ✅`）。
- **记录标准：** 任一维变化时记录。见 §4。
- **生命周期：** initiative 时长。完成时 state 文件成为历史；关键教训晋升到 Tier 3。

### 3.5 Tier 3 — 长期记忆

跨项目、跨 session、无限期持久的知识。这是让智能体「随时间变聪明」的东西。

- **内容：** 学到的教训、可复用模式/工作流、项目约定、工具怪癖、用户偏好、已完成 initiative 的提炼经验。
- **存储：** 一个长期记忆存储，**必须**支持：
  - **精确检索：** 按 project、topic、problem key 找条目。
  - **模糊/语义搜索：** 跨项目找概念相似条目。
  - **人类可读导出：** 存储的只读、curator 生成的镜像，用于 git-diff 与离线阅读。（存储本身是 source of truth；导出是派生的。）
  - **统一搜索范围：** 所有项目、所有 session、两个 IDE——一个搜索面。
- **捕获：**
  - **每 turn（次、可靠性）：** 每个重要 tool call 的关键信息被提取并增量写入。尽力而为——失败不阻塞 session。
  - **session 结束总结（主、质量）：** session 结束时，background LLM 读完整 transcript，提取教训/模式，识别可复用工作流，并对照每 turn 捕获做对账/去重。每个 session 产出学习。
- **生命周期：** 永久，带自动维护（§3.7）。
- **检索：** 脚本用 CLI，人类用 skill。智能体遇到与过往相似情境时可主动搜索记忆。

### 3.6 记忆同步流

- **每 turn 同步：** 每个重要 tool call 后，关键信息提取到 Tier 2（state）和 Tier 3（长期）。轻量、非阻塞。覆盖缺口由 session 结束那次缓解。
- **session 结束同步：** 完整 transcript 由 background LLM 总结；教训/模式写入 Tier 3。捕获每 turn 漏掉的（subagent 结果、丢弃的输出）。也触发 post-session 总结（§5.4）。
- **Provider 回退：** 主 background LLM 不可用时回退到备用 provider。全挂则推迟到下一周期。无数据丢失——原始 transcript 保留。
- **Audit trail：** 每次同步写带时间戳的 audit 记录，便于缺口检测。
- **Subagent 内容：** 由专门的 subagent 完成触发器捕获，session 结束总结作为次路径。

### 3.7 记忆维护（Curator）

定期维护保持长期存储健康：

- **触发：** 定期，智能体空闲时。
- **动作：** 跟踪每条目使用；标记未用（30 天 → `stale` → 90 天 → `archived`）；pin 高价值条目；合并重复；生成报告；重新生成人类可读导出。只动智能体创建的条目——绝不手写。
- **恢复：** 归档条目可恢复。

### 3.8 上下文注入（Snapshot）

session 开始时，相关长期记忆的冻结 snapshot 注入 session 上下文。Claude Code 与 OpenCode 都在 session 开始时读取个人上下文文件，所以 snapshot 立即可用——无需 tool call。

- **开始时冻结：** 一次性捕获。session 中写入不刷新活跃 snapshot。
- **每 session 替换：** 下个 session 开始时旧 snapshot 整体替换，由 merge 层守护以防破坏人类内容。
- **session 中刷新：** 手动命令从磁盘重载 snapshot。长 session（>2h）有用。默认行为保持冻结。
- **智能体管理、人类可读：** 由智能体写入，人类可读可编辑。

---

## 4. State 引擎

### 4.1 触发

每个 turn → 捕获触发 → 平台写入 state 文件。无需手动——state 记录是使用 IDE 的副作用。

### 4.2 State 文件

```
docs/<initiative>/state/YYYY-MM-DD-state.md
```

- 持续更新的活文档（不只是每日 snapshot）
- 追加新事件**并**修改先前条目（如 `🚧 → ✅`）
- phase 完成（PRD/spec/design/plan/test）强制一次 state 更新

### 4.3 记录标准

三维——任一满足即记录：

| 维度 | 含义 |
|-----------|--------------|
| **做了什么** | 具体产出：代码、文档、配置、研究结论、外部动作、自动化 |
| **对/错** | 教训：什么奏效、什么没有、发现的 bug、暴露的盲点、compaction 风险 |
| **进度** | 跟踪：done/not done/谁在做/何时 done/依赖 |

**总是记录：** 代码/文档/配置变更；系统事件（MCP 设置、模型配置、备份/恢复、compaction）；带结论的研究；失败尝试；subagent 结论。

**绝不记录：** 即时查询（只是看看）；单命令原子操作；纯聊天/好奇；瞬态状态检查。

---

## 5. 自演化引擎

### 5.1 自动 Skill 创建

**触发（双）：**

1. **Post-session 触发——主：** 当 background LLM 总结 session 时（§5.4），它同时评估是否有工作流/模式可复用。是 → 以完整 session transcript 为上下文调用 `skill-create`。最强——有完整 session 全貌。
2. **In-session 触发——次：** 完成一个有显著 tool-call 足迹的任务（默认阈值：10+ tool calls）。可配置。

**CLAUDE.md 中的规则：**
```markdown
## Self-Evolution Rules
When you complete a complex task using significant tool calls:
1. Assess whether the workflow/pattern/knowledge is reusable
2. If yes → invoke `skill-create` to generate SKILL.md automatically
```

**审批模型：**

| 模式 | 行为 |
|------|----------|
| **Review 模式**（`auto_approve: false`，默认） | skill 暂存到 pending queue——用户 review |
| **Auto 模式**（`auto_approve: true`） | skill 自动创建无需提示（opt-in） |

**Pending queue 不得无限增长**（需求）：queue 支持 batch approve/reject，且 30 天未触碰的条目自动过期（auto-rejected，绝不静默晋升）。queue 跨重启持久化。*（简单 v1；质量评分延后。）*

- 记忆写入：轻量，inline review
- Skill 写入：总是暂存（太大，无法 inline 预览）
- **安全闸**（见 §5.6）：circuit breaker、sandbox 测试、rollback。

### 5.2 Skill 生命周期与晋升

Skill **先在本地创建**，不直接进 skill-factory。它们靠自己挣上去。

**规则：**
- **0–9 次：** 共享存储，两个 IDE 都可 sync
- **10+ 次：** 自动标记晋升 → 复制到 `skill-factory/personal-skills/` → 人工 review 并提交
- **使用跟踪：** sidecar JSON，原子写入。失败尽力而为——坏计数器绝不阻塞 skill 调用。跟踪 use/view/patch 计数、state、provenance。
- **质量指标：** `error_rate`、`patch_frequency`、`user_override_rate`、回归检测（patch 后 error rate 超 patch 前则 rollback）。
- **生命周期：** active → stale（30d 未用）→ archived（90d）。Pinned/高历史用量 skill 豁免。
- **Provenance：** agent-created / bundled / skill-factory / hub。Curator 只动 agent-created。

### 5.3 自动 Skill Patching

**触发：** 使用现有 skill 时发现它过时、不完整或错误 → 调用 `skill-edit`（外科式：`old_string → new_string`）。`patch_count` 喂给 curator 与晋升。与创建相同的审批模型 + 安全闸。可 rollback。

### 5.4 Post-Session 总结（核心演化机制）

**触发：** session 结束。

这是隐式演化体验的核心机制。每个 session 在一次 LLM 过完整 transcript 的单遍中产出两个结果：

1. **总结经验** → 教训/模式/坑点到记忆 → 索引 → 下个 session 的 snapshot 含此知识。
2. **识别可复用工作流** → 评估是否有任务模式值得捕获为 skill → 是则通过 `skill-create` 暂存。

单遍同时做两件事避免额外 API 调用。完整 transcript 为 skill 识别提供比任何单次 in-session 触发更丰富的上下文。

**隐私模型：** session transcript 可能含专有代码与凭证。默认地，总结把 session 内容发送给配置的**远程** background LLM（项目所选 provider）。需要对敏感内容做本地处理的用户可 opt in 到本地模型。provider 回退链（§3.6）在配置 provider 不可用时适用。

> v5 默认本地；v6 按业主决策反转为远程默认（默认使用配置的 provider；本地为敏感 session 的 opt-in）。

**这就是让演化感觉自动的东西。** 你完成工作、关闭 IDE，下次智能体已从上个 session 学到东西。

### 5.5 Curator

**触发：** 定期（空闲）。索引维护更频繁。

**动作：** 跟踪使用指标；归档过期（30d → 90d）；pin 高用；合并重复；生成报告；重新生成人类可读导出；只动 agent-created 条目。通过 unarchive 命令恢复。

### 5.6 安全与对齐架构

> **为何存在：** 上海 AI Lab 研究（2026）记录了全部四条自演化路径的安全侵蚀：模型演化把钓鱼风险触发从 18.2% 抬到 71.4%；记忆演化把恶意代码拒绝从 99.4% 降到 54.4%；工具演化显示 65.5% 的自动创建工具不安全；工作流演化把恶意请求拒绝从 46.3% 压到 6.3%。AgentWorm（北京大学，2026）展示了对自传播智能体漏洞 63% 的攻击成功率。没有安全基础设施的自修改自主智能体是站不住脚的。

**默认：** 所有自演化默认 **review 模式**。Auto-approval 是 opt-in 且按操作类型限定。

| 操作 | 默认 | 可 opt-in auto？ |
|-----------|---------|---------------------|
| Skill 创建 | Review（pending queue） | 是，按 skill 域 |
| Skill patching | Review（pending queue） | 是，按 skill |
| 记忆写入 | Inline review | N/A（轻量） |
| 后台创建 | 总是暂存 | 否 |

**Circuit breaker：** 24 小时内创建或 patch 超过 3 个 skill，则 halt 所有自动演化（暂停 create/patch、保留 pending queue、通知用户、仅 review 后 resume）。

**Sandbox 测试：** pending skill 晋升前，在沙箱 session 中 dry-run（无副作用）并验证最小安全检查。失败 → 留在 pending 并记录原因。

**Rollback：** 每个自动创建/patch 的 skill 支持回滚到上一个 known-good 版本。patch 后 error rate 超 patch 前 50%+ 则自动回滚。版本历史保留最近 5 版。

**安全监控：** 每 session 跟踪 `refusal_rate`、`unsafe_output_rate`、`skill_error_rate`、`circuit_breaker_trips`；喂给 curator 决策。

> **已知缺口（语义威胁）：** sandbox 检查是语法层的（如危险 shell 模式）。所引威胁是语义的（钓鱼、拒绝崩溃）。语义 guard 是公认需求；作为后续项跟踪，而非 MVP 阻塞项。

### 5.7 有效性指标

愿景是「随时间变聪明」。除安全指标（§5.6）外，系统**必须**衡量它是否真的变得更有用。这些是需求：

| 指标 | 信号 | 目标趋势 |
|--------|--------|--------------|
| `skill_reuse_rate` | 调用自动创建 skill 的 session 占比 | 上升 |
| `user_correction_rate` | 每任务用户覆盖/纠正智能体的次数 | 下降 |
| `task_first_pass_rate` | 无返工完成的任务 | 上升 |
| `memory_hit_rate` | 返回有用条目的搜索 | 上升；非零基线说明记忆被使用 |

采集每 session 自动进行，在 curator 报告中呈现。确切公式是实现细节（spec）。

---

## 6. 实现

实现（记忆基座、skill 提炼 loop、hook/event 接线、schema、错误处理、成本模型、现有 walter-worker 基础设施复用分析）在 [spec](../spec/self-evolving-agent-spec.md) 中指定。本 PRD 刻意省略需求**如何**被满足。

---

## 7. 范围外（MVP）

- Publish / Transact 操作
- GEPA/DSPy prompt 演化（v2）
- 多智能体委派 mesh（v2）
- Guild Agent 集成（已评估——互补的任务协调层，v2 候选；非记忆架构的替代）
- 超出语法层 sandbox 检查的语义安全 guard（后续项；见 §5.6）

---

## 8. 开放问题

### 已解决

1. ✅ **SDK loop 终止：** 三个条件（§2.2）：目标标准、停滞（3 周期）、时间到期（12h）。
2. ✅ **搜索索引重建：** 增量为主；完整性失败时从 source of truth 全量重建。
3. ✅ **Snapshot 注入：** 分项目的 snapshot 块；session 中可刷新。
4. ✅ **主 UX：** Hook 嵌入的隐式演化；SDK loop 留给自动化。
5. ✅ **向量/embedding 记忆：** 在 scope 内（MVP）。基座选择（mem0）在 spec。
6. ✅ **隐私默认：** 默认远程 background LLM；本地 opt-in（v6 反转 v5）。
7. ✅ **长期存储 schema 与 MEMORY.md 角色：** 存储是 source of truth，带已定义条目 schema；MEMORY.md 是只读 curator 导出（spec §2.3、§5.2）。

### 新增（v2+）

1. **OpenCode 捕获覆盖：** OpenCode 的每 tool 事件是否对所有 tool 类型触发，等价于 Claude Code？需实证验证才能宣布双 IDE 生产级 parity（spec §8 spike）。
2. **Skill 质量自动检测：** 能否不等用户覆盖信号就自动检测 skill 退化？
3. **跨项目 skill 晋升：** 项目本地 skill 何时晋升到 skill-factory？
4. **Loop 停滞敏感度：** 3 周期是否是正确的 SDK 阈值？需真实运行调参。
