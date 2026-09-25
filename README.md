<img src="pic/walter-worker-logo.png" alt="Walter Worker" width="100%">

# walter-worker

**Claude Code context and memory manager.** walter-worker manages your CLAUDE.md, records every session, tracks file I/O and skill usage, and builds cross-session memory — all through slash commands inside Claude Code.

---

## What It Tracks

| Signal | Skill | What It Does |
|--------|-------|---------------|
| **CLAUDE.md** | `/project` `/feature` `/status` | Auto-generates project catalog, features, docs structure into CLAUDE.md managed blocks |
| **Sessions** | `/dashboard` | Every Claude session recorded: messages, tool calls, duration, project |
| **File I/O** | `/dashboard` | Files read/written per session — spot hot files, churn, accidental writes |
| **Skills** | `/dashboard` | Which slash commands get used, how often, by which project |
| **Memory** | `/memory` `/knowledge` | Cross-session vector recall — lessons, patterns, wrong-history, knowledge graph |
| **Cost & Tokens** | `/dashboard` | Per-session, per-model token counts and cost estimates |

## Install

```bash
git clone https://github.com/cicidi/walter-worker.git ~/walter-worker
cd ~/walter-worker
pipx install ".[memory]"      # [memory] pulls the vector-memory dependencies
bash setup/install.sh --global
```

Without the `[memory]` extra the CLI installs and `/dashboard`, `/project`,
`/feature` and `/status` work, but `/memory` and `/knowledge` fail at import
with `No module named 'openai'`.

`setup/install.sh` edits your global AI-tool configuration: it merges hooks into
`~/.claude/settings.json`, writes `~/.claude/CLAUDE.md`, and installs skills
under `~/.claude/`, `~/.config/opencode/` and `~/.cursor/`. It only rewrites the
regions it manages between its own markers, and `bash setup/uninstall.sh`
reverses it.

### Configure memory

`/memory` and `/knowledge` need an LLM key. Without one they stop with
`No LLM provider configured`. Set at least one:

```bash
export DEEPSEEK_API_KEY=...     # preferred
# fallback: GEMINI_API_KEY (the only one implemented)
```

Put it in `~/.coworker/.env` to make it persistent. Memory search also uses
[graphify](https://github.com/cicidi/graphify) for scoring when present; it has
no PyPI distribution, is optional, and search falls back to a simpler ranking
without it.

## Usage

walter-worker runs inside Claude Code. Everything is a `/skill`:

**CLAUDE.md & context:**
```
/project          # Add, list, sync projects — auto-injects into CLAUDE.md
/feature       # Create, activate, manage cross-project features
/status           # Show what's configured and active
```

**Memory & knowledge:**
```
/memory           # Search past sessions, knowledge graph, wrong-history
/knowledge        # Extract insights from sessions → memory cards
```

**Analytics:**
```
/dashboard        # Setup → Import → Launch web UI (http://localhost:8080)
```

General-purpose dev skills (`/auto-tdd`, `/bug`, `/wayfinder`, `/research`, …) come from **[the-super-lab](https://github.com/cicidi/the-super-lab)**.

## How CLAUDE.md Works

walter-worker writes into managed comment blocks — your own content is never touched:

```markdown
<!-- COWORKER:STATIC START -->
## Project Catalog
| Project | Path | Upstream | Downstream |
|---------|------|----------|------------|
| walter-worker | ~/walter-worker | — | the-super-lab |
<!-- COWORKER:STATIC END -->

<!-- FEATURE:self-evolving-agent START -->
## Active Feature: self-evolving-agent
<!-- FEATURE:self-evolving-agent END -->
```

## Skill Management

**Operational skills** — `/dashboard` `/feature` `/project` `/memory` `/knowledge` `/status` — live here.

**Development skills** — `/auto-tdd` `/bug` `/wayfinder` `/to-spec` `/implement` … — live in **[the-super-lab](https://github.com/cicidi/the-super-lab)**.

## Testing

```bash
pip install -e ".[test]"
python -m pytest tests/ -v
```

Tests that need `[memory]`, a `DEEPSEEK_API_KEY`, or a checkout of
the-super-lab skip when those are absent, so the suite passes on a clean machine.

## Built On

**Runtime dependencies**

| Project | Role |
|---------|------|
| **[mem0](https://github.com/mem0ai/mem0)** | Vector memory — cross-session recall |
| **[graphify](https://github.com/cicidi/graphify)** | Optional scoring engine for memory search |

**Skills** come from **[the-super-lab](https://github.com/cicidi/the-super-lab)**.

**Research references** — read while designing this, not depended on:

| Project | Role |
|---------|------|
| **[Guild AI](https://github.com/mathomhaus/guild)** | Multi-agent orchestration |
| **[Jam](https://github.com/Dag7/jam)** | Browser MCP agent reference |
| **[Pioneer](https://agent.pioneer.ai)** | Self-evolving agent research |

## License

MIT
