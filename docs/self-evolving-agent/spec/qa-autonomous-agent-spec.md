# QA Autonomous Agent — Spec ⚠️ DEFERRED

> **Status: DEFERRED (2026-07-25)**
>
> This document has been renamed conceptually to **auto-worker** — a self-discovering, self-fixing agent. It will be rewritten after the memory platform (PRD v4) is built.
>
> This document is preserved as-is for reference. Do NOT implement from it.

> Initiative: self-evolving-agent | Type: spec | Status: **DEFERRED**
>
> Derived from: [PRD](../prd/self-evolving-agent-prd-zh.md) | [Design](../design/qa-autonomous-agent-design.md)

---

## §1 CLI Interface & Entry Points

### 1.1 Slash Command

```
/qa-run <task-name> [options]

Options:
  --max-hours <n>        最大运行时间，默认 12，范围 1-72
  --project <name>       项目名，默认从当前目录自动检测（匹配 project.yaml）
  --dry-run              只出报告，不执行修复
  --from-state <path>    从指定 state 文件恢复（默认读取最新 state）
```

**Behavior:**
- 不带 `task-name` → 交互式问 task-name 和 max-hours
- 带 `task-name` → 跳过交互，默认 max-hours=12
- 当前目录匹配不到 project.yaml → `QA_E001` 退出
- `--dry-run` → 执行到 gap report 即停止，不进入 fix/continuous-discovery

### 1.2 Git Push Hook

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash(git push*)",
        "command": "coworker qa hook-push --session-id ${SESSION_ID}"
      }
    ]
  }
}
```

**Behavior:**
1. Incremental index: new git-commit + git-pr entries only
2. Mutable source hash check: detect PRD/CLAUDE.md changes
3. Layer 1 static gap check only (no test execution, no fix)
4. Append results to current state file
5. Execution: sync if <60s, async if >60s (don't block push)

---

## §2 Data Schemas

### 2.1 SQLite knowledge_index DDL

```sql
CREATE TABLE knowledge_index (
    id              TEXT PRIMARY KEY,  -- SHA256(project||topic||problem||source)
    project         TEXT NOT NULL,
    topic           TEXT NOT NULL,
    problem         TEXT NOT NULL,
    type            TEXT NOT NULL CHECK(type IN ('decision','knowledge','requirement','bug-fix')),
    source          TEXT NOT NULL,
    source_type     TEXT NOT NULL CHECK(source_type IN (
                        'session','git-commit','git-pr','issue',
                        'prd','claude-md','spec','state')),
    source_hash     TEXT NOT NULL,
    timestamp       TEXT NOT NULL,     -- ISO 8601
    memory_ref      TEXT NOT NULL,     -- "project/<name>/MEMORY.md#L{line}" or "session:{id}"
    superseded_by   TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_exact ON knowledge_index(project, topic, problem);
CREATE INDEX idx_time  ON knowledge_index(project, topic, problem, timestamp);
CREATE INDEX idx_hash  ON knowledge_index(source_type, source_hash);
```

### 2.2 MEMORY.md Entry Format (QA-skill extension; PRD §3.2 specifies only the § delimiter, not this shape)

```markdown
§ {2-3 sentence summary}
  → reasoning: {why this decision was made}
  → decision: {what was decided}
  → evidence: {source_ref, date}
```

### 2.3 Ingestion I/O

```
collect(source_type, source_path) → {raw_text, timestamp, project}
    │
    ▼
standardize(raw_text, existing_topics) → {
  topic: str,           // reused from existing if match, else new normalized slug
  problem: str,         // normalized slug, 30-80 chars, lowercase-hyphenated
  type: str,            // decision|knowledge|requirement|bug-fix
  summary: str,         // 2-3 sentences
  key_points: [str],    // 3-5 key claims
  evidence: str         // verbatim quote snippet
}
    │
    ├──→ INSERT INTO knowledge_index (metadata only)
    ├──→ UPSERT MEMORY.md § entry (full content)
    └──→ embed(standardize_output) → INSERT INTO knowledge_vec (384-dim vector via fastembed)
```

### 2.4 Query Output

```json
{
  "exact_matches": [
    {
      "id": "sha256(...)",
      "summary": "修复 token 过期问题...",
      "key_points": ["sessionStorage", "5min pre-expiry"],
      "timestamp": "2026-07-20T14:30:00Z",
      "memory_ref": "project/mfangdai/MEMORY.md#L89",
      "source": "git:abc123"
    }
  ],
  "related": [],
  "conflicts": [],
  "relevance": "exact"
}
```



### 2.5 Semantic Search (sqlite-vec)

**Backend:** sqlite-vec + fastembed on `analytics.db` (Path 1b, decided 2026-07-24). Replaces the now-removed FTS5.

```sql
-- vec0 virtual table for KNN semantic search
-- coexists with knowledge_index (B-tree, for exact WHERE queries)
CREATE VIRTUAL TABLE knowledge_vec USING vec0(
    embedding float[384]      -- BAAI/bge-small-en-v1.5 (fastembed/ONNX)
);
```

**Embedding pipeline (post-ingestion):**
```
standardize_output → fastembed (BAAI/bge-small-en-v1.5, 384-dim, ONNX)
    │
    ▼
INSERT OR REPLACE INTO knowledge_vec(rowid, embedding)
VALUES (knowledge_index_row_id, normalized_384d_vector)
```

**Dual retrieval path:**
```
PRD item → topic/problem keywords
    │
    ├── SQLite exact (WHERE project=? AND topic=? AND problem=?)
    │       → exact match → read MEMORY.md → done
    │
    └── no exact match?
            └── embed(query) → vec0 KNN (L2)
                    → candidates → LLM semantic filter → done
```

**Dependencies:**
- `sqlite-vec` (Python package, in-process SQLite extension — no server)
- `fastembed` (ONNX runtime, `BAAI/bge-small-en-v1.5`, 384-dim — first run downloads ~50MB)
- `onnxruntime` (already in environment)

**Spike validated:** 2026-07-24 — 6/6 semantically matched queries returned correct #1 result on 6 knowledge entries in `analytics.db`.

---

## §3 Gap Detection

### 3.1 Test Plan Schema

```json
{
  "module": "auth",
  "version": 1,
  "scenarios": [
    {
      "id": "auth-001",
      "name": "正常登录",
      "priority": "P0",
      "given": "有效用户名和密码",
      "when": "POST /login",
      "then": "200 + token",
      "spec_ref": "Spec §3.3",
      "status": "pending"
    }
  ],
  "acceptance_criteria": {
    "p0_threshold": "all pass",
    "p1_threshold": "80% pass"
  }
}
```

**Rules:**
- Test plan derived from PRD + Spec (not from state)
- Written to `docs/<initiative>/test-plan/<module>-test-plan.md`
- Version must match PRD version; mismatch → re-discuss
- P0 not all pass → don't enter fix phase

### 3.2 Research → Discussion → Test Plan Flow

```
PRD + Spec
    │
    ▼
Research Phase
  ├── Analyze existing tests: coverage scope, patterns, gaps
  ├── Map PRD items to test coverage
  ├── Search external references: official docs, similar OSS projects
  └── Output: docs/<initiative>/research/<module>-test-research.md
    │
    ▼
Discussion Phase
  ├── Present findings: "现有 15 个测试, 3 个 PRD item 未覆盖, 建议新增..."
  ├── User confirms P0/P1 prioritization + acceptance criteria
  └── Output: docs/<initiative>/test-plan/<module>-test-plan.md
    │
    ▼
State: record test plan path + progress only (not test plan content)
```

### 3.3 Verification Output

```json
{
  "run_id": "qa-run-2026-07-24-001",
  "prd_item": {
    "id": "req-auth-03",
    "description": "token auto-refresh on expiry"
  },
  "verification": {
    "layer_1_static": {
      "verdict": "found",
      "evidence": [
        {"type": "file", "ref": "src/auth/tokenRefresh.ts:42-68"}
      ],
      "confidence": "high"
    },
    "layer_2_test": {
      "verdict": "tested",
      "evidence": [
        {"file": "tests/auth/token.test.ts", "line": 89, "result": "pass"}
      ],
      "coverage": "2/2 pass"
    },
    "layer_3_dynamic": null
  },
  "gap": false,
  "confidence": "high",
  "reasoning": "实现存在 + 测试覆盖 + 全部通过"
}
```

**Verdict Enums:**

| Field | Values |
|-------|--------|
| `layer_1_static.verdict` | `found` / `not_found` / `partial` |
| `layer_2_test.verdict` | `tested` / `not_tested` / `test_failed` |
| `layer_3_dynamic.verdict` | `verified` / `not_working` / `skipped` |

**Confidence Rules:**
- `high`: 3 layers verified
- `medium`: 2 layers, or 1 layer with `partial`
- `low`: only static check, no test coverage

### 3.4 Gap Report

```json
{
  "report_id": "gap-report-2026-07-24-001",
  "project": "mfangdai",
  "generated_by": "Claude/GLM",
  "summary": "3 gap found: 1 not implemented, 2 missing tests",
  "gaps": [
    {
      "id": "G-1",
      "prd_item": "token auto-refresh",
      "severity": "P0",
      "verdict": "not_implemented",
      "evidence": "no code matching 'refresh' pattern in src/auth/",
      "suggested_fix": "实现 tokenRefresh.ts: sessionStorage + 5min pre-expiry timer"
    }
  ],
  "stats": {
    "total_prd_items": 12,
    "verified": 9,
    "gaps": 3,
    "p0_gaps": 1
  }
}
```

---

## §4 Continuous Discovery & State

### 4.1 Discovery I/O

```json
// Input (all 7 dimensions share this)
{
  "project": "mfangdai",
  "dimension": "external-reference",
  "context": {
    "prd_items": ["..."],
    "tech_stack": {"framework": "Next.js 14", "lang": "TypeScript"},
    "existing_tests": ["tests/auth/", "tests/api/"]
  }
}

// Output (unified schema)
{
  "findings": [
    {
      "id": "O-2026-07-24-001",
      "dimension": "external-reference",
      "severity": "medium",
      "title": "migrate API routes to Server Actions",
      "current_state": "4 mutation endpoints use API routes",
      "reference": {
        "url": "https://nextjs.org/docs/...",
        "type": "official_doc",
        "relevant_quote": "Server Actions are the recommended way..."
      },
      "suggested_change": "migrate POST/PUT/DELETE routes to Server Actions",
      "evidence": "src/app/api/users/route.ts, src/app/api/orders/route.ts",
      "auto_fixable": true
    }
  ],
  "stats": {
    "dimensions_scanned": 7,
    "total_findings": 5,
    "by_severity": {"low": 1, "medium": 3, "high": 1, "critical": 0}
  }
}
```

### 4.2 Severity Classification

| Severity | Condition | Action |
|----------|-----------|--------|
| `critical` | Security vulnerability, CVE in dependency | Fix immediately, pause other discovery |
| `high` | Perf regression >20%, missing error handling on critical path | Fix this run |
| `medium` | Code pattern inconsistency, missing test coverage | Queue for fix |
| `low` | Minor dependency bump, code style | Fix if time permits |

### 4.3 Mini Test Plan

```json
{
  "optimization_id": "O-2026-07-24-001",
  "test_plan": [
    {
      "step": "before",
      "action": "run existing API route tests",
      "expected": "all pass",
      "result": null
    },
    {
      "step": "after",
      "action": "run same tests against migrated Server Actions",
      "expected": "all pass, response time ≤ baseline + 50ms",
      "result": null
    }
  ],
  "rollback": "git revert <commit> + re-run before tests"
}
```

**Rules:**
- `before` and `after` must be paired — no baseline, no fix
- `rollback` must be explicit — no unrecoverable changes
- `auto_fixable: false` → add `manual_check: true`

### 4.4 State Write (extends PRD §4)

```json
{
  "initiative": "self-evolving-agent",
  "task": "qa-run-mfangdai-2026-07-24",
  "phase": "discovery",

  "what_was_done": [
    {"type": "gap_found", "id": "G-1", "detail": "token refresh not implemented"},
    {"type": "fix_applied", "id": "G-1", "commit": "abc123"},
    {"type": "optimization_found", "id": "O-1", "dimension": "external-ref"}
  ],

  "lessons": [
    {"type": "pitfall", "detail": "grep cannot find Server Actions — need AST search"},
    {"type": "pattern", "detail": "project has 3 different error handler styles"}
  ],

  "progress": {
    "test_plan": {"path": "docs/self-evolving-agent/test-plan/auth-module-test-plan.md", "total": 10, "pass": 8, "pending": 2},
    "gaps": {"total": 3, "fixed": 1, "remaining": 2},
    "optimizations": {"total": 5, "fixed": 1, "remaining": 4},
    "time_elapsed_seconds": 23400,
    "time_remaining_seconds": 19800
  },

  "next": "continue discovery — external-reference done, starting code-pattern-consistency"
}
```

### 4.5 Time Budget

```
Each loop iteration start:

  if elapsed_seconds > max_duration_seconds:
      → save phase: "stopped_timeout" → state
      → write session post-summary (PRD §5.4)
      → exit code 2

  if remaining < 600 AND phase != "repair":
      → skip discovery
      → enter "wrap_up": fix queued P0 gaps only
      → exit code 0 when P0 gaps resolved
```

---

## §5 Hook Config & Error Handling

### 5.1 Git Push Hook Config

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash(git push*)",
        "command": "coworker qa hook-push --session-id ${SESSION_ID}"
      }
    ]
  }
}
```

### 5.2 Error Codes

| Code | Fault | Behavior | Recovery |
|------|-------|----------|----------|
| `QA_E001` | Project not in catalog | Exit, suggest `--project` or `project-add` | User fix |
| `QA_E002` | PRD not found | Exit, prompt for PRD path | User provides |
| `QA_E003` | MEMORY.md corrupted | Degrade: vec0 KNN only, skip SQLite exact-match | Next Curator run rebuilds |
| `QA_E004` | vec0 embedding index corrupted | Rebuild from knowledge table source + fastembed re-embed | Auto |
| `QA_E005` | LLM timeout (DeepSeek) | Switch to backup provider (Gemini Flash / Claude Haiku), PRD §6.7 | Auto |
| `QA_E006` | LLM timeout (Claude/GLM) | Degrade: use DeepSeek Pro for report, mark `degraded_report: true` | Auto degrade |
| `QA_E007` | Test infra error (not test failure) | Skip Layer 2/3, mark `confidence: low`, continue | Retry next run |
| `QA_E008` | Time budget exhausted mid-fix | Save fix progress to state, do NOT commit half-done work | Resume from state |
| `QA_E009` | Disk full on state write | Write to `/tmp`, log to audit.log | Manual cleanup then retry |
| `QA_E010` | Circuit breaker tripped (PRD §5.6.2) | Pause all auto-fix, keep pending queue | User review + `coworker skill resume` |
| `QA_E011` | Embedding model unavailable (fastembed) | Degrade: SQLite exact-match only, mark `confidence: low` | Next run reattempts |

**General principles:**
- Degrade, don't crash
- Auto-recover where possible, log to audit.log
- Unrecoverable → write state + notify user
- Never commit incomplete work

---

## §6 Skill Contracts

### 6.1 `qa-orchestrator`

```
Input:
  task_name: str
  max_hours: float          // default 12, range 1-72
  project: str | None       // auto-detect
  dry_run: bool             // default false
  from_state: str | None

Output (streamed events):
  {"event": "phase_start",  "phase": "research"}
  {"event": "phase_done",   "phase": "research", "result": {...}}
  {"event": "gap_found",    "gap": {...}}
  {"event": "fix_applied",  "gap_id": "G-1", "commit": "abc123"}
  {"event": "optimization", "finding": {...}}
  {"event": "timeout",      "reason": "max_hours reached"}
  {"event": "done",         "summary": {...}}

Exit codes:
  0 — completed (may have remaining gaps)
  1 — error
  2 — timeout (state saved, resumable)
```

### 6.2 `qa-knowledge-extract`

```
Input:
  sources: [{source_type, source_path, project}]

Output:
  {
    "ingested": 12,
    "skipped": 3,
    "updated": 2,
    "errors": []
  }

Model: DeepSeek Pro (two-step: classify topic → extract fields)
Writes: SQLite knowledge_index (metadata) + MEMORY.md (full content) + knowledge_vec (384-dim embedding via fastembed)
```

### 6.3 `qa-knowledge-search`

```
Input:
  project: str
  topic: str
  problem: str | None
  prd_item_description: str

Output:
  {
    "exact_matches": [{id, summary, key_points, timestamp, memory_ref, source}],
    "related": [...],
    "conflicts": [{newer, older, reason}],
    "relevance": "exact" | "related" | "none"
  }

Model: no model (SQLite exact + vec0 KNN) + DeepSeek Pro (semantic filter: one question per candidate)
```

### 6.4 `qa-test-plan`

```
Input:
  prd_path: str
  spec_path: str
  existing_test_dirs: [str]

Output:
  Phase 1 → docs/<initiative>/research/<module>-test-research.md
  Phase 2 → docs/<initiative>/test-plan/<module>-test-plan.md

Model: Claude/GLM (user discussion) + DeepSeek Pro (scenario generation)
```

### 6.5 `qa-gap-check`

```
Input:
  prd_items: [{id, description}]
  project: str

Output:
  {
    "run_id": str,
    "items": [{prd_item, verification: {layer_1, layer_2, layer_3}, gap: bool, confidence, reasoning}],
    "stats": {total, verified, gaps, p0_gaps}
  }

Model: DeepSeek Pro (per-item yes/no) + Claude/GLM (final report)
```

### 6.6 `qa-fix`

```
Input:
  gaps_or_optimizations: [{id, title, suggested_change, evidence, auto_fixable}]

Output:
  {
    "fixes": [{id, status, commit?, mini_test_plan_result?, rollback?}],
    "stats": {attempted, fixed, skipped, failed}
  }

Constraints:
  - auto_fixable=false → skip
  - mini test plan must exist before fix
  - one commit per item
  - rollback instructions must be explicit

Model: DeepSeek Flash
```

### 6.7 `qa-continuous-discovery`

```
Input:
  project: str
  tech_stack: {framework, lang, package_manager, test_framework}
  dimensions: [str]    // subset of 7, default: all
  prd_items: [{id, description}]

Output:
  {
    "findings": [{id, dimension, severity, title, current_state, reference, suggested_change, evidence, auto_fixable}],
    "stats": {dimensions_scanned, total_findings, by_severity}
  }

Dimensions (parallelizable):
  external-reference    → WebSearch + diff
  code-pattern          → grep + AST
  test-coverage         → coverage tool + PRD boundary analysis
  dependency-debt       → package manager outdated/audit
  performance           → Lighthouse / bundler / query profiler
  security              → secret scan / auth check grep
  error-handling        → static analysis

Model: DeepSeek Pro (per-dimension) + Claude/GLM (external-reference only)
```

---

## §7 Spec Meta

### 7.1 Document Relationships

```
Global CLAUDE.md §0.5 (Autonomous Job Guardrail)
  "自主任务必须先 Research + Advocate"
       │
       ▼
Design §1-7
  "两层知识存储、三层验证、七维发现、模型路由"
       │
       ▼
Spec §1-7 (this document)
  "CLI 签名、JSON schema、错误码、skill I/O 契约"
```

### 7.2 Section Index

| § | Content |
|---|---------|
| §1 | CLI Interface & Entry Points |
| §2 | Data Schemas (SQLite DDL, MEMORY.md, ingestion, query) |
| §3 | Gap Detection (test plan, research flow, verification, report) |
| §4 | Continuous Discovery & State (I/O, severity, mini test plan, state write, time budget) |
| §5 | Hook Config & Error Handling (push hook, error codes) |
| §6 | Skill Contracts (7 skills with I/O + model routing) |
| §7 | Spec Meta (this section) |

---

## Change Log

| Date | Change |
|------|--------|
| 2026-07-24 | Initial spec — §1-§7 drafted from Design + PRD |
| 2026-07-24 | Path 1b / sqlite-vec (§2.5): replaced FTS5 with sqlite-vec + fastembed on analytics.db. Added embedding step to ingestion (§2.3). Updated error codes (QA_E003 vec0 KNN, QA_E004 vec0 corrupt, QA_E011 embed model unavailable). Updated §6.2-§6.3 skill contracts. Spike validated 6/6 semantic queries. |
