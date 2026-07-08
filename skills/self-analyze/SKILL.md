---
name: self-analyze
version: 0.1.0
description: Scan project's .self-healing/traces/, find patterns, inject summary into CLAUDE.md
triggers:
- analyze-traces
- analyze
- self-improve
when-to-use: Scan project's .self-healing/traces/, find patterns, inject summary into CLAUDE.md
aliases:
- analyze-traces
- analyze
- self-improve
---

# Self-Analyze

Read project correction traces, find patterns, generate rules.

## Process

### 1. Load Traces

```
→ Read all .self-healing/traces/*.yaml
→ Parse correction entries
→ Group by category
→ Count frequency per normalized correction
```

### 2. Find Patterns

A pattern = same correction occurring 2+ times:

| Category | Correction | Count |
|----------|-----------|-------|
| code-conventions | never use git add . | 3 |
| workflow | always confirm before deleting | 2 |

### 3. Generate Summary

```markdown
<!-- SELF-ANALYZE START -->
## Self-Healing Insights ({date})

**Analyzed:** {N} traces over {M} days

### Patterns Found

- **{correction}** ({count}×) — {context}

### Rules Added
- {rule} → {file}

<!-- SELF-ANALYZE END -->
```

### 4. Inject into CLAUDE.md

```
→ Read project CLAUDE.md
→ If SELF-ANALYZE block exists → replace
→ If not → append at end
→ Write CLAUDE.md
```

### 5. Report

```
Self-analyze complete:
  {N} traces analyzed
  {M} patterns found
  {K} rules injected into CLAUDE.md
  Summary in <!-- SELF-ANALYZE --> block
```
