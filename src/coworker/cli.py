from __future__ import annotations
import json
import sys
from pathlib import Path

import yaml
import click
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from .config import (
    GLOBAL_DIR, GLOBAL_CONFIG, PROJECT_CONFIG_NAME,
    load_global_config, load_project_config, merged_config, save_config,
    load_project_catalog, save_project_catalog,
    load_initiative, save_initiative, list_initiatives, initiative_exists,
)
from .models import (
    CoworkerConfig, ProjectEntry, ProjectRef, ProjectCatalog,
    InitiativeConfig, InitiativeProjectRef, LinkRef, Decision, ReferenceDoc,
    KnowledgePoolEntry,
)
from .adapters import ADAPTERS
from .initiatives.manager import InitiativeManager
from .templates.project_claude_md import generate_project_claude_md
from .templates.local_claude_md import generate_local_claude_md
from .templates.project_claude_md import PROJECT_CLAUDE_MD_SENTINEL
from . import backup

console = Console()

GLOBAL_CONFIG_TEMPLATE = """\
version: "1"
scope: global

# MCP Servers — shared across Claude Code, Gemini, OpenCode
mcp: []
  # - name: filesystem
  #   command: npx
  #   args: ["-y", "@modelcontextprotocol/server-filesystem", "/home"]
  #   enabled: true

# Skills — point to SKILL.md files or directories
skills: []
  # - name: commit
  #   path: skills/commit
  #   enabled: true

# Permissions (Claude Code)
permissions:
  allow:
    - Bash(git *)
    - Read(*)
    - Write(*)
  deny: []

# Claude Code specific settings
claude:
  effortLevel: medium
  skipDangerousModePermissionPrompt: false

# Gemini CLI specific settings
gemini:
  extra: {}

# OpenCode specific settings
opencode:
  extra: {}
"""

PROJECT_CONFIG_TEMPLATE = """\
version: "1"
scope: project

# Project-level MCP servers (merged with global)
mcp: []

# Project-level skills (merged with global)
skills: []

# Project permissions override global
permissions:
  allow: []
  deny: []
"""


@click.group()
def main():
    """Coworker — unified AI dev environment for Claude Code, Gemini & OpenCode."""
    pass


def _scan_project() -> dict:
    cwd = Path.cwd()
    info = {
        "project_name": cwd.name,
        "language": "unknown",
        "framework": [],
        "package_manager": None,
        "test_command": None,
        "lint_command": None,
        "ides": [],
        "repo_url": None,
        "deps": [],
        "doc_map": "",
        "relationships": "",
    }
    import subprocess
    try:
        r = subprocess.run(["git", "remote", "get-url", "origin"],
                          capture_output=True, text=True, cwd=str(cwd))
        if r.returncode == 0:
            info["repo_url"] = r.stdout.strip()
    except Exception:
        pass
    if (cwd / "package.json").exists():
        info["language"] = "Node.js"
        info["package_manager"] = "npm"
        try:
            pkg = json.loads((cwd / "package.json").read_text())
            deps = {}
            deps.update(pkg.get("dependencies", {}))
            deps.update(pkg.get("devDependencies", {}))
            info["deps"] = list(deps.keys())
            if "react" in deps: info["framework"].append("React")
            if "next" in deps: info["framework"].append("Next.js")
            if "express" in deps: info["framework"].append("Express")
            scripts = pkg.get("scripts", {})
            if "test" in scripts: info["test_command"] = "npm test"
            if "lint" in scripts: info["lint_command"] = "npm run lint"
        except Exception:
            pass
    elif (cwd / "pyproject.toml").exists():
        info["language"] = "Python"
        info["package_manager"] = "pip"
        info["test_command"] = "pytest"
        info["lint_command"] = "ruff"
        try:
            pyproject = (cwd / "pyproject.toml").read_text()
            if "fastapi" in pyproject.lower(): info["framework"].append("FastAPI")
            if "django" in pyproject.lower(): info["framework"].append("Django")
            if "flask" in pyproject.lower() and "flask" != pyproject.lower()[:100]: info["framework"].append("Flask")
            if "click" in pyproject.lower(): info["framework"].append("Click")
        except Exception:
            pass
    elif (cwd / "go.mod").exists():
        info["language"] = "Go"
        info["package_manager"] = "go mod"
        info["test_command"] = "go test ./..."
    elif (cwd / "Cargo.toml").exists():
        info["language"] = "Rust"
        info["package_manager"] = "cargo"
        info["test_command"] = "cargo test"
    home = Path.home()
    if (home / ".claude").exists(): info["ides"].append("claude")
    if (home / ".config/opencode").exists(): info["ides"].append("opencode")
    if (home / ".gemini").exists(): info["ides"].append("gemini")
    if (cwd / ".cursor").exists(): info["ides"].append("cursor")

    docs_dir = cwd / "docs"
    if docs_dir.exists():
        parts = []
        if (docs_dir / "specs").exists():
            parts.append("- Specs: `docs/specs/`")
        if (docs_dir / "discussion").exists():
            parts.append("- Discussions: `docs/discussion/`")
        info["doc_map"] = "\n".join(parts) if parts else "- `docs/` exists but no specs/discussion subdirectories"
    else:
        info["doc_map"] = "_`docs/` directory not found. Run `coworker init` to create._"

    try:
        catalog = load_project_catalog()
        current_path = str(cwd.resolve())
        rels = []
        for entry in catalog.projects:
            for ref in entry.upstream:
                rels.append(f"| {entry.name} | upstream | {ref.name} |")
            for ref in entry.downstream:
                rels.append(f"| {entry.name} | downstream | {ref.name} |")
        if rels:
            info["relationships"] = "\n".join(rels)
    except Exception:
        pass

    return info


def _build_project_claude_md(info: dict) -> str:
    """Generate project CLAUDE.md using canonical template."""
    return generate_project_claude_md(
        project_name=info.get("project_name", ""),
        repo=info.get("repo_url") or "",
        branch="main",
        relationships=info.get("relationships", ""),
        doc_map=info.get("doc_map", ""),
        team_links=info.get("team_links", ""),
    )


@main.command()
@click.option("--global", "is_global", is_flag=True, default=False, help="Init global config")
@click.option("--project", "is_project", is_flag=True, default=False, help="Init project config in cwd")
def init(is_global, is_project):
    """Initialize global or project config with auto-scan."""
    if not is_global and not is_project:
        is_global = click.confirm("Init global config (~/.coworker/)?", default=True)
        if not is_global:
            is_project = True

    if is_global:
        GLOBAL_DIR.mkdir(parents=True, exist_ok=True)
        skills_dir = GLOBAL_DIR / "skills"
        skills_dir.mkdir(exist_ok=True)
        if GLOBAL_CONFIG.exists():
            console.print(f"[yellow]Already exists:[/yellow] {GLOBAL_CONFIG}")
        else:
            GLOBAL_CONFIG.write_text(GLOBAL_CONFIG_TEMPLATE)
            console.print(f"[green]Created:[/green] {GLOBAL_CONFIG}")
        console.print(f"[dim]Skills dir:[/dim] {skills_dir}")

    if is_project:
        info = _scan_project()
        console.print(f"\n[bold]Project Scan:[/bold] {info['project_name']}")
        console.print(f"  Language:      {info['language']}")
        if info["framework"]:
            console.print(f"  Framework:     {', '.join(info['framework'])}")
        if info["deps"]:
            deps_show = info["deps"][:8]
            console.print(f"  Dependencies:  {', '.join(deps_show)}{'...' if len(info['deps']) > 8 else ''}")
        if info["repo_url"]:
            console.print(f"  Repo:          {info['repo_url']}")
        if info["ides"]:
            console.print(f"  Detected IDEs: {', '.join(info['ides'])}")
        console.print(f"  Test command:  {info['test_command'] or 'not detected'}")
        console.print(f"  Lint command:  {info['lint_command'] or 'not detected'}")

        if not click.confirm("\nCreate project config with these settings?", default=True):
            return

        project_config = Path.cwd() / PROJECT_CONFIG_NAME
        project_config.parent.mkdir(parents=True, exist_ok=True)
        project_config.write_text(PROJECT_CONFIG_TEMPLATE)
        console.print(f"[green]Created:[/green] {project_config}")

        claude_md = Path.cwd() / "CLAUDE.md"
        new_content = _build_project_claude_md(info)
        if claude_md.exists():
            content = claude_md.read_text()
            if PROJECT_CLAUDE_MD_SENTINEL in content:
                console.print("[yellow]CLAUDE.md already has project context, skipping generation.[/yellow]")
            else:
                backup.snapshot([claude_md], "init")
                claude_md.write_text(new_content)
                console.print(f"[green]Created:[/green] CLAUDE.md (with new template)")
                console.print(f"[dim]Backup of original CLAUDE.md taken.[/dim]")
        else:
            claude_md.write_text(new_content)
            console.print(f"[green]Created:[/green] CLAUDE.md")

        docs_dir = Path.cwd() / "docs"
        for subdir in ["specs", "discussion"]:
            (docs_dir / subdir).mkdir(parents=True, exist_ok=True)
        console.print("[green]Created docs/ structure (specs/, discussion/)[/green]")

        local_md_path = Path.cwd() / "CLAUDE.local.md"
        if not local_md_path.exists():
            local_md_path.write_text(generate_local_claude_md())
            console.print(f"[green]Created:[/green] CLAUDE.local.md")
            gitignore_path = Path.cwd() / ".gitignore"
            entries = ["CLAUDE.local.md", "docs/state/"]
            if not gitignore_path.exists():
                gitignore_path.write_text("\n".join(entries) + "\n")
            else:
                existing = gitignore_path.read_text()
                with open(gitignore_path, "a") as f:
                    for entry in entries:
                        if entry not in existing:
                            f.write(f"{entry}\n")
            console.print("[dim]Added CLAUDE.local.md, docs/state/ to .gitignore[/dim]")

        console.print("\n[bold green]Setup complete![/bold green] Run [cyan]coworker sync[/cyan] to apply.")


@main.command()
@click.argument("task", required=False, default=None)
@click.option("--summary", "-s", default=None, help="One-line progress summary")
def state_update(task, summary):
    """Update the task state file (called on Stop or manually for milestones).

    When no task name is given, a timestamp is used to ensure uniqueness.
    Use a descriptive task name for manual milestone saves:
      coworker state-update fix-state-paths -s "moved state files to docs/state/"
    """
    cwd = Path.cwd()

    # Auto-generate timestamp task name when none provided
    if not task:
        from datetime import datetime
        task = datetime.now().strftime("%Y-%m-%d-%H%M")

    # Find state file path from CLAUDE.local.md
    local_md = cwd / "CLAUDE.local.md"
    state_path = cwd / "docs" / "state" / f"state-{task}.md"
    if local_md.exists():
        import re
        content = local_md.read_text()
        match = re.search(r"State file:\s*`([^`]+)`", content)
        if match:
            state_path = cwd / match.group(1).replace("{taskname}", task)

    state_path.parent.mkdir(parents=True, exist_ok=True)

    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    if state_path.exists():
        existing = state_path.read_text()
        entry = f"\n\n## Update — {now}\n\n"
        if summary:
            entry += f"{summary}\n"
        else:
            entry += "_Progress checkpoint._\n"
        state_path.write_text(existing.rstrip() + entry)
    else:
        state_path.write_text(f"# Task State: {task}\n\n"
                              f"**Started:** {now}\n"
                              f"**Status:** in progress\n\n"
                              f"## Progress\n\n")

    console.print(f"[green]State updated: {state_path}[/green]")


@main.command()
@click.option("--tool", type=click.Choice(["claude", "gemini", "opencode", "all"]), default="all")
@click.option("--project", "is_project", is_flag=True, default=False, help="Sync project-level config only")
@click.option("--global", "is_global", is_flag=True, default=False, help="Sync global config only")
def sync(tool, is_project, is_global):
    """Sync config to Claude Code, Gemini, and/or OpenCode."""
    config = merged_config()
    tools = list(ADAPTERS.keys()) if tool == "all" else [tool]

    project_dir = Path.cwd() if is_project else None

    for t in tools:
        adapter = ADAPTERS[t]
        console.print(f"\n[bold cyan]{t}[/bold cyan]")
        try:
            actions = adapter.sync(config, project_dir=project_dir)
            for action in actions:
                console.print(f"  [green]✓[/green] {action}")
        except Exception as e:
            console.print(f"  [red]✗ {e}[/red]")

    console.print("\n[bold green]Done.[/bold green]")


@main.command()
def status():
    """Show current config status."""
    table = Table(title="Coworker Config Status")
    table.add_column("Scope", style="cyan")
    table.add_column("Path")
    table.add_column("Status")
    table.add_column("MCPs")
    table.add_column("Skills")

    g = load_global_config()
    global_path = GLOBAL_CONFIG
    table.add_row(
        "global",
        str(global_path),
        "[green]found[/green]" if g else "[red]not found[/red]",
        str(len(g.mcp)) if g else "-",
        str(len(g.skills)) if g else "-",
    )

    p = load_project_config()
    from .config import find_project_config
    proj_path = find_project_config()
    table.add_row(
        "project",
        str(proj_path) if proj_path else "(none)",
        "[green]found[/green]" if p else "[dim]none[/dim]",
        str(len(p.mcp)) if p else "-",
        str(len(p.skills)) if p else "-",
    )

    console.print(table)


@main.group()
def skill():
    """Manage skills."""
    pass


@skill.command("list")
def skill_list():
    """List all skills."""
    config = merged_config()
    if not config.skills:
        console.print("[dim]No skills configured.[/dim]")
        return
    table = Table(title="Skills")
    table.add_column("Name", style="cyan")
    table.add_column("Path")
    table.add_column("Enabled")
    for s in config.skills:
        table.add_row(s.name, s.path, "[green]yes[/green]" if s.enabled else "[red]no[/red]")
    console.print(table)


@skill.command("new")
@click.argument("name")
@click.option("--global", "is_global", is_flag=True, default=True)
def skill_new(name, is_global):
    """Scaffold a new skill."""
    if is_global:
        skill_dir = GLOBAL_DIR / "skills" / name
    else:
        skill_dir = Path.cwd() / ".coworker" / "skills" / name

    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    if skill_file.exists():
        console.print(f"[yellow]Already exists:[/yellow] {skill_file}")
        return

    skill_file.write_text(f"""\
---
name: {name}
description: "{name} skill — describe what this skill does and when to use it"
user-invocable: true
---

# {name}

## When to use
Describe when Claude should invoke this skill.

## Steps
1. Step one
2. Step two
3. Step three
""")
    console.print(f"[green]Created:[/green] {skill_file}")
    console.print(f"[dim]Add to coworker.yaml:[/dim]")
    console.print(f"  skills:\n    - name: {name}\n      path: skills/{name}")


# ── Project Catalog ───────────────────────────────────────────────────────


@main.group()
def project():
    """Manage project catalog (project.yaml)."""
    pass


@project.command("list")
def project_list():
    """List all tracked projects."""
    catalog = load_project_catalog()
    if not catalog.projects:
        console.print(
            "[dim]No projects configured. Use 'coworker project add'.[/dim]"
        )
        return
    table = Table(title="Project Catalog")
    table.add_column("Name", style="cyan")
    table.add_column("Path")
    table.add_column("Upstream")
    table.add_column("Downstream")
    for p in catalog.projects:
        up = ", ".join(u.name for u in p.upstream) or "-"
        down = ", ".join(d.name for d in p.downstream) or "-"
        table.add_row(p.name, p.local_path, up, down)
    console.print(table)


@project.command("show")
@click.argument("name")
def project_show(name):
    """Show details of a single project."""
    catalog = load_project_catalog()
    for p in catalog.projects:
        if p.name == name:
            import yaml
            data = p.model_dump(exclude_none=True)
            console.print(
                yaml.dump(data, default_flow_style=False, allow_unicode=True)
            )
            return
    console.print(f"[red]Project '{name}' not found.[/red]")


@project.command("add")
@click.argument("name")
@click.option("--path", "local_path", default=None, help="Local directory")
@click.option("--repo", default=None, help="Git remote URL")
@click.option("--team", default=None, help="Owning team")
def project_add(name, local_path, repo, team):
    """Add a project to the catalog."""
    catalog = load_project_catalog()
    for p in catalog.projects:
        if p.name == name:
            console.print(f"[yellow]Project '{name}' already exists.[/yellow]")
            return

    entry = ProjectEntry(
        name=name,
        local_path=local_path or str(Path.cwd()),
        repo=repo or "",
        team=team or "",
    )
    catalog.projects.append(entry)
    save_project_catalog(catalog)
    console.print(f"[green]Added project '{name}' to catalog.[/green]")


@project.command("edit")
@click.argument("name")
@click.option("--path", "local_path", default=None)
@click.option("--repo", default=None)
@click.option(
    "--add-upstream", multiple=True, help="Add upstream project name"
)
@click.option(
    "--add-downstream", multiple=True, help="Add downstream project name"
)
@click.option("--add-kp-url", "kp_url", default=None)
@click.option("--add-kp-type", "kp_type", default="other")
def project_edit(
    name, local_path, repo, add_upstream, add_downstream, kp_url, kp_type
):
    """Edit a project entry."""
    catalog = load_project_catalog()
    for p in catalog.projects:
        if p.name == name:
            if local_path:
                p.local_path = local_path
            if repo:
                p.repo = repo
            for up in add_upstream:
                if not any(u.name == up for u in p.upstream):
                    p.upstream.append(ProjectRef(name=up))
            for down in add_downstream:
                if not any(d.name == down for d in p.downstream):
                    p.downstream.append(ProjectRef(name=down))
            if kp_url:
                p.knowledge_pool.append(
                    KnowledgePoolEntry(url=kp_url, type=kp_type)
                )
            save_project_catalog(catalog)
            console.print(f"[green]Updated project '{name}'.[/green]")
            return
    console.print(f"[red]Project '{name}' not found.[/red]")


@project.command("remove")
@click.argument("name")
def project_remove(name):
    """Remove a project from the catalog."""
    catalog = load_project_catalog()
    before = len(catalog.projects)
    catalog.projects = [p for p in catalog.projects if p.name != name]
    if len(catalog.projects) == before:
        console.print(f"[yellow]Project '{name}' not found.[/yellow]")
        return
    save_project_catalog(catalog)
    console.print(f"[green]Removed project '{name}'.[/green]")


@project.command("sync")
def project_sync():
    """Re-inject static context into IDE configs."""
    mgr = InitiativeManager()
    actions = mgr.inject_static_context()
    for action in actions:
        console.print(f"  [green]✓[/green] {action}")
    console.print("[bold green]Static context synced.[/bold green]")


# ── Initiative ─────────────────────────────────────────────────────────────


@main.group()
def initiative():
    """Manage initiatives."""
    pass


@initiative.command("start")
@click.argument("name")
@click.option("--description", "-d", default="")
@click.option("--project", "-p", "proj_dir", default=None, help="Project directory (default: current)")
@click.option("--role", default="peer", help="Project role: upstream|downstream|peer")
@click.option("--branch", "-b", "branches", default="main", help="Branches (comma-separated)")
def initiative_start(name, description, proj_dir, role, branches):
    """Quick-start: create, add project, and activate in one step."""
    pd = Path(proj_dir) if proj_dir else Path.cwd()
    mgr = InitiativeManager(project_dir=pd)

    try:
        mgr.create(name, description)
    except FileExistsError:
        console.print(f"[yellow]Initiative '{name}' exists, activating it.[/yellow]")
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        return

    if proj_dir:
        config = load_initiative(name)
        if config and not any(p.name == proj_dir for p in config.projects):
            branch_list = [b.strip() for b in branches.split(",") if b.strip()]
            config.projects.append(
                InitiativeProjectRef(
                    name=proj_dir,
                    role=role,
                    branches=branch_list,
                )
            )
            save_initiative(config)

    try:
        actions = mgr.activate(name)
        for action in actions:
            console.print(f"  [green]✓[/green] {action}")
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")


@initiative.command("create")
@click.argument("name")
@click.option("--description", "-d", default="")
@click.option("--project", "-p", "proj_dir", default=None, help="Project directory (default: current)")
def initiative_create(name, description, proj_dir):
    """Create a new initiative."""
    pd = Path(proj_dir) if proj_dir else Path.cwd()
    mgr = InitiativeManager(project_dir=pd)
    try:
        mgr.create(name, description)
        console.print(f"[green]Created initiative '{name}'[/green]")
    except FileExistsError as e:
        console.print(f"[red]{e}[/red]")


@initiative.command("edit")
@click.argument("name")
@click.option("--project", "-p", "proj_dir", default=None, help="Project directory (default: current)")
@click.option("--description", "-d", default=None)
@click.option("--add-project", "add_proj", default=None, help="Add project (name:role:branches)")
@click.option("--add-link", "add_link_spec", default=None, help="Add link (Title|URL)")
@click.option("--add-decision", "add_decision_spec", default=None, help="Add decision (date|decision|rationale|by)")
@click.option("--add-doc", "add_doc_spec", default=None, help="Add reference doc (Title|path)")
@click.option("--archive", "do_archive", is_flag=True, default=False, help="Archive the initiative")
def initiative_edit(name, proj_dir, description, add_proj, add_link_spec, add_decision_spec, add_doc_spec, do_archive):
    """Edit an existing initiative."""
    pd = Path(proj_dir) if proj_dir else Path.cwd()
    config = load_initiative(name)
    if config is None:
        console.print(f"[red]Initiative '{name}' not found.[/red]")
        return

    if description is not None:
        config.description = description
    if do_archive:
        config.status = "archived"

    if add_proj:
        parts = add_proj.split(":")
        proj_name = parts[0]
        existing = [p for p in config.projects if p.name == proj_name]
        if existing:
            console.print(
                f"[yellow]Project '{proj_name}' is already in this initiative.[/yellow]"
            )
            return
        proj = InitiativeProjectRef(
            name=proj_name,
            role=parts[1] if len(parts) > 1 else "peer",
            branches=(
                parts[2].split(",") if len(parts) > 2 and parts[2] else []
            ),
        )
        config.projects.append(proj)

    if add_link_spec:
        parts = add_link_spec.split("|", 1)
        config.links.append(
            LinkRef(
                title=parts[0],
                url=parts[1] if len(parts) > 1 else parts[0],
            )
        )

    if add_decision_spec:
        parts = add_decision_spec.split("|")
        config.decisions.append(
            Decision(
                date=parts[0] if len(parts) > 0 else "",
                decision=parts[1] if len(parts) > 1 else "",
                rationale=parts[2] if len(parts) > 2 else "",
                by=parts[3] if len(parts) > 3 else "",
            )
        )

    if add_doc_spec:
        parts = add_doc_spec.split("|", 1)
        config.reference_docs.append(
            ReferenceDoc(
                title=parts[0],
                path=parts[1] if len(parts) > 1 else parts[0],
            )
        )

    save_initiative(config)
    console.print(f"[green]Updated initiative '{name}'.[/green]")


@initiative.command("list")
@click.option("--project", "-p", "proj_dir", default=None, help="Project directory (default: current)")
@click.option("--verbose", "-v", is_flag=True, default=False)
def initiative_list(proj_dir, verbose):
    """List all initiatives for a project."""
    pd = Path(proj_dir) if proj_dir else Path.cwd()
    mgr = InitiativeManager(project_dir=pd)
    active = mgr.active_name()
    initiatives = mgr.list_all()
    if not initiatives:
        console.print(f"[dim]No initiatives found. Use 'coworker initiative create'.[/dim]")
        return

    table = Table(title="Initiatives")
    table.add_column("Name", style="cyan")
    table.add_column("Status")
    table.add_column("Active")
    if verbose:
        table.add_column("Projects")
    table.add_column("Description")
    for i in initiatives:
        mark = "[green]✓[/green]" if i.name == active else ""
        sc = "green" if i.status == "active" else "dim"
        row = [i.name, f"[{sc}]{i.status}[/{sc}]", mark]
        if verbose:
            proj_str = ", ".join(p.name for p in i.projects) or "-"
            row.append(proj_str)
        row.append(i.description or "-")
        table.add_row(*row)
    console.print(table)


@initiative.command("show")
@click.argument("name")
@click.option("--project", "-p", "proj_dir", default=None, help="Project directory (default: current)")
def initiative_show(name, proj_dir):
    """Show full initiative config."""
    config = load_initiative(name)
    if config is None:
        console.print(f"[red]Initiative '{name}' not found.[/red]")
        return
    import yaml
    data = config.model_dump(exclude_none=True)
    console.print(yaml.dump(data, default_flow_style=False, allow_unicode=True))


@initiative.command("activate")
@click.argument("name")
@click.option("--project", "-p", "proj_dir", default=None, help="Project directory (default: current)")
def initiative_activate(name, proj_dir):
    """Activate an initiative (inject context into IDE configs)."""
    pd = Path(proj_dir) if proj_dir else Path.cwd()
    mgr = InitiativeManager(project_dir=pd)
    try:
        actions = mgr.activate(name)
        for action in actions:
            console.print(f"  [green]✓[/green] {action}")
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")


@initiative.command("deactivate")
@click.option("--project", "-p", "proj_dir", default=None, help="Project directory (default: current)")
def initiative_deactivate(proj_dir):
    """Deactivate current initiative."""
    pd = Path(proj_dir) if proj_dir else Path.cwd()
    mgr = InitiativeManager(project_dir=pd)
    actions = mgr.deactivate()
    for action in actions:
        console.print(f"  [green]✓[/green] {action}")


@initiative.command("remove")
@click.argument("name")
@click.option("--project", "-p", "proj_dir", default=None, help="Project directory (default: current)")
@click.option("--force", is_flag=True, default=False, help="Skip confirmation")
def initiative_remove(name, proj_dir, force):
    """Remove an initiative permanently."""
    pd = Path(proj_dir) if proj_dir else Path.cwd()
    mgr = InitiativeManager(project_dir=pd)
    config = mgr.show(name)
    if config is None:
        console.print(f"[red]Initiative '{name}' not found.[/red]")
        return
    if not force:
        ok = click.confirm(f"Remove initiative '{name}' permanently?", default=False)
        if not ok:
            console.print("[dim]Cancelled.[/dim]")
            return
    try:
        mgr.remove(name)
        console.print(f"[green]Removed initiative '{name}'.[/green]")
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")


# ── Analytics ─────────────────────────────────────────────────────────────

@main.group()
def analytics():
    """Analytics database and dashboard commands."""
    pass


@analytics.command("create-db")
def analytics_create_db():
    """Initialize analytics SQLite database."""
    from .analytics.db import init_db
    init_db()
    console.print("[green]Analytics database initialized.[/green]")


@analytics.command("import")
def analytics_import():
    """Import raw JSONL sessions into SQLite."""
    from .analytics.import_data import import_all
    import_all()


@analytics.command("daemon")
def analytics_daemon():
    """Run auto-import daemon — polls every 30 minutes for new sessions."""
    from .analytics.auto_import import run_daemon
    run_daemon()


@analytics.command("once")
def analytics_once():
    """Import new sessions once (no daemon)."""
    from .analytics.auto_import import run_once
    stats = run_once(verbose=True)
    console.print(f"[green]Imported:[/green] claude_jsonl={stats['claude_jsonl']} claude_hooks={stats['claude_hooks']} opencode={stats['opencode']} skipped={stats['skipped']}")


@analytics.command("dashboard")
@click.option("--port", default=8080, help="Port to listen on")
@click.option("--db", default=None, help="Path to analytics database")
def analytics_dashboard(port, db):
    """Start the analytics dashboard."""
    import os
    if db:
        os.environ["COWORKER_ANALYTICS_DB"] = db
    import uvicorn
    from .dashboard.app import app
    console.print(f"[green]Dashboard: http://localhost:{port}[/green]")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
