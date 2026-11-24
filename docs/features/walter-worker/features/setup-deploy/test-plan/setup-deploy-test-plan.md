---
feature: setup-deploy
type: test-plan
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Setup and Deploy — Test Plan

Most cases below run the real script against a temporary home directory, with `git` and the `coworker` command replaced by mocks. TST-N is weaker: its bats tests check the script's text rather than running it, so PRD-K has no behavioral test yet. Each case names the requirement from the [PRD](../prd/setup-deploy-prd.md) it covers and the bats test that implements it at commit `a0f4ce0`.

## Test Cases

| ID | Covers | Case | Bats test |
|---|---|---|---|
| **TST-A** | PRD-A | A project-mode install writes commands under the project, not the home directory | `test_install.bats` "installs to project Claude Code directory" |
| **TST-B** | PRD-B | An existing global `CLAUDE.md` is left unchanged | `test_install.bats` "preserves existing global CLAUDE.md" |
| **TST-C** | PRD-B | A missing global `CLAUDE.md` is created | `test_install.bats` "creates global CLAUDE.md when missing" |
| **TST-D** | PRD-C | The snapshot is taken on a fresh machine and restoring it deletes files that did not exist before | `test_uninstall.bats` "a pristine snapshot is taken even when the files do not exist yet", "install saves a pristine snapshot that uninstall can restore" |
| **TST-E** | PRD-D | Every the-super-lab and personal skill reaches Claude Code, Cursor, and OpenCode | `test_install.bats` "deploys the-super-lab skills to the three harnesses", "deploys personal-skills to the three harnesses" |
| **TST-F** | PRD-D | A the-super-lab skill is never also written as a command, and an identical old command copy is retired while an edited one is kept | `test_install.bats` "a the-super-lab skill named in --skills is not also written as a command", "retires an unchanged command copy of a the-super-lab skill", "keeps an edited command copy of a the-super-lab skill and says so" |
| **TST-G** | PRD-D | A destination symlinked back to the source does not abort the install or claim source files | `test_install.bats` "a skill directory symlinked back to the source does not abort the install" |
| **TST-H** | PRD-E | `init` is always installed as a command | `test_install.bats` "always installs the core init skill" |
| **TST-I** | PRD-F | Every shipped hook is registered, and a second run adds none | `test_install.bats` "no shipped on-* hook is left unregistered", "does not add a second capture hook when one is present", "a capture and close joined into one hook are not added back separately" |
| **TST-J** | PRD-G | A path claimed earlier and no longer produced is removed; a path never claimed is left alone | `test_install.bats` "retires a path an earlier install claimed and this one does not", "leaves a skill this installer never wrote alone" |
| **TST-K** | PRD-H | A second identical run skips every up-to-date file, and answering "None" keeps installed commands | `test_install.bats` "skips already up-to-date skills", "skipping skills does not retire the ones already installed", "a second install keeps the CLAUDE.md the first install created" |
| **TST-L** | PRD-I | Update resolves the mode from the manifest and reuses the recorded selection without asking | `test_update.bats` "resolves the install mode from the manifest, not coworker.yaml", "update reuses the recorded skill selection instead of re-asking" |
| **TST-M** | PRD-J | Uninstall aborts without confirmation, refuses a version-1 manifest, keeps the user's files, and preserves analytics data | `test_uninstall.bats` "aborts without confirmation", "refuses to remove files from a pre-schema_version manifest", "uninstall keeps the user's own CLAUDE.md and their own hooks", "preserves analytics data it claims to preserve", "uninstall keeps the user's data in ~/.coworker" |
| **TST-N** | PRD-K | The-super-lab update can be declined, and a non-git the-super-lab still deploys its skills | `test_update.bats` "the-super-lab update can be declined", "notifies when the-super-lab is not a git checkout" |

One case checks less than its requirement asks. TST-I checks only the capture hook for duplicates. The open questions are in the [design](../design/setup-deploy-design.md#open-questions).

## Test Execution Order

Run `bats tests/setup/test_install.bats` first, because update and uninstall cases install before they act. Then run `test_update.bats`, then `test_uninstall.bats`. Within a file the cases are independent; each creates its own temporary home directory.

## Expected Pass Threshold

All cases must pass; the threshold is 100%. A failing case blocks a merge, because each one guards behavior that once deleted or duplicated a user's files.

## Traceability

| Requirement | Test cases |
|---|---|
| PRD-A | TST-A |
| PRD-B | TST-B, TST-C |
| PRD-C | TST-D |
| PRD-D | TST-E, TST-F, TST-G |
| PRD-E | TST-H |
| PRD-F | TST-I |
| PRD-G | TST-J |
| PRD-H | TST-K |
| PRD-I | TST-L |
| PRD-J | TST-M |
| PRD-K | TST-N |

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft (never committed) |
| 0.2 | 2026-11-24 | Rewritten with one case per requirement, mapped to bats tests, plus a traceability table (ARD-D) |
| 0.3 | 2026-11-24 | Weak and incomplete cases stated (ARD-E) |
