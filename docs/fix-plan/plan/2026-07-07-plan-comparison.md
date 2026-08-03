# Comparison: My Audit Plan vs. The Photo FIX-PLAN

- **My plan**: `docs/plan/2026-07-07-walter-worker-fix-plan.md` (6 Critical, 5 High, 11 Medium, 18 Low, 2 failing tests)
- **Photo plan**: `docs/plan/2026-07-07-photo-fix-plan-transcribed.md` (~30 items across 5 phases; **already executed** — 192 passed / 0 failed, baseline 86/7)

---

## TL;DR

The photo plan is **substantially broader and deeper** than mine. It was built from a pre-existing repro-verified analysis (`CICIDI-IMPROVEMENTS.md`), covers the **whole product surface** (shell scripts, skills, docs, README, CI, licensing, test infrastructure) — not just `src/` — and was actually executed with per-item `As-built` verification and `Field Notes` traps.

My plan is **narrower but finds some things theirs missed** — notably a **path-traversal security hole** in initiative names, and several **analytics data-quality bugs** (missing `tool_calls` rows, wrong `bash_count`/`tool_count`/`skill_count` semantics, NULL→"Project: None" in LLM prompts, no `busy_timeout`).

**Net**: treat the photo plan as the authoritative work order. Use my plan as a supplemental list of ~8 items the photo plan didn't cover (see §C below).

---

## A. Methodology differences

| Dimension | My plan | Photo plan |
|-----------|---------|------------|
| Source | GitHub Issue #1 + TODO.md + my own 2-agent source audit + test run | Pre-existing `CICIDI-IMPROVEMENTS.md`, every claim repro-verified |
| Scope | `src/coworker/**` Python only | `src/` + `setup/*.sh` (install/uninstall/update) + `skills/**` + `README`/`blueprint` + CI/packaging |
| Organization | Severity-ordered (Critical→Low) | Phase/dependency-ordered (Safety net → Quick wins → Data-safety → Consistency → Honesty) |
| Per-item structure | File/Problem/Repro/Fix/Verify | Problem/Fix steps/Acceptance/**As-built** (what was actually done) |
| Execution | Not executed | **Fully executed** on `fix/fix-plan-round1`; 192 passed / 0 failed |
| Extra value | — | `Field Notes` (execution traps), cross-cutting invariants, PR sequence with explicit dependencies |
| Severity calibration | Found 6 "Critical" | Only ~2 of mine are truly critical (C1/C2 = their P1); the photo plan is more conservative and accurate on severity |

---

## B. Overlapping findings (same root cause, both found)

| Topic | My ID | Their ID | Notes |
|-------|-------|----------|-------|
| `from src.coworker...` breaks installed package | C2 | P1 | Theirs is better: notes **6 sites not 5** (2 inline `python3 -c` in `install.sh`) |
| `analytics once` KeyError | C1 | P1 (2nd half) | Same fix |
| CLAUDE.md overwrite / sentinel mismatch | C5 | P2 | Theirs adds: `mkdir` for `.coworker/` + sentinel as a shared constant + backup-before-overwrite |
| Hardcoded `~/walter-worker` path (Issue #1) | GH1 | G10 + G2 + H4 | Theirs decomposes it into 5 stale assumptions; mine lumped it together |
| `semantic_merge` is dead code | L1 | P3 + G1 | Theirs goes further: it's not just dead, it **corrupts documents** (fence-blind, dup-heading, empty-section) and must be fixed *before* wiring (G1) |
| `initiative activate` swallows errors / false success | H5 | P10 (sub-issue 2) | Theirs also catches the **split-brain global `.active` marker** I missed |
| `_replace_or_append_block` crash on missing END | H4 | P10 (sub-issue 4) | Same fix (regex range match + self-heal) |
| Verb "updated" vs "injected" computed after mutation | L3 | P10 (sub-issue 4) | Same |
| Non-atomic config writes | M2 | P5 step 5 | Theirs ties it to the settings-clobber fix + backup |
| `initiative start` doesn't record current project | M3 | P13 item 1 | Theirs also fixes `-p` storing raw path as name |
| Flask guard always-true | L2 | P13 item 5 | Same |
| `.gitignore` substring dedup | L8 | P13 item 4 | Theirs adds trailing-newline guard |
| OpenCode writes config twice / wrong location | L7 | G7 | Theirs is much deeper: `instructions.md` not registered, legacy `config.json` path |
| Dashboard static path fragile | L13 | P12 | Theirs connects it to wheel packaging (the real bug) |
| Hooks assume `Stop` is a list | L6 | P5 step 2 | Theirs frames it as wrong hook *shape*, broader |
| `initiative_exists` mkdirs on read | L4 | — | (I found; theirs didn't call out) |
| `find_project_config` skips root | L5 | — | (I found; theirs didn't call out) |

---

## C. What the photo plan MISSED (my plan's unique value)

These are **not** in the photo plan. They're worth adding as supplemental items:

1. **Path traversal in initiative name** (my H1) — `coworker initiative show "../../../../tmp/secret"` reads `/tmp/secret.yaml`; `remove --force` deletes it. **Security: arbitrary file read/write/delete.** The photo plan's P10 covers the initiative subsystem but does NOT mention name sanitization. **This is my most important unique finding.**
2. **`get_db()` never creates the schema** (my C3) — on a fresh DB, every analytics subcommand except `create-db` crashes with `no such table: sessions`. The photo plan's P1 fixes imports+keys but doesn't explicitly call out making `get_db()` idempotently run `SCHEMA`. (Their fixes may indirectly help, but the explicit bootstrap-in-`get_db` fix isn't stated.)
3. **Claude-JSONL importer writes no `tool_calls` rows** (my M6) — dashboard `/api/tools` is empty for Claude sessions.
4. **`bash_count` always 0, `tool_count` undercounts** (my M7) — Bash misclassified as file op; tool_count excludes Skill/Task/WebFetch.
5. **`skill_count` semantics differ between importers** (my M8) — invocations vs unique names; cross-session comparison meaningless.
6. **OpenCode sessions imported with NULLs → "Project: None" in LLM prompts** (my M9) — `knowledge.build_summary_prompt` renders literal `"Project: None"`.
7. **No `busy_timeout`** (my M11) — "database is locked" under concurrent writer (daemon + import).
8. **All file I/O missing `encoding="utf-8"`** (my M1) — breaks on Windows / non-UTF-8 locales. (The photo plan targets macOS bash, so this is lower priority for them but still real.)
9. Minor: `find_project_config` root-edge (L5), `initiative_exists` mkdir-on-read (L4), unbounded `limit` query (L17), Glob `file_ops` not recorded (L14), hand-rolled YAML parser (L15).

---

## D. What my plan MISSED (the photo plan's unique value — the big gaps)

These are the items I did **not** find. Grouped by why I missed them.

### D1. Entire categories I didn't audit at all
- **Shell scripts** (`setup/install.sh`, `uninstall.sh`, `update.sh`) — I only glanced at `install.sh` for the GH1 side-finding. The photo plan found: bash 3.2 `declare -A` crash (P6), `origin main` vs `master` silent no-op (P7), phantom `coworker import-mcp` (G2), hook-array assignment overwrites (P9), uninstall removes 0 files then deletes user hooks (P8).
- **Test infrastructure rot** (H2) — I ran the tests and saw 2 failures but didn't diagnose the *causes*: tuple-comma bug, `or True`, wrong hook-schema assertion, non-hermetic `$HOME`. The photo plan fixes the suite itself.
- **CI / licensing / packaging** (H1, P12) — no LICENSE, no CI, no wheel-smoke job. I missed all of it.
- **Skills content quality** (G3, G4, G11) — diverged skills across two repos, bundled skills never reaching Claude Code, four frontmatter dialects. I didn't audit `skills/` content.
- **README/blueprint honesty** (G6, G8) — overclaimed IDE support, token/cost/knowledge features that don't exist, `--break-system-packages` install docs. I didn't cross-check claims vs. code.
- **The `backup.py` safety layer** (F-BACKUP) — a whole architectural pattern (snapshot/manifest/ownership) I didn't conceive.

### D2. Deeper analysis I didn't do on files I DID audit
- **`semantic_merge` corruption bugs** (P3) — I flagged it as dead code (L1) but didn't analyze *how* it corrupts (fence-blind parsing, duplicate-heading collapse, empty-section deletion, dead `OUTDATED` class). The photo plan rewrites it properly.
- **PROTECTED block-spanning markers broken** (P4) — **major correctness/security issue I missed.** The PROTECTED span wraps 6 sections but `classify_sections` only checks each section's own body for the `<!-- PROTECTED` literal, so interior sections are unprotected → "Never push to main/master" is rewritable. This is the tool's core promise.
- **`coworker upgrade` is dead code + dead regex** (G1) — I noted semantic_merge was dead but didn't trace that the upgrade skill's template-extraction regex silently yields empty (install.sh builds the var via `$(python3 -c)` since commit `81e946e`), so global CLAUDE.md is never updated after first install.
- **`sync` clobbers settings — privilege escalation** (P5) — I found the hooks-dict assumption (L6) and atomic-write gap (M2) but **missed**: `permissions.allow` replaced wholesale with a default including `Write(*)`/`Read(*)` (silent privilege escalation), the Stop hook written in the wrong shape (never fires), MCP written to `settings.json` where Claude Code doesn't read it (real location `~/.claude.json`/`.mcp.json`), and Gemini `mcpServers` replaced wholesale.
- **Initiative split-brain** (P10 sub-issue 1) — `.active` is a single global marker but activation only edits the current project's `CLAUDE.local.md`, so activating B leaves A's stale block. I found the swallowed-error half (H5) but not the split-brain half.
- **Global Stop hook litters every repo** (G9) — `state-update` writes `docs/state/state-<minute>.md` relative to whatever cwd the session stopped in, including non-coworker repos. Currently masked by P5's malformed hook. I missed this entirely.
- **Self-heal false-positive detector** (G12) — greps raw JSON for `\b(no|stop|wrong|...)\b`, fires on "there is no config file". I didn't audit the hook's detector logic.
- **Injected STATIC block describes nonexistent things** (G5) — `_build_static_block` tells the AI about `personal/skills/`, `.cursor/rules/` auto-loading, a 5-stage pipeline, `create-skill` — none exist. Plus duplicates ~55 lines of Karpathy text per project. I didn't audit the *content truthfulness* of generated instructions.
- **Three docs/ conventions drift** (G13) — init scaffolds `docs/specs/`, static block advertises `docs/architecture|spec|planning`, repo uses `docs/spec/`+`docs/plan/`. I noted docs/ tracked in git (T1) but missed the convention drift.
- **Session mis-attribution** (P11) — hooks resolve session as `ls -t | head -1` (newest dir) when `SESSION_ID` unset; Claude Code never sets it; concurrent sessions interleave into one record. I found skill double-counting (H3) but not the upstream attribution bug.
- **Upgrade skill's 5 stale assumptions** (G10) — I found the hardcoded path (GH1) but missed: `~/.config/walter-worker` paths (copy-paste leakage), `init --project`-as-generator writing files mid-upgrade, Phase 7 calling the Click object as a plain function.

### D3. Calibration differences
- I labeled 6 items "Critical"; the photo plan treats most of those as HIGH and reserves true-critical for the data-loss class. Their calibration is more accurate: e.g. my C3/C4 (DB bootstrap) are real but fixable in 20 min — not "critical" in the same sense as P4 (PROTECTED guarantee broken) or P8 (uninstall deletes user hooks).
- The photo plan's phase ordering (safety net first, then dangerous work) is a workflow design I didn't provide.

---

## E. Recommendation

1. **Adopt the photo plan as the authoritative work order.** It's broader, deeper, already-executed, and has the `As-built`/`Field Notes` institutional knowledge.
2. **Fold my unique findings in as supplemental items**, in priority order:
   - **H1 (path traversal)** — security; add to P10's initiative work or a standalone PR. Highest priority of my unique items.
   - **C3 (get_db schema bootstrap)** — confirm whether the photo plan's P1 implicitly fixes this; if not, add an explicit `get_db()` idempotent-schema step.
   - **M6/M7/M8 (analytics count correctness)** — pair with P11 (session attribution) since they're the same import pipeline; do after P11.
   - **M9 (NULL→prompt)** — pair with G6b (knowledge layer).
   - **M11 (busy_timeout)** — trivial, fold into the analytics PR.
   - **M1 (encoding=utf-8)** — batch cleanup PR.
3. **For the junior engineer**: give them the **photo plan** as the primary doc, plus my `2026-07-07-walter-worker-fix-plan.md` §"What my plan found that the photo plan missed" as a supplemental checklist. The path-traversal item should be filed as its own GitHub issue.

---

## F. Why my audit missed so much (retrospective)

- **Scope was too narrow.** I limited the audit to `src/coworker/**` Python. The photo plan audited the *whole product*: shell scripts, skills content, README/blueprint claims, CI, packaging. A tool's bugs aren't only in its Python.
- **Didn't cross-check claims vs. reality.** README/blueprint overclaims (G6/G8) and the static block's phantom features (G5) require comparing marketing text to code — I didn't do that pass.
- **Didn't analyze the merge engine's correctness**, only noted it was dead code. The PROTECTED-span bug (P4) is the kind of thing that only surfaces when you ask "does this actually protect what it claims?"
- **Didn't trace data flow end-to-end.** The settings-clobber chain (P5), the session-attribution chain (P11), and the upgrade-dead-regex chain (G1) each require following a value across 3+ files; my per-file audit stopped at each file's boundary.
- **Didn't look at test quality**, only test results. The photo plan's H2 (self-neutralized asserts, non-hermetic HOME) is a whole class of "tests pass but prove nothing" that I didn't consider.
- **Two parallel agents gave breadth but not depth.** The photo plan's single deeper analysis (from `CICIDI-IMPROVEMENTS.md`) caught chains my parallel agents didn't.
