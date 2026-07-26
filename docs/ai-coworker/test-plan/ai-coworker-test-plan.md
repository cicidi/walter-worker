# ai-coworker Test Plan

## Change Log

| Date       | Version | Description |
|------------|---------|-------------|
| 2026-07-25 | 1.0     | Initial test plan. Based on development history through 2026-07-25. Covers all identified testing strategies, key scenarios, quality gates, tools, and bug patterns. |

---

## 1. Testing Strategy

The project follows a **three-tier testing pyramid** augmented with **acceptance** and **smoke** tests. The strategy aligns with the development history, which shows explicit unit, integration, and end-to-end (e2e) test runs, as well as acceptance gates.

### 1.1 Unit Tests
- **Scope**: Individual functions, classes, and methods (e.g., semantic merge engine, skill installer, analytics pipeline components, dashboard data processing).
- **Coverage target**: ≥ 96% (achieved via “300+ new tests across 10 modules” on 2026-07-25).
- **Examples from history**:
  - `fix(P1)`: “relative imports + stats keys + fresh-DB bootstrap + smoke test”
  - `fix(P3)`: “rewrite semantic_merge — fence-aware ordered parse, round-trip, protected ranges + verify”
  - `fix(tests)`: “restore cwd in test_scaffold_conforms (monkeypatch fixture) — fixes 3 state_update failures”
- **Framework**: pytest (with fixtures, monkeypatch, tmp_path).

### 1.2 Integration Tests
- **Scope**: Interaction between subsystems – skills ↔ install mechanism, analytics daemon ↔ database, CLI ↔ configuration files, dashboard ↔ backend API.
- **Key examples**:
  - Hermetic install fixture (`fix(H2): hermetic install fixture + fix dead/wrong asserts`)
  - Skill sync and rename detection (`fix: skill sync without --delete, detect renames via content hash`)
  - Analytics auto-import daemon with checkpoint (`feat: analytics auto-import daemon with checkpoint`)
  - Session import from Claude Code JSONL (`feat: import Claude Code native JSONL sessions`)
- **Approach**: Isolation using temporary directories (tmp_path), mock LLM calls (DeepSeek), in‑memory SQLite databases.

### 1.3 End-to-End (E2E) Tests
- **Scope**: Full user workflows – install ai-coworker, run a skill, verify output, tear down.
- **Explicit evidence**:
  - `feat: add knowledge skill, e2e tests (3/3 passing)`
  - `reviews: 6/6 tests PASS` (combined unit + e2e)
  - “36 tests PASS” (mix of unit, integration, e2e)
- **Tooling**: Minimal CLI invocations; possibly `pytest` with shell fixtures or custom runners.

### 1.4 Smoke Tests
- **Scope**: Quick sanity checks after installation or upgrades.
- **Examples**:
  - `smoke test` part of `fix(P1)`.
  - `feat: add analytics installer integration, uninstall cleanup, install verification tests (5/5 PASS)` → install/uninstall verification is a smoke test.

### 1.5 Acceptance Tests
- **Scope**: Validation against signed acceptance criteria.
- **Evidence**: “11/12 criteria SIGNED” → “12/12 criteria SIGNED, 36 tests PASS, 0 blockers”.
- **Process**: Criteria defined in planning docs (e.g., PRD, spec), then manual/automated verification during review.

---

## 2. Key Test Scenarios

Listed by functional area, with references to decisions that motivated or validated them.

### 2.1 Skill Lifecycle
- **Install skill**: Validate that `coworker install <skill>` copies files to the correct location, updates manifest, fires hooks.
- **Uninstall skill**: Remove files, restore original hooks, verify no orphan state.
- **Import external skill** (`meta-import-skill`): License check, auto-install, conflict detection.
- **Skill naming scheme** (`coworker-{category}`): Ensure all skills adhere to the new naming; upgrade from old names works.
- **Skill frontmatter format**: Dual-format (Claude Code + OpenCode) parsing passes for all skills.

### 2.2 Init & Configuration
- **`coworker init`**: Auto‑detect language, dependencies, IDE; generate `CLAUDE.md`, `.local_config.yaml`, and hooks.
- **Three-layer CLAUDE.md**: Verify that global → project → local files are merged correctly and that the local file can override the project file.
- **Environment variables**: Hardcoded personal paths removed (`fix(H4)`); parameterized paths work across machines.

### 2.3 Analytics & Dashboard
- **Analytics import pipeline**: Collect session data from OpenCode / Claude Code, parse JSONL, store in SQLite.
- **Session deduplication**: LLM‑based semantic dedup using DeepSeek (`fix(analytics): session dedup + LLM semantic knowledge dedup`).
- **Dashboard views**: Session Monitor, Projects, Hotspots, Errors, Memory Control, Cost/Token, Model/IDE, Efficiency, Data Quality – all correct data fetched from correct DB columns.
- **DB schema consistency**: Column names (`op_type → op`, `file_path → path`) match actual migration (`fix(dashboard): correct DB column names`).

### 2.4 Initiative & Project Management
- **Initiative migration**: Migrate from global‑level to project‑level storage; data integrity after migration.
- **Project catalog**: `bug-report` supports any repo via catalog – verify catalog loading.

### 2.5 Self-Heal & Development Loop
- **Self-heal hooks**: Global hooks for Claude Code / OpenCode; auto‑inject to `CLAUDE.md`.
- **Auto-worker**: Spec‑compliant Claude SDK agent with safety gates, metrics, skill CLI.
- **Polish loop**: QA PROTECTED heuristic flags only marker removals, not legitimate changes.

### 2.6 CLI Commands
- 18 CLI command skills (analytics, initiative, project, status) – test each command with valid/invalid arguments.
- `coworker upgrade` – merge engine wired to CLI (`fix(G1)`).

### 2.7 State & File Management
- **State file naming**: `state-{task}.md` in `docs/state/`; auto‑timestamp to avoid session collisions.
- **Semantic merge**: Fence‑aware, ordered, round‑trip, protected ranges – verify with forced edge cases (nested fences, missing close markers).

---

## 3. Quality Gates / Acceptance Criteria

Based on the signed criteria in the development timeline (11→12 criteria).

| Gate | Condition | Measured by |
|------|-----------|-------------|
| **G1: All Tests Pass** | 0 failures across unit, integration, e2e suites. | Automated CI run (pytest exit code). |
| **G2: No Blockers** | No open P0/P1 bugs. | GitHub issues / tracker. |
| **G3: Coverage ≥ 96%** | Line coverage for core modules (skills, analytics, dashboard). | `pytest --cov` report. |
| **G4: Acceptance Criteria Signed** | All PRD/spec criteria met and signed off by reviewer. | Review checklist (12 items). |
| **G5: Smoke Test Passes** | Minimal install → run → uninstall cycle works on a fresh environment. | Manual or automated script. |
| **G6: Security / Safety** | No hardcoded personal paths; license checks on imported skills; hook‑ownership safety. | Code review + assertions. |
| **G7: Performance** | Analytics import handles sessions up to 1 MB without truncation (fix: “remove 8000 char truncation”). | Load test. |
| **G8: Compatibility** | Bash 3.2+ (macOS default) supported – no `declare -A`. | Shell syntax linter. |
| **G9: Documentation** | README, blueprint, and changelog reflect current architecture; no overclaimed features. | Editorial review. |
| **G10: Install & Uninstall** | Verify install verification tests (5/5 pass); clean teardown after uninstall. | `fix(G2)`, `fix(P8)`. |
| **G11: State Consistency** | State files are timestamped and never collide. | Automation test with concurrent runs. |
| **G12: Dashboard Correctness** | All views return expected data with correct field names. | E2E dashboard tests. |

---

## 4. Tools and Frameworks Used

| Tool / Framework | Purpose | Evidence in History |
|------------------|---------|---------------------|
| **pytest** | Primary test runner (unit, integration, e2e) | `fix(tests): restore cwd in test_scaffold_conforms (monkeypatch fixture)` – implies pytest fixtures. |
| **pytest-monkeypatch** | Environment/temp isolation | Same commit as above. |
| **pytest-cov** | Coverage measurement | Coverage target achieved. |
| **tox / nox** (likely) | Multi‑environment testing | Not explicit, but common with CI. |
| **GitHub Actions** | CI – automated test runs | `fix(H1): add … CI`. |
| **SQLite (in‑memory)** | Test database isolation | Integration tests use fresh DB bootstrap (`fix(P1)`). |
| **DeepSeek / LLM** | Semantic dedup verification | `fix(analytics): session dedup + LLM semantic knowledge dedup`. |
| **ShellCheck** / bash linting | Bash 3.2 compatibility | `fix(P6): bash 3.2 compat — replace declare -A with indexed arrays`. |
| **Hermetic install fixture** | Custom pytest fixture to simulate install/uninstall | `fix(H2): hermetic install fixture + fix dead/wrong asserts`. |
| **content‑hash rename detection** | Skill sync without `--delete` | `fix: skill sync without --delete, detect renames via content hash`. |
| **pre‑commit hooks** (likely) | Code quality | Not explicit, but consistent with project discipline. |

---

## 5. Bug Patterns Found and How They Were Fixed

The development history reveals several recurring bug categories. Each pattern below includes the root cause and the applied fix.

### 5.1 Hardcoded Paths and Environment Assumptions
- **Pattern**: Personal home paths (`/Users/cicidi/…`), absolute paths in configuration.
- **Impact**: Unportable, breaks on other machines.
- **Fix**: Parameterize with environment variables (`$HOME`, `$(whoami)`, config files).  
  *Decision*: `fix(H4): remove hardcoded personal paths; parameterize with env vars`.

### 5.2 Database Schema Mismatches
- **Pattern**: Column names in code differ from actual DB schema (e.g., `op_type` vs `op`, `file_path` vs `path`).
- **Impact**: Dashboard shows empty/missing data.
- **Fix**: Correct column names in SQL queries; add migration step or use constants.  
  *Decision*: `fix(dashboard): correct DB column names — op_type→op, file_path→path`.

### 5.3 Truncation and Data Loss
- **Pattern**: 8000-character limit on message import; data truncated silently.
- **Impact**: Loss of session context, incomplete analytics.
- **Fix**: Remove truncation; store full message content.  
  *Decision*: `fix: remove 8000 char truncation on OpenCode message import`.

### 5.4 Bash Compatibility
- **Pattern**: Use of `declare -A` (associative arrays) requires Bash 4, but macOS (default shell) is Bash 3.2.
- **Impact**: Installation script fails on macOS.
- **Fix**: Replace with indexed arrays and separate key/value lists.  
  *Decision*: `fix(P6): bash 3.2 compat — replace declare -A with indexed arrays`.

### 5.5 State File Collisions
- **Pattern**: Multiple sessions write to the same state file (e.g., `state-task.md`).
- **Impact**: Overwritten state, concurrent session corruption.
- **Fix**: Auto‑timestamp state filenames (e.g., `state-{task}-{epoch}.md`).  
  *Decision*: `fix: auto-timestamp state files to prevent session collisions`.

### 5.6 Broken Import/Missing Dependencies
- **Pattern**: Phantom import references (`import-mcp` skill no longer exists), missing `fi` in shell script blocks.
- **Impact**: Installation fails; tests fail with ImportError.
- **Fix**: Delete stale references, restore correct syntax.  
  *Decisions*: `fix(G2): remove phantom import-mcp, fix core skill path, fix banner` and `fix(G2): restore missing fi — install.sh MCP block syntax`.

### 5.7 Inconsistent Frontmatter and Doc Types
- **Pattern**: Skills had old naming schemes, mixed doc types (e.g., `doc-review`, `flow-*`).
- **Impact**: Claude Code cannot discover skills; documentation becomes hard to navigate.
- **Fix**: Canonical frontmatter schema, migration script, merge of doc types (9 types).  
  *Decisions*: `fix(G11): canonical frontmatter schema + migration + scaffold fix`, several refactors merging types.

### 5.8 Threading / Test Isolation Issues
- **Pattern**: Tests that modify global state (like `os.chdir`) cause cascading failures.
- **Impact**: 3 state_update tests failing because CWD not restored after test.
- **Fix**: Use monkeypatch fixture to restore CWD after each test.  
  *Decision*: `fix(tests): restore cwd in test_scaffold_conforms (monkeypatch fixture) — fixes 3 state_update failures`.

### 5.9 Overclaimed Documentation
- **Pattern**: README claimed features (e.g., token savings, knowledge graph) that were not yet implemented.
- **Impact**: Misleading users; unrealistic expectations.
-