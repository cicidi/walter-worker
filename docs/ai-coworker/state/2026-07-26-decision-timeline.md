# Decision Timeline — ai-coworker
> Generated: 2026-07-26 05:28:37 UTC
> Total decisions: 155

## Timeline

- 2026-07-25T22:22:15 🔀 fix(dashboard): restore original CSS (420→442 lines) and JS (531→560 lines)

- 2026-07-25T22:13:29 🔀 feat(dashboard): add Cost/Token, Model/IDE, Efficiency, Data Quality views

- 2026-07-25T22:06:10 🔀 fix: replace deprecated datetime.utcnow() with datetime.now(timezone.utc)

- 2026-07-25T22:03:22 🔀 feat(dashboard): add Projects, Hotspots, Errors, Memory Control views

- 2026-07-25T21:09:46 🔀 feat: spec-compliant auto-worker — Claude SDK agent, safety gates, metrics, skill CLI

- 2026-07-25T21:00:08 🔀 feat: add auto-worker skill (SKILL.md with 8 rules reference)

- 2026-07-25T19:53:11 🔀 feat: dashboard evolution page, auto-worker module, CLI commands — Waves 5-7

- 2026-07-25T19:40:45 🔀 feat(memory): capture layer, engine, injection, curator, training — Waves 2-4

- 2026-07-25T19:20:39 🔀 feat(memory): mem0 substrate + DeepSeek LLM client — Wave 1 foundation

- 2026-07-25T18:44:23 🔀 docs: complete self-evolving-agent design phase — PRD v7, spec v1.2, 3 design docs, impl-plan, test-plan

- 2026-07-25T17:49:57 🔀 feat: achieve 96%+ test coverage with 300+ new tests across 10 modules

- 2026-07-24T17:43:56 🔀 docs: add post-session skill creation trigger to PRD

- 2026-07-24T17:42:27 🔀 docs: fix PRD - auto-update targets CLAUDE.local.md not CLAUDE.md

- 2026-07-24T17:28:17 🔀 docs: add Chinese translation of self-evolving-agent PRD v2

- 2026-07-24T17:26:39 🔀 docs: revise self-evolving-agent PRD v2 based on adversarial review

- 2026-07-24T11:38:57 🔀 docs: add skill placement guide and doc-organize template conventions

- 2026-07-24T00:00:00 💬 Remove budget flags from SDK mode CLI example

- 2026-07-24T00:00:00 💬 Remove 'Budget exhausted' from termination conditions

- 2026-07-24T00:00:00 💬 Remove Budget Guards subsection entirely

- 2026-07-24T00:00:00 💬 Replace Cost Model section with simplified version

- 2026-07-24T00:00:00 💬 Update termination conditions to reference the 12h default max-time

- 2026-07-24T00:00:00 💬 Perform infrastructure reuse analysis and update PRD Section 7

- 2026-07-24T00:00:00 💬 Update all PRD documents (zh.md, en.html, zh.html, design doc) to v3 in parallel

- 2026-07-17T13:27:48 🔀 docs: add doc-organize + INDEX.md refs to CLAUDE.md and global template

- 2026-07-17T13:25:38 🔀 docs: generate INDEX.md with full paths and content summaries

- 2026-07-17T12:59:19 🔀 refactor: add -type suffix to all doc filenames

- 2026-07-17T12:07:02 🔀 refactor: reorganize docs/ using doc-organize conventions (9 types, no dates)

- 2026-07-17T09:51:05 🔀 refactor: move 22 general skills to skill-factory, keep 5 core

- 2026-07-17T09:50:29 🔀 refactor: remove 4 skills already in skill-factory

- 2026-07-17T09:49:34 🔀 refactor: move doc-organize to skill-factory (general-purpose skill)

- 2026-07-17T09:49:06 🔀 fix: remove residual old naming patterns and evidence folder refs

- 2026-07-17T09:47:33 🔀 refactor: merge why-this into decision-history (9 types)

- 2026-07-17T09:47:00 🔀 refactor: merge hld/lld into design type with .hld.md/.lld.md suffixes (10 types)

- 2026-07-17T09:46:21 🔀 refactor: evidence as .evidence.md suffix, not standalone type (11 types)

- 2026-07-17T09:44:41 🔀 refactor: merge compare into research type (12 types total)

- 2026-07-17T09:43:42 🔀 docs: add 4 realistic examples to doc-organize skill

- 2026-07-17T09:43:15 🔀 fix: simplify doc naming — initiative is container, filename is specific topic

- 2026-07-17T09:39:49 🔀 chore: comprehensive cleanup and upgrade

- 2026-07-17T09:39:30 🔀 feat: upgrade skill frontmatter to Claude Code + OpenCode dual format

- 2026-07-17T00:39:17 🔀 refactor: install skills to ~/.claude/skills/ instead of commands/

- 2026-07-13T22:21:13 🔀 feat: add emoji and color-coded fields to tmux status bar

- 2026-07-13T22:16:31 🔀 feat: add --force flag to init for upgrading project CLAUDE.md

- 2026-07-13T22:00:28 🔀 feat: add "suggest next actions" to Development Loop template

- 2026-07-10T20:55:57 🔀 Merge pull request #6 from cicidi/experiment/claude-md-harness-optimization

- 2026-07-10T20:48:01 🔀 feat: enforce topic-based docs convention via initiative names

- 2026-07-10T20:39:06 🔀 docs: translate all Chinese to English + reorganize by topic

- 2026-07-10T20:23:20 🔀 docs: translate METHODOLOGY.md to english

- 2026-07-10T20:19:20 🔀 Merge pull request #5 from cicidi/experiment/claude-md-harness-optimization

- 2026-07-10T19:32:33 🔀 docs: comprehensive methodology report — APO experiment design, 7 rounds, session execution log

- 2026-07-10T00:44:26 🔀 feat: CLAUDE.md optimization — 95→60 lines (37% leaner), fix local.md regeneration Rounds 5-7: add Development Loop, fix

- 2026-07-10T00:41:49 🔀 refactor: leaner templates — merge sections, remove redundancies, 95→56 lines Round 2-4: merge Git/Code/Quality guardrai

- 2026-07-10T00:39:36 🔀 refactor: simplify CLAUDE.md templates — remove Info Flow table, condense sections, move project info to local.md Round 

- 2026-07-08T18:44:36 🔀 fix(analytics): session dedup + LLM semantic knowledge dedup (DeepSeek)

- 2026-07-08T18:27:42 🔀 fix(dashboard): bind to 0.0.0.0 by default + --host option

- 2026-07-08T12:35:53 🔀 Merge pull request #4 from cicidi/fix/s3-core-design-docs

- 2026-07-08T12:35:16 🔀 Merge pull request #3 from cicidi/fix/b1-state-update-tests

- 2026-07-08T12:34:52 🔀 Merge pull request #2 from cicidi/fix/fix-plan-round1

- 2026-07-08T04:24:42 🔀 fix(polish-loop): QA PROTECTED heuristic only flags marker removals

- 2026-07-08T04:15:46 🔀 docs: track core design specs + fix-plan

- 2026-07-08T00:47:34 🔀 chore: record B1 in CHANGELOG + per-cycle timeout in loop driver

- 2026-07-08T00:36:08 🔀 fix(tests): restore cwd in test_scaffold_conforms (monkeypatch fixture) — fixes 3 state_update failures

- 2026-07-08T00:36:08 🔀 fix(tests): restore cwd in test_scaffold_conforms (monkeypatch fixture) — fixes 3 state_update failures

- 2026-07-08T00:32:04 🔀 refactor(dashboard): remove root static/ (moved into package) + polish-loop infra

- 2026-07-08T00:20:24 🔀 fix(dashboard): correct DB column names — op_type→op, file_path→path

- 2026-07-08T00:19:16 🔀 feat(dashboard): session monitor — file ops, skill usage, unified timeline

- 2026-07-08T00:00:05 🔀 fix(G4): deploy bundle skills to Claude Code (index_skills $REPO_ROOT/skills)

- 2026-07-07T23:52:31 🔀 fix: add catch_exceptions=False to state-update tests

- 2026-07-07T23:51:45 🔀 fix(G6): README honesty — remove overclaimed token/cost/knowledge; add Roadmap

- 2026-07-07T23:43:09 🔀 fix(G13+G5): docs-dirs constant + static block from verified facts

- 2026-07-07T23:42:02 🔀 fix(G11): canonical frontmatter schema + migration + scaffold fix

- 2026-07-07T23:37:26 🔀 fix(P8): manifest-driven install/uninstall with hook-ownership safety

- 2026-07-07T23:33:55 🔀 fix(P5): settings ownership — permissions union, MCP location, atomic writes

- 2026-07-07T23:30:42 🔀 fix(G1): coworker upgrade command — merge engine wired to CLI

- 2026-07-07T23:11:04 🔀 fix(P3): rewrite semantic_merge — fence-aware ordered parse, round-trip, protected ranges + verify

- 2026-07-07T22:07:30 🔀 fix(H4): remove hardcoded personal paths; parameterize with env vars

- 2026-07-07T22:04:17 🔀 fix(G2): restore missing fi — install.sh MCP block syntax

- 2026-07-07T22:03:10 🔀 fix(G2): remove phantom import-mcp, fix core skill path, fix banner

- 2026-07-07T21:58:56 🔀 fix(P6): bash 3.2 compat — replace declare -A with indexed arrays

- 2026-07-07T21:57:06 🔀 fix(P2): init mkdir + sentinel constant + backup-before-overwrite

- 2026-07-07T21:27:35 🔀 fix(P1): relative imports + stats keys + fresh-DB bootstrap + smoke test

- 2026-07-07T21:23:55 🔀 fix(H2): hermetic install fixture + fix dead/wrong asserts

- 2026-07-07T21:17:25 🔀 fix(F-BACKUP): backup.py snapshot/restore safety net

- 2026-07-07T21:15:51 🔀 fix(H1): add LICENSE, MIT license, [test] extras, CONTRIBUTING, CI

- 2026-07-07T21:14:32 🔀 wip(P5): correct Stop hook shape in claude adapter + setup skill

- 2026-07-07T21:14:32 🔀 chore: gitignore pic/ (local screenshots)

- 2026-07-02T22:19:43 🔀 fix: auto-timestamp state files to prevent session collisions

- 2026-07-02T22:14:35 🔀 fix: keep state- prefix in state filenames (docs/state/state-{task}.md)

- 2026-07-02T15:23:41 🔀 fix: move state files to docs/state/ directory

- 2026-07-02T14:28:12 🔀 feat: refactor OpenCode plugin to v1 format, add state-update on compaction

- 2026-07-02T11:43:23 🔀 fix: worktree project detection uses main repo name

- 2026-07-02T09:24:00 🔀 fix: skill sync without --delete, detect renames via content hash

- 2026-07-02T09:18:32 🔀 feat: deploy tmux status bar with worktree support via install.sh

- 2026-07-02T09:10:12 🔀 feat: global initiatives, ai-coworker-fix skill, and fix-ai-coworker rule

- 2026-07-02T02:24:23 🔀 feat: three-layer CLAUDE.md architecture (Global → Project → Local)

- 2026-06-30T23:35:21 🔀 fix: deploy ai-coworker skills to opencode skill directory

- 2026-06-24T00:26:30 🔀 chore: review fixes — broken refs, tests, docs, changelog

- 2026-06-23T23:28:03 🔀 chore: remove self-strain

- 2026-06-23T23:26:25 🔀 refactor: rename self-patch to english-grammar-fix

- 2026-06-23T23:23:57 🔀 chore: delete connect-* integration skills

- 2026-06-23T23:22:35 🔀 chore: delete gate-review, gate-ship, gate-tests

- 2026-06-23T23:22:25 🔀 chore: gitignore .claude/hooks/

- 2026-06-23T23:22:14 🔀 docs: remove 5-stage pipeline from CLAUDE.md

- 2026-06-23T23:21:14 🔀 chore: delete flow-* development pipeline skills

- 2026-06-23T23:18:59 🔀 chore: delete doc-review skill

- 2026-06-23T23:18:11 🔀 refactor: bug-hunt — collect first, then reason with evidence

- 2026-06-23T23:16:30 🔀 refactor: merge bug-sleuth into bug-hunt

- 2026-06-23T23:15:19 🔀 refactor: bug-report supports any repo via project catalog

- 2026-06-23T23:14:57 🔀 refactor: merge bug-create into bug-report — unified issue creation

- 2026-06-23T23:09:53 🔀 feat: global self-heal hooks for Claude Code + OpenCode, project-level traces

- 2026-06-23T23:08:15 🔀 feat: rewrite self-heal + self-analyze — project-level traces, auto-hook, inject to CLAUDE.md

- 2026-06-23T22:57:54 🔀 feat: add session-memory skill to ai-coworker skills/

- 2026-06-23T22:54:46 🔀 feat: track file reads per session, distinguish skill vs prompt

- 2026-06-23T22:53:40 🔀 refactor: store session metadata only, not raw messages

- 2026-06-23T22:52:57 🔀 feat: import Claude Code native JSONL sessions (full messages + tool calls)

- 2026-06-23T22:52:11 🔀 fix: remove 8000 char truncation on OpenCode message import

- 2026-06-23T22:50:06 🔀 refactor: use DB as checkpoint, support incremental session updates

- 2026-06-23T22:48:09 🔀 feat: ask for DeepSeek API key during init, save to .local_config.yaml

- 2026-06-23T22:46:54 🔀 feat: add analytics auto-import daemon with checkpoint

- 2026-06-23T22:33:46 🔀 docs: add analytics/memory/autonomous-agent roadmap to docs

- 2026-06-23T22:32:52 🔀 docs: rewrite README and blueprint — ai-coworker is context manager, not dev tool

- 2026-06-23T22:29:48 🔀 docs: rewrite blueprint and README for current architecture

- 2026-06-23T22:29:06 🔀 docs: add README with install and usage guide

- 2026-06-23T22:28:00 🔀 chore: remove personal/skills-backup-2026-05-01

- 2026-06-23T22:27:45 🔀 feat: auto-scan in coworker init — detect language, deps, IDE, generate config

- 2026-06-23T22:23:01 🔀 refactor: replace flat coworker-init.md with skills/init/SKILL.md

- 2026-06-23T22:21:46 🔀 chore: remove install and import-mcp commands and skills

- 2026-06-23T22:19:40 🔀 feat: add 18 CLI command skills (analytics, initiative, project, status)

- 2026-06-23T22:14:52 🔀 chore: remove personal/skills/ from ai-coworker, skills live in skill-factory

- 2026-06-23T22:14:18 🔀 chore: remove global/ directory

- 2026-06-23T22:13:09 🔀 chore: remove .mcp.json, add to gitignore

- 2026-06-23T22:10:41 🔀 refactor: rename all skills to new naming scheme

- 2026-06-23T22:07:17 🔀 refactor: rename setup-coworker to init, delete duplicate create-skill files

- 2026-06-23T21:54:08 🔀 chore: remove docs/ and global/skills/commit/ from tracking, add to gitignore

- 2026-06-16T23:09:12 🔀 feat: replace 8-stage pipeline with 5-stage workflow, add docs/skills/karpathy to static context

- 2026-06-12T17:23:53 🔀 feat: add OpenCode context injection, InitiativeManager, initiative skills

- 2026-06-12T17:11:15 🔀 refactor: migrate initiative from global to project-level storage

- 2026-06-12T17:08:19 🔀 docs: add initiative global-to-project-level migration design

- 2026-06-12T01:58:47 🔀 review: ACCEPTED — 12/12 criteria SIGNED, 36 tests PASS, 0 blockers

- 2026-06-12T01:58:20 🔀 feat: add analytics installer integration, uninstall cleanup, install verification tests (5/5 PASS)

- 2026-06-12T01:48:19 🔀 review: acceptance — 6/6 tests PASS, 11/12 criteria SIGNED

- 2026-06-12T01:44:00 🔀 feat: add knowledge skill, e2e tests (3/3 passing)

- 2026-06-12T01:41:55 🔀 feat: add analytics listener, import pipeline, dashboard (backend + frontend)

- 2026-06-12T01:22:31 🔀 docs: add comprehensive implementation plan for analytics listener + dashboard

- 2026-06-12T01:16:54 🔀 docs: add skills, knowledge, session_summaries tables to support dashboard views

- 2026-06-12T01:13:55 🔀 merge: resolve docs directory conflict

- 2026-06-12T01:07:25 🔀 docs: reorganize to prd/spec/plan/test structure, add dashboard design mockups

- 2026-06-11T20:16:38 🔀 docs: finalize analytics listener design with DB schema and import pipeline

- 2026-06-11T19:55:58 🔀 docs: add SQLite database schema to analytics listener design

- 2026-06-11T19:53:50 🔀 docs: add analytics listener design spec

- 2026-06-11T19:35:10 🔀 chore: add .worktrees/ to .gitignore

- 2026-06-11T01:03:12 🔀 chore: cleanup project — remove photos, templates, migrate skills, optimize setup

- 2026-05-06T20:19:17 🔀 feat: add skill meta-import-skill — import external skills with license check and auto-install

- 2026-05-06T20:18:00 🔀 refactor: move all skills to public skills/ directory

- 2026-05-01T22:53:13 🔀 refactor: add skill restructure plan for coworker-{category} naming

- 2026-03-30T21:06:17 🔀 feat: initial commit — unified ai-coworker dev environment
