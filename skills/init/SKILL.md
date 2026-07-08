---
name: init
version: 0.1.0
description: Auto-scan project and generate config — detects language, dependencies, IDEs
triggers:
- init
- setup coworker
- initialize ai coworker
- coworker init
when-to-use: When setting up ai-coworker for a new project
license: MIT
compatibility: claude-code,opencode,gemini
---

# init

Auto-scan project and generate configuration.

## Usage

```bash
coworker init
```

CLI will:
1. Scan the project for language, framework, dependencies
2. Detect installed IDEs
3. Show findings for confirmation
4. Generate `coworker.yaml`
5. Generate/update `CLAUDE.md` with Project Context

After init, run `coworker sync` to apply.
