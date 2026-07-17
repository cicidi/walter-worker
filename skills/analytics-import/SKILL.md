---
name: analytics-import
version: 0.1.0
description: Import session JSONL files into the analytics SQLite database
triggers:
- analytics-import
- import analytics data
- import sessions to db
when-to-use: When user needs to import session data into analytics
license: MIT
compatibility: claude-code,opencode,gemini
user-invocable: true
---
# analytics-import

Import raw session JSONL files into the analytics SQLite database.

## Usage

```bash
coworker analytics import
```
