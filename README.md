<img src="pic/walter-worker-logo.png" alt="Walter Worker" width="100%">

# walter-worker

**Claude Code context and memory manager.** walter-worker manages your CLAUDE.md, records every session, tracks file I/O and skill usage, and builds cross-session memory — all through slash commands inside Claude Code.

---

## What It Tracks

| Signal | Skill | What It Does |
|--------|-------|---------------|
| **CLAUDE.md** | `/project` `/initiative` `/status` | Auto-generates project catalog, initiatives, docs structure into CLAUDE.md managed blocks |
| **Sessions** | `/dashboard` | Every Claude session recorded: messages, tool calls, duration, project |
| **File I/O** | `/dashboard` | Files read/written per session — spot hot files, churn, accidental writes |
| **Skills** | `/dashboard` | Which slash commands get used, how often, by which project |
| **Memory** | `/memory` `/knowledge` | Cross-session vector recall — lessons, patterns, wrong-history, knowledge graph |
| **Cost & Tokens** | `/dashboard` | Per-session, per-model token counts and cost estimates |

## Install

```bash
git clone git@github.com:cicidi/walter-worker.git ~/walter-worker
cd ~/walter-worker
pipx install .
bash setup/install.sh --global
```

## Usage

walter-worker runs inside Claude Code. Everything is a `/skill`:

**CLAUDE.md & context:**
```
/project          # Add, list, sync projects — auto-injects into CLAUDE.md
/initiative       # Create, activate, manage cross-project initiatives
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

<!-- INITIATIVE:self-evolving-agent START -->
## Active Initiative: self-evolving-agent
<!-- INITIATIVE:self-evolving-agent END -->
```

## Skill Management

**Operational skills** — `/dashboard` `/initiative` `/project` `/memory` `/knowledge` `/status` — live here.

**Development skills** — `/auto-tdd` `/bug` `/wayfinder` `/to-spec` `/implement` … — live in **[the-super-lab](https://github.com/cicidi/the-super-lab)**.

## Testing

```bash
python -m pytest tests/ -v
```

## Built On

| Project | Role |
|---------|------|
| **[the-super-lab](https://github.com/cicidi/the-super-lab)** | General-purpose development skills |
| **[graphify](https://github.com/cicidi/graphify)** | Code knowledge graph — scoring engine for memory search |
| **[mem0](https://github.com/mem0ai/mem0)** | Vector memory — cross-session recall |
| **[Guild AI](https://github.com/mathomhaus/guild)** | Multi-agent orchestration |
| **[Jam](https://github.com/Dag7/jam)** | Browser MCP agent reference |
| **[Pioneer](https://agent.pioneer.ai)** | Self-evolving agent research |

## License

MIT
