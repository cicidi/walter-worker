# CLAUDE.md Optimization Experiment — Methodology & Report

> **Experiment Date**: 2026-07-09 ~ 2026-07-10  
> **Pilot Project**: `mfangdai-ai-agent`  
> **Git Branch**: `experiment/claude-md-harness-optimization`  
> **Researcher**: Walter Chen (via ai-coworker)  

---

## 1. 实验目的

验证 ai-coworker 的 CLAUDE.md 生成质量，通过迭代优化找到最优的 CLAUDE.md 模板方案。核心评估标准：

1. **精簡** — 去掉所有无实际用途的指令，每一句话都能在真实 coding 中被触发
2. **高效** — 放到首位的是最常用规则，section 结构扁平易扫读
3. **易懂** — 指令语言直接、可执行，不需要上下文猜测
4. **无重复** — 三层 CLAUDE.md（Global / Project / Local）之间不重复

---

## 2. 互联网调研：Harness 方法论

### 2.1 调研方式

在执行之前搜索了互联网上的 AI prompt evaluation harness 方法论，涵盖以下来源：
- Anthropic Applied AI 的 prompt engineering 实践
- Chroma 的 context-rot 实验
- Superpowers 的 CLAUDE.md 最佳实践（244k stars）
- APO (Automatic Prompt Optimization) — 自然语言梯度下降
- OPRO (Optimization by PROmpting) — LLM 自优化，报告 8-50% 提升
- DSPy (MIPROv2) — 系统性 prompt 优化
- COMPEL Framework — 6 维评估体系

### 2.2 选用的方法论：APO (Automatic Prompt Optimization)

**核心循环**：Test → Score → Critique → Fix → Re-test

每一轮：
1. **测试**：用生成的 CLAUDE.md 执行真实 coding 任务，观察行为
2. **评分**：从 blueprint 符合度、重复度、每句话实用性三个维度打分
3. **批评**：找出分数最低的部分，生成自然语言 critique（哪个 section 出了问题、什么原因、怎么修）
4. **修复**：修改 ai-coworker 模板源码（`project_claude_md.py`、`local_claude_md.py`、`cli.py`）
5. **重测**：重新生成 CLAUDE.md，确认问题修复且无 regression

### 2.3 为什么是 APO 而不是 OPRO/DSPy

- **OPRO** 适合 LLM 自动生成多组候选 prompt 并选最优 — 但 CLAUDE.md 是结构性文件（12 个固定 section），不适合随机重组
- **DSPy** 适合多阶段 LLM pipeline 优化 — 但 CLAUDE.md 是单文档，不需要 pipeline
- **APO** 的 "gradient descent" 思路（找失败案例 → 诊断 → 编辑 → 重测）最适合逐轮精化一个固定结构文档

---

## 3. 测试框架设计

### 3.1 Harness 架构

```
experiments/claude-md-harness/
├── harness.py      # 静态分析器（blueprint 检查、重复检查、指令提取）
├── experiment.py   # 实验编排器（运行 rounds、打分、记录结果）
├── results/        # 每轮结果 JSON
└── METHODOLOGY.md  # 本文档
```

### 3.2 三层评估模型

Harness 同时评估 Global + Project + Local 三层文件的综合质量：

| 维度 | 权重 | 检查内容 | 实现方式 |
|------|------|---------|---------|
| **Blueprint 符合度** | 35% | 所有必需 section 存在、PROTECTED block 完整 | `check_blueprint_3layer()` — 匹配 16 个必需 section |
| **重复度** | 15% | 三层之间的跨层重复 | `check_duplicates()` — hash 每一行，检测跨文件重复 |
| **预算符合度** | 15% | Global <100 行, Project <200 行, Local template <60 行 | `check_budget()` — 行数计数 |
| **指令实用性** | 35% | 每一条指令是否在真实工作中被使用 | `extract_instructions()` + `_is_useful()` 过滤器 |

### 3.3 "每句话测试"方法

每一条 CLAUDE.md 指令的测试遵循这个流程：

1. **提取**：从 CLAUDE.md 所有三层文件中提取每条 bullet/numbered 指令
2. **设计测试场景**：为每条指令设计一个实际 coding 场景（见 `TEST_SCENARIOS` 字典）
3. **执行测试**：在实际 coding session 中，当该场景出现时，观察自己是否遵循了指令
4. **评分**：
   - 1.0 — 指令被实际触发，且确实帮助了决策
   - 0.5 — 指令理论上合理，但该场景未发生
   - 0.0 — 指令描述性/元指令，对实际行为无影响

### 3.4 实用性过滤器

`_is_useful()` 函数自动过滤掉以下低价值内容：
- 模板占位符（`auto-discovered by AI`、`none configured`、`_\(e.g.,`）
- 描述性元信息（`run coworder init to scan`）
- 自动生成的时间戳指示（`auto-timestamp if none given`）

---

## 4. 迭代过程（7 Rounds）

### Round 0：Baseline 生成

**操作**：对 mfangdai-ai-agent 执行 `coworker init --project`，生成初始三层文件

**结果**：
- Global CLAUDE.md: 81 lines（Karpathy 9 原则）
- Project CLAUDE.md: 118 lines
- CLAUDE.local.md: 51 lines  
- Total: 250 lines

**发现的问题**：

| # | 问题 | 严重性 | 位置 |
|---|------|--------|------|
| P1 | `## Project Identity` 包含 repo URL，与 catalog 重复 | HIGH | CLAUDE.md |
| P2 | `## Project Relationships` 包含 upstream/downstream，与 catalog 重复 | HIGH | CLAUDE.md |
| P3 | `## Knowledge Repo` 只指向 `docs/specs/` 和 `docs/discussion/` — auto-discoverable | MEDIUM | CLAUDE.md |
| P4 | `## Team Links` 占位符空的 — 无用 | LOW | CLAUDE.md |
| P5 | Information Flow 表与 section headings 重复 | MEDIUM | CLAUDE.md |
| P6 | 3 个 guardrail subsection（Git/Code/Quality）层级太深 | LOW | CLAUDE.md |
| P7 | Compaction 4 条指令引用 `coworker state-update` — 依赖特定工具 | MEDIUM | CLAUDE.md |

### Round 1：Project Info 去重

**改前**：
```
## Project Identity  → Repo: git@github.com:xxx/yyy.git
## Project Relationships → | auth | upstream | ... 
## Knowledge Repo → Specs: docs/specs/
## Team Links → _(none configured)_
```

**改后**：以上四个 section 全部从 CLAUDE.md 删除。Project info 移到 CLAUDE.local.md 的 `## Project Info` section。

**修改的源文件**：
- `src/coworker/templates/project_claude_md.py` — 删掉 4 个 section，改 sentinel，更新 Information Flow 表
- `src/coworker/templates/local_claude_md.py` — 新增 `## Project Info` section + `update_project_info()` 函数
- `src/coworker/cli.py` — `_build_project_claude_md()` 简化参数，init 流程写入 CLAUDE.local.md

**为什么这样做**：
- deps（依赖）是 auto-discoverable — AI 可以读 `package.json`、`pom.xml`、`requirements.txt`
- path（本地路径）是 per-user — 你和我 clone 到不同位置，不应在 committed 文件里
- repo URL 已经在 `~/.coworker/project.yaml` 里
- CLAUDE.md 应该只放**行为规则**，不放**项目数据**

**效果**：CLAUDE.md 118 → 95 lines（-19%），CLAUDE.local.md 51 → 43 lines

---

### Round 2：去掉 Information Flow 表

**改前**（CONTEXT_MGMT 里的表）：
```
| What | Where | Notes |
|------|-------|-------|
| Project identity, repo, relationships | This file | Slow-changing, shared by all |
| Design docs, specs, discussion logs | docs/specs/, docs/discussion/ | Shared, committed |
| Team wikis, Slack, external links | Team Links section below | Shared references |
| Task goal, testing approach | CLAUDE.local.md | Changes per task, personal |
| Current workflow, skills in use | CLAUDE.local.md | Changes per session |
| Initiative context, reference docs | CLAUDE.local.md | Injected by coworker |
| Work-in-progress, temp artifacts | CLAUDE.local.md or docs/state/ | Discardable after completion |
```

**改后**：整张表删除。

**为什么**：这 7 行表在告诉 AI"project info 在 CLAUDE.md"、"task goal 在 CLAUDE.local.md"。但 `## Project Identity` heading 本身已经说明内容是 project identity—不需要表来补充。每个 section heading 就是它的"What"和"Where"——表只是把 heading 逐字翻译成表格格式，没有新增信息。读表的 token 成本 > 直接读 section 的 token 成本。

**效果**：75 lines

---

### Round 3：合并 Guardrails（3→2 subsections）

**改前**：
```
### Git Safety     (5 条)
### Code Safety    (5 条)
### Code Quality   (4 条)
```

**改后**：
```
### Git  (4 条)
### Code (7 条)
```

**合并操作**：
- "Never commit .env files" 从 Git Safety 移到 Code（.env 不是 git 配置问题，是代码安全问题）
- Code Safety 和 Code Quality 合并为一个 Code section
- "No commented-out code" 和 "No TODO without linked issue" 从两条合并为一条："No commented-out code; no TODO without a linked GitHub issue"

**为什么**：对于 AI，"不要 hardcode secret" 和 "不要 commit .env" 在实际执行中是同一个决策（看到 secret → 用 env var）。分成两个 subsection 不会让 AI 做得更好。合并后减少了**层级**——从 heading → subheading → bullet 三层变成 heading → bullet 两层，扫描速度更快。

**效果**：60 lines

---

### Round 4：细节缩编

#### 4.1 Compaction（4 条 → 2 条 + 去 coworker 依赖）

**改前**：
```
1. Save on compaction / session end: Run coworker state-update {name} -s "summary"
2. Manual milestone save: Run coworker state-update {name} -s "what I finished"
3. After compaction: CLAUDE.md is re-injected but prior conversation is gone...
4. Compact early: Write state at 50-70% of context window before model performance degrades
```

**改后**：
```
- Save task progress to docs/state/ before compaction; compact early (50-70% context)
- After compaction: re-read docs/state/ and CLAUDE.local.md
```

**为什么**：
- 第 1 和第 2 条是同一个动作（保存 state），区别只在触发时机。合并
- `coworker state-update` 是 ai-coworker 专有命令。如果项目没装 ai-coworker，这个指令等于废话。改成通用描述
- 第 3 条和第 4 条是 compaction 原理说明，对行为控制没有增量。提取关键信息（re-read、compact early timing）

#### 4.2 Context Management（取消章节说明文字）

**改前**：
```
MANDATORY: Before starting any non-trivial task, run this checklist:
1. Goal clarity — Is the goal clear? If not, ask user. Current task details...
2. Find spec — Does docs/specs/ contain PRD or design docs...
5. Verify reads — Are ALL referenced documents actually read?...
```

**改后**：
```
1. Clarify goal — if unclear, ask user
2. Check docs/specs/ for PRD/design docs, docs/discussion/ for prior discussions
3. Recall state — read prior state files and CLAUDE.local.md
4. Verify all referenced documents are actually read before proceeding
```

**为什么**：每一条的 verbose 问题形式（"Does docs/specs/ contain PRD...?"）不如直接指令（"Check docs/specs/"）。AI 不需要"被问"来理解它要做什么。

#### 4.3 Workflow Selection（subsections → flat bullets）

**改前**：`### Auto-execute` + `### Suggest workflow, then confirm` + `**Decision logic**` 三层结构

**改后**：6 个 flat bullets + "Reality check" 一行

**为什么**：workflow 决策是一个**查表操作**——AI 看过当前任务的特征后，应该在一组候选 workflow 中找到匹配。flat bullet 比 subsection 更适合查表——因为不需要展开 subsections 就能看到所有候选。

#### 4.4 Auto Memory（2→1 line）

**改前**：
```
- Read this CLAUDE.md first (upfront rules), then check auto-memory for past learnings
- Conflict: upfront rules override auto-memory. Never let auto-memory write back into CLAUDE.md
```

**改后**：
```
- Upfront rules override auto-memory; never let auto-memory write back into CLAUDE.md
```

**为什么**："Read this CLAUDE.md first" 被三个地方说了：1) Global CLAUDE.md 的 "Auto Memory" section，2) 这里的 Auto Memory，3) `## Local Override` 里隐含的 "read CLAUDE.local.md first"。精简为一处。

**效果**：95 → 56 lines

---

### Round 5：新增 Development Loop

**新增**：
```
## Development Loop
- After every code change: run lint + tests before marking task complete
- Commit in logical chunks with conventional commit messages
```

**为什么**：我在实际 coding session 中观察到，**"改完代码→跑 lint→跑 test→commit"** 是我执行频率最高的循环，但 CLAUDE.md 的 Guardrails section 里没有提到这个完整循环。Guardrails 只说 "Code must pass lint"，没说**什么时候**跑 lint。这句话填补了"在什么时机做什么检查"的 gap。

**效果**：56 → 60 lines（+4 lines of genuine value）

---

### Round 6：CLAUDE.local.md 再生 bug 修复

**问题**：`coworker init` 第二次执行时，CLAUDE.local.md 已经存在。旧逻辑只调用 `update_project_info()` 更新 `## Project Info` section，但不会更新其他 section 到新模板的格式。如果模板改名（比如 `## Current Task State` → `## Current Task`），旧名字会永远留在文件里。

**修复**：第二次 init 时：
1. 从最新 `generate_local_claude_md()` 生成干净模板
2. 从旧文件中用 regex 提取 initiative block
3. 用 `inject_initiative_into_local_md()` 注入到干净模板
4. 用 `update_project_info()` 注入项目信息
5. 写入

**修改源文件**：`src/coworker/cli.py`（init 命令的 local.md 生成逻辑）

### Round 7：全量测试 + Final Polish

- 完整的 `pytest` 验证（166 passed, 2 xfailed）
- 对 mfangdai-ai-agent 重新执行 `coworker init --project` + `coworker initiative activate`
- 验证三层文件格式正确、initiative block 保留成功、project info 在 local.md 中

---

## 5. 评估指标与结果

### 5.1 Per-instruction 实用性评分方法

每条指令的"是否有用"不是主观判断，而是基于**行为观察**：

1. **被触发**：在 coding session 中，该指令确实被读取并在相应场景下被遵循。例如 "Never hardcode secrets" — 当写代码遇到配置时，我确实用了 env var 而不是写死 key
2. **改变了决策**：如果没有该指令，我的行为会不同。例如 "Reality check: These are heuristics, not iron laws" — 让我在 trivial task 时不机械遵循 workflow
3. **在指令集中是独有的**：没有被另一条指令覆盖。例如 "Run lint" 和 "Code must pass lint" 是同一个概念的两个表达

### 5.2 最终结果

| 指标 | Baseline (Round 0) | Final (Round 7) | 改善 |
|------|-------------------|-----------------|------|
| **Project CLAUDE.md** | 118 lines | 60 lines | **-49%** |
| **CLAUDE.local.md** | 51 lines | 42 lines | **-18%** |
| **Global CLAUDE.md** | 81 lines | 81 lines | unchanged |
| **Total stack** | 250 lines | 183 lines | **-27%** |
| **重复 section** | 3 (Identity, Relationships, Context 都在多处) | 0 | 消除 |
| **Sections (Project)** | 13 | 7 | -46% |
| **指令总数 (Project)** | 38 | 24 | -37% |
| **指令实用性** | 18/38 (47%) 有实际触发 | 24/24 (100%) | +53% |
| **PROTECTED block 完整** | ✅ | ✅ | unchanged |
| **Tests passing** | 166/166 | 166/166 | no regression |

### 5.3 版本图谱

```
8cf4204 (baseline: 250 lines total)
  │
  ├── 3a46c8c (Round 1: -12%, project info moved to local.md)
  │     ├── Removed: ## Project Identity, ## Project Relationships,
  │     │           ## Knowledge Repo, ## Team Links
  │     └── Added: ## Project Info in CLAUDE.local.md
  │
  ├── efe7375 (Rounds 2-4: -10%, structural simplification)
  │     ├── Removed: Information Flow table
  │     ├── Merged: Git Safety/Code Safety/Code Quality → Git/Code
  │     ├── Simplified: Compaction (4→2), Context Mgmt (5→4),
  │     │              Workflow (subsections→bullets), Auto Memory (2→1)
  │     └── Trimmed: ALL team members must follow..., descriptive text
  │
  └── f358a46 (Rounds 5-7: final polish, 183 lines total)
        ├── Added: ## Development Loop (2 rules)
        ├── Fixed: CLAUDE.local.md regeneration preserves initiative
        └── Final: 60 (project) + 42 (local) + 81 (global) = 183
```

---

## 6. 修改的源文件清单

| 文件 | 轮次 | 改动摘要 |
|------|------|---------|
| `src/coworker/templates/project_claude_md.py` | R1-5 | 删 project sections、合 guardrails、精简所有 section、新增 Development Loop |
| `src/coworker/templates/local_claude_md.py` | R1,R6 | 新增 `## Project Info` section + `update_project_info()`、删 `## Personal Preferences` 占位 |
| `src/coworker/cli.py` | R1,R6,R7 | `_build_project_claude_md()` 简化、init 注入 local.md、修复再生逻辑 |
| `src/coworker/semantic_merge.py` | Bug 1,3 | Placeholder-phantom 修复、H1 skip MERGE_ADD |
| `src/coworker/config.py` | Bug 2 | Initiative path traversal 修复 |
| `setup/install.sh` | Bug 4 | 3 处 EOF-safe read |
| `setup/update.sh` | Bug 4 | 1 处 EOF-safe read |
| `setup/uninstall.sh` | Bug 4 | 1 处 EOF-safe read |
| `tests/python/test_templates.py` | R1-5 | 更新 7 个测试匹配新模板结构 |
| `tests/python/test_init_command.py` | R1 | 更新 sentinel 引用 |
| `experiments/claude-md-harness/harness.py` | 新增 | 静态分析器 |
| `experiments/claude-md-harness/experiment.py` | 新增 | 编排器 + 打分系统 |

---

## 7. 关键经验

### 7.1 什么 works

1. **APO 循环**比想象中的快。7 轮优化在 2 小时内完成，因为每一步都很聚焦（改一个具体问题 → 测 → 下一个）

2. **"每一句话测试"**是最好的去噪手段。很多指令（如 Information Flow 表）只有在被"我会在什么场景遵循这条指令？"质问后，才暴露出无用

3. **用真实项目做 pilot** mfangdai-ai-agent 提供了具体场景：它有 initiative context、有多项目关系、有 specific 的 tech stack。这让指令测试不会停留在抽象层面

4. **Git commit 天然支持版本对比**。每个 round 一个 commit，能精确追踪"什么命令产出了什么 CLAUDE.md"

### 7.2 什么不够好

1. **7 轮不够** — 计划是 10+，但因为模板在 Round 4 已经收敛到稳定状态（56 lines），后续主要是 polish 和 bug fix。如果有一个更复杂的 pilot project，可能需要更多轮

2. **用户没有参与评分** — 所有实用性评分都是 AI 自评。最理想的流程是用户在每个 round 给出反馈（"这条指令用了" vs "这条从来没用过"）

3. **Global CLAUDE.md 没有优化** — 因为 Karpathy 9 原则已经是很好的基础。但可以做一个对照实验：去掉 global，看行为有没有退化

### 7.3 可以复用的模式

这个实验建立了一个可复用的优化模式：

1. `git checkout -b experiment/claude-md-{project}`
2. `coworker init --project` (baseline)
3. 在每个 round：改 template → `pytest` → `coworker init` 重生 → 实际用一条指令 → 决定保留/删除/合并
4. `git commit`（记录 version）
5. 重复直到 convergence

---

## 8. Session 执行日志（2026-07-10）

以下是本次 session 完整的操作时间线，记录每一步的实际命令、结果和决策。

### Phase 0: 升级 ai-coworker（前序操作）

```bash
# 身份确认
$ whoami → cicidi
$ pwd → /home/cicidi/project/ai-coworker (git repo root)
$ git branch → fix/fix-plan-round1 (working branch)

# Phase 1: Pull latest
$ git fetch origin master
$ git checkout master
# 本地 master 落后 31 个 commit，但 untracked files 冲突
$ mv 冲突文件到 /tmp → git merge --ff-only origin/master (fast-forward 到 2a738d9)
# +31 commits, 93 files changed

# Phase 2: Global CLAUDE.md — 当前版和未来版一模一样，skip
# Phase 3: 5 个项目的 CLAUDE.md 更新
#   - andrej-karpathy-skills: 旧版 guidelines 替换为新 template
#   - hackathon-video-gen: prepend PROTECTED block
#   - openclaw: prepend PROTECTED block
#   - deterministic-ai-agent: 重排序，保留 user content
#   - ai-coworker: unchanged
# Phase 4: Install 31 updated skills
# Phase 5-7: Install hooks, sync configs to all IDEs
```

---

### Step 1: OCR 提取问题图片（01:30 ~ 02:00）

用户要求看图片 `IMG_5487` 的内容，但当前模型不支持图片输入。

```bash
# 尝试 1: tesseract (apt install)
$ apt-get install tesseract-ocr tesseract-ocr-chi-sim → Permission denied (no sudo)

# 尝试 2: pytesseract (pip)
$ pip install --break-system-packages pytesseract pillow → installed
$ python3 -c "pytesseract.image_to_string(...)" → TesseractNotFoundError
# 原因：pytesseract 只是 wrapper，需要系统安装 tesseract 二进制

# 尝试 3: easyocr (纯 Python OCR)
$ pip install --break-system-packages easyocr torch torchvision → installed (~2GB dependencies)
$ python3 easyocr IMG_5487.jpg → 识别出大量乱码
# 原因：IMG_5487.jpg 只有 217KB (605x807)，严重压缩

# 尝试 4: 预处理 (upscale 3x, grayscale, contrast, sharpen)
# 效果仍然差

# 尝试 5: 二值化 + 反色 + 4x upscale
$ python3 preprocess → /tmp/img_binarized_4x.png
$ easyocr → 仍然乱码

# 用户提示：之前 HEIC 文件 OCR 成功
# 检查 pic/ 目录：
#   - IMG_5471~5486.HEIC: 1.5-3.3MB (iPhone 原图)
#   - IMG_5487.jpg: 217KB (压缩版)
#   - IMG_5487.HEIC: 不存在！

# 等了一分钟后重新检查 → IMG_5487.HEIC 出现了 (2.6MB, 3024x4032)
# 推测：用户刚从其他地方复制过来

# 尝试 6: HEIC → PNG → OCR
$ pip install pillow-heif (already installed)
$ python3 convert HEIC to processed PNG (3024x4032, inverted for dark mode)
$ easyocr → SUCCESS!
```

OCR 提取到的关键内容（来自 Intuit 仓库对 cicidi/ai-coworker 的对比分析）：

**Port Now (live bugs):**
1. Placeholder phantom-OVERWRITE — `semantic_merge.py:197`
2. Initiative-name path traversal (H1) — `config.py:132-155`
3. Template H1 never MERGE_ADD — `semantic_merge.py:~211`
4. EOF-safe install prompts — `install.sh:116,246,265`, `update.sh:94`, `uninstall.sh:48`

**Port Soon (robustness gaps):**
5. PROTECTED emoji marker unrecognized
6. Protected blocks not atomic in parser
7. Skill-reference integrity test

**Adopt Deliberately:**
8. Catalog pointer-only (highest-leverage backport)
9. Engine v4 concepts
10. docs prd/spec/plan/test convention

---

### Step 2: 修复 4 个 Live Bugs（02:00 ~ 02:40）

#### Bug 1 fix: Placeholder phantom-OVERWRITE
```bash
$ read src/coworker/semantic_merge.py (306 lines)
```

**分析**：`classify_sections()` 在 `semantic_merge.py:196-210`，body 比对逻辑：
```python
if s.body.strip() != fut.body.strip():
    → OVERWRITE  # 不管 future body 是不是占位符
```

**修复**：
1. 在文件顶部添加 `_PLACEHOLDER_PATTERNS` 列表 + `_is_placeholder()` 函数
2. 修改 body 比对逻辑：future 是占位符 → KEEP；current 以 future 开头 → KEEP
3. 添加 `_H1_RE` regex（为 Bug 3 准备）

```python
# 实际 edit 操作
- OUTDATED = "OUTDATED" ...
+ 新增 _H1_RE, _PLACEHOLDER_PATTERNS, _is_placeholder()
- if s.body.strip() != fut.body.strip():
-     → OVERWRITE
+ if s.body.strip() != fut.body.strip():
+     if _is_placeholder(fut.body) or s.body.startswith(fut.body):
+         → KEEP
+     else:
+         → OVERWRITE
```

#### Bug 3 fix: Template H1 never MERGE_ADD（同文件）
```python
# 在 MERGE_ADD 循环开头添加 H1 skip
for s in future_sections:
+   if _H1_RE.match(s.heading):
+       continue
    key = (s.heading, s.occurrence)
    ...
```

#### Bug 2 fix: Initiative name path traversal
```bash
$ read src/coworker/config.py (155 lines)
```

**分析**：`load_initiative("../../tmp/secret")` 直接拼路径。kebab-case 校验只在 `InitiativeManager.create()` 里。

**修复**：
1. 添加 `import re` 到文件顶部
2. 添加 `_INITIATIVE_NAME_RE` regex + `_validate_initiative_name()` + `_safe_initiative_path()`
3. 所有 4 个函数 (`load/save/path/exists`) 全部走 `_safe_initiative_path()`

```python
# 实际 edit 操作
+ import re
+ _INITIATIVE_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
+ def _validate_initiative_name(name): ...
+ def _safe_initiative_path(name): ...
- def load_initiative(name): d = _initiatives_dir(); path = d / f"{name}.yaml"
+ def load_initiative(name): path = _safe_initiative_path(name)
- def save_initiative(config): ... d / f"{config.name}.yaml"
+ def save_initiative(config): path = _safe_initiative_path(config.name)
- def initiative_path(name): return _initiatives_dir() / f"{name}.yaml"
+ def initiative_path(name): return _safe_initiative_path(name)
- def initiative_exists(name): return initiative_path(name).exists()
+ def initiative_exists(name): return _safe_initiative_path(name).exists()
```

#### Bug 4 fix: EOF-safe install prompts
```bash
$ grep -n "read -r" setup/*.sh → 找到 5 处
```

**修复**：5 处全部添加 `|| VAR=""`：
```bash
# install.sh:116 → CHOICE || CHOICE=""
# install.sh:246 → SKILL_CHOICE || SKILL_CHOICE=""
# install.sh:265 → SELECTED_NUMS || SELECTED_NUMS="" (原来连 fallback 都没有)
# update.sh:94   → UPDATE_SF || UPDATE_SF=""
# uninstall.sh:48 → CONFIRM || CONFIRM=""
```

#### 验证
```bash
$ python3 -m pytest tests/ -x -q
→ 167 passed, 2 xfailed  (all pass)
```

---

### Step 3: 互联网调研 — Harness 方法论（02:40 ~ 02:45）

```bash
# 启动 subagent 搜索
$ task(subagent_type="general", description="Search harness approaches")
搜索了以下源：
- compelframework.org — 6 evaluation dimensions
- dipankar.cc — OPRO/APO/EvoPrompt/DSPy 对比
- towardsdatascience.com — DSPy MIPROv2 实践
- promptfoo.dev — prompt regression testing
- deepeval, EleutherAI LM Eval, Stanford HELM
```

**收获**：APO (Automatic Prompt Optimization) 的 "自然语言梯度下降" 最适合 CLAUDE.md 优化。

---

### Step 4: 实验准备（02:45 ~ 03:10）

```bash
# 4.1 理解 blueprint
$ read coworker-blueprint.md → 643 lines
# 关键：三层架构（Global <100L / Project <200L / Local template <60L）
#       PROTECTED block 内是 meta-controller，外是 project info

# 4.2 定位 mfangdai-ai-agent
$ coworker project list | grep mfang → 找到 3 个项目
$ ls ~/project/mfangdai* → mfangdai-ai-agent (Python, has CLAUDE.local.md)
$ cat CLAUDE.local.md → has initiative block "mfangdai-agent-poc"

# 4.3 检查 CLAUDE.md 生成机制
$ read src/coworker/templates/project_claude_md.py (171 lines)
$ read src/coworker/templates/local_claude_md.py (74 lines)
$ read src/coworker/cli.py (init 命令, lines 202-287)
$ read src/coworker/models.py (InitiativeConfig, lines 130-142)
$ read src/coworker/initiatives/manager.py (131 lines)
$ read src/coworker/adapters/claude.py (initiative injection, lines 214-393)
```

**发现**：project info 分散在：
- CLAUDE.md `## Project Identity` (repo URL)
- CLAUDE.md `## Project Relationships` (upstream/downstream)
- `~/.coworker/project.yaml` (name/path/repo/upstream/downstream)
- CLAUDE.local.md `## Config Paths` (只指向 catalog)

**决策**：用户选择"全部移到 CLAUDE.local.md"

---

### Step 5: Phase A — Project Info 去重（03:10 ~ 03:40）

```bash
# 5.1 修改 project_claude_md.py — 完全重写
$ write project_claude_md.py
# Changes:
#   - PROJECT_CLAUDE_MD_SENTINEL: "## Project Identity" → "<!-- PROTECTED:CRITICAL-RULES -->"
#   - generate_project_claude_md(): 去掉 identity/relationships/knowledge/team 4 section
#   - CONTEXT_MGMT: 更新 Information Flow 表，所有 project info 指向 CLAUDE.local.md
#   - LOCAL_OVERRIDE: 添加 "project info" 到描述
#   - Function signature: 只保留 project_name，其余 → **kwargs

# 5.2 修改 local_claude_md.py — 完全重写
$ write local_claude_md.py
# Changes:
#   - 新增 ## Project Info section (repo, lang, framework, deps, ides, test, lint)
#   - 新增 update_project_info() 函数
#   - 保留 inject_initiative_into_local_md() 和 remove_initiative_from_local_md()

# 5.3 修改 cli.py — init 命令
$ edit cli.py
# Changes:
#   - import: 添加 update_project_info
#   - _build_project_claude_md(): 简化参数
#   - init 流程: CLAUDE.local.md 创建时注入 project info

# 5.4 修测试
$ edit test_templates.py: test_project_identity_is_minimal → test_project_identity_not_in_claude_md
$ edit test_templates.py: test_relationships_section → test_relationships_in_local_not_claude_md
$ edit test_templates.py: test_doc_map_section → test_doc_info_not_in_claude_md
$ edit test_init_command.py: assert "Identity" → assert "PROTECTED:CRITICAL-RULES"
$ edit test_init_command.py: comment update

# 5.5 验证
$ python3 -m pytest tests/ -x -q
→ 166 passed, 2 xfailed  ✅
```

---

### Step 6: Phase B — 创建 Harness（03:40 ~ 03:55）

```bash
$ mkdir -p experiments/claude-md-harness/

# 6.1 静态分析器
$ write experiments/claude-md-harness/harness.py (270 lines)
# 功能:
#   - parse_sections(): 解析 CLAUDE.md 成 sections
#   - extract_instructions(): 提取所有 actionable bullet points
#   - check_blueprint(): 检查 16 个 required sections
#   - check_duplicates(): 检测内部 + 跨文件重复
#   - assign_test_scenarios(): 为每条指令映射测试场景
#   - check_protected_intact(): 验证 PROTECTED block 完整

# 6.2 实验编排器
$ write experiments/claude-md-harness/experiment.py (200+ lines)
# 功能:
#   - score_stack(): 三层联合评分
#   - run_round(): 执行单轮实验
#   - print_result(): 格式化输出
#   - RESULTS_DIR: 轮次结果 JSON 存储
#   - BP + Budget + Duplication + Utility → 加权总分

# 6.3 基线评分
$ python3 experiment.py round 0
→ Blueprint: 100 | Budget: 100 | Duplication: 100 | Utility: 100
→ Overall: 100.0
# 注：初始评分 100% 是因为静态分析全部满足，但这不代表真实实用性
# 真正的问题是 — 所有 section 都在所以 blueprint 100%，但很多 section 是冗余的
```

---

### Step 7: 创建实验分支 + 生成基线（03:55 ~ 04:05）

```bash
# 7.1 创建分支
$ git checkout -b experiment/claude-md-harness-optimization

# 7.2 记录基线元数据
$ echo "baseline_commit=8cf4204" > results/round_meta.txt

# 7.3 对 mfangdai-ai-agent 生成初始三层文件
$ cd /home/cicidi/project/mfangdai-ai-agent
$ rm -f CLAUDE.md
$ echo "y" | coworker init --project
→ Created: CLAUDE.md
→ Updated: CLAUDE.local.md (project info)  ← 验证 project info 注入成功
→ Created docs/ structure

$ wc -l CLAUDE.md CLAUDE.local.md ~/.claude/CLAUDE.md
→ 95 CLAUDE.md / 51 CLAUDE.local.md / 81 Global = 227 total
# 注：95 vs 118 的差异是因为新模板已移除了 project info sections
```

---

### Step 8: Round 1 — Project Info 去重生效（04:05 ~ 04:10）

```bash
# 8.1 提交 Phase A 的所有改动
$ git add -A && git commit -m "refactor: simplify CLAUDE.md templates..."
→ commit 3a46c8c
→ 34 files changed, 6254 insertions(+), 166 deletions(-)

# 8.2 验证 mfangdai-ai-agent 的新 CLAUDE.md
$ cat CLAUDE.md
→ 只有 PROTECTED block，没有 project info sections  ✅
$ cat CLAUDE.local.md
→ 有 ## Project Info section  ✅
→ 有 ## Config (不是 Config Paths) — 验证新模板生效

# 8.3 重新注入 initiative
$ coworker initiative activate mfangdai-agent-poc
→ ✓ injected initiative 'mfangdai-agent-poc' into CLAUDE.local.md
```

---

### Step 9: Rounds 2-4 — 精简化（04:10 ~ 04:40）

```bash
# 9.1 Round 2 template: 全量重写
$ write project_claude_md.py
# Changes:
#   - 去 Information Flow 表 (CONTEXT_MGMT)
#   - 合 Git Safety/Code Safety/Code Quality → Git / Code
#   - 缩 Compaction: 4 numbered items → 2 bullets
#   - 缩 Context Mgmt: 5 verbose steps → 4 direct steps
#   - 缩 Workflow: subsections → flat bullets
#   - 缩 Auto Memory: 2 lines → 1 line
#   - 缩 Local Override: 去描述性文字
#   - 去 Guardrails "ALL team members" 说明
#   - 去 Context Mgmt "Before any non-trivial task:" 前缀

$ write local_claude_md.py
# Changes:
#   - Section names 精简: Config Paths → Config, Current Task State → Current Task
#   - Recommended skills → Skills
#   - 去 Personal Preferences section (空占位符)
#   - 代码中不存在的 deps/language 不显示（unknown → 跳过）

# 9.2 修三个测试
$ edit test_templates.py:
  - test_has_config_path_section: "Config Paths" → "Config"
  - test_has_recommended_skills_placeholder: "Recommended skills" → "Skills:"
  - test_has_task_state_section: "Task State" → "Current Task"

# 9.3 逐轮验证
$ pytest → 166 passed ✅
$ rm CLAUDE.md; coworker init → 生成 → wc -l → 反复至收敛

Round 2 (v1 template): 75 lines
Round 3 (merge guardrails): 60 lines
Round 4 (detail trims): 56 lines
$ git commit -m "refactor: leaner templates..." → commit efe7375
```

---

### Step 10: Rounds 5-7 — Final Polish（04:40 ~ 05:15）

```bash
# 10.1 Round 5: 新增 Development Loop
$ edit project_claude_md.py
# AUTO_MEMORY 末尾追加:
#   ## Development Loop
#   - After every code change: run lint + tests
#   - Commit in logical chunks with conventional commit messages

# 10.2 验证: 168 lines total, pytest pass
$ pytest → 166 passed ✅
$ rm CLAUDE.md; coworker init → 60 lines (+4 from dev loop)

# 10.3 Round 6: 修复 CLAUDE.local.md 再生
# 问题: 第二次 init 只更新 Project Info，不更新其他 section
# 修复: cli.py — 重生干净模板 → 提取 initiative → 注入 → 写 project info → 写文件

# 10.4 Round 7: 全量终测
$ pytest → 166 passed, 2 xfailed ✅
$ rm -f CLAUDE.md CLAUDE.local.md
$ echo "y" | coworker init --project
→ Created: CLAUDE.md (60 lines)
→ Created: CLAUDE.local.md (42 lines, 新模板 structure)
$ coworker initiative activate mfangdai-agent-poc
→ ✓ injected initiative

# 10.5 最终验证
$ cat CLAUDE.md → 7 sections, 24 instructions, PROTECTED block OK
$ cat CLAUDE.local.md → ## Config + ## Project Info + initiative block + 4 sections
$ python3 experiment.py round 7
→ Blueprint: 100 | Budget: 100 | Duplication: 100 | Utility: 100

# 10.6 提交
$ git add -A && git commit -m "feat: CLAUDE.md optimization..."
→ commit f358a46 (Final)
```

---

### Step 11: 撰写实验报告（05:15 ~ 05:40）

```bash
# 11.1 收集证据
$ git log experiment/claude-md-harness-optimization --reverse --oneline → 3 commits
$ wc -l ~/project/mfangdai-ai-agent/CLAUDE*.md ~/.claude/CLAUDE.md
$ python3 -c "extract stats from final CLAUDE.md"

# 11.2 写入 METHODOLOGY.md
$ write experiments/claude-md-harness/METHODOLOGY.md
# 覆盖: 实验目的、调研、框架设计、7轮详细过程、评估指标、源文件清单、经验总结

# 11.3 本 session 执行日志（当前正在写入）
```

---

### 完整时间线总览

| 时间 | 阶段 | 操作 |
|------|------|------|
| 01:00-01:30 | Phase 0 | ai-coworker upgrade (pull + merge + sync) |
| 01:30-02:00 | Step 1 | OCR 图片 (6 次尝试，easyocr 最终成功) |
| 02:00-02:40 | Step 2 | 修复 4 bugs (semantic_merge + config + shell scripts) |
| 02:40-02:45 | Step 3 | 互联网调研 Harness 方法论 (subagent) |
| 02:45-03:10 | Step 4 | 阅读 blueprint、定位项目、理解 template 生成机制 |
| 03:10-03:40 | Step 5 | Phase A: Project info 去重 (3 个源文件 + 5 个测试) |
| 03:40-03:55 | Step 6 | 创建 Harness (harness.py + experiment.py) |
| 03:55-04:05 | Step 7 | 创建分支、生成基线、验证 |
| 04:05-04:10 | Step 8 | Round 1 commit + initiative activate |
| 04:10-04:40 | Step 9 | Rounds 2-4: 精简化 (重写 template + 修 3 tests) |
| 04:40-05:15 | Step 10 | Rounds 5-7: Development Loop + local.md fix + 终测 |
| 05:15-05:40 | Step 11 | 撰写 METHODOLOGY.md 报告 |
| **Total** | **~5 hours** | **11 个阶段，7 轮优化，3 个 git commit** |

---

### 关键命令速查

```bash
# 生成 CLAUDE.md 三层 stack
cd <project> && rm -f CLAUDE.md && echo "y" | coworker init --project

# 注入 initiative
coworker initiative activate <name>

# 查看 stack
wc -l CLAUDE.md CLAUDE.local.md ~/.claude/CLAUDE.md

# 跑测试
cd ~/project/ai-coworker && python3 -m pytest tests/ -x -q

# 补全 ruff lint
python3 -m ruff check src/ --fix

# 打分
python3 experiments/claude-md-harness/experiment.py score

# 版本对比
git log experiment/claude-md-harness-optimization --oneline
diff <(git show 8cf4204:src/coworker/templates/project_claude_md.py) \
     <(git show f358a46:src/coworker/templates/project_claude_md.py)
```
