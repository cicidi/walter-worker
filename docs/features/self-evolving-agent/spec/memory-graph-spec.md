# Memory Graph — Spec

> Initiative: self-evolving-agent | Type: spec | Status: **draft v1.0**
>
> The Memory Graph is a stigmergy-inspired knowledge graph that federates static
> code/document structure (from Graphify) with dynamic session experience (from
> AI transcript extraction). Agents deposit traces, later agents follow the
> strongest paths, and the graph self-reinforces over time.

---

## §0 Background

### 0.1 Biological Metaphor

| Biology | Memory Graph |
|---------|-------------|
| Ant/bee | Each AI session |
| Food/nectar | Insight, lesson, decision discovered in session |
| Pheromone trail / waggle dance | Nodes + edges written to graph with base_weight |
| Trail concentration | Edge weight — more traversals = stronger |
| Pheromone evaporation | Passive decay — unused edges fade over time |
| Hive floor (shared environment) | Graph itself — all agents read/write the same structure |

### 0.2 Relationship to Existing Systems

| System | Role |
|--------|------|
| **Graphify** | Static skeleton: code + documents → `graphify-out/graph.json` (read-only input source). Weekly cron sync via deterministic ID merge. |
| **mem0** | Vector index for semantic search. Complementary to graph traversal — answers "what is similar?" while graph answers "what is connected and how?" |
| **capture.py** | Per-session extraction. LLM reads transcript → outputs lessons (mem0), session nodes + edges (graph). |
| **Memory Graph** | The authoritative live graph. Federates Graphify skeleton + session experience. Owns weights, decay, reinforcement. Stored at `~/.coworker/memory/graph.json`. |

---

## §1 Data Model

### 1.1 Node Types

| type | provenance | id format | source |
|------|-----------|-----------|--------|
| `code` | graphify | `path/to/file.py::symbol_name` | Graphify |
| `document` | graphify | `path/to/doc.md::section_title` | Graphify |
| `session` | capture | `session_<date>_<seq>` | capture.py |
| `decision_point` | capture | `session_<date>_<seq>::<decision_label>` | capture.py |
| `concept` | either | arbitrary, unique | either |

### 1.2 Edge Schema

```json
{
  "source": "node_id",
  "target": "node_id",
  "relation": "calls | imports | implements | references | depends_on | tried | pivoted_to | modifies | contradicts | verifies | discusses",
  "confidence": "EXTRACTED | INFERRED | AMBIGUOUS",
  "confidence_score": 0.9,       // EXTRACTED=0.9, INFERRED=0.7, AMBIGUOUS=0.5, WEAK=0.2
  "base_weight": 0.7,            // Initial: confidence_score
  "last_traversed_at": null,     // ISO timestamp or null
  "source_file": "...",
  "provenance": "graphify | capture"
}
```

### 1.3 Confidence Tiers

| Tier | Score | Source | Behavior |
|------|-------|--------|----------|
| **EXTRACTED** | 90% (0.9) | Deterministic source (AST, grep) | Gold — rewrite conflicting ≤70% edges |
| **INFERRED** | 70% (0.7) | LLM-based single-pass extraction | Navigable — rewrite conflicting ≤50% |
| **AMBIGUOUS** | 50% (0.5) | LLM-based with uncertainty | Reference only — don't navigate; can be rewritten by ≥70% |
| **WEAK** | 20% (0.2) | Noise floor | Recorded for audit; never returned in query results |

**Comparing tiers:** Tier names are **not** alphabetically ordered — never compare
them with string operators. `confidence < "EXTRACTED"` is a latent bug
(`'INFERRED' > 'EXTRACTED'` and `'WEAK' > 'EXTRACTED'` lexicographically, so the
guard would silently skip INFERRED/WEAK). Always compare the numeric
`confidence_score`, or use the explicit rank
`EXTRACTED(4) > INFERRED(3) > AMBIGUOUS(2) > WEAK(1)`.

### 1.4 Node ID Namespace Isolation

Graphify IDs never collide with capture IDs:
- Graphify: `path/to/file::symbol` or `path/to/doc::heading`
- Capture: always prefixed `session_<date>_<seq>` for root nodes, `session_<date>_<seq>::sub` for children

> **From review #9 (Pro-win, clarified):** namespace isolation does **not** rely
> on matching ID string prefixes. Each node's `type` (`code`/`document` vs
> `session`/`decision_point`) and `provenance` (`graphify` vs `capture`) are **set
> at creation** (see test N1-N5) and stored as fields — never derived from the ID
> string. So even a file literally named `session_20260101_001.py` produces a
> Graphify node with `type=code, provenance=graphify`, unambiguously distinct from
> a capture node. IDs are compared as opaque primary keys.

---

## §2 Passive Decay

### 2.1 Formula

```
effective_weight = base_weight   if days_since(last_traversed_at) < 20
                 = base_weight × 0.99^(days - 20)   if days ≥ 20
```

| Days idle | Effective weight (from 0.9) | Effective weight (from 0.5) |
|-----------|---------------------------|---------------------------|
| 10 | 0.9 (protected) | 0.5 (protected) |
| 20 | 0.9 | 0.5 |
| 30 | 0.814 | 0.452 |
| 60 | 0.602 | 0.335 |
| 90 | 0.446 | 0.248 |
| 120 | 0.330 | 0.183 |

> **Decay model boundary (from review #5):** this exponential decay applies to
> **graph edges only**. `mem0` memory cards use a *different, step-function*
> decay already implemented in `src/coworker/memory/curator.py` (`_score_memories`:
> `<7d=1.0, 7-30d=0.5, 30-60d=0.1, >60d=0`). The two models coexist by design —
> graph edges are weighted relations (continuous decay fits); mem0 cards are
> unstructured text (recency buckets fit). They operate on different stores and
> do not interact at decay time.

### 2.2 Query Filter

- `effective_weight ≥ 0.5` → normal navigation
- `0.3 ≤ effective_weight < 0.5` → returned with `stale` flag
- `effective_weight < 0.3` → suppressed from results

### 2.3 Edge Cases

- `last_traversed_at = null` (never traversed) → `effective_weight = base_weight` (no decay)
- `last_traversed_at` in the future → clamp to `now()`, compute normally
- `base_weight = 0` or negative → treat as 0.2 (WEAK floor)

### 2.4 No Background Process

Decay is computed at query time — no daemon, no cron, no O(N) writes. Only the queried edges are evaluated.

---

## §3 Path Reinforcement

> **Scope (v1 vs v2):** v1 implements only **decay** (§2) and **initial weights**
> (`base_weight = confidence_score` at write time). The weight-mutations in §3.1/§3.2
> and the `verify_finding` API (§3.3) require an **agent-protocol** — agents
> reporting traversal outcome (which path they followed, success/failure) — that
> is not yet designed. They are **deferred to v1.5/v2**. The pseudocode below is
> the corrected v2 design, kept here so v2 inherits correct logic rather than the
> original string-compare bug (see §1.3).

### 3.1 Successful Traversal (v2)

When an agent follows a graph path and achieves a verified outcome:

```
for each edge in traversed_path:
    edge["last_traversed_at"] = now()
    # Compare NUMERIC score, NEVER the tier string (latent bug — see §1.3).
    # Reinforce INFERRED(0.7) + AMBIGUOUS(0.5) only:
    #   EXTRACTED(0.9) is at ceiling; WEAK(0.2) must stay suppressed (§1.3).
    if 0.2 < edge["confidence_score"] < 0.9:
        edge["base_weight"] = min(0.9, edge["base_weight"] + 0.05)
```

### 3.2 Failed Traversal (v2)

When an agent follows a path and it leads to a dead end:

```
for each edge in traversed_path:
    edge["last_traversed_at"] = now()
    edge["base_weight"] = max(0.2, base_weight - 0.1)  # cap floor at 0.2
```

**Rationale (clock reset on failure, §3.2):** decay (§2) models *disuse* — an
unused edge fades. A failed traversal is still a *use* (the agent exercised the
path), so the decay clock refreshes. The *failure* signal is carried by the
`-0.1` ratchet, which is independent of the decay clock. Two mechanisms, two
signals: ratchet = "this path fails", decay = "this path is unused". A
consistently-failing edge is driven to the 0.2 floor by the ratchet (5 failures
from 0.7), not by decay.

### 3.3 Verification Signals (v2)

A traversal is "successful" when:
- Code compiles + tests pass after the change
- PRD → Spec → Code → Test chain is intact
- A downstream agent confirms the finding independently

**Concrete verification API:**

```python
def verify_finding(node_id: str, verification_type: str, evidence: dict):
    """Called by agent after independently confirming a prior finding."""
    edge = find_edge_to_reinforce(graph, node_id)
    if edge:
        edge["verified_by"].append({
            "agent_session": evidence.get("session_id"),
            "verification_type": verification_type,  # "test_pass" | "pr_merged" | "agent_confirmed"
            "timestamp": now(),
        })
        # Only reinforce when an explicit verification event fires
        if verification_type in ("test_pass", "pr_merged"):
            edge["last_traversed_at"] = now()
            edge["base_weight"] = min(0.9, edge["base_weight"] + 0.05)
```

Verification is opt-in and explicit — agents call `verify_finding()` when they have evidence.
This replaces the vague "downstream agent confirms" with a concrete API.

> **v1 gap (from review #4):** `verify_finding` / `record_traversal` currently
> have **zero callers** — no CLI subcommand, hook, or MCP tool invokes them.
> Without a caller, `last_traversed_at` stays `null` and decay never fires.
> v1 therefore refreshes `last_traversed_at` directly in the **merge worker**
> when a session references an edge (§8.3), making decay work *without* the
> agent-protocol. Wiring the full `verify_finding` caller (CLI + agent-protocol
> + integration test) is **v1.5**.

---

## §4 Session Integration (capture.py)

### 4.0 Dual IDE Support

Both Claude Code and OpenCode sessions feed the same graph. The graph layer is IDE-agnostic.

> **Honest current state (from review #1):** the prior claim that "capture.py
> already supports both IDEs via existing hook config in `coworker.yaml`" is
> **FALSE**. Verified against the codebase:
> - **OpenCode** (`adapters/opencode.py`) writes only MCP/permission config —
>   **zero hook integration**.
> - **Claude Code** (`~/.claude/settings.json`) routes `PostToolUse` →
>   `on-post-tool.sh` (analytics JSONL only) and `Stop` → `coworker state-update`.
>   **No hook calls `coworker memory sync` / `close` today.**
> - `coworker.yaml` has **no `hooks:` section**.
>
> The capture.py *module* and the `coworker memory sync`/`close` CLI subcommands
> exist, but are dead code from the hook perspective. **Wiring the session-end
> hook is required v1 work** (see §10).

| | Claude Code | OpenCode |
|---|-------------|----------|
| **Session-end hook (graph)** | `Stop` (async, stdin) → `coworker memory close` | `session.end` → `coworker memory close` (needs verification) |
| Per-turn hook | `PostToolUse` → analytics JSONL only (**NOT** graph) | `tool.execute.after` → analytics only (**NOT** graph) |
| Transcript format | JSONL | JSONL |
| Graph write | `capture.py` → `pending/<session>.json` → merge worker → `graph.json` | Same |
| node provenance | `provenance: "claude-code"` | `provenance: "opencode"` |

**Graph extracts at session-end only** — one LLM pass over the full transcript,
not per-turn. Per-turn extraction is expensive and fragmented; the full transcript
gives the LLM complete context for accurate node/edge extraction. `PostToolUse`
continues to serve **analytics** (recording tool calls) and is unrelated to the graph.

Implementation: the graph extension is a new output field in capture.py's
session-end LLM call. The required per-IDE change is **wiring the session-end
hook** (§10), not modifying capture.py.

Note: OpenCode session import to analytics.db is a pre-existing gap (see
self-evolving-agent-spec §3.2). It affects metrics dashboard completeness but
does NOT block graph functionality — graph writes happen in capture.py, not
analytics import.

### 4.1 Prompt Extension

Add to `SESSION_END_PROMPT`:

```
3. Graph nodes — key entities this session touched (files, concepts, decisions).
   - id format: session_<date>_<seq>::<short_label>
   - type: session | decision_point | concept
   - Use past lessons (mem0) and wrong-history as reference for what to recognize.

4. Graph edges — relationships discovered.
   - relation: tried | pivoted_to | modifies | implements | verifies | contradicts | discusses
   - confidence: EXTRACTED (certain from transcript) | INFERRED (likely) | AMBIGUOUS (guess)
   - Always link to corresponding Graphify code/document nodes when known.
```

LLM output:

```json
{
  "lessons": [...],
  "skill_candidates": [...],
  "session_nodes": [{...}],
  "session_edges": [{...}]
}
```

### 4.2 Write Logic (capture.py → pending only)

> **From review #3:** capture.py **never touches `graph.json`**. It writes only a
> raw session dump to `pending/<session_id>.json`. Enrichment (`base_weight`,
> `last_traversed_at`, `provenance`), dedup (§4.3), and the merge into `graph.json`
> are the **merge worker's** job (§8.3). This preserves the single-writer invariant
> and resolves the §4.3-vs-§8.3 contradiction.

```python
def _write_session_pending(pending_dir, session_id, session_nodes, session_edges):
    """capture.py writes RAW nodes/edges. No enrichment, no dedup, no graph.json."""
    dump = {
        "session_id": session_id,
        "nodes": session_nodes,   # raw — no base_weight/provenance yet
        "edges": session_edges,   # raw — confidence only; enrichment happens in merge worker
    }
    write_json_atomic(pending_dir / f"{session_id}.json", dump, indent=2)
```

The merge worker (§8.3) enriches each edge using the **single shared mapper**
(defined here; §5.2 Graphify-sync reuses the same function — do not duplicate
under `_confidence_to_score` or any other name, per review #10):

```python
def _confidence_to_score(confidence: str) -> float:
    """Single source of truth for tier → score. Used by BOTH capture-merge (§4.2)
    and Graphify-sync (§5.2). Unknown/missing → AMBIGUOUS (0.5)."""
    return {"EXTRACTED": 0.9, "INFERRED": 0.7, "AMBIGUOUS": 0.5, "WEAK": 0.2}.get(confidence, 0.5)
```

Enrichment sets `base_weight = _confidence_to_score(confidence)`,
`last_traversed_at = now()` (**refreshed on every session reference** — this is
what makes decay actually fire in v1; see §3.3 v1-gap note), and
`provenance = "capture"`. The merge worker then dedups nodes (§4.3) and appends
to `graph.json`.

> **ID validation (from review #8):** when enriching edges, the merge worker
> validates that each edge's `target` node exists in the graph (or is among the
> session's own new nodes). Edges whose target is a freeform/unresolved ID
> (e.g. LLM emitted `src/auth.py` instead of the Graphify ID `src/auth.py::authenticate`)
> are **skipped and logged as `graph_misses`** rather than written as dangling edges.

### 4.3 Node Deduplication (runs in merge worker)

> **From review #3:** dedup runs in the **merge worker** (which holds the full
> graph), not in capture.py (which only sees its own session dump and therefore
> could never find duplicates). `_dedup_and_merge` is called by the merge worker
> after enrichment (§4.2), before appending to `graph.json`.

Multiple sessions touching the same code/file produce near-identical nodes. The
merge worker merges on write:

```python
def _dedup_and_merge(g, new_node):
    # g = full graph (merge worker holds it).
    for existing in g["nodes"]:
        if (existing.get("type") == new_node["type"] and
            existing.get("related_file") == new_node.get("related_file") and
            _similarity(existing["label"], new_node["label"]) > 0.7):
            existing["session_count"] = existing.get("session_count", 1) + 1
            existing["last_seen"] = new_node.get("timestamp")
            return existing["id"]  # reuse existing ID, don't create duplicate
    g["nodes"].append(new_node)
    return new_node["id"]
```

**`_similarity` definition (from review #7):** pinned to Python's standard-library
`difflib.SequenceMatcher` so the 0.7 threshold is meaningful (Jaccard / cosine /
Levenshtein behave differently and would require re-tuning):

```python
import difflib
def _similarity(a: str, b: str) -> float:
    """Label similarity in [0, 1]. 1.0 = identical. Pinned to difflib so the
    0.7 dedup threshold has a single, reproducible meaning."""
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()
```

Threshold 0.7 with `SequenceMatcher` prevents unrelated sessions from merging
while catching "session A tried X" vs "session B tried X on same file". Test
plan D1/D3 (§1.7) assert merge/no-merge outcomes against this pinned metric.

### 4.4 Archival

- Archive: edges with `effective_weight < 0.1` for 90+ days → moved to `~/.coworker/memory/archive/graph_archive.json`
- Target: graph.json ≤ 50 MB

---

## §5 Graphify Integration

### 5.1 Schema Mismatch

Graphify output uses `links` (not edges), different confidence naming, no weight fields.
**We never modify Graphify's file.** We copy relevant nodes + edges into our graph.json on first run.

### 5.2 Sync Logic

```python
def sync_graphify_skeleton(my_graph, new_graphify_json):
    new_nodes = new_graphify_json["nodes"]
    new_links = new_graphify_json["links"]

    for node in new_nodes:
        if node["id"] not in my_graph:
            my_graph.add(node)
        else:
            # Update metadata, preserve weights
            my_graph[node["id"]]["label"] = node.get("label", node["id"])
            my_graph[node["id"]]["community"] = node.get("community")

    for link in new_links:
        key = (link["source"], link["target"], link.get("relation", "references"))
        if key not in my_graph:
            edge = {
                "source": link["source"],
                "target": link["target"],
                "relation": link.get("relation", "references"),
                "confidence": link.get("confidence", "INFERRED"),
                "confidence_score": _confidence_to_score(link.get("confidence")),
                "base_weight": _confidence_to_score(link.get("confidence")),
                "last_traversed_at": None,
                "provenance": "graphify",
            }
            my_graph.add(edge)
        # existing edges: skip — preserve our weights
```

### 5.3 Schedule

- **On install:** `graphify .` once, import skeleton
- **Weekly cron:** `0 3 * * 0` (Sunday 3am) re-sync — new code/docs from `git pull` not seen in sessions
- **On-demand:** after major PRD/Spec rewrite

### 5.4 File Rename Handling (future)

If Graphify detects a renamed file, it produces a new ID. Old node's weights are orphaned.
Mitigation (v2): label-based fuzzy match `find_by_label_and_type()` to reconnect renamed nodes.
Scope: low-frequency problem, not in v1.

---

## §6 Query API

### 6.1 Search Modes

```python
def query(graph, question, mode="both"):
    if mode in ("graph", "both"):
        # Traverse graph with decay-adjusted weights
        results_graph = graph_traverse(graph, question)
    if mode in ("vector", "both"):
        # mem0 semantic search
        results_vector = mem0_client.search(question)
    return merge_and_rank(results_graph, results_vector)
```

### 6.2 Graph Traversal

- Start from nodes matching query terms
- BFS with max depth 3
- Rank by edge effective_weight
- Prefer EXTRACTED (90%) edges over INFERRED (70%)
- Suppress edges with effective_weight < 0.3

### 6.3 Agent Integration

```
Agent receives task → query(graph, task) → receives ranked paths
    → decides which path to follow
    → after completion → record_traversal(path, success=True/False)
```

---

## §7 Visualization

### 7.1 Reuse Graphify's Export — ⚠️ UNVERIFIED (from review #12)

> **Verification gap:** Graphify is **not currently installed** (no `graphify`
> package, no `graphify-out/` directory). The claim below — that Graphify's
> export module *consumes our* `graph.json` (output direction) — is
> **unverified**. This is distinct from §5.1, which defends the *input*
> direction (Graphify → our graph) via a translation layer; that translation
> layer does **not** defend this output-direction reuse claim.

Our `graph.json` is NetworkX node-link format — *intended* to match what
Graphify's export module consumes. Pending verification:

```bash
# UNVERIFIED — gate behind a §11 test before relying on it:
python -m graphify.export graphify-out/ --input ~/.coworker/memory/graph.json
```

**v1 action:** treat the `/graph` tab (§7.2) as dependent on verifying this
command. If Graphify's actual export format differs, fall back to a direct
NetworkX → pyvis render (§7.2) without the Graphify export step.

### 7.2 Dashboard Integration

The live graph is embedded in the analytics dashboard as a `/graph` tab:

```
Dashboard
├── Overview
├── Projects
├── Evolution
├── Graph    ← NEW: interactive viz powered by pyvis/vis.js
└── ...
```

Features:
- Node color by type (code=blue, document=green, session=orange, decision_point=red)
- Edge thickness by effective_weight (thicker = stronger)
- Community grouping via Graphify's Leiden labels
- Toggle: show/hide decayed edges (effective_weight < 0.3)
- Click node → show related sessions + code files

Implementation: NetworkX → pyvis → embed in FastAPI route. **~150-250 lines** of
Python (from review #14: existing dashboard query modules run 150-486 lines; a
pyvis integration with weight-driven thickness, decay toggle, and click-to-detail
panel is realistically in that range — the original "~50 lines" estimate was
4-8× too low).

---

## §8 Storage

### 8.1 File Layout

```
~/.coworker/memory/
├── graph.json              # Live merged graph (authoritative)
├── archive/
│   └── graph_archive.json  # Edges decayed below 0.1 for 90+ days
├── vector/                 # mem0 Qdrant store (existing)
└── MEMORY.md               # Curator export (existing, read-only)
```

### 8.2 Schema Version

graph.json includes a version field for forward compatibility:

```json
{
  "schema_version": "1.0",
  "nodes": [...],
  "links": [...],
  "hyperedges": [...]
}
```

On load, check `schema_version`. If missing → treat as 1.0.
Future versions include a migration function: `migrate_graph(data, from_version, to_version)`.

### 8.3 Concurrency & Merge Worker

Two sessions ending simultaneously must not silently drop each other's edges.
Solution: **write-ahead queue** (not file locking).

> **From review #3 + #4:** the merge worker does **enrichment + dedup + decay
> refresh**, not just append. And it is triggered **synchronously by the
> session-end hook** (`coworker memory close`, §4.0) — not by a 30s daemon/cron,
> avoiding a new long-running process for a single-user tool.

```
session-end hook (Stop / session.end)
     │  invokes `coworker memory close`
     ▼
capture.py → ~/.coworker/memory/pending/<session_id>.json   (atomic write, never conflicts)
     │
     ▼
merge worker (single-threaded, invoked synchronously by the hook)
     │
     ├─ read pending/<session_id>.json  (+ any leftover pending/*.json from a prior crashed run)
     ├─ ENRICH each edge:
     │     base_weight       = _confidence_to_score(confidence)   (§4.2)
     │     last_traversed_at = now()         ← makes decay fire in v1 (§3.3 v1-gap)
     │     provenance        = "capture"
     ├─ validate edge targets exist (skip + log dangling as graph_misses)   (§4.2)
     ├─ DEDUP nodes via _dedup_and_merge                                     (§4.3)
     ├─ merge into graph.json (single writer, no race)
     ├─ write graph.json (atomic os.replace)
     └─ delete pending/<session_id>.json
```

Each session writes an independent file — zero contention. The merge worker
serializes all writes. Triggered synchronously by the session-end hook, so the
graph updates immediately when a session ends (no daemon, no 30s latency). If the
worker crashes mid-merge, the pending file survives (not yet deleted) and is
re-processed on the next session's hook invocation.

> **Why synchronous hook, not a daemon (review #3 decision):** walter-worker is a
> single-user, low-concurrency tool. A 30s daemon adds process-management and
> crash-recovery overhead for negligible benefit. The session-end hook already
> fires per session; running merge there gives immediate updates with no new
> long-running process. Two sessions ending simultaneously still serialize safely
> (each writes its own pending file; the merge worker is single-threaded).

### 8.4 Atomic Writes

All writes use temp-file + rename to prevent corruption on crash:

```python
def write_json_atomic(path, data):
    tmp = path.parent / f".{path.name}.tmp"
    json.dump(data, open(tmp, "w"), indent=2)
    os.replace(tmp, path)  # atomic on POSIX
```

---

## §9 Metrics & Validation

Three dimensions. All data from analytics.db. No new services, no cron.

### 9.1 Data Sources

| Data | Source | Status |
|------|--------|--------|
| Session metadata (project, model, cwd) | `sessions` table | ✅ existing |
| Tool calls (Grep, Read, Bash) per session | `tool_calls` + `session_stats` | ✅ existing |
| Session duration | `session_stats.duration_min` | ✅ existing |
| Baseline (no graph) comparison data | Same tables, sessions before graph launch | ✅ existing |
| Graph query accuracy | `graph_queries` table (new, ~40 lines) | ❌ to implement |

### 9.2 Dimension 1: Accuracy — Does graph actually help?

```python
# capture.py writes this at session end
{
    "session_id": "...",
    "query": "add OAuth to dashboard",
    "graph_hits": 5,              # 返回了几个节点
    "graph_useful": True,         # agent 判断：帮到了？
    "avoided_tool_calls": [       # 因为 graph 跳过的
        "grep auth → skipped",
        "read src/auth.py → skipped"
    ],
    "graph_misses": [             # 没搜到的，fallback
        "oauth config format → graph empty → grep oauth"
    ]
}
```

```sql
-- Dashboard: accuracy panel
SELECT
    COUNT(*) as total,
    SUM(CASE WHEN graph_useful THEN 1 ELSE 0 END) as hits,
    ROUND(100.0 * SUM(CASE WHEN graph_useful THEN 1 ELSE 0 END) / COUNT(*), 1) as hit_rate,
    GROUP_CONCAT(DISTINCT graph_misses) as gaps_to_fill
FROM graph_queries
WHERE timestamp >= date('now', '-7 days');
```

### 9.3 Dimension 2: Token & Tool Call Savings

```sql
-- Same task type, with vs without graph
SELECT
    s.initiative,
    CASE WHEN gq.session_id IS NULL THEN 'without_graph' ELSE 'with_graph' END as mode,
    COUNT(*) as sessions,
    AVG(ss.tool_count) as avg_tool_calls,
    AVG(ss.read_count + ss.bash_count) as avg_search_calls
FROM sessions s
JOIN session_stats ss ON s.id = ss.session_id
LEFT JOIN (SELECT DISTINCT session_id FROM graph_queries) gq ON s.id = gq.session_id
GROUP BY s.initiative, mode;
```

### 9.4 Dimension 3: Time per Turn

```sql
-- Turn-level timing per model, with/without graph
-- (tool_calls.ts already has timestamps)
SELECT
    s.model,
    CASE WHEN gq.session_id IS NULL THEN 'no_graph' ELSE 'graph' END as mode,
    AVG(ss.duration_min) as avg_minutes,
    COUNT(*) as session_count
FROM sessions s
JOIN session_stats ss ON s.id = ss.session_id
LEFT JOIN (SELECT DISTINCT session_id FROM graph_queries) gq ON s.id = gq.session_id
GROUP BY s.model, mode;
```

### 9.5 Baseline

Baseline data already exists in analytics.db — all historical sessions were recorded without graph.
To enable A/B comparison:

1. Add a `graph_enabled` column to the sessions table (default 0).
2. Set `graph_enabled = 1` for all sessions created after the graph launch timestamp.
3. Comparison queries use `WHERE graph_enabled = 0` for baseline, `= 1` for with-graph.

No waiting period — historical data is the baseline. The v1 checkbox for "Baseline metrics collection" refers to adding this column and backfilling, not to collecting new data.

### 9.6 Dashboard Panel

```
Dashboard → Evolution → Graph Metrics

  📊 Accuracy (7 days)
  ├─ Queries: 47
  ├─ Useful:  38 (80.9%)
  ├─ Misses:   9 → logged as incidents
  └─ Gaps: [oauth config, error handler, ...]

  💰 Token & Tool Calls
  ┌─────────────┬──────────┬──────────┐
  │ Initiative   │ No Graph │ Graph    │
  ├─────────────┼──────────┼──────────┤
  │ self-evolve │ 87 calls │ 50 calls │
  │ dashboard   │ 62 calls │ 35 calls │
  └─────────────┴──────────┴──────────┘

  ⏱️  Avg Time (min)
  ┌─────────────┬──────────┬──────────┐
  │ Model        │ No Graph │ Graph    │
  ├─────────────┼──────────┼──────────┤
  │ claude-5     │   18     │   10     │
  │ deepseek-v4  │   15     │    9     │
  └─────────────┴──────────┴──────────┘
```

No numbers are pre-filled. All values come from real SQL queries at page load.

---

## §10 Scope & Non-Goals

### In Scope (v1)
- [ ] **Wire session-end hooks** — Claude `Stop` → `coworker memory close`; OpenCode `session.end` → same (verify OpenCode hook support) (§4.0, #1)
- [ ] capture.py prompt extension: session_nodes + session_edges (session-end extraction only, no per-turn)
- [ ] **capture.py writes raw `pending/<session_id>.json` only** — never touches graph.json (§4.2, #3)
- [ ] **Merge worker**: enrich + ID-validate + dedup + merge + atomic write, triggered synchronously by the session-end hook (§8.3, #3/#4)
- [ ] graph.json init from Graphify + mem0 existing lessons (with `schema_version: "1.0"`)
- [ ] passive decay at query time (with `last_traversed_at` refreshed by merge worker — #4)
- [ ] atomic writes
- [ ] curator: stale edge archival
- [ ] Dashboard: `/graph` tab with interactive visualization (§7.2; pending §7.1 Graphify-export verification)
- [ ] Baseline metrics: `graph_enabled` column + backfill + comparison queries

### Out of Scope (v1.5)
- [ ] **Path reinforcement weight-mutation** (`+0.05` success / `-0.1` failure) — needs an agent-protocol for traversal outcome (§3.1, §3.2, #4)
- [ ] **`verify_finding()` / `record_traversal` caller wiring** — CLI + agent-protocol + integration test (§3.3, #4)

### Out of Scope (v2+)
- [ ] File rename detection (label-based fuzzy merge)
- [ ] Real-time graph sync (currently: synchronous session-end hook)
- [ ] Multi-project graph federation
- [ ] Graph-vs-vector conflict resolution (AI self-judges for now)

---

## §11 Test Plan

> See companion: [memory-graph-test-plan.md](../test-plan/memory-graph-test-plan.md)

### 11.1 Unit Tests
- Decay computation: verify effective_weight at days 0, 10, 20, 30, 60, 90, 120
- Confidence mapping: EXTRACTED→0.9, INFERRED→0.7, AMBIGUOUS→0.5, WEAK→0.2
- Node ID namespace: graphify IDs don't collide with session IDs
- Graphify sync: new nodes added, existing edges untouched
- Atomic write: crash mid-write doesn't corrupt graph.json

### 11.2 Integration Tests
- capture.py LLM output schema validation (session_nodes + session_edges present)
- Full pipeline: session transcript → nodes/edges → graph.json written
- Query: decay-suppressed edges not returned

### 11.3 Behavioral Tests
- 2 sessions on same topic → edges reinforced
- 90-day idle edge → weight < 0.3 → suppressed
- Conflicting conclusions (2 agents, 90% each, opposite) → both survive, agent self-judges

---

## Change Log

### v1.1 (2026-07-27) — independent re-review fixes (devil-advocate v2)

Driven by `docs/self-evolving-agent/devil-advocate/2026-07-27-memory-graph-v2/report.md`.
The v1 review's "ready for implementation" verdict was **retracted**: 3 of its 5
"fixes" were themselves defective, and 1 HIGH bug (§3.1 string-compare) was
invisible to v1.

**Must-fix (HIGH):**
- **#1 §4.0** — retracted the false "capture.py already supports both IDEs" claim;
  documented honest current state; graph now session-end-only (no per-turn);
  dual-IDE hook wiring added to §10.
- **#2 §3.1** — fixed the string-compare bug: guard is now
  `0.2 < confidence_score < 0.9` (numeric; reinforces INFERRED+AMBIGUOUS only).
  §1.3 added a tier-rank comparison warning.
- **#3 §4.3/§8.3** — resolved the contradiction: dedup moved to the merge worker;
  capture.py writes raw `pending/` only; merge worker does enrich+validate+dedup+merge.
- **#4 §3/§8.3** — `last_traversed_at` is now refreshed by the merge worker (so
  decay actually fires in v1). Reinforcement weight-mutation + `verify_finding`
  caller deferred to v1.5 (need an agent-protocol).

**Should-fix:**
- #5 §2.1 — decay-model boundary documented (graph=exponential, mem0=step).
- #7 §4.3 — `_similarity` pinned to `difflib.SequenceMatcher`.
- #8 §4.2 — ID validation in merge worker (skip/log dangling edges).
- #10 — unified `_confidence_to_score` (removed duplicate `_map_gf_confidence`).
- #11 §3.2 — clock-reset-on-failure rationale documented.
- #12 §7.1 — Graphify-export reuse marked UNVERIFIED.
- #14 §7.2 — pyvis line estimate corrected (~50 → ~150-250).

### v1.0 (2026-07-27) — initial draft + v1 devil-advocate fixes
