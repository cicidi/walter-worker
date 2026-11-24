---
feature: core-cli
type: test-plan
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Core CLI — Test Plan

Each case names the requirement from the [PRD](../prd/core-cli-prd.md) it covers and the pytest test that implements it at commit `a0f4ce0`. Command tests use Click's test runner against a temporary home directory.

## Test Cases

| ID | Covers | Case | Pytest test |
|---|---|---|---|
| **TST-A** | PRD-A | `init --global` creates the global configuration and does not overwrite it | No test yet |
| **TST-B** | PRD-B | `init --project` creates the project configuration, is repeatable, backs up a hand-written `CLAUDE.md`, and keeps the user's text in `CLAUDE.local.md` | `test_init_command.py` `test_init_project_creates_coworker_dir`, `test_init_project_idempotent`, `test_init_over_handwritten_claude_md_backs_up`; `test_cli.py` `test_user_text_survives_a_second_init` |
| **TST-C** | PRD-C | Project servers replace same-named global ones, global skills win a clash, and empty project permissions do not override | `test_config.py` `test_project_overrides_global_mcp_same_name`, `test_project_skills_dedup_by_name`, `test_project_empty_permissions_do_not_override` |
| **TST-D** | PRD-D | Sync keeps the user's permissions, hooks, and MCP servers, writes the state-update hook once, writes MCP to `~/.claude.json`, and skips identical writes | `test_adapter_sync_safety.py` `test_permissions_user_entries_survive`, `test_foreign_hook_survives_sync`, `test_state_update_hook_deduped`, `test_mcp_written_to_claude_json_not_settings`, `test_identical_write_is_a_noop` |
| **TST-E** | PRD-D | A retired server walter-worker wrote is removed and the user's server never is | `test_gemini_adapter.py` `test_our_retired_server_is_removed`, `test_the_users_server_is_never_removed` |
| **TST-F** | PRD-D | An adapter failure is reported and the command still finishes | `test_cli.py` `test_sync_adapter_error`, `test_failure_is_the_last_thing_said` |
| **TST-G** | PRD-E | No configuration command makes a network call | No test yet; checked by reading the code |
| **TST-H** | PRD-F | `status` prints and reads the configured analytics database | `test_cli.py` `TestStatus::test_status`, `test_the_scan_reads_the_resolved_path` |
| **TST-I** | PRD-G | Catalog commands reject duplicates and unknown names, and `project sync` writes the static block | `test_cli.py` `test_project_add_duplicate`, `test_project_remove_missing`, `test_project_show_missing`, `test_project_sync` |
| **TST-J** | PRD-H | `skill new` refuses to overwrite; approval promotes the skill to both command folders, and rejection marks the item rejected | `test_cli.py` `test_skill_new_duplicate`; `test_pending.py` `test_approve`, `test_reject`, `test_promote_writes_to_both` |
| **TST-K** | PRD-I | A dry run writes nothing, a non-terminal run without `-y` refuses, a user's inserted line survives, `--force` takes the template, and a protected-span violation stops the command without writing | `test_upgrade_command.py` `test_upgrade_dry_run_writes_nothing`, `test_upgrade_no_tty_without_yes_refuses`, `test_a_line_inserted_mid_section_survives`, `test_force_takes_the_template_version`; `test_cli.py` `test_upgrade_protected_block_violation` |
| **TST-L** | PRD-J | Restore by label works, an unknown backup is an error, and declining leaves the file alone | `test_cli.py` `test_it_restores_by_label`, `test_an_unknown_backup_is_an_error`, `test_declining_leaves_the_file_alone` |
| **TST-M** | PRD-K | State update is silent in a folder with no marker up to a home folder that has no `.coworker/`, writes one file for two stops, and writes at the project root | `test_state_update.py` `test_state_update_noop_outside_coworker`, `test_two_stops_one_file`; `test_cli.py` `test_writes_to_the_root_not_the_cwd` |
| **TST-N** | PRD-K | State update writes nothing from an unmanaged repository under a home folder that has `~/.coworker/` | No test yet; fails today (QUES-L) |
| **TST-O** | PRD-I | `upgrade` never discards a user's line in a section both the user and the template changed, unless `--force` is given | No test yet; fails today (QUES-M) |
| **TST-P** | PRD-D | Sync keeps or migrates a user's `mcpServers` block found in Claude Code's `settings.json` | No test yet; fails today (QUES-O) |
| **TST-Q** | PRD-G | `project sync` leaves the user's text after a START marker that has no END marker | No test yet; fails today (QUES-S) |
| **TST-R** | PRD-G | `project add`, `edit`, and `remove` keep the catalog's comments and unknown keys, or back the file up first | No test yet; fails today (QUES-T) |

Not covered today: `init --global` (TST-A), an invalid configuration (QUES-C), the `skill pending`, `approve`, and `reject` commands at the command level, the upgrade mix of a conflict with an overwrite (QUES-A), and `status` with an active feature beyond a smoke test. Also untested: a protected span below a section whose line count changes (QUES-N), keys outside `extra` in the per-tool sections and the unused `claude` section (QUES-P), approving a rejected item (QUES-Q), the `--approve-all` count with a failing item and the `--type` filter (QUES-R; `test_pending.py` `test_batch_approve` covers only items that pass), a skill folder with a subfolder (QUES-J), global skills under `sync --project` (QUES-U), `restore` of a directory outside the backups folder (QUES-V), and a skill name containing `..` (QUES-W). Two tests pin today's behavior that an open question disputes: `test_semantic_merge.py` `test_non_placeholder_different_body_triggers_overwrite` (QUES-M) and `test_claude_adapter.py` `test_replace_or_append_truncated_block_appends_after_start` (QUES-S). The open questions are in the [design](../design/core-cli-design.md#open-questions).

## Test Execution Order

Run `test_config.py` and `test_backup.py` first, because every command builds on them. Then the adapter suites, then `test_init_command.py`, `test_upgrade_command.py`, `test_state_update.py`, `test_pending.py`, and finally `test_cli.py`.

## Expected Pass Threshold

Every case with a test must pass; the threshold is 100%. TST-A and TST-G have no test, so PRD-A and PRD-E are not yet verified by automation. TST-N to TST-R have no test and would fail against the code at `a0f4ce0`; each is tied to a blocking open question.

## Traceability

| Requirement | Test cases |
|---|---|
| PRD-A | TST-A |
| PRD-B | TST-B |
| PRD-C | TST-C |
| PRD-D | TST-D, TST-E, TST-F, TST-P |
| PRD-E | TST-G |
| PRD-F | TST-H |
| PRD-G | TST-I, TST-Q, TST-R |
| PRD-H | TST-J |
| PRD-I | TST-K, TST-O |
| PRD-J | TST-L |
| PRD-K | TST-M, TST-N |

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft (never committed) |
| 0.2 | 2026-11-24 | Rewritten with one case per requirement, mapped to pytest tests, untested behavior listed (ARD-A) |
| 0.3 | 2026-11-24 | Review fixes: TST-J no longer cites the staging-limit test; TST-K says "stops without writing"; TST-N to TST-R added for the blocking gaps; untested behavior extended (ARD-F) |
