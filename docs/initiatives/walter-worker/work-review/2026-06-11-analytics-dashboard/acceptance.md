# Analytics Dashboard — Acceptance Review

## Acceptance Criteria

### MUST (block)

| # | Criteria | Source | Line |
|---|----------|--------|------|
| AC01 | DB schema has 8 tables (sessions, messages, tool_calls, file_ops, session_stats, skills, knowledge, session_summaries) | analytics-listener-design.md:§7.1 | MUST |
| AC02 | Import script merges pre+post tool calls, extracts file_ops, aggregates skills | analytics-listener-design.md:§7.2 | MUST |
| AC03 | Dashboard backend exposes REST API: /api/overview, /api/sessions, /api/sessions/{id}, /api/skills, /api/tools, /api/files, /api/knowledge, /api/initiatives | dashboard-prd.md:Overview | MUST |
| AC04 | Dashboard frontend renders 7 sidebar views (overview, sessions, skills, tools, files, knowledge, initiatives) | dashboard-prd.md:§Dashboard Views | MUST |
| AC05 | Session detail view shows messages + tool calls + file ops + summary | dashboard-prd.md:View 10 | MUST |
| AC06 | E2E pipeline test passes: generate data → import → DB query → API response | plan.md:§Verification | MUST |

### SHOULD

| # | Criteria | Source | Line |
|---|----------|--------|------|
| AC07 | OpenCode plugin records session events via @opencode-ai/plugin hooks | analytics-listener-design.md:§5 | SHOULD |
| AC08 | Claude Code hook scripts record UserPromptSubmit, PreToolUse, PostToolUse, Stop | analytics-listener-design.md:§4 | SHOULD |
| AC09 | Professional dark-themed UI matching Grafana/SigNoz style | User requirement | SHOULD |
| AC10 | Knowledge Skill SKILL.md exists with summarize/analyze triggers | knowledge-skill-prd.md | SHOULD |

### NICE

| # | Criteria | Source | Line |
|---|----------|--------|------|
| AC11 | Test data generator creates 20 realistic sessions | plan.md:Task 9 | NICE |
| AC12 | Installer sets up hooks + DB out-of-box | plan.md:Task 5 | NICE |

## Test Plan

| # | Test | Type | Steps | Expected |
|---|------|------|-------|----------|
| T01 | Full pipeline E2E | UT | pytest tests/analytics/test_e2e_setup.py::test_full_pipeline | PASS — 5 sessions, all tables >0 rows |
| T02 | Dashboard API E2E | UT | pytest tests/analytics/test_e2e_setup.py::test_dashboard_api | PASS — 8 endpoints return 200 |
| T03 | DB idempotent init | UT | pytest tests/analytics/test_e2e_setup.py::test_db_idempotent | PASS — double init does not fail |
| T04 | Dashboard loads HTML | Manual | curl http://localhost:8080/ | Returns HTML with Coworker Dashboard title |
| T05 | API overview returns data | Manual | curl http://localhost:8080/api/overview | Returns JSON with sessions/messages/tools counts |
| T06 | Frontend assets served | Manual | curl http://localhost:8080/dashboard.js | Returns JS file |

## Regression Guard

| # | Test | Command |
|---|------|---------|
| R01 | Existing tests still pass | PYTHONPATH=. pytest tests/python/ -v |
| R02 | No import breaks | PYTHONPATH=. python3 -c "from src.coworker.analytics.db import init_db" |
