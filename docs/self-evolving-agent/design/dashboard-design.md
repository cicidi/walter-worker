# Dashboard — Evolution Page Design

> Initiative: self-evolving-agent | Type: design | Status: **draft v1**
>
> Builds on: [PRD v6](../prd/self-evolving-agent-prd.md) (requirements), [Spec v1.1](../spec/self-evolving-agent-spec.md) (technical detail), [Memory Platform Design](memory-platform-design.md)
>
> Design for a new "Evolution" page in the existing Coworker Analytics Dashboard. The page shows auto-trained skills and experiences with their session traceability and reuse metrics — the primary surface for answering "is this thing working?"

---

## 1. Page Layout

```
┌──────────────────────────────────────────────────────────────┐
│  ⧩ Coworker                      ┌──────────────────────────┐│
│                                   │                          ││
│  ── Analytics ──                  │  ◉ Evolution             ││
│  ◉ Overview                       │                          ││
│  ☰ Sessions                       │  ┌────────────────────┐  ││
│  ◎ Knowledge                      │  │ Stat Cards          │  ││
│  ◈ Initiatives                    │  │ Skills │ Exp │ Rate │  ││
│                                   │  └────────────────────┘  ││
│  ── Monitoring ──                 │                          ││
│  ◉ Monitor                        │  ┌────────────────────┐  ││
│  ◆ Skills                         │  │ Skills Table        │  ││
│  ◉ Evolution    ← NEW             │  │ (auto-train flag,   │  ││
│  ⚙ Tools                          │  │  sessions, reuses)  │  ││
│  ◫ Files                          │  └────────────────────┘  ││
│                                   │                          ││
│                                   │  ┌────────────────────┐  ││
│                                   │  │ Experiences Table   │  ││
│                                   │  │ (auto-train flag,   │  ││
│                                   │  │  source session,    │  ││
│                                   │  │  reuses)            │  ││
│                                   │  └────────────────────┘  ││
└──────────────────────────────────────────────────────────────┘
```

New sidebar item: `◉ Evolution` under Monitoring section (between Skills and Tools).

---

## 2. Stat Cards (Top Row)

Four metrics at a glance:

| Card | Label | Source |
|------|-------|--------|
| Auto-Trained Skills | count | mem0 skill store: `provenance=agent` |
| Experiences | count | mem0: `type=lesson, provenance=agent` |
| Skill Reuse Rate | % | sessions invoking auto-skill / total sessions |
| Evolution Score | % | composite: rising reuse + falling corrections |

---

## 3. Skills Table

Each row = one skill. Key columns:

| Column | Source | Notes |
|--------|--------|-------|
| **Name** | skill store | Clickable → skill detail |
| **Auto-Train** | `provenance` | 🟢 Auto-Train / 🔵 Bundled / ⚪ Hand-Written |
| **Status** | `state` | active / stale / archived |
| **Created** | `created_at` | Date |
| **Sessions Invoked** | analytics.db | Count of sessions that called this skill |
| **Total Calls** | analytics.db | Total invocation count |
| **Last Used** | analytics.db | Most recent session date |
| **Reuse Rate** | sessions_invoked / total_sessions | % of sessions |

**Default filter:** `Auto-Train = true` — show auto-trained skills first.

**Click behavior:** Click skill name → expand row showing sessions that invoked it, with links to session detail.

---

## 4. Experiences Table

Each row = one experience/lesson. Key columns:

| Column | Source | Notes |
|--------|--------|-------|
| **Summary** | mem0 `memory` field | Truncated to 120 chars |
| **Auto-Train** | `provenance` | 🟢 Auto-Train / ⚪ Hand-Written |
| **Topic** | `metadata.topic` | Slug |
| **Project** | `metadata.project` | Which project |
| **Source Session** | `metadata.source_session` | Session that generated this |
| **Times Retrieved** | `metadata.use_count` | How many times searched/used |
| **Last Retrieved** | `metadata.last_used` | Most recent retrieval |
| **Status** | `metadata.state` | active / stale / archived / pinned |

**Default filter:** `Auto-Train = true`.

**Click behavior:** Click summary → expand row showing full memory text + related sessions.

---

## 5. Filters & Controls

| Filter | Type | Default |
|--------|------|---------|
| Auto-Train toggle | switch (auto-train / all) | auto-train only |
| Project | dropdown | all projects |
| Status | multi-select (active/stale/archived/pinned) | active only |
| Topic | search + autocomplete | none |
| Date range | from → to | last 30 days |

**Batch actions:**
- Approve all pending skills
- Reject all pending skills
- Export as CSV

---

## 6. API Endpoints

New endpoints to add to `app.py`:

| Endpoint | Returns |
|----------|---------|
| `GET /api/evolution/overview` | Stat card data (counts, rates) |
| `GET /api/evolution/skills?auto_train=true&project=X&status=active` | Skills list with columns above |
| `GET /api/evolution/skills/{id}` | Single skill detail + session trace |
| `GET /api/evolution/experiences?auto_train=true&project=X&status=active` | Experiences list |
| `GET /api/evolution/experiences/{id}` | Single experience detail |
| `GET /api/evolution/pending` | Pending queue items |
| `POST /api/evolution/approve/{id}` | Approve pending skill/experience |
| `POST /api/evolution/reject/{id}` | Reject pending skill/experience |

---

## 7. Integration Points

| Data Source | What the page reads |
|-------------|---------------------|
| mem0 (Tier 3) | Experiences, skill metadata, `provenance`, `state` |
| analytics.db | Session trace: which session called which skill |
| Skill store (`~/.coworker/skills/`) | Skill names, `usage.json` sidecar |
| Pending queue (`~/.coworker/pending/`) | Staged items awaiting review |

---

## 8. Visual Spec

- Matches existing dashboard style: sidebar nav, stat-grid, panel + table
- Auto-train badge: green pill `🟢 Auto` vs grey pill `⚪ Manual`
- Status badges: `● active` (green), `◉ stale` (yellow), `◎ archived` (grey)
- Row hover: highlight + expand arrow
- Default view: auto-train skills first, then auto-train experiences below

---

## 9. States

| State | What shows |
|-------|------------|
| **Empty (no data)** | "No auto-trained skills yet. Complete a few sessions to start evolution." + link to docs |
| **Loading** | Skeleton cards + pulse animation |
| **Error** | Panel with error message + retry button |
| **No auto-train items** | "All skills were created manually. Auto-train is enabled but hasn't generated any skills yet." |
| **All items archived** | "All auto-trained items are archived. Unarchive items or complete more sessions." |

---

## Change Log

| Date | Change |
|------|--------|
| 2026-07-25 | Initial creation |
