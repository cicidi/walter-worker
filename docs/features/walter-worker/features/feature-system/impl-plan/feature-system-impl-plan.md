---
feature: feature-system
type: impl-plan
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Feature System — Implementation Plan

This plan was written after the code shipped. Each task records a unit of work that exists at commit `a0f4ce0`, what it depends on, what it blocks, and the test that proves it. Behavior is defined in the [design](../design/feature-system-design.md).

## Global Constraints

Every file access goes through the name check in DSGN-A. Activation writes only the given project's `CLAUDE.local.md` and never text outside the feature markers. Records keep unknown keys across a load and save.

## Acceptance Criteria

The feature is done when the tasks below are done, the pytest suites listed in each Verify line pass, and the open questions in the design are each fixed or explicitly accepted by the owner. None of them is blocking.

## Execution order

IMPL-A first, because every command reads and writes records through it. IMPL-B depends on IMPL-A. IMPL-C and IMPL-D depend on IMPL-A and IMPL-B and can proceed in parallel. IMPL-E depends on all of them.

## IMPL-A — Records and names

Store records as YAML under `~/.coworker/features/`, enforce the name rule on every access, and keep unknown keys (DSGN-A, DSGN-B). Depends on nothing. Blocks IMPL-B to IMPL-E.

Verify: `tests/python/test_features_manager.py::test_create_invalid_name` and `tests/python/test_config.py` `test_load_save_preserves_unknown_keys` pass.

## IMPL-B — Block injection

Build the delimited block, remove every existing feature block, and place the new one at the placeholder or the end of `CLAUDE.local.md` (DSGN-D). Depends on IMPL-A. Blocks IMPL-C, IMPL-D, and IMPL-E.

Verify: `tests/python/test_local_claude_md.py` `test_inject_feature_replaces_previous` and `test_remove_feature_only_removes_specified` pass.

## IMPL-C — Commands

The eight subcommands with their options and exit statuses (DSGN-C). Depends on IMPL-A and IMPL-B. Blocks IMPL-E.

Verify: `tests/python/test_features_manager.py` `test_create_duplicate` and `test_activate_deactivates_previous_first` pass, and the `TestFeature*` classes in `tests/python/test_cli.py` pass.

## IMPL-D — Removal across projects

Deactivate in the current project, delete the record, and clear the block from other catalog projects after backing each file up (DSGN-E). Depends on IMPL-A and IMPL-B. Blocks IMPL-E.

Verify: `tests/python/test_features_manager.py::test_remove_deactivates_if_active` passes. The cross-project sweep and its backup have no test yet.

## IMPL-E — Old "initiative" name

Read the old folder in place, recognize old markers and the old placeholder, and keep the hidden `initiative` command group (DSGN-F). Depends on IMPL-A to IMPL-D. Blocks nothing.

Verify: `tests/python/test_local_claude_md.py` `test_legacy_placeholder_is_read_and_upgraded` and `tests/python/test_cli.py` `test_alias_mirrors_every_feature_subcommand` pass.

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft as `initiative-system` (never committed) |
| 0.2 | 2026-11-24 | Rewritten as a record of shipped work with Verify lines; added Acceptance Criteria (ARD-A) |
