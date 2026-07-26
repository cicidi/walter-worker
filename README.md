# AI Coworker

**Project context and memory manager for AI coding assistants.**

AI Coworker keeps your IDE (Claude Code, OpenCode, Gemini) aware of your project structure, active initiatives, and available skills. It auto-scans projects, injects context into your AI's config, and connects to [skill-factory](https://github.com/cicidi/skill-factory) for skill lifecycle management.

It also records your AI sessions (SQLite-backed) — tracking which skills get used, how often, and what patterns emerge — building the data foundation for an autonomous coding agent.

## Self-Evolving Agent (new in feat/self-evolving-agent)

The **self-evolving agent** learns from every session and gets smarter over time:

- **🧠 Cross-session memory** — mem0-powered vector store remembers lessons, patterns, and conventions across sessions
- **📊 Analytics dashboard** — 16-tab web UI with Projects, Models, Cost/Token, Efficiency, Evolution, and Data Quality views
- **🔍 Auto-inspection** — `coworker find-issues` audits code against PRD/spec and finds gaps
- **🔧 Auto-repair** — `coworker run --loop` continuously fixes bugs, runs tests, and maintains health
- **⚡ Per-turn capture** — PostToolUse hooks extract lessons in real-time ($0.0004/turn)
- **🔒 Safety gates** — Circuit breaker prevents runaway auto-evolution (>3 skills/24h)
- **📝 Wrong-history** — Records mistakes so the agent never repeats them

| IDE | Support |
|-----|---------|
| Claude Code | Full — config sync, skills, context injection, analytics |
| OpenCode | Config + skills + context injection |
| Gemini | Settings / MCP config only |

## What It Does

- **Auto-scan** projects — detect language, framework, dependencies, IDEs
- **Inject context** into CLAUDE.md — project catalog, initiative status, docs structure
- **Manage initiatives** — cross-project work with decisions, links, project scope
- **Track projects** — catalog with upstream/downstream relationships, knowledge pools
- **Sync skills** from config to all installed IDEs
- **Record sessions** — sessions are stored in SQLite; dashboard for browsing
- **Road to autonomy** — data foundation for building an auto-coding agent

## What It Doesn't Do

- Write code or follow a development pipeline
- Create or edit skills (that's [skill-factory](https://github.com/cicidi/skill-factory))
- Implement OWASP guardrails or code review (those are skills you get from skill-factory)

## Install

```bash
git clone https://github.com/cicidi/ai-coworker.git ~/ai-coworker
cd ~/ai-coworker
pipx install .           # or: python3 -m venv .venv && source .venv/bin/activate && pip install -e .
```

After installing the Python package, run the setup script to wire analytics hooks and IDE integration:

```bash
bash setup/install.sh --global
```

## Usage

```bash
coworker init              # Auto-scan project, generate config + CLAUDE.md context
coworker sync              # Sync config to all detected IDEs
coworker status            # Show current config status

# Project catalog
coworker project add       # Add a project to the catalog
coworker project list      # List all tracked projects
coworker project sync      # Inject catalog into IDE configs

# Initiatives (cross-project work)
coworker initiative start  # Create, add project, activate in one step
coworker initiative list   # List all initiatives

# Analytics
coworker analytics create-db   # Initialize session tracking database
coworker analytics dashboard   # View session stats
```

## How Context Injection Works

AI Coworker writes managed sections into your `CLAUDE.md` (or `instructions.md` for OpenCode):

```markdown
# Your CLAUDE.md — user-written content stays untouched

<!-- COWORKER:STATIC START -->
## Project Catalog
| Project | Path | Upstream | Downstream |
|---------|------|----------|------------|
| ai-coworker | ~/ai-coworker | - | skill-factory |

## Docs Directory Structure
...

## Coworker Skills
Prefer coworker skills for repeatable workflows...
<!-- COWORKER:STATIC END -->
```

When you activate an initiative:
```markdown
<!-- INITIATIVE:skill-migration START -->
## Active Initiative: skill-migration
> Migrate all skills from ai-coworker to skill-factory
...
<!-- INITIATIVE:skill-migration END -->
```

Your content outside these comment blocks is never modified.

## Skill Management

Skills are created and edited in the [skill-factory source repo](https://github.com/cicidi/skill-factory), then deployed to IDE configs:

| Task | Tool |
|------|------|
| Create a skill | skill-factory `skill-create` |
| Edit a skill | skill-factory `skill-edit` |
| Import external skill | skill-factory `skill-import` |
| List/install skills | `coworker sync` |

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test suites
python -m pytest tests/python/test_models.py -v
python -m pytest tests/python/test_config.py -v
python -m pytest tests/python/test_injection.py -v
python -m pytest tests/python/test_cli.py -v
python -m pytest tests/python/test_skill_factory_integration.py -v
```

## License

MIT

## Roadmap (not shipped yet)

- **Token/cost tracking** — per-session token counts and cost estimates
- **Knowledge extraction** — LLM-driven session summaries: extract reusable insights into SQLite + Obsidian
- **Gemini full support** — context injection and skill sync for Gemini CLI
- **Cursor adapter** — config sync and context injection for Cursor
