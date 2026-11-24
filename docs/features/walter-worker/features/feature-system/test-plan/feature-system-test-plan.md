---
feature: feature-system
type: test-plan
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Feature System — Test Plan

Each case names the requirement from the [PRD](../prd/feature-system-prd.md) it covers and the pytest test that implements it at commit `a0f4ce0`. Tests run against a temporary home directory and project folder.

## Test Cases

| ID | Covers | Case | Pytest test |
|---|---|---|---|
| **TST-A** | PRD-A | An invalid name is rejected | `test_features_manager.py::test_create_invalid_name` |
| **TST-B** | PRD-B | A record survives a load and save with unknown keys intact | `test_config.py` `test_load_save_preserves_unknown_keys` |
| **TST-C** | PRD-C | Creating an existing name reports it and exits 0 | `test_features_manager.py::test_create_duplicate`; `test_cli.py` `TestFeatureCreate` |
| **TST-D** | PRD-D | `start` creates, scopes, and activates | `test_cli.py` `TestFeatureStart` |
| **TST-E** | PRD-E | Activating replaces the previous feature's block, and removing one block leaves another | `test_features_manager.py::test_activate_deactivates_previous_first`; `test_local_claude_md.py` `test_inject_feature_replaces_previous`, `test_remove_feature_only_removes_specified` |
| **TST-F** | PRD-E | A project with no block has no active feature | `test_features_manager.py::test_active_name_no_feature_in_file` |
| **TST-G** | PRD-F | Edit options change the record, and archiving sets the status | `test_cli.py` `TestFeatureEdit`, `TestFeatureArchive` |
| **TST-H** | PRD-G | `list` and `show` print without writing | `test_cli.py` `TestFeatureList`, `TestFeatureShow` |
| **TST-I** | PRD-H | Removing an active feature deactivates it first | `test_features_manager.py::test_remove_deactivates_if_active`; `test_cli.py` `TestFeatureRemove` |
| **TST-J** | PRD-I | The old placeholder is upgraded and old marker blocks are removed; the `initiative` group mirrors every subcommand | `test_local_claude_md.py` `test_legacy_placeholder_is_read_and_upgraded`, `test_legacy_marker_block_is_removed`; `test_cli.py` `test_alias_mirrors_every_feature_subcommand` |
| **TST-K** | PRD-J | `remove` backs up another project's file before clearing its block | No test yet |

Not covered by any test today: the old `initiatives/` folder (QUES-C), an active-feature lookup on an old marker (QUES-B), the cross-project sweep and backup (TST-K), and how the command line reports an invalid name (QUES-A). These gaps are tracked in the [design](../design/feature-system-design.md#open-questions).

## Test Execution Order

Run `test_config.py` and `test_features_manager.py` first, because they check the record layer the commands build on. Then `test_local_claude_md.py`, then the feature classes in `test_cli.py`.

## Expected Pass Threshold

Every case with a test must pass; the threshold is 100%. TST-K has no test, so PRD-J is not yet verified.

## Traceability

| Requirement | Test cases |
|---|---|
| PRD-A | TST-A |
| PRD-B | TST-B |
| PRD-C | TST-C |
| PRD-D | TST-D |
| PRD-E | TST-E, TST-F |
| PRD-F | TST-G |
| PRD-G | TST-H |
| PRD-H | TST-I |
| PRD-I | TST-J |
| PRD-J | TST-K |

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft as `initiative-system` (never committed) |
| 0.2 | 2026-11-24 | Rewritten with one case per requirement, mapped to pytest tests, untested behavior listed (ARD-A) |
