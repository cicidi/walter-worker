# QA Autonomous Agent Implementation Plan ⚠️ DEFERRED

> **Status: DEFERRED (2026-07-25)**
>
> This document has been renamed conceptually to **auto-worker** — a self-discovering, self-fixing agent. It will be rewritten after the memory platform (PRD v4) is built.
>
> This document is preserved as-is for reference. Do NOT implement from it.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the QA autonomous agent pipeline — 7 skills that autonomously find gaps between PRD and reality, fix them, and continuously discover optimizations. Built on MEMORY.md (content) + sqlite-vec + fastembed (semantic KNN search, 384-dim, in-process).

**Architecture:** New `src/coworker/qa/` module with 7 files. sqlite-vec (in-process SQLite extension) + fastembed (ONNX, `BAAI/bge-small-en-v1.5`) provide semantic KNN search — replacing FTS5 from v1. Lightweight SQLite `knowledge_index` retained for exact structured queries (`WHERE project=? AND topic=? AND problem=?`). Task tracking and session continuity via state files (`docs/<initiative>/state/`). Discovery uses grep/coverage/deps/perf/security scans — no third-party MCP required.

**Tech Stack:** Python 3.12+, Click, SQLite3 (stdlib), pytest, sqlite-vec (Python package, pip install, in-process), fastembed (ONNX, pip install, zero GPU), DeepSeek API, Claude/GLM API

## Global Constraints

- Follow existing project patterns: `src/coworker/analytics/db.py` for DB, `src/coworker/cli.py` for Click commands
- DB path: `~/.coworker/qa/knowledge.db` (exact-match queries only — semantic search is vec0)
- All skills go to `~/.coworker/skills/qa-*/SKILL.md`
- Never commit half-done work; atomic commits per task
- Do NOT build a parallel memory system — MEMORY.md stores full content, `knowledge_vec` (vec0) stores 384-dim embeddings for KNN search, same `analytics.db`
- Research + Advocate gate (Global CLAUDE.md §0.5) applies before any auto action
- Run tests after every code change before marking task complete

---

## Architecture: What sqlite-vec replaces

```
v1 (纯自建)                              v2 (sqlite-vec + fastembed)
──────────                              ──────────────────────────────

knowledge_index.py • FTS5 全文搜索      → knowledge_vec (vec0 KNN, 384-dim)
                                         knowledge_index.py 精简为只做精确 SQL 查询

state 文件 • Gap 列表 (手动 markdown)    → state 文件 (保留，pending/fixing/done)
state 文件 • 进度快照                     → state 文件 (保留，phase headers)

无 (关键词搜索)                           → fastembed (ONNX, BAAI/bge-small-en-v1.5)

保留:                                   保留:
  knowledge_index.py (精确查询)           MEMORY.md (完整内容，PRD 核心)
  三层验证逻辑 (static/test/dynamic)      7 维度 discovery 扫描
  test plan 生成 + discussion            orchestrator 循环
  7 个 skill 的业务逻辑                   LLM 模型路由
```

---

## File Structure

```
src/coworker/qa/
├── __init__.py              # Module init, version
├── errors.py                # QA error codes (QA_E001 - QA_E010)
├── knowledge_index.py       # SQLite exact-match queries only (no FTS5)
├── knowledge_extract.py     # Ingestion: source → standardizer → SQLite + MEMORY.md + vec0
├── knowledge_search.py      # Layer 1: SQLite exact → Layer 2: vec0 semantic
├── test_plan.py             # Research → discussion → test plan generation
├── gap_check.py             # Three-layer verification (static → test → dynamic)
├── fix.py                   # Fix with state tracking + mini test plan
├── discovery.py             # 7-dimension discovery
├── orchestrator.py          # Main loop: state-driven gap tracking, state-driven continuity
└── cli.py                   # Click commands: `qa run`, `qa hook-push`
```

Skills (7 new, in `~/.coworker/skills/`):
```
qa-orchestrator/SKILL.md
qa-knowledge-extract/SKILL.md
qa-knowledge-search/SKILL.md
qa-test-plan/SKILL.md
qa-gap-check/SKILL.md
qa-fix/SKILL.md
qa-continuous-discovery/SKILL.md
```

Modified files:
- `src/coworker/cli.py` — add `qa` command group
- `~/.claude/settings.json` — add git push hook

---

### Task 0: sqlite-vec + fastembed Setup

**Files:**
- Create: `docs/self-evolving-agent/how-to/sqlite-vec-setup-how-to.md`

- [ ] **Step 1: Install sqlite-vec**

```bash
pip install sqlite-vec
python3 -c "import sqlite_vec; print('✅ sqlite-vec loaded')"
```

- [ ] **Step 2: Install fastembed**

```bash
pip install fastembed
python3 -c "from fastembed import TextEmbedding; m = TextEmbedding(); v = list(m.embed(['test']))[0]; print(f'✅ fastembed, dim={v.shape[0]}')"
```

- [ ] **Step 3: Create knowledge_vec table on analytics.db**

```python
import sqlite3, sqlite_vec
db = sqlite3.connect("~/.coworker/analytics/analytics.db")
db.enable_load_extension(True)
sqlite_vec.load(db)
db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_vec USING vec0(embedding float[384])")
db.commit()
print("✅ knowledge_vec created")
```

- [ ] **Step 4: Embed + store first entry, verify self-match**

```python
from fastembed import TextEmbedding
import numpy as np

embed = TextEmbedding()
text = "test knowledge entry"
vec = list(embed.embed([text]))[0]
vec = vec / np.linalg.norm(vec)

db.execute("INSERT OR REPLACE INTO knowledge_vec(rowid, embedding) VALUES (?, ?)",
           [1, vec.astype(np.float32).tobytes()])
db.commit()

result = db.execute("""
    SELECT rowid, vec_distance_l2(embedding, ?) as dist
    FROM knowledge_vec ORDER BY dist LIMIT 1
""", [vec.astype(np.float32).tobytes()]).fetchone()
print(f"✅ Self-match: rowid={result[0]}, dist={result[1]:.6f} (expect ~0.0)")
```

- [ ] **Step 5: Commit**

```bash
git add docs/self-evolving-agent/how-to/sqlite-vec-setup-how-to.md
git commit -m "chore(qa): add sqlite-vec + fastembed setup guide"
```

> ✅ Spike validated 2026-07-24: 6/6 semantic queries correctly retrieved on real knowledge entries in analytics.db.

---

### Task 1: QA Error Codes

**Files:**
- Create: `src/coworker/qa/__init__.py`
- Create: `src/coworker/qa/errors.py`
- Create: `tests/qa/test_errors.py`

**Interfaces:**
- Produces: `QAError(Exception)` base class, 10 error subclasses with codes, `error_registry` dict

新增错误：

- [ ] **Step 1: Write failing tests**

```python
# tests/qa/test_errors.py
import pytest
from coworker.qa.errors import (
    QAError, QA_E001_ProjectNotFound, QA_E002_PRDNotFound,
    QA_E003_MemoryCorrupted, QA_E005_LLMTimeout_DeepSeek,
    QA_E006_LLMTimeout_Claude, QA_E007_TestInfraError, QA_E008_TimeBudgetExhausted,
    QA_E009_DiskFull, QA_E010_CircuitBreakerTripped,
    QA_E011_EmbeddingUnavailable, QA_E012_StateConflict,
    error_registry,
)

class TestQAErrors:
    def test_each_error_has_unique_code(self):
        codes = [cls.code for cls in error_registry.values()]
        assert len(codes) == len(set(codes))
        assert len(codes) == 12  # E001-E010 + E011-E012

    def test_qa_e011_embedding_unavailable(self):
        err = QA_E011_EmbeddingUnavailable()
        assert "sqlite-vec" in str(err)
        assert err.code == "QA_E011"

    def test_qa_e012_state_assign_conflict(self):
        err = QA_E012_StateConflict(quest_id="quest-gap-03", claimed_by="agent-b")
        assert "quest-gap-03" in str(err)
        assert "agent-b" in str(err)
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/qa/test_errors.py -v
```
Expected: all fail (module not found)

- [ ] **Step 3: Create `__init__.py` + `errors.py`**

```python
# src/coworker/qa/__init__.py
"""QA autonomous agent module. Part of self-evolving-agent initiative."""
__version__ = "0.2.0"
```

```python
# src/coworker/qa/errors.py

class QAError(Exception):
    """Base error for QA module."""
    code: str = "QA_E000"
    def __init__(self, message: str | None = None, **ctx):
        self.ctx = ctx
        super().__init__(message or self.default_message())
    def default_message(self) -> str:
        return f"{self.code}: An unknown QA error occurred."


class QA_E001_ProjectNotFound(QAError):
    code = "QA_E001"
    def default_message(self) -> str:
        return f"QA_E001: Project '{self.ctx.get('project','unknown')}' not in catalog. Use --project or 'project-add'."

class QA_E002_PRDNotFound(QAError):
    code = "QA_E002"
    def default_message(self) -> str:
        return f"QA_E002: No PRD found at '{self.ctx.get('path','docs/')}'."

class QA_E003_MemoryCorrupted(QAError):
    code = "QA_E003"
    def default_message(self) -> str:
        return "QA_E003: MEMORY.md corrupted. Degrading to vec0-only search."

class QA_E005_LLMTimeout_DeepSeek(QAError):
    code = "QA_E005"
    def default_message(self) -> str:
        return "QA_E005: DeepSeek API timeout. Switching to backup provider."

class QA_E006_LLMTimeout_Claude(QAError):
    code = "QA_E006"
    def default_message(self) -> str:
        return "QA_E006: Claude/GLM API timeout. Degrading report to DeepSeek Pro (degraded_report: true)."

class QA_E007_TestInfraError(QAError):
    code = "QA_E007"
    def default_message(self) -> str:
        return "QA_E007: Test infra error. Skipping Layer 2/3, marking confidence: low."

class QA_E008_TimeBudgetExhausted(QAError):
    code = "QA_E008"
    def default_message(self) -> str:
        return "QA_E008: Time budget exhausted mid-fix. Saving to state, no half-done commits."

class QA_E009_DiskFull(QAError):
    code = "QA_E009"
    def default_message(self) -> str:
        return "QA_E009: Disk full. Writing to /tmp fallback."

class QA_E010_CircuitBreakerTripped(QAError):
    code = "QA_E010"
    def default_message(self) -> str:
        return f"QA_E010: Circuit breaker — {self.ctx.get('count','?')} skills modified in 24h. Paused."

class QA_E011_EmbeddingUnavailable(QAError):
    code = "QA_E011"
    def default_message(self) -> str:
        return "QA_E011: Embedding model (fastembed) unavailable. Gap tracking degraded to state file fallback."

class QA_E012_StateConflict(QAError):
    code = "QA_E012"
    def default_message(self) -> str:
        return (f"QA_E012: Quest '{self.ctx.get('quest_id','?')}' "
                f"already claimed by {self.ctx.get('claimed_by','another agent')}.")


error_registry: dict[int, type[QAError]] = {
    1: QA_E001_ProjectNotFound,  2: QA_E002_PRDNotFound,
    3: QA_E003_MemoryCorrupted,  5: QA_E005_LLMTimeout_DeepSeek,
    6: QA_E006_LLMTimeout_Claude, 7: QA_E007_TestInfraError,
    8: QA_E008_TimeBudgetExhausted, 9: QA_E009_DiskFull,
    10: QA_E010_CircuitBreakerTripped,
    11: QA_E011_EmbeddingUnavailable, 12: QA_E012_StateConflict,
}
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/qa/test_errors.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/coworker/qa/__init__.py src/coworker/qa/errors.py tests/qa/test_errors.py
git commit -m "feat(qa): add error codes QA_E001-E012 "
```

---

### Task 2: Knowledge Index — SQLite Exact-Match Only

**Files:**
- Create: `src/coworker/qa/knowledge_index.py`
- Create: `tests/qa/test_knowledge_index.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `SCHEMA: str` — CREATE TABLE SQL (simplified: no FTS5)
  - `KnowledgeIndex(db_path)` — context manager
  - `.upsert(entry) -> str` — insert/replace
  - `.query_exact(project, topic, problem) -> list[dict]` — exact WHERE match
  - `.get_by_id(id) -> dict | None`
  - `.get_stale_sources(source_types) -> list[dict]` — hash mismatch detection
  - `.mark_superseded(newer_id, older_id) -> None`

**Change from v1:** FTS5 removed — semantic search is vec0's job. This table is ONLY for `WHERE project=? AND topic=? AND problem=?` queries.

- [ ] **Step 1: Write failing tests** (same as v1 Task 2, minus FTS5 tests)

```python
# tests/qa/test_knowledge_index.py
import pytest
from pathlib import Path
from coworker.qa.knowledge_index import KnowledgeIndex

SAMPLE = {
    "project": "test-app", "topic": "auth",
    "problem": "token-expiry-on-reload", "type": "decision",
    "source": "git:abc123", "source_type": "git-commit",
    "source_hash": "sha256:abc", "timestamp": "2026-07-20T14:30:00Z",
    "memory_ref": "project/test-app/MEMORY.md#L89",
}

@pytest.fixture
def index(tmp_path):
    db = tmp_path / "test.db"
    with KnowledgeIndex(db) as idx:
        idx.initialize()
        yield idx

class TestKnowledgeIndex:
    def test_upsert_and_query_exact(self, index):
        index.upsert(SAMPLE)
        results = index.query_exact("test-app", "auth", "token-expiry-on-reload")
        assert len(results) == 1
        assert results[0]["topic"] == "auth"

    def test_idempotent_upsert(self, index):
        id1 = index.upsert(SAMPLE)
        id2 = index.upsert(SAMPLE)
        assert id1 == id2

    def test_timestamp_ordering(self, index):
        index.upsert({**SAMPLE, "timestamp": "2026-07-01", "source": "old"})
        index.upsert({**SAMPLE, "timestamp": "2026-07-20", "source": "new"})
        results = index.query_exact("test-app", "auth", "token-expiry-on-reload")
        assert results[0]["source"] == "new"

    def test_topic_only_query(self, index):
        index.upsert(SAMPLE)
        index.upsert({**SAMPLE, "problem": "another-issue", "source": "git:def"})
        results = index.query_exact("test-app", "auth", None)
        assert len(results) == 2

    def test_stale_source_detection(self, index):
        index.upsert({**SAMPLE, "source_type": "prd", "source_hash": "old-hash"})
        stale = index.get_stale_sources(["prd"])
        assert len(stale) >= 1

    def test_superseded_chain(self, index):
        id1 = index.upsert(SAMPLE)
        id2 = index.upsert({**SAMPLE, "source": "git:newer"})
        index.mark_superseded(id2, id1)
        row = index.get_by_id(id1)
        assert row["superseded_by"] == id2
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/qa/test_knowledge_index.py -v
```

- [ ] **Step 3: Create `knowledge_index.py`** (same as v1 Task 2, remove FTS5-related code, keep schema identical)

- [ ] **Step 4: Run tests — verify they pass**

- [ ] **Step 5: Commit**

```bash
git add src/coworker/qa/knowledge_index.py tests/qa/test_knowledge_index.py
git commit -m "feat(qa): add knowledge_index SQLite for exact (project,topic,problem) queries"
```

---

### Task 3: Knowledge Extraction — SQLite + MEMORY.md + vec0

**Files:**
- Create: `src/coworker/qa/knowledge_extract.py`
- Create: `tests/qa/test_knowledge_extract.py`

**Interfaces:**
- Consumes: `KnowledgeIndex` (Task 2)
- Produces:
  - `ExtractionInput`, `ExtractionOutput` dataclasses
  - `TopicRegistry.get_existing_topics(index, project) -> list[str]`
  - `Standardizer.extract(raw_text, existing_topics) -> ExtractionOutput` — two-step LLM
  - `ingest(sources, index) -> dict` — writes to 3 places:
    1. SQLite `knowledge_index` (exact-match metadata)
    2. MEMORY.md (full content for LLM + human reading)
    3. sqlite-vec `fastembed.encode` (semantic search index)

**Change from v1:** Added vec0 ingestion as third write target. This means every ingested knowledge entry is searchable via Lore's BM25+vector hybrid search.

- [ ] **Step 1: Write `knowledge_extract.py`** (same core logic as v1 Task 3, add Lore write)

```python
# In ingest():
# After SQLite upsert + MEMORY.md write, add:
try:
    _fastembed_encode(
        kind=output.type,       # decision|knowledge|requirement|bug-fix
        summary=output.summary,
        topic=output.topic,
        content=f"§ {output.summary}\n"
                f"  → key_points: {', '.join(output.key_points)}\n"
                f"  → evidence: {output.evidence}\n"
                f"  → source: {src.source_path}\n"
                f"  → timestamp: {src.timestamp}",
    )
except QA_E011_EmbeddingUnavailable:
    pass  # Degrade gracefully — SQLite + MEMORY.md still work
```

- [ ] **Step 2: Write tests** (same as v1 Task 3, mock `_fastembed_encode`)

- [ ] **Step 3: Run tests → pass → commit**

```bash
git add src/coworker/qa/knowledge_extract.py tests/qa/test_knowledge_extract.py
git commit -m "feat(qa): add knowledge extraction pipeline with vec0 integration"
```

---

### Task 4: Knowledge Search — SQLite Exact + vec0 Semantic

**Files:**
- Create: `src/coworker/qa/knowledge_search.py`
- Create: `tests/qa/test_knowledge_search.py`

**Interfaces:**
- Consumes: `KnowledgeIndex` (Task 2)
- Produces: `search_knowledge(index, project, topic, problem, prd_item_description) -> SearchResult`

**Change from v1:** Layer 2 is vec0 instead of FTS5.

```
Query flow (v2):

PRD item → extract topic + problem keywords
    │
    ▼
Layer 1: SQLite exact match
  SELECT * FROM knowledge_index
  WHERE project=? AND topic=? AND problem LIKE ?
  ORDER BY timestamp DESC
    │
    ├── exact match found? → return via memory_ref → done
    │
    ├── no exact match? → Layer 2: vec0
    │   vec0 KNN lookup(query="{topic} {problem} {prd_description}")
    │   → BM25 + vector hybrid search
    │   → returns relevant lore entries with scores
    │
    └── LLM filter (minimal tokens):
        "Same thing? {relevant: bool, reason: one sentence}"
```

- [ ] **Step 1: Write `knowledge_search.py`**

```python
# src/coworker/qa/knowledge_search.py
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from coworker.qa.knowledge_index import KnowledgeIndex


@dataclass
class SearchResult:
    exact_matches: list[dict] = field(default_factory=list)
    related: list[dict] = field(default_factory=list)
    conflicts: list[dict] = field(default_factory=list)
    relevance: str = "none"  # "exact" | "related" | "none"


def _vec0_knn_lookup(query: str, topic: str | None = None) -> list[dict]:
    """Call sqlite-vec vec0 KNN lookup tool.

    Returns list of lore entries with scores.
    Falls back to empty list if sqlite-vec unavailable.
    """
    # TODO: Wire to MCP tool: sqlite_vec.vec0 KNN lookup
    return []


def search_knowledge(
    index: "KnowledgeIndex",
    project: str,
    topic: str,
    problem: str | None,
    prd_item_description: str,
) -> SearchResult:
    result = SearchResult()

    # Layer 1: SQLite exact match
    exact = index.query_exact(project, topic, problem)
    if not exact and problem:
        exact = index.query_exact(project, topic, None)

    active = [r for r in exact if not r.get("superseded_by")]
    superseded = [r for r in exact if r.get("superseded_by")]

    result.exact_matches = active

    # Build conflicts from superseded chain
    for older in superseded:
        newer_id = older["superseded_by"]
        newer = next((r for r in active if r["id"] == newer_id), None)
        if newer:
            result.conflicts.append({
                "newer": newer_id, "older": older["id"],
                "reason": f"v{newer['timestamp']} supersedes v{older['timestamp']}",
            })

    if active:
        result.relevance = "exact"
        return result

    # Layer 2: vec0 semantic search
    query = f"{topic} {problem or ''} {prd_item_description}"
    knn_results = _vec0_knn_lookup(query, topic=topic)
    result.related = knn_results
    result.relevance = "related" if knn_results else "none"

    return result
```

- [ ] **Step 2: Write tests**

```python
# tests/qa/test_knowledge_search.py
import pytest
from unittest.mock import Mock, patch
from coworker.qa.knowledge_search import search_knowledge, SearchResult

SAMPLE_ROW = {
    "id": "id_abc", "project": "test-app", "topic": "auth",
    "problem": "token-expiry-on-reload", "type": "decision",
    "timestamp": "2026-07-20T14:30:00Z",
    "memory_ref": "project/test-app/MEMORY.md#L89",
    "superseded_by": None,
}

class TestSearchKnowledge:
    def test_exact_match_via_sqlite(self):
        idx = Mock()
        idx.query_exact = Mock(return_value=[SAMPLE_ROW])
        result = search_knowledge(idx, "test-app", "auth", "token-expiry-on-reload", "token feature")
        assert result.relevance == "exact"
        assert len(result.exact_matches) == 1

    def test_fallback_to_lore_when_no_sqlite_match(self):
        idx = Mock()
        idx.query_exact = Mock(return_value=[])
        with patch("coworker.qa.knowledge_search._vec0_knn_lookup") as lore:
            lore.return_value = [{"summary": "related token fix", "score": 0.85}]
            result = search_knowledge(idx, "test-app", "auth", "unknown", "token feature")
            assert result.relevance == "related"
            assert len(result.related) == 1

    def test_conflicts_detected(self):
        idx = Mock()
        idx.query_exact = Mock(return_value=[
            {**SAMPLE_ROW, "id": "id_old", "superseded_by": "id_new"},
            {**SAMPLE_ROW, "id": "id_new", "superseded_by": None},
        ])
        result = search_knowledge(idx, "test-app", "auth", "token-expiry-on-reload", "token feature")
        assert len(result.conflicts) == 1
```

- [ ] **Step 3: Run tests → pass → commit**

```bash
git add src/coworker/qa/knowledge_search.py tests/qa/test_knowledge_search.py
git commit -m "feat(qa): add two-layer search (SQLite exact + vec0 semantic)"
```

---

### Task 5: Test Plan — Research → Discussion → Plan (unchanged)

Same as v1 Task 5. No sqlite-vec dependency — test plan logic is pure filesystem + LLM.

- [ ] **Step 1-4: Same as v1 Task 5**
- [ ] **Step 5: Commit**

```bash
git add src/coworker/qa/test_plan.py tests/qa/test_test_plan.py
git commit -m "feat(qa): add test plan research, coverage mapping, and scenario generation"
```

---

### Task 6: Gap Check + state-driven gap tracking

**Files:**
- Create: `src/coworker/qa/gap_check.py`
- Create: `tests/qa/test_gap_check.py`

**Interfaces:**
- Consumes: `KnowledgeIndex` (Task 2), `search_knowledge` (Task 4)
- Produces:
  - `static_check(prd_item, project_dir) -> LayerResult`
  - `test_check(prd_item, test_dirs) -> LayerResult`
  - `dynamic_check(prd_item, project_dir) -> LayerResult | None`
  - `verify_item(prd_item, project_dir, test_dirs) -> VerificationResult`
  - `create_gap_quests(gaps: list[dict]) -> list[str]` — **NEW: create state file for each gap**
  - `generate_gap_report(items) -> GapReport`

**Change from v1:** After gaps are detected, each gap automatically becomes a Gap item with atomic claiming and dependency tracking.

- [ ] **Step 1: Write gap_check.py core** (same verification logic as v1 Task 6)

- [ ] **Step 2: Add Quest creation**

```python
# src/coworker/qa/gap_check.py (new function)

def create_gap_quests(gaps: list[dict]) -> list[str]:
    """Convert detected gaps into state file.

    Each gap becomes a Quest with:
    - title: PRD item description
    - declarations: verifiable conditions (file exists, test passes, etc.)
    - depends_on: P0 gaps first, then P1 gaps depend on P0 resolution
    """
    quest_ids = []

    # P0 gaps first (no dependencies)
    p0_gaps = [g for g in gaps if g["severity"] == "P0"]
    for gap in p0_gaps:
        quest_id = _state_file_append(
            title=f"[GAP-P0] {gap['prd_item']}",
            declarations=_build_declarations(gap),
        )
        quest_ids.append(quest_id)

    # P1 gaps depend on all P0 gaps
    p1_gaps = [g for g in gaps if g["severity"] != "P0"]
    for gap in p1_gaps:
        quest_id = _state_file_append(
            title=f"[GAP-P1] {gap['prd_item']}",
            declarations=_build_declarations(gap),
            depends_on=quest_ids[:len(p0_gaps)],  # wait for P0
        )
        quest_ids.append(quest_id)

    return quest_ids


def _build_declarations(gap: dict) -> list[str]:
    """Build machine-verifiable declarations from a gap."""
    decls = []
    verdict = gap.get("verdict", "")
    if verdict == "not_implemented":
        decls.append(f"File implementing '{gap['prd_item']}' exists in source tree")
    decls.append(f"Test for '{gap['prd_item']}' exists and passes")
    decls.append(f"No regression in existing test suite")
    return decls


def _state_file_append(title: str, declarations: list[str],
                        depends_on: list[str] | None = None) -> str:
    """Call sqlite-vec MCP state_append tool. Falls back to state file if unavailable."""
    # TODO: Wire to MCP tool: sqlite_vec.state_append
    # Returns quest_id
    import uuid
    return f"quest-{uuid.uuid4().hex[:12]}"
```

- [ ] **Step 3: Write tests**

```python
class TestGapQuestCreation:
    def test_creates_quest_for_each_gap(self):
        gaps = [
            {"id": "G-1", "prd_item": "token refresh", "severity": "P0",
             "verdict": "not_implemented"},
            {"id": "G-2", "prd_item": "rate limiting", "severity": "P1",
             "verdict": "missing_test"},
        ]
        with patch("coworker.qa.gap_check._state_file_append") as mock_create:
            mock_create.return_value = "quest-abc123"
            ids = create_gap_quests(gaps)
            assert len(ids) == 2

    def test_p0_gaps_have_no_dependencies(self):
        gaps = [
            {"id": "G-1", "prd_item": "token refresh", "severity": "P0",
             "verdict": "not_implemented"},
        ]
        with patch("coworker.qa.gap_check._state_file_append") as mock_create:
            mock_create.return_value = "quest-abc123"
            create_gap_quests(gaps)
            call_args = mock_create.call_args
            assert call_args[1]["depends_on"] is None  # P0: no deps

    def test_p1_gaps_depend_on_p0(self):
        gaps = [
            {"id": "G-1", "prd_item": "p0-gap", "severity": "P0",
             "verdict": "not_implemented"},
            {"id": "G-2", "prd_item": "p1-gap", "severity": "P1",
             "verdict": "missing_test"},
        ]
        with patch("coworker.qa.gap_check._state_file_append") as mock_create:
            mock_create.side_effect = ["quest-p0", "quest-p1"]
            create_gap_quests(gaps)
            # Second call (P1) should depend on first quest
            p1_call = mock_create.call_args_list[1]
            assert "quest-p0" in p1_call[1]["depends_on"]
```

- [ ] **Step 4: Run tests → pass → commit**

```bash
git add src/coworker/qa/gap_check.py tests/qa/test_gap_check.py
git commit -m "feat(qa): add three-layer gap detection with Gap item creation"
```

---

### Task 7: Fix, Discovery , Orchestrator, CLI

**Files:**
- Create: `src/coworker/qa/fix.py`
- Create: `src/coworker/qa/discovery.py`
- Create: `src/coworker/qa/orchestrator.py`
- Create: `src/coworker/qa/cli.py`
- Create: `tests/qa/test_fix.py`
- Create: `tests/qa/test_discovery.py`
- Create: `tests/qa/test_orchestrator.py`
- Create: `tests/qa/test_cli.py`
- Modify: `src/coworker/cli.py`

### 7a: fix.py — Quest-Driven Fix Execution

```python
# src/coworker/qa/fix.py
from dataclasses import dataclass

@dataclass
class FixResult:
    id: str
    status: str  # fixed | skipped | failed | blocked
    quest_id: str | None = None
    commit: str | None = None
    reason: str = ""


def execute_fix(gap: dict, project_dir: str) -> FixResult:
    """Execute one fix. state-driven: claims quest first, verifies declarations after.

    Flow (v2 with sqlite-vec):
    1. Claim the Quest for this gap (atomic — prevents duplicate work)
    2. Create mini test plan
    3. Execute fix
    4. Verify all Quest declarations pass
    5. Mark Quest complete → auto-unlocks dependent Quests
    """
    quest_id = gap.get("quest_id")
    if not quest_id:
        return FixResult(id=gap["id"], status="skipped",
                         reason="no quest_id — gap was not registered as Quest")

    # Step 1: Claim Quest
    if not _state_file_assign(quest_id):
        return FixResult(id=gap["id"], status="blocked",
                         quest_id=quest_id,
                         reason=f"Quest {quest_id} already claimed by another agent")

    # Step 2: Verify auto_fixable
    if not gap.get("auto_fixable", True):
        return FixResult(id=gap["id"], status="skipped", quest_id=quest_id,
                         reason="auto_fixable=false, needs manual review")

    # Step 3: Fix (DeepSeek Flash) + verify
    # TODO: Wire to actual LLM + git workflow

    # Step 4: Verify declarations + complete Quest
    # _state_file_mark_done(quest_id)  ← verifies all declarations pass

    return FixResult(id=gap["id"], status="fixed", quest_id=quest_id)


def _state_file_assign(quest_id: str) -> bool:
    """Atomically claim a Quest. Returns False if already claimed."""
    # TODO: Wire to MCP tool: sqlite_vec.state_assign
    return True


def _state_file_mark_done(quest_id: str) -> bool:
    """Mark Quest complete. Only succeeds if all declarations verified."""
    # TODO: Wire to MCP tool: sqlite_vec.state_mark_done
    return True
```

### 7b: discovery.py — 7 Dimensions

```python
# src/coworker/qa/discovery.py

DISCOVERY_DIMENSIONS = [
    "external-reference", "code-pattern", "test-coverage",
    "dependency-debt", "performance", "security", "error-handling",
]

@dataclass
class DiscoveryFinding:
    id: str
    dimension: str
    severity: str
    title: str
    current_state: str
    reference: dict = field(default_factory=dict)
    suggested_change: str = ""
    evidence: str = ""
    auto_fixable: bool = True
    jam_bug_url: str | None = None  # NEW: link torecording


def scan_dimension(dimension: str, context: dict) -> list[DiscoveryFinding]:
    """Scan one dimension. error-handling dimension uses ."""
    if dimension == "error-handling":
        return _scan_error_handling_with_jam(context)
    # ... other dimensions same as before
    return []


def _scan_error_handling_with_jam(context: dict) -> list[DiscoveryFinding]:
    """Pull bug context fromrecordings for richer discovery."""
    findings = []

    # Check forbug URLs in project context
    jam_urls = context.get("jam_bug_urls", [])
    for url in jam_urls:
        try:
            # Pull structured context from 
            console = _jam_get_console_logs(url)
            network = _jam_get_network_logs(url)
            transcript = _jam_get_video_transcript(url)

            # Analyze for error patterns
            if console_has_errors(console):
                findings.append(DiscoveryFinding(
                    id=f"JAM-{_short_hash(url)}",
                    dimension="error-handling",
                    severity="high",
                    title=f"Bug recording found: {_summarize_transcript(transcript)}",
                    current_state=f"Console errors: {_count_errors(console)}, "
                                  f"Network failures: {_count_network_errors(network)}",
                    evidence=f"Jam: {url}",
                    jam_bug_url=url,
                    auto_fixable=False,  # Needs human verification first
                ))
        except Exception:
            continue

    return findings


def _jam_get_console_logs(url: str) -> dict: ...
def _jam_get_network_logs(url: str) -> dict: ...
def _jam_get_video_transcript(url: str) -> str: ...
```

### 7c: orchestrator.py — Quest-Driven Loop

```python
# src/coworker/qa/orchestrator.py
import time
from dataclasses import dataclass, field
from typing import Generator

MAX_DEFAULT_HOURS = 12
WRAP_UP_THRESHOLD = 600  # 10 min


@dataclass
class OrchestratorEvent:
    event: str
    data: dict = field(default_factory=dict)


def run(task_name: str, max_hours: float = MAX_DEFAULT_HOURS,
        project: str | None = None, dry_run: bool = False,
        from_state: str | None = None,
        ) -> Generator[OrchestratorEvent, None, None]:
    """Main QA loop — state-driven (v2).

    Key v2 changes:
    - Gap tracking via state file (not state file lists)
    - Session continuity via state file (read previous, write current)
    - Oath enforcement at each phase transition
    -  in discovery phase
    """
    max_seconds = max_hours * 3600
    start = time.time()

    yield OrchestratorEvent("phase_start", {"phase": "init", "max_hours": max_hours})

    # Load Oaths before anything else
    yield OrchestratorEvent("phase_start", {"phase": "load_oaths"})
    oaths = _code_qa_gate_check()  # ["p0-gate", "research-before-action", ...]
    yield OrchestratorEvent("phase_done", {"phase": "load_oaths", "oaths": oaths})

    # Resume from prior Brief
    if from_state:
        prior = _state_file_read(task_name)
    else:
        prior = _state_file_read(task_name)  # Always try — returns None if first run
    yield OrchestratorEvent("phase_done", {"phase": "load_context", "has_prior_brief": prior is not None})

    # Check Oath: research-before-action
    if "research-before-action" in oaths:
        yield OrchestratorEvent("phase_start", {"phase": "research"})
        # ... research phase ...
        yield OrchestratorEvent("phase_done", {"phase": "research"})

    # Test plan gate
    # ... same as v1 ...

    # Gap check → create Quests
    yield OrchestratorEvent("phase_start", {"phase": "gap_check"})
    gaps = []  # TODO: actual gap detection results
    quest_ids = _state_file_append_batch(gaps)  # Task 6's create_gap_quests()
    yield OrchestratorEvent("phase_done", {
        "phase": "gap_check",
        "gaps_found": len(gaps),
        "quest_ids": quest_ids,
    })

    # Check Oath: p0-gate
    if "p0-gate" in oaths:
        p0_quests = _state_file_list(status="pending", filter_p0=True)
        if p0_quests:
            yield OrchestratorEvent("blocked", {
                "reason": "p0-gate Oath: P0 gaps must be fixed before proceeding",
                "pending_p0_quests": len(p0_quests),
            })
            # Loop won't proceed past repair until P0 quests are complete

    # Repair: claim Quest → fix → verify declarations → complete
    yield OrchestratorEvent("phase_start", {"phase": "repair"})
    for quest_id in quest_ids:
        if time.time() - start > max_seconds - WRAP_UP_THRESHOLD:
            break
        # claim quest → fix → complete
    yield OrchestratorEvent("phase_done", {"phase": "repair"})

    # Discovery loop
    yield OrchestratorEvent("phase_start", {"phase": "discovery"})
    # ... scan dimensions, create optimization quests ...

    # Time up → write Brief
    elapsed = time.time() - start
    _state_file_note(task_name, {
        "phase": "done",
        "elapsed_seconds": elapsed,
        "time_remaining": max(0, max_seconds - elapsed),
    })
    yield OrchestratorEvent("done", {"elapsed_seconds": elapsed})
```

### 7d: cli.py (same as v1, minor updates)

```python
# src/coworker/qa/cli.py — same as v1 Task 7
```

- [ ] **Step 1-7: Write all 4 files + tests** (follow same TDD pattern as prior tasks)
- [ ] **Step 8: Wire `qa_group` into `src/coworker/cli.py`**
- [ ] **Step 9: Run all tests**

```bash
pytest tests/qa/ -v
```

- [ ] **Step 10: Commit**

```bash
git add src/coworker/qa/fix.py src/coworker/qa/discovery.py \
        src/coworker/qa/orchestrator.py src/coworker/qa/cli.py \
        tests/qa/test_fix.py tests/qa/test_discovery.py \
        tests/qa/test_orchestrator.py tests/qa/test_cli.py
git commit -m "feat(qa): add state-driven fix,  discovery, state-driven orchestrator, CLI"
```

---

### Task 8: 7 SKILL.md Files

Same as v1 Task 8. Each skill's description updated to mention sqlite-vec/fastembed where relevant.

```markdown
---
name: qa-orchestrator
description: Run the QA autonomous agent pipeline using state file for gap tracking and Briefs for session continuity. Part of self-evolving-agent initiative.
---
```

```markdown
---
name: qa-continuous-discovery
description: Scan for optimizations across 7 dimensions. Uses state file for bug reproduction context in error-handling dimension.
---
```

- [ ] **Step 1: Create all 7 SKILL.md**
- [ ] **Step 2: `coworker sync` to register**
- [ ] **Step 3: Commit**

---

### Task 9: Git Push Hook + Verification

Same as v1 Task 9.

---

## v1 → v2 Changes Summary

| Component | v1 | v2 |
|-----------|----|----|
| Semantic search | FTS5 only | vec0 (BM25 + vector hybrid) |
| Gap tracking | State file markdown list | state file (atomic claim + dependency cascading) |
| Session continuity | State file manual read/write | state file (auto session handoff) |
| Quality gates | Agent "remembers" rules | code-enforced QA gates (auto-loaded, enforced at phase transitions) |
| Bug context in discovery | None | state file (console + network + transcript) |
| knowledge_index.py | 200 lines (SQL + FTS5) | ~120 lines (SQL exact-match only) |
| knowledge_search.py | FTS5 query code | vec0 MCP calls |
| orchestrator.py | Manual state list management | Quest claim/complete + Brief read/write |
| New dependencies | None | sqlite-vec (pip), fastembed |
| Total new files | ~15 | ~12 (removed FTS5 code, state management code) |

## Plan Summary

| Task | Files | Description | Est. Time |
|------|-------|-------------|-----------|
| 0 | 2 | sqlite-vec + fastembed setup | 20 min |
| 1 | 3 | Error codes (12 codes ) | 20 min |
| 2 | 2 | SQLite exact-match only (no FTS5) | 25 min |
| 3 | 2 | Extraction → SQLite + MEMORY.md + vec0 | 30 min |
| 4 | 2 | Search: SQLite exact + vec0 semantic | 25 min |
| 5 | 2 | Test plan research + scenario generation | 30 min |
| 6 | 2 | Gap check + Gap item creation | 35 min |
| 7 | 9 | Fix (state-driven), discovery (+Jam), orchestrator, CLI | 50 min |
| 8 | 7 | 7 SKILL.md files | 20 min |
| 9 | 1 | Git push hook | 10 min |
| **Total** | **32** | | **~4.5 hours** |
