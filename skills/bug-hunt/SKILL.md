---
name: bug-hunt
version: 0.1.0
description: Root cause investigation — from quick code bug to multi-service outage. Hypothesis-driven, no guessing.
triggers:
- debug
- investigate
- oncall
- deep-dive
- sleuth
when-to-use: Root cause investigation — from quick code bug to multi-service outage. Hypothesis-driven, no guessing.
aliases:
- debug
- investigate
- oncall
- deep-dive
- sleuth
user-invocable: true
---
# Bug Hunt

Find and fix the root cause. Two modes depending on scope.

## Choose Mode

### Mode 1: Quick Debug
Known code bug, single service, stack trace available.

1. **Collect** — gather ALL potentially relevant info before analyzing:
   - Error message + full stack trace
   - Failing test or reproduction steps
   - Recent git log (what changed?)
   - Related logs, config values, env differences
   - Any user reports or messages about the issue
   - Do NOT filter or judge relevance yet — grab everything

2. **Reason** — list evidence and form hypotheses:
   - List each piece of evidence found
   - 3-5 possible root causes, ranked by likelihood
   - Link each hypothesis to specific evidence

3. **Test** — test each hypothesis, stop when confirmed
4. **Fix** — minimal fix + regression test
5. **Document** — commit: "fix: {desc} — root cause: {cause}"

### Mode 2: Deep Investigation
Unknown cause, multi-service, production outage, on-call.

1. **Collect** — exhaust all data sources before forming theories:
   - Logs (all services, around the incident window)
   - Git log / recent PRs / deployments
   - Metrics, dashboards, alerts
   - Messages: Slack, on-call pings, user reports
   - Config changes, env diffs, infra changes
   - Everything. Don't filter yet.

2. **Reason** — build evidence list and timeline:
   - List every finding from step 1
   - Highlight anomalies: "this log line doesn't belong", "this metric spiked"
   - Build timeline of events
   - Form hypotheses linked to evidence

3. **Investigate** — follow leads, verify root cause
4. **Report** — structured report: problem, evidence, root cause, fix, prevention
5. **Issue** — create GitHub Issue with the report

## Investigation Report Format (Mode 2)

```markdown
## Investigation Report

**Problem:** {description}
**Duration:** {start} → {end or ongoing}
**Impact:** {affected users/systems}

## Root Cause
{precise description}

## Evidence
1. {evidence}
2. {evidence}

## Timeline
| Time | Event |
|------|-------|
| T1   | {event} |
| T2   | {event} ← root cause here |

## Fix
{what to do}

## Prevention
{how to prevent recurrence}
```

## Rules

- Never guess — every fix backed by evidence
- Never fix symptoms instead of root cause
- Never add workarounds for code you don't understand
- Always add a regression test
- If pattern is generalizable → log self-heal trace
- Use strongest model for complex investigations
