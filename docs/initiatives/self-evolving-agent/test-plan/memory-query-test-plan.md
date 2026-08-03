# Memory Query System — Test Plan

## Background

After the memory query code refactoring, two core scenarios need verification:
1. **Query quality**: Search "how to update or change a skill" → find skill update conventions (update → grade install)
2. **Subagent using experience**: Create a subagent, give it a task → verify it retrieves and uses past experience

## Test Environment

- mem0 data: skill creation conventions, naming conventions, bug fix patterns (3018 graph nodes, 5571 edges)
- mem0 search results: skill-related queries score 0.50-0.87
- New code features: min_score filtering, token budget, decay suppression, MCP server fix

---

## Test 1: Query "how to update or change a skill"

### Purpose
Verify memory query returns high-quality skill update memories via min_score quality filtering + token budget.

### Test Points

| # | Test | Expected |
|---|------|------|
| 1.1 | Query skill update with min_score=0.3 | Returns multiple results (loose filter) |
| 1.2 | Query skill update with min_score=0.7 | Returns only high-quality results, count drops significantly |
| 1.3 | Query with budget=500 | Results truncated by token budget |
| 1.4 | Query with budget=None | Returns full top_k results |
| 1.5 | Verify results contain "skill" vocabulary | At least 50% of results contain "skill"/"update"/"convention" |
| 1.6 | Verify low-score results filtered | Results with score < min_score not present |

---

## Test 2: Subagent Using Past Experience

### Purpose
Verify a subagent, when given a task, can search and apply past experience from memory.

### Scenario
Give subagent the task: "Create a new CLI command skill for walter-worker"
1. Subagent should first call search_memory for "skill creation" experience
2. Found conventions include: create SKILL.md in skill-factory/personal-skills/, write design spec, update all references
3. Subagent should reflect these conventions in its approach

### Test Points

| # | Test | Expected |
|---|------|------|
| 2.1 | search_memory("skill creation convention") returns results | At least 1 result with score > 0.7 |
| 2.2 | Results contain SKILL.md path convention | Memory text contains "skill-factory/personal-skills" |
| 2.3 | Results contain design spec convention | Memory text contains "design spec" or "docs/" |
| 2.4 | min_score=0.7 still has valid results | High-quality filter doesn't lose relevant results |
| 2.5 | Subagent calls search_memory via MCP tool | JSON-RPC tools/call returns correct results |

---

## Test 3: Graph Query

### Purpose
Verify graph search results follow graphify standards (token budget, BFS depth, decay suppression).

| # | Test | Expected |
|---|------|------|
| 3.1 | query(mode="graph") returns nodes | Returns graph nodes |
| 3.2 | budget=500 cuts results | Results within token budget |
| 3.3 | All graph results tagged source="graph" | Verify source tag |
| 3.4 | path_weight descending | Results sorted by depth, path_weight |

---

## Execution Steps

1. Write unit tests → `tests/memory/test_query_quality.py`
2. Write integration tests → `tests/memory/test_memory_integration.py`
3. Write subagent tests → `tests/memory/test_subagent_memory.py`
4. Run all tests
5. Generate execution report

## Expected Results

- Test 1: All min_score/budget assertions pass, quality filtering effective
- Test 2: Subagent retrieves and references past experience
- Test 3: Graph results follow graphify standards
