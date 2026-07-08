---
name: bug-report
version: 0.1.0
description: Create a GitHub Issue on any repo — bugs, features, coworker system issues. Reads project catalog for repos.
triggers:
- new-issue
- create-issue
- report-bug
- issue
- report
when-to-use: Create a GitHub Issue on any repo — bugs, features, coworker system issues. Reads project catalog for repos.
aliases:
- new-issue
- create-issue
- report-bug
- issue
- report
---

# Bug Report

Create a structured GitHub Issue. Covers project bugs, coworker system issues, and feature requests.

## When to Use

- User reports a bug or unexpected behavior
- Coworker system itself malfunctions
- Feature request that needs discussion
- Any non-trivial change before code

## Process

### 1. Pick Repo

```
→ Check if coworker project catalog has GitHub repos
→ List available: "Report to which repo?"
  1. {current project} (default)
  2. ai-coworker
  3. skill-factory
  4. Other (enter owner/repo manually)
→ Default: current project's repo
```

### 2. Detect Scope

```
→ Is this a code bug? → label: bug
→ Coworker system issue? → label: coworker
→ Feature request? → label: enhancement
```

### 3. Gather Context

```
→ What happened vs what was expected?
→ Steps to reproduce (if bug)
→ Relevant files, error messages
→ Affected project/repo
```

### 4. Title

```
fix: {short description}    (for bugs)
feat: {short description}   (for features)
```

### 5. Create on GitHub

```bash
gh issue create \
  --repo {owner}/{repo} \
  --title "fix: {description}" \
  --body "{body}" \
  --label "{labels}"
```

### 6. If AI Mistake

Log self-heal trace and note in issue body.

## Rules

- One issue per problem
- Fill in all sections before creating
- Always assign yourself
- Never skip the issue for non-trivial changes
