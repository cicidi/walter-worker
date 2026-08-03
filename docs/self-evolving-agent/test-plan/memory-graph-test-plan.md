# Memory Graph — Test Plan

> Initiative: self-evolving-agent | Type: test-plan | Status: **draft v1.0**
>
> Covers: memory-graph-spec.md §1–§7

---

## 1. Unit Tests

### 1.1 Passive Decay

| ID | Test | Input | Expected |
|----|------|-------|----------|
| D1 | Within protection window | base=0.9, last_traversed=10 days ago | effective=0.9 |
| D2 | At boundary | base=0.9, last_traversed=20 days ago | effective=0.9 |
| D3 | 30 days idle | base=0.9, last_traversed=30 days ago | effective ≈ 0.814 |
| D4 | 60 days idle | base=0.9, last_traversed=60 days ago | effective ≈ 0.602 |
| D5 | 90 days idle | base=0.5, last_traversed=90 days ago | effective ≈ 0.248 |
| D6 | 120 days idle | base=0.9, last_traversed=120 days ago | effective ≈ 0.330 |
| D7 | Zero base weight | base=0.2, last_traversed=120 days ago | effective < 0.1 |
| D8 | Untraversed edge | last_traversed_at=null | effective = base (no decay) |
| D9 | Future date | last_traversed_at in future | effective = base (clamp to 0) |

### 1.2 Confidence Mapping

| ID | Test | Input | Expected |
|----|------|-------|----------|
| C1 | EXTRACTED | confidence="EXTRACTED" | score=0.9 |
| C2 | INFERRED | confidence="INFERRED" | score=0.7 |
| C3 | AMBIGUOUS | confidence="AMBIGUOUS" | score=0.5 |
| C4 | Unknown string | confidence="FOO" | score=0.5 (default AMBIGUOUS) |
| C5 | Null/missing | confidence=None | score=0.5 |

### 1.3 Node ID Namespace

| ID | Test | Input | Expected |
|----|------|-------|----------|
| N1 | Graphify code ID | `src/auth.py::login` | Type `code` |
| N2 | Graphify doc ID | `docs/prd.md::r4_auth` | Type `document` |
| N3 | Session root ID | `session_20260727_001` | Type `session` |
| N4 | Session child ID | `session_20260727_001::attempt_bearer` | Type `decision_point` |
| N5 | No collision | merge graphify + capture nodes | 0 ID conflicts |

### 1.4 Graphify Sync

| ID | Test | Input | Expected |
|----|------|-------|----------|
| S1 | New code node | graph.json missing `src/new.py::fn` | Added |
| S2 | Existing code node | graph.json has `src/auth.py::login` | Label updated, base_weight preserved |
| S3 | New edge | graph.json missing edge `a→b` | Added with base_weight=confidence_score |
| S4 | Existing edge | graph.json has edge `a→b::calls` | Skipped, base_weight untouched |
| S5 | Removed file | Graphify doesn't include old node | Orphaned in graph.json (no crash) |

### 1.5 Atomic Write

| ID | Test | Input | Expected |
|----|------|-------|----------|
| A1 | Normal write | graph.json with 500 nodes | File updated correctly |
| A2 | Simulated crash | Kill process during write | graph.json intact (no .tmp corruption) |
| A3 | Disk full | ENOSPC during write | Old graph.json preserved |

### 1.6 Concurrency (Write-Ahead Queue, merge worker triggered by session-end hook)

> **From review #3:** merge worker runs synchronously on the session-end hook
> (`coworker memory close`), not a 30s daemon. capture.py writes raw
> `pending/<session>.json`; the merge worker enriches + dedups + writes graph.json.

| ID | Test | Input | Expected |
|----|------|-------|----------|
| W1 | Two concurrent writes | 2 sessions end simultaneously | Both session dumps written to pending/, merge worker serializes both |
| W2 | Merge worker crash | Kill merge worker mid-merge | Pending file survives (not yet deleted), re-processed on next session's hook invocation |
| W3 | Single writer | Only merge worker writes graph.json | No race possible |

### 1.7 Node Deduplication

| ID | Test | Input | Expected |
|----|------|-------|----------|
| D1 | Same file, same decision | 2 sessions both "try bearer on auth.py" | Merged into one node, session_count=2 |
| D2 | Same file, different decision | "try cookie" vs "try bearer" | Two separate nodes |
| D3 | Unrelated files | "try bearer on auth.py" vs "try bearer on db.py" | Two separate nodes |

### 1.8 Schema Version

| ID | Test | Input | Expected |
|----|------|-------|----------|
| V1 | Load v1 graph | `{"schema_version": "1.0", ...}` | Valid, loaded |
| V2 | Load legacy graph | No schema_version field | Treated as 1.0, loaded |
| V3 | Future version | `{"schema_version": "2.0", ...}` | Attempt migration, or error with clear message |
| V4 | Migration | v1 → v2 schema with new edge field | Migration function applies, data preserved |

---

## 2. Integration Tests

### 2.1 capture.py → graph.json

| ID | Test | Input | Expected |
|----|------|-------|----------|
| I1 | Session transcript | Standard session with code writes | LLM returns session_nodes + session_edges in JSON |
| I2 | Schema validation | LLM output | All required fields present (id, type, relation, confidence) |
| I3 | Write to graph | Valid session_nodes + session_edges | Appended to graph.json, base_weight set |
| I4 | Empty session | Session with no actionable work | Empty lists, no write |
| I5 | Malformed LLM output | LLM returns incomplete JSON | Graceful error, no corrupt write |

### 2.2 Full Pipeline

| ID | Test | Input | Expected |
|----|------|-------|----------|
| P1 | Build from scratch | No graph.json exists | Init from Graphify + mem0 lessons |
| P2 | Build incremental | graph.json exists + new session | Session nodes appended, old nodes preserved |
| P3 | Query with decay | graph.json with mixed-age edges | Old edges ranked lower than fresh edges |

### 2.3 Graphify Interop

| ID | Test | Input | Expected |
|----|------|-------|----------|
| G1 | First sync | Empty graph.json + graphify output | All code/doc nodes imported |
| G2 | Re-sync | graph.json has weights + new graphify output | New nodes added, existing edges untouched |
| G3 | Graphify missing | graphify-out/ doesn't exist | graph.json still loads (session nodes only) |
| G4 | Graphify empty | graph.json has session nodes, graphify has 0 nodes | Merge succeeds, session nodes survive |

---

## 3. Behavioral Tests

### 3.1 Path Reinforcement (v2 — needs agent-protocol)

> **Deferred to v1.5** (spec §3): reinforcement weight-mutation requires agents to
> report traversal outcome. v1 only refreshes `last_traversed_at` (decay works);
> `base_weight` stays at the initial `confidence_score`.

| ID | Scenario | Expected |
|----|----------|----------|
| B1 | 2 sessions touch same code path | Edge base_weight increases |
| B2 | 1 success after 1 failure | Success path > failure path weight |
| B3 | Agent finds new route | New edge added, old edge decays naturally |
| B4 | Conflicting conclusions | Both edges survive at 90%, agent sees both |

### 3.2 Long-Term Decay

| ID | Scenario | Expected |
|----|----------|----------|
| L1 | 90-day idle edge | effective_weight < 0.3, suppressed from query |
| L2 | Edge survives 20-day protection | No decay before day 21 |
| L3 | Recently traversed edge | Full weight, not decayed |

### 3.3 Edge Cases

| ID | Scenario | Expected |
|----|----------|----------|
| E1 | Circular reference in graph | Traversal terminates, no infinite loop |
| E2 | 10,000 nodes | Query < 100ms |
| E3 | Concurrent session writes | Last write wins (atomic), no corruption |
| E4 | Unicode node labels | Stored and queried correctly |

---

## 4. Metrics & Validation

### 4.1 Accuracy

| ID | Test | Input | Expected |
|----|------|-------|----------|
| M1 | Graph useful | Agent query returns relevant node, avoids grep | graph_useful=True, avoided_tool_calls populated |
| M2 | Graph miss | Agent query returns empty, falls back to grep | graph_useful=False, graph_misses logged |
| M3 | Hit rate calculation | 47 queries, 38 useful | hit_rate = 80.9% |
| M4 | Miss logged as incident | graph_misses populated | Dashboard shows gap list |

### 4.2 Token/Tool Call Comparison

| ID | Test | Input | Expected |
|----|------|-------|----------|
| M5 | Baseline exists | Query sessions table before graph launch | Returns non-zero row count |
| M6 | Compare same initiative | self-evolve tasks with vs without graph | tool_calls lower with graph |
| M7 | Read/Grep reduction | avg search calls before vs after | Reduction visible in SQL output |

### 4.3 Time

| ID | Test | Input | Expected |
|----|------|-------|----------|
| M8 | Per-model timing | Group by model + graph presence | Valid AVG() returned |
| M9 | Session duration | session_stats.duration_min | Matches session.yaml timestamps |

## 5. Non-Functional

| ID | Metric | Target |
|----|--------|--------|
| NF1 | graph.json load time (5000 nodes) | < 500ms |
| NF2 | Query latency (traverse + decay compute) | < 100ms |
| NF3 | Memory usage (10k nodes in memory) | < 500 MB |
| NF4 | File size growth per session | < 5 KB |
| NF5 | Graphify sync time (walter-worker size) | < 30s |

---

## 5. Test Data

### 5.1 Sample Session Transcript (minimal)

```
Tool: Write
Input: {"file_path": "src/auth.py", "content": "def authenticate(token): ..."}
Result: File created

Tool: Bash
Input: curl http://localhost:8080/api/status -H "Authorization: Bearer test"
Result: HTTP 200 {"status": "ok"}
```

LLM should extract:
- node: `src/auth.py::authenticate` (type=code)
- edge: `session_N::attempt_bearer → src/auth.py::authenticate` (relation=modifies)

### 5.2 Sample Graphify Output (minimal)

```json
{
  "nodes": [
    {"id": "src/auth.py::authenticate", "label": "authenticate", "file_type": "code", "source_file": "src/auth.py"}
  ],
  "links": [
    {"source": "src/auth.py::authenticate", "target": "src/dashboard/app.py::dashboard_app", "relation": "calls", "confidence": "EXTRACTED"}
  ]
}
```

### 5.3 Merge Operation

```python
def test_merge_preserves_weights():
    my_graph = load_graph("test_fixtures/my_graph.json")
    graphify_new = load_graph("test_fixtures/graphify_new.json")

    merged = sync_graphify_skeleton(my_graph, graphify_new)

    # Existing edge keeps its weight
    assert merged["links"][0]["base_weight"] == 0.8
    assert merged["links"][0]["last_traversed_at"] == "2026-01-15T00:00:00Z"
    # New edge is added
    assert len(merged["links"]) == len(my_graph["links"]) + len(graphify_new["links"])
```
