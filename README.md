<img src="pic/walter-worker-logo.png" alt="Walter Worker" width="100%">

# walter-worker

**walter-worker** gives your AI coding assistant context, skills, and memory so it stops forgetting between sessions.

---

## Install

```bash
git clone git@github.com:cicidi/walter-worker.git ~/walter-worker
cd ~/walter-worker
pipx install .
bash setup/install.sh --global
```

## Usage

walter-worker **runs inside Claude Code** — invoke skills with `/skill-name`:

```bash
/dashboard         # Analytics — session stats, cost trends, daemon
/initiative        # Cross-project work tracking
/project           # Manage project catalog
/memory            # Search past sessions & knowledge graph
/knowledge         # Extract insights from sessions → memory cards
/status            # Show config & initiative progress
```

General-purpose development skills (`/auto-tdd`, `/bug`, `/research`, `/wayfinder`, etc.) live in **[the-super-lab](https://github.com/cicidi/the-super-lab)**.

```bash
coworker sync          # Sync skills & config to all IDEs
coworker status        # Show what's configured
```

## Skill Management

**Operational skills** (dashboard, initiative, project, memory, knowledge, status) live here — they wrap `coworker` CLI commands.

**Development skills** (auto-tdd, bug, wayfinder, to-spec, implement, …) live in **[the-super-lab](https://github.com/cicidi/the-super-lab)**. `coworker sync` pulls from both.

## Analytics Dashboard

Every Claude session gets recorded. Browse usage patterns, skill effectiveness, and cost trends:

```bash
coworker analytics create-db     # Initialize tracking database
coworker analytics import        # Import session data
coworker analytics dashboard     # Launch at http://localhost:8080
```

Tabs: Sessions • Projects • Models • Cost/Token • Efficiency • Evolution • Data Quality

## Testing

```bash
python -m pytest tests/ -v
```

## How It Works

walter-worker writes into managed comment blocks inside your `CLAUDE.md` — your own content is never touched:

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

## Built On

| Project | What we use |
|---------|-------------|
| **[the-super-lab](https://github.com/cicidi/the-super-lab)** | General-purpose development skills |
| **[mem0](https://github.com/mem0ai/mem0)** | Vector memory layer — cross-session recall |
| **[Guild AI](https://github.com/mathomhaus/guild)** | Multi-agent orchestration patterns |
| **[Jam](https://github.com/Dag7/jam)** | Browser-based MCP agent reference |
| **[Pioneer](https://agent.pioneer.ai)** | Self-evolving agent research foundation |

## License

MIT
