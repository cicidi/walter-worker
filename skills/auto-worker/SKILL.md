---
name: auto-worker
version: 0.2.0
description: "Use when running autonomous QA — the 乙方 (builder) that fixes issues found by find-issues (甲方 inspector). Runs health checks, executes fixes, verifies repairs, and reports. Works in a closed loop with find-issues: inspect, fix, verify, repeat. NOT a deterministic script."
triggers:
  - auto-worker
  - "run --loop"
  - autonomous
when-to-use: "Use when running autonomous QA or when find-issues has discovered issues to fix."
---

# Auto-Worker — 乙方 (Builder)

> **Closed-loop: 甲方 (find-issues) inspects → 乙方 (auto-worker) fixes → 甲方 verifies → loop**

## Two-Role System

```
┌─────────────────────────────────────────────────────┐
│                 Autonomous QA Loop                   │
│                                                      │
│  🔍 find-issues (甲方质检)                            │
│  ├─ Read PRD/spec → find gaps                        │
│  ├─ WebSearch GitHub/Reddit/Google → best practices  │
│  ├─ DeepSeek v4 deep analysis → ranked improvements  │
│  └─ Output: issues-found-YYYY-MM-DD.md               │
│                         │                            │
│                         ▼                            │
│  🔧 auto-worker (乙方) ← YOU ARE HERE                 │
│  ├─ Read issues-found-*.md                           │
│  ├─ Health checks (tests, dashboard, frontend)       │
│  ├─ Fix auto-fixable issues                          │
│  ├─ Verify fixes                                     │
│  └─ Report: auto-worker-YYYY-MM-DD-state.md          │
│                         │                            │
│                         ▼                            │
│                    🔄 LOOP                            │
└─────────────────────────────────────────────────────┘
```

## Workflow

### Step 1: Read Issues
```bash
cat docs/self-evolving-agent/state/issues-found-*.md | tail -100
```
Identify auto-fixable items (bugs, missing tests, broken APIs, frontend issues).

### Step 2: Health Checks
Run these every round — they're the baseline:
1. `pytest tests/python/ -q --tb=no` — all tests must pass
2. Dashboard API endpoints — all must return data
3. Frontend integrity — JS init call, CSS expand classes
4. Circuit breaker — must not be tripped
5. Wrong-history prevention rules — must be followed

### Step 3: Fix Issues
For each auto-fixable issue from find-issues:
- Read the relevant code
- Fix the bug / add the missing test / wire the endpoint
- Commit with `fix:` prefix

### Step 4: Verify
- Re-run the specific test that was failing
- Re-check the API endpoint that was 404
- Verify the fix in the dashboard

### Step 5: Report
Write to `docs/self-evolving-agent/state/auto-worker-YYYY-MM-DD-state.md`:
```markdown
## Round N — HH:MM UTC
- Fixed: X issues (list)
- Verified: Y fixes confirmed
- Health: tests/dashboard/frontend/circuit all OK
- Remaining: Z issues need human review
```

## Integration with find-issues

| Role | Tool | Frequency |
|------|------|-----------|
| 🔍 甲方 Inspector | `/find-issues` | Every 30 min |
| 🔧 乙方 Builder | `/auto-worker` | Every 10 min |

The auto-worker reads the issues file from find-issues. If no issues file exists, run a health check only. If issues exist, fix them.

## Auto-Fixable Issues (examples)

| Issue Type | Can Auto-Fix? |
|-----------|---------------|
| Missing test for new code | ✅ Yes |
| Broken API endpoint (404) | ✅ Yes |
| Dashboard JS missing init call | ✅ Yes |
| Circuit breaker tripped | ✅ Yes (reset) |
| Typo in error message | ✅ Yes |
| Missing spec implementation | ⚠️ Partial (can scaffold) |
| Design-level architecture change | ❌ No (needs human) |
| PRD scope decision | ❌ No (needs human) |

## CLI

```bash
coworker run --loop --max-hours 12    # Continuous agent loop
coworker memory refresh               # Refresh CLAUDE.local.md snapshots
```

## Anti-Patterns

- **DO NOT** just run a Python script and call it done
- **DO NOT** skip reading the find-issues output
- **DO NOT** claim "nothing to fix" without checking the issues file
- **DO** use Grep, Bash, Read, Glob for actual investigation
- **DO** fix issues with real code changes, not comments

## Related

- `/find-issues` — 甲方质检员 (issue discovery)
- `/wrong-history` — Record mistakes so they never repeat
- `docs/self-evolving-agent/state/issues-found-*.md` — Issue backlog

## Sources

- Spec: `docs/self-evolving-agent/spec/self-evolving-agent-spec.md` §12
- Engine: `src/coworker/autoworker/engine.py` (AutoWorkerAgent)\n- CLI: `src/coworker/cli_autoworker.py` (register_autoworker)
- Rules: `src/coworker/autoworker/rules.py`
