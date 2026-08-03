<img src="pic/walter-worker-logo.png" alt="Walter Worker" width="100%">

# walter-worker

**Claude Code context and memory manager.** walter-worker auto-generates your CLAUDE.md, records every session, tracks which files your AI reads and writes, measures skill usage, and builds cross-session memory so your AI assistant stops forgetting.

---

## What It Tracks

| Signal | Why It Matters |
|--------|---------------|
| **CLAUDE.md** | Auto-generates project catalog, initiative status, docs structure — injected into managed comment blocks so the AI always knows what project it's in |
| **Sessions** | Every Claude session recorded: messages sent, tool calls made, duration, project context |
| **File I/O** | Which files the AI reads and writes — spot hot files, track churn, catch accidental writes |
| **Skills** | Which slash commands get used, how often, by which project — measure what's actually useful |
| **Memory** | Cross-session vector recall — lessons, patterns, wrong-history are stored and searchable via `/memory` |
| **Cost & Tokens** | Per-session, per-model token counts and cost estimates |

## Install

```bash
git clone git@github.com:cicidi/walter-worker.git ~/walter-worker
cd ~/walter-worker
pipx install .
bash setup/install.sh --global
```

After install, walter-worker hooks into Claude Code's session lifecycle — every session gets recorded automatically.

## How CLAUDE.md Management Works

walter-worker writes into managed comment blocks inside your `CLAUDE.md` — **your own content outside these blocks is never touched:**

```markdown
# Your CLAUDE.md — your content lives here, untouched

<!-- COWORKER:STATIC START -->
## Project Catalog
| Project | Path | Upstream | Downstream |
|---------|------|----------|------------|
| walter-worker | ~/walter-worker | — | the-super-lab |
<!-- COWORKER:STATIC END -->

<!-- INITIATIVE:self-evolving-agent START -->
## Active Initiative: self-evolving-agent
> Ship an autonomous agent that self-evolves in a continuous loop
<!-- INITIATIVE:self-evolving-agent END -->
```

Run `coworker sync` to push the latest project catalog, active initiatives, and docs structure into your IDE config.

## Usage

All interaction is through Claude Code slash commands:

**CLAUDE.md & project context:**
```bash
/initiative        # Cross-project work tracking — start, activate, list initiatives
/project           # Manage project catalog — add repos, set upstream/downstream
/status            # Show what's configured and active right now
```

**Session memory & knowledge:**
```bash
/memory            # Search past sessions, knowledge graph, wrong-history entries
/knowledge         # Extract insights from sessions → memory cards (Obsidian + SQLite)
```

**Analytics & tracking:**
```bash
/dashboard         # Launch web UI → sessions, file I/O, skills, tokens, cost trends
```

General-purpose dev skills (`/auto-tdd`, `/bug`, `/wayfinder`, `/research`, …) live in **[the-super-lab](https://github.com/cicidi/the-super-lab)**.

## Analytics Dashboard

```bash
coworker analytics create-db     # Initialize tracking database
coworker analytics import        # Import recorded sessions
coworker analytics dashboard     # Launch at http://localhost:8080
```

16 tabs covering: Sessions · Projects · Models · Cost/Token · Efficiency · Skills · Tools · Files · Knowledge · Initiatives · Evolution · Hotspots · Errors · Memory · Data Quality

## Skill Management

**Operational skills** (dashboard, initiative, project, memory, knowledge, status) wrap `coworker` CLI commands and live in this repo.

**Development skills** (auto-tdd, bug, wayfinder, to-spec, implement, …) live in **[the-super-lab](https://github.com/cicidi/the-super-lab)**. `coworker sync` pulls from both.

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
