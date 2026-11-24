---
feature: core-cli
type: impl-plan
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Core CLI — Implementation Plan

This plan was written after the code shipped. Each task records a unit of work that exists at commit `a0f4ce0`, what it depends on, what it blocks, and the test that proves it. Behavior is defined in the [design](../design/core-cli-design.md).

## Global Constraints

No configuration command makes a network call. A command that overwrites a user-visible file takes a backup first (ARD-C). Settings files are merged, never replaced, and entries the user wrote are never removed (ARD-B).

## Acceptance Criteria

The feature is not done while the blocking open question QUES-A is open. Beyond that, it is done when the tasks below are done, the pytest suites in their Verify lines pass, and every other open question is fixed or explicitly accepted by the owner.

## Execution order

IMPL-A and IMPL-B first, because every other command reads the configuration and writes through backups. IMPL-C to IMPL-H depend on them and can proceed in parallel. IMPL-I depends on nothing and can run at any time.

## IMPL-A — Configuration model and merge

Load, validate, and merge the global and project files (DSGN-B). Depends on nothing. Blocks IMPL-C to IMPL-F.

Verify: `tests/python/test_config.py` `test_project_overrides_global_mcp_same_name`, `test_project_skills_dedup_by_name`, and `test_project_empty_permissions_do_not_override` pass.

## IMPL-B — Backups

Snapshot files before overwriting, keep twenty per label, never prune `pristine` (ARD-C, DSGN-H). Depends on nothing. Blocks IMPL-C, IMPL-D, IMPL-G, and IMPL-H.

Verify: `tests/python/test_backup.py` `test_invalid_label_rejected` and `test_deliberate_snapshots_and_pristine_survive` pass.

## IMPL-C — `init`

Global and project initialization with the scan, confirmation, and protected `CLAUDE.md` handling (DSGN-A). Depends on IMPL-A and IMPL-B. Blocks nothing.

Verify: `tests/python/test_init_command.py` `test_init_project_creates_coworker_dir`, `test_init_project_idempotent`, and `test_init_over_handwritten_claude_md_backs_up` pass.

## IMPL-D — `sync` adapters

The Claude Code, Gemini, and OpenCode adapters with managed MCP pruning (DSGN-C). Depends on IMPL-A and IMPL-B. Blocks nothing.

Verify: `tests/python/test_adapter_sync_safety.py` `test_permissions_user_entries_survive`, `test_foreign_hook_survives_sync`, and `test_identical_write_is_a_noop` pass, and `tests/python/test_gemini_adapter.py` `test_the_users_server_is_never_removed` passes.

## IMPL-E — `status` and `project`

The read-only summary and the catalog commands (DSGN-D, DSGN-E). Depends on IMPL-A. Blocks nothing.

Verify: `tests/python/test_cli.py` `TestStatus::test_status`, `test_project_add_duplicate`, and `test_project_sync` pass.

## IMPL-F — `skill` and the review queue

Listing, scaffolding, and the approve and reject flow with its safety check (DSGN-F). Depends on IMPL-A. Blocks nothing.

Verify: `tests/python/test_cli.py` `test_skill_new_duplicate` passes, and `tests/python/test_pending.py` `test_approve` and `test_staging_stops_after_the_limit` pass.

## IMPL-G — `upgrade`

The section merge, plan, dry run, confirmation, backup, and protected-span verification (DSGN-G). Depends on IMPL-B. Blocks nothing.

Verify: `tests/python/test_upgrade_command.py` `test_upgrade_dry_run_writes_nothing`, `test_a_line_inserted_mid_section_survives`, and `test_force_takes_the_template_version` pass.

## IMPL-H — `restore`

Resolve a backup by path, folder, or label and copy it back after confirmation (DSGN-H). Depends on IMPL-B. Blocks nothing.

Verify: `tests/python/test_cli.py` `test_it_restores_by_label` and `test_an_unknown_backup_is_an_error` pass.

## IMPL-I — `state-update`

The managed-project gate and the daily state file (DSGN-I). Depends on nothing. Blocks nothing.

Verify: `tests/python/test_state_update.py` `test_state_update_noop_outside_coworker` and `test_two_stops_one_file` pass, and `tests/python/test_cli.py` `test_writes_to_the_root_not_the_cwd` passes.

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft (never committed) |
| 0.2 | 2026-11-24 | Rewritten as a record of shipped work with Verify lines; added Acceptance Criteria (ARD-A) |
