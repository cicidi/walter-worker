---
date: 2026-07-28
session_id: 
severity: high
category: code-quality
tags: []
---

# find-issues command always fails on code phase due to 120s test timeout

**What happened:** find-issues run --phases all always crashed with TimeoutExpired before writing output file

**Root cause:** Hardcoded timeout=120 in subprocess.run for pytest, but full suite takes 300-370s

**How it was discovered:** auto-worker health check

**Impact:** Unknown — auto-detected

**Fix:** Increased timeout to 600s and added pass/fail count extraction

**Prevention rule:** When running subprocess for full test suite, timeout must be >= 600s (tests take 5-6 min)

**Anti-pattern:** Not following the prevention rule above

**Related entries:**
