# Core Architecture Design

<!-- PROTECTED -->
Project: ai-coworker
Last Updated: 2026-06-11
<!-- END PROTECTED -->

## Architecture Overview

```
[coworker CLI] → [Config Manager] → [IDE Adapters]
                      ↓                    ↓
              [coworker.yaml]      [Context Injection]
              [.mcp.json]               ↓
              [project.yaml]     [CLAUDE.md / instructions.md]
              [initiatives/<name>.yaml]
                      ↓
              [Claude Code / OpenCode / Gemini / Cursor]
```

Single Python CLI that reads YAML config and propagates skills, MCP servers, permissions, and initiative context to target IDEs.

## Tech Stack

| Layer | Technology | Reason |
|-------|-----------|--------|
| CLI framework | Click | Rich terminal UI, composable commands |
| Data models | Pydantic 2 | Strict schema validation for YAML config |
| Config format | YAML | Human-readable, existing ecosystem |
| Output formatting | Rich | Tables, panels, progress bars |
| Package manager | setuptools/pyproject.toml | Python standard |

## Data Model

**coworker.yaml** — source of truth for:
- MCP servers (name, command, args, env)
- Skills (name, source path, triggers)
- Permissions (tool allow/deny rules)
- Tool overrides (custom configurations per IDE)

**Project Catalog** (`~/.coworker/project.yaml`):
- List of all projects with paths, upstream/downstream relationships, knowledge pools

**Initiatives** (`~/.coworker/initiatives/<name>.yaml`):
- Per-workstream config: branches, decisions, links, reference docs

## Context Injection API

Static context (project catalog) and dynamic initiative context are injected into IDE instruction files via HTML comment markers:

| Function | Target | Block Type |
|----------|--------|-----------|
| `inject_static_context(catalog)` | CLAUDE.md, instructions.md | `<!-- COWORKER:STATIC START/END -->` |
| `inject_initiative(config)` | CLAUDE.md, instructions.md | `<!-- INITIATIVE:<name> START/END -->` |
| `remove_initiative()` | CLAUDE.md, instructions.md | Removes all initiative blocks |

**InitiativeManager** (`src/coworker/initiatives/manager.py`) orchestrates CRUD and activation:
- `create(name, description)` — validates kebab-case, creates YAML
- `edit(name, **updates)` — partial update of any field
- `activate(name)` / `deactivate()` — injects/removes context from both Claude and OpenCode
- `inject_static_context()` — writes project catalog to all IDE instruction files

See `tests/python/test_injection.py` for test coverage.

## IDE Adapters

| Adapter | Targets | Key Behavior |
|---------|---------|-------------|
| `adapters/claude.py` | `~/.claude/commands/`, `settings.local.json` | Context injection via HTML comments in CLAUDE.md |
| `adapters/opencode.py` | `~/.opencode/instructions/` | Config sync + context injection in instructions.md |
| `adapters/gemini.py` | `~/.gemini/` | Config sync |
| `adapters/cursor.py` | `.cursor/rules/` | Symlinks from Claude |

## Security Design

- No auth — single developer, local machine
- Secrets in env vars only (`coworker.yaml` references `$ENV_VAR`)
- `.local_config.yaml` gitignored (identity, project name)
- `.env` gitignored
- No network calls in core sync (all local file operations)

## Open Questions

- [ ] Docker/devcontainer support for portable setup
