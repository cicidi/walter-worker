#!/usr/bin/env python3
"""
Bridge pipeline: walter-worker analytics SQLite → claude-obsidian Obsidian vault.

Exports session memory as structured knowledge cards and session notes into
the claude-obsidian vault format with wikilinks, frontmatter, and tags.
"""

import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

from src.coworker.analytics.db import get_db

VAULT_PATH = Path.home() / "obsidian" / "coworker-brain"
WIKI_PATH = VAULT_PATH / "wiki"
SESSIONS_PATH = WIKI_PATH / "sources" / "sessions"
CONCEPTS_PATH = WIKI_PATH / "concepts"
ENTITIES_SKILLS = WIKI_PATH / "entities" / "skills"
ENTITIES_TOOLS = WIKI_PATH / "entities" / "tools"
PROJECTS_PATH = WIKI_PATH / "entities" / "projects"
KNOWLEDGE_PATH = WIKI_PATH / "concepts"

SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    return SLUG_RE.sub("-", text.lower()).strip("-")


def write_markdown(path: Path, frontmatter: dict, body: str):
    """Write a markdown file with YAML frontmatter."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = "---\n"
    for k, v in frontmatter.items():
        if isinstance(v, list):
            fm += f"{k}:\n"
            for item in v:
                fm += f"  - \"{item}\"\n"
        elif isinstance(v, str) and "\n" in v:
            fm += f"{k}: |\n  {v.replace(chr(10), chr(10) + '  ')}\n"
        else:
            fm += f"{k}: \"{v}\"\n"
    fm += "---\n\n"
    path.write_text(fm + body)


def export_sessions(conn):
    """Export all sessions as individual markdown notes."""
    rows = conn.execute(
        """SELECT s.*, ss.message_count, ss.tool_count, ss.skill_count,
                  ss.duration_min, ss.read_count, ss.write_count, ss.bash_count
           FROM sessions s LEFT JOIN session_stats ss ON s.id = ss.session_id
           ORDER BY s.created_at DESC"""
    ).fetchall()

    # Clear existing session notes
    if SESSIONS_PATH.exists():
        shutil.rmtree(SESSIONS_PATH)
    SESSIONS_PATH.mkdir(parents=True)

    exported = []
    for row in rows:
        s = dict(row)
        sid = s["id"]
        date_str = (s["created_at"] or "")[:10]
        slug = f"{date_str}-{s['ide']}-{s['project']}"

        # Get messages for this session
        msgs = conn.execute(
            "SELECT type, content, ts FROM messages WHERE session_id = ? ORDER BY seq LIMIT 20",
            (sid,),
        ).fetchall()

        # Get tool calls
        tools = [dict(r) for r in conn.execute(
            "SELECT tool, tool_type, server_name, duration_ms FROM tool_calls WHERE session_id = ? ORDER BY COALESCE(seq_before, seq_after) LIMIT 30",
            (sid,),
        ).fetchall()]

        # Get session summary
        summary = conn.execute(
            "SELECT * FROM session_summaries WHERE session_id = ?", (sid,)
        ).fetchone()
        if summary:
            summary = dict(summary)

        # Build message section
        msg_lines = []
        for m in msgs:
            prefix = "**User:**" if m["type"] == "user" else "**Assistant:**"
            content = (m["content"] or "")[:300]
            msg_lines.append(f"{prefix} {content}")

        # Build tool section  
        tool_lines = []
        tool_set = set()
        for t in tools:
            label = f"{t['tool']}"
            if t.get("tool_type") == "mcp" and t.get("server_name"):
                label += f" ({t.get('server_name')})"
            if label not in tool_set:
                tool_lines.append(f"- `{label}`")
                tool_set.add(label)

        # Build summary section
        summary_section = ""
        decisions = ""
        problems = ""
        next_steps = ""
        if summary:
            summary_section = f"""## AI Efficiency Analysis

- **Efficiency Score:** {summary.get('efficiency_score', 'N/A')}
- **Efficiency Tip:** {summary.get('efficiency_tip', 'N/A')}
- **Context:** {str(summary.get('context_to_remember', 'N/A'))[:300]}
- **Pitfalls & Fixes:** {str(summary.get('pitfalls_and_fixes', 'N/A'))[:200]}
- **Memory Keywords:** {summary.get('memory_keywords', 'N/A')}
"""
            # Extract decisions from context
            context = summary.get("context_to_remember", "") or ""
            if context:
                sentences = re.split(r"(?<=[.!?])\s+", context)
                decisions = [sent for sent in sentences if any(
                    kw in sent.lower() for kw in ["decided", "decision", "chose", "selected", "picked"])]
                problems = [sent for sent in sentences if any(
                    kw in sent.lower() for kw in ["bug", "issue", "problem", "broke", "failed", "error"])]

        # Build entity wikilinks
        wikilinks = [f"[[projects/{s['project']}]]"] if s["project"] else []
        if s.get("initiative"):
            wikilinks.append(f"[[initiatives/{s['initiative']}]]")

        body = f"""# Session: {slug}

## Overview
- **IDE:** {s['ide']}
- **Project:** [[projects/{s['project']}]]
- **Branch:** `{s['branch'] or 'N/A'}`
- **Initiative:** {f'[[initiatives/{s["initiative"]}]]' if s.get('initiative') else 'N/A'}
- **Started:** {s['created_at']}
- **Duration:** {s.get('duration_min', 'N/A')} minutes
- **Model:** {s.get('model', 'N/A')}

## Stats
| Metric | Count |
|--------|-------|
| Messages | {s.get('message_count', 0)} |
| Tool Calls | {s.get('tool_count', 0)} |
| Skills Used | {s.get('skill_count', 0)} |
| Files Read | {s.get('read_count', 0)} |
| Files Written | {s.get('write_count', 0)} |
| Bash Commands | {s.get('bash_count', 0)} |

## Conversation Excerpt
{chr(10).join(msg_lines[:12])}

## Tools Used
{chr(10).join(tool_lines[:15])}
{summary_section}
## Related
{chr(10).join(f'- {wl}' for wl in wikilinks)}
"""
        frontmatter = {
            "type": "session",
            "title": f"Session: {slug}",
            "date": date_str,
            "ide": s["ide"],
            "project": s["project"] or "",
            "initiative": s.get("initiative", ""),
            "branch": s.get("branch", ""),
            "tags": [
                f"ide/{s['ide']}",
                f"proj/{s['project']}",
                "session",
            ],
            "status": "complete",
        }
        if s.get("initiative"):
            frontmatter["tags"].append(f"initiative/{s['initiative']}")

        write_markdown(SESSIONS_PATH / f"{slug}.md", frontmatter, body)
        exported.append({"slug": slug, "project": s["project"], "date": date_str,
                        "ide": s["ide"], "initiative": s.get("initiative", ""),
                        "duration": s.get("duration_min", 0)})

    return exported


def export_knowledge_cards(conn):
    """Export knowledge cards as concepts in the vault."""
    rows = conn.execute(
        "SELECT * FROM knowledge ORDER BY generated_at DESC"
    ).fetchall()

    if KNOWLEDGE_PATH.exists():
        for f in KNOWLEDGE_PATH.glob("knowledge-*.md"):
            f.unlink()

    cards = []
    for row in rows:
        k = dict(row)
        slug = slugify(k["title"])[:60]
        card_type = k.get("type", "best")

        body = f"""# {k['title']}

**Type:** {card_type}
**Project:** {k.get('project', 'N/A')}
**Session:** [[{k.get('session_id', '')}]]
**Generated:** {k.get('generated_at', 'N/A')}

## Summary
{k.get('summary', 'N/A')}

## Evidence
{k.get('evidence', 'N/A')}

## Related Skills
{k.get('skills', 'N/A')}
"""
        fm = {
            "type": "knowledge-card",
            "title": k["title"],
            "card_type": card_type,
            "project": k.get("project", ""),
            "session_id": k.get("session_id", ""),
            "tags": [f"type/{card_type}", "knowledge-card"],
            "status": "active",
        }
        write_markdown(KNOWLEDGE_PATH / f"knowledge-{slug}.md", fm, body)
        cards.append({"title": k["title"], "type": card_type, "slug": slug})

    return cards


def export_skills(conn):
    """Export skills as entity pages."""
    rows = conn.execute(
        "SELECT * FROM skills ORDER BY total_calls DESC"
    ).fetchall()

    ENTITIES_SKILLS.mkdir(parents=True, exist_ok=True)
    for f in ENTITIES_SKILLS.glob("*.md"):
        f.unlink()

    skills = []
    for row in rows:
        s = dict(row)
        name = s["name"]
        body = f"""# Skill: {name}

**Total Invocations:** {s.get('total_calls', 0)}
**First Invoked:** {s.get('first_invoked', 'N/A')}
**Last Invoked:** {s.get('last_invoked', 'N/A')}

## Usage
This skill has been invoked {s.get('total_calls', 0)} times across all sessions.

## Related
- [[index]]
"""
        fm = {
            "type": "skill",
            "title": f"Skill: {name}",
            "skill_name": name,
            "total_calls": s.get("total_calls", 0),
            "tags": ["entity/skill", f"skill/{name}"],
            "status": "active",
        }
        write_markdown(ENTITIES_SKILLS / f"{name}.md", fm, body)
        skills.append({"name": name, "calls": s.get("total_calls", 0)})

    return skills


def export_tools(conn):
    """Export tool stats as entity pages."""
    rows = conn.execute(
        """SELECT tool, tool_type, server_name, COUNT(*) as calls,
                  ROUND(AVG(duration_ms), 1) as avg_ms,
                  MAX(duration_ms) as max_ms
           FROM tool_calls GROUP BY tool, tool_type ORDER BY calls DESC"""
    ).fetchall()

    ENTITIES_TOOLS.mkdir(parents=True, exist_ok=True)
    for f in ENTITIES_TOOLS.glob("*.md"):
        f.unlink()

    tools_list = []
    for row in rows:
        t = dict(row)
        name = t["tool"]
        tool_type = t.get("tool_type", "builtin")
        server = t.get("server_name", "")

        body = f"""# Tool: {name}

**Type:** {tool_type}{f' ({server})' if server else ''}
**Total Calls:** {t.get('calls', 0)}
**Avg Duration:** {t.get('avg_ms', 'N/A')}ms
**Max Duration:** {t.get('max_ms', 'N/A')}ms

## Related
- [[index]]
"""
        fm = {
            "type": "tool",
            "title": f"Tool: {name}",
            "tool_name": name,
            "tool_type": tool_type,
            "server_name": server,
            "total_calls": t.get("calls", 0),
            "tags": ["entity/tool", f"tool/{name}"],
            "status": "active",
        }
        write_markdown(ENTITIES_TOOLS / f"{name}.md", fm, body)
        tools_list.append({"name": name, "type": tool_type, "calls": t.get("calls", 0)})

    return tools_list


def export_projects(conn):
    """Create project entity pages."""
    rows = conn.execute(
        """SELECT project, COUNT(*) as session_count,
                  SUM(ss.duration_min) as total_min
           FROM sessions s LEFT JOIN session_stats ss ON s.id = ss.session_id
           WHERE project IS NOT NULL AND project != ''
           GROUP BY project ORDER BY session_count DESC"""
    ).fetchall()

    PROJECTS_PATH.mkdir(parents=True, exist_ok=True)
    for f in PROJECTS_PATH.glob("*.md"):
        f.unlink()

    projects = []
    for row in rows:
        p = dict(row)
        body = f"""# Project: {p['project']}

**Sessions:** {p.get('session_count', 0)}
**Total Time:** {p.get('total_min', 0) or 0} minutes

## Sessions
See [[sources/sessions/]] for all sessions related to this project.

## Related
- [[index]]
"""
        fm = {
            "type": "project",
            "title": f"Project: {p['project']}",
            "project_name": p["project"],
            "session_count": p.get("session_count", 0),
            "tags": ["entity/project", f"proj/{p['project']}"],
            "status": "active",
        }
        write_markdown(PROJECTS_PATH / f"{p['project']}.md", fm, body)
        projects.append({"name": p["project"], "sessions": p.get("session_count", 0)})

    return projects


def export_initiatives(conn):
    """Create initiative entity pages."""
    rows = conn.execute(
        """SELECT s.initiative, s.project, COUNT(*) as session_count
           FROM sessions s
           WHERE s.initiative IS NOT NULL AND s.initiative != ''
           GROUP BY s.initiative ORDER BY session_count DESC"""
    ).fetchall()

    path = WIKI_PATH / "entities" / "initiatives"
    path.mkdir(parents=True, exist_ok=True)
    for f in path.glob("*.md"):
        f.unlink()

    initiatives = []
    for row in rows:
        i = dict(row)
        body = f"""# Initiative: {i['initiative']}

**Project:** [[projects/{i.get('project', '')}]]
**Sessions:** {i.get('session_count', 0)}

## Sessions
See [[sources/sessions/]] for all sessions in this initiative.

## Related
- [[projects/{i.get('project', '')}]]
- [[index]]
"""
        fm = {
            "type": "initiative",
            "title": f"Initiative: {i['initiative']}",
            "initiative_name": i["initiative"],
            "project": i.get("project", ""),
            "session_count": i.get("session_count", 0),
            "tags": ["entity/initiative", f"initiative/{i['initiative']}"],
            "status": "active",
        }
        write_markdown(path / f"{i['initiative']}.md", fm, body)
        initiatives.append({"name": i["initiative"], "sessions": i.get("session_count", 0)})

    return initiatives


def update_index(sessions, skills, tools, projects, initiatives):
    """Update wiki/index.md with exported content."""
    total_pages = (len(sessions) + len(skills) + len(tools) + len(projects) + len(initiatives))

    session_links = "\n".join(
        f"- [[sources/sessions/{s['slug']}]] — {s['date']} | {s['ide']} | {s['project']} | {s['duration']}min"
        for s in sessions[:20]
    )

    skill_links = "\n".join(
        f"- [[entities/skills/{s['name']}]] — {s['calls']} invocations"
        for s in skills
    )

    tool_links = "\n".join(
        f"- [[entities/tools/{t['name']}]] — {t['calls']} calls"
        for t in tools
    )

    project_links = "\n".join(
        f"- [[entities/projects/{p['name']}]] — {p['sessions']} sessions"
        for p in projects
    )

    initiative_links = "\n".join(
        f"- [[entities/initiatives/{i['name']}]] — {i['sessions']} sessions"
        for i in initiatives
    )

    content = f"""---
type: meta
title: "Coworker Brain Index"
updated: {datetime.now().strftime('%Y-%m-%d')}
tags:
  - meta
  - index
status: evergreen
related:
  - "[[overview]]"
  - "[[log]]"
  - "[[hot]]"
---

# Coworker Brain Index

Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Total pages: {total_pages}

## Recent Sessions
{session_links}

## Skills
{skill_links}

## Tools
{tool_links}

## Projects
{project_links}

## Initiatives
{initiative_links}
"""
    (WIKI_PATH / "index.md").write_text(content)


def update_hot(sessions, skills, projects):
    """Update wiki/hot.md with recent context."""
    top_skills = ", ".join(f"[[entities/skills/{s['name']}]] ({s['calls']})" for s in skills[:5])
    top_projects = ", ".join(f"[[entities/projects/{p['name']}]] ({p['sessions']})" for p in projects[:3])

    recent = sessions[:8]
    recent_str = "\n".join(
        f"- [[sources/sessions/{s['slug']}]] | {s['ide']} | {s['project']} | {s['duration']}min"
        for s in recent
    )

    content = f"""---
type: meta
title: "Hot Cache"
updated: {datetime.now().isoformat()}
tags:
  - meta
  - hot-cache
status: evergreen
---

# Recent Context

## Last Updated
{datetime.now().strftime('%Y-%m-%d %H:%M')} — Coworker Brain sync from walter-worker analytics.

## Stats
- **Sessions:** {len(sessions)}
- **Top Skills:** {top_skills}
- **Active Projects:** {top_projects}

## Recent Sessions
{recent_str}

## Quick Links
- [[index]] — full index
- [[overview]] — executive summary
- [[getting-started]] — how to use this vault
"""
    (WIKI_PATH / "hot.md").write_text(content)


def update_log(counts: dict):
    """Append to wiki/log.md."""
    log_entry = f"""
## {datetime.now().strftime('%Y-%m-%d %H:%M')} — Coworker Brain Sync

- **Sessions exported:** {counts.get('sessions', 0)}
- **Knowledge cards:** {counts.get('knowledge', 0)}
- **Skills:** {counts.get('skills', 0)}
- **Tools:** {counts.get('tools', 0)}
- **Projects:** {counts.get('projects', 0)}
- **Initiatives:** {counts.get('initiatives', 0)}
- **Total messages:** {counts.get('messages', 0)}
- **Total tool calls:** {counts.get('tool_calls', 0)}
"""
    log_path = WIKI_PATH / "log.md"
    current = log_path.read_text() if log_path.exists() else "# Operation Log\n"
    # Insert after the first heading
    lines = current.split("\n")
    insert_at = 1
    for i, line in enumerate(lines):
        if line.startswith("# "):
            insert_at = i + 1
            break
    for i in range(insert_at, len(lines)):
        if lines[i].startswith("## "):
            insert_at = i
            break
    lines.insert(insert_at, log_entry)
    log_path.write_text("\n".join(lines))


def bridge_export():
    """Main export: read SQLite and populate claude-obsidian vault."""
    conn = get_db()

    # Check DB has data
    count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    if count == 0:
        print("No sessions in database. Run seed_dashboard first.")
        conn.close()
        return

    print(f"Exporting {count} sessions to {VAULT_PATH}...")

    # Stats
    total_msgs = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    total_tools = conn.execute("SELECT COUNT(*) FROM tool_calls").fetchone()[0]

    # Export all components
    print("  → Sessions...")
    sessions = export_sessions(conn)

    print("  → Knowledge cards...")
    knowledge = export_knowledge_cards(conn)

    print("  → Skills...")
    skills = export_skills(conn)

    print("  → Tools...")
    tools = export_tools(conn)

    print("  → Projects...")
    projects = export_projects(conn)

    print("  → Initiatives...")
    initiatives = export_initiatives(conn)

    # Update meta files
    print("  → Updating index...")
    update_index(sessions, skills, tools, projects, initiatives)

    print("  → Updating hot cache...")
    update_hot(sessions, skills, projects)

    counts = {
        "sessions": len(sessions),
        "knowledge": len(knowledge),
        "skills": len(skills),
        "tools": len(tools),
        "projects": len(projects),
        "initiatives": len(initiatives),
        "messages": total_msgs,
        "tool_calls": total_tools,
    }
    print("  → Updating log...")
    update_log(counts)

    conn.close()

    print(f"\n✅ Export complete!")
    print(f"   Vault: {VAULT_PATH}")
    print(f"   Sessions: {len(sessions)}")
    print(f"   Knowledge cards: {len(knowledge)}")
    print(f"   Skills: {len(skills)}")
    print(f"   Tools: {len(tools)}")
    print(f"   Projects: {len(projects)}")
    print(f"   Initiatives: {len(initiatives)}")
    print(f"\nOpen Obsidian: ~/.local/bin/obsidian --vault {VAULT_PATH}")


if __name__ == "__main__":
    bridge_export()
