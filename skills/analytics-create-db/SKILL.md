---
name: analytics-create-db
version: 0.1.0
description: Initialize the analytics SQLite database at ~/.coworker/analytics/analytics.db
triggers:
- analytics-create-db
- create analytics db
- setup analytics database
when-to-use: When user needs to initialize the analytics SQLite database
license: MIT
compatibility: claude-code,opencode,gemini
user-invocable: true
---
# analytics-create-db

Initialize the analytics SQLite database.

## Usage

```bash
coworker analytics create-db
```
