---
feature: setup-deploy
type: impl-plan
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Setup and Deploy — Implementation Plan

This plan was written after the scripts shipped. Each task below records a unit of work that exists at commit `634adf1`, what it depends on, what it blocks, and the test that proves it is done. Behavior is defined in the [design](../design/setup-deploy-design.md); this plan does not restate it.

## Global Constraints

The scripts run under `set -euo pipefail`, so an unguarded failing command aborts the install. Steps that may fail without stopping the install are guarded explicitly and warn instead; DSGN-H lists them. Python embedded in the scripts sits inside double-quoted bash strings and must contain no double quote, backtick, or dollar-parenthesis. The scripts must run on bash 3.2, so they use indexed arrays only. Every path the installer writes must be claimed in the manifest by name (DSGN-E).

## Acceptance Criteria

The feature is not done while any blocking question in the design's Open Questions (QUES-F) is open. Beyond that, it is done when all tasks below are done, the bats suites in `tests/setup/` pass in CI, and a real install on a machine that already has walter-worker leaves no duplicate skill, no duplicate hook, and no manifest entry pointing at a missing path.

## Execution order

IMPL-A first, because every later task writes paths that IMPL-A must be able to record and prune. IMPL-B and IMPL-C can proceed in parallel after it. IMPL-D depends on IMPL-A's manifest format. IMPL-E and IMPL-F depend on the manifest that IMPL-A writes.

## IMPL-A — Manifest by name

Write `~/.coworker/install-manifest.json` with `schema_version: 2`, claiming each written path by name, and prune paths the previous manifest claimed that this run did not produce (DSGN-E). Depends on: nothing. Blocks: IMPL-B, IMPL-C, IMPL-D, IMPL-E, and IMPL-F.

Verify: `tests/setup/test_install.bats` cases "retires a path an earlier install claimed and this one does not" and "leaves a skill this installer never wrote alone" pass.

## IMPL-B — Pristine snapshot and global CLAUDE.md

Take the one-time snapshot with its `.taken` marker and `absent.txt`, and create `CLAUDE.md` only when missing (DSGN-B). Depends on: IMPL-A for the rule that the manifest claims `CLAUDE.md` once an install created it. Blocks: IMPL-F's restore path.

Verify: `test_uninstall.bats` "a pristine snapshot is taken even when the files do not exist yet" and `test_install.bats` "preserves existing global CLAUDE.md" pass.

## IMPL-C — Skill deployment

Deploy the-super-lab skills to the three tools and bundle skills as commands, skipping same-file destinations and retiring identical command copies (DSGN-C). Depends on: IMPL-A. Blocks: nothing.

Verify: `test_install.bats` "deploys the-super-lab skills to the three harnesses", "a skill directory symlinked back to the source does not abort the install", and "a the-super-lab skill named in --skills is not also written as a command" pass.

## IMPL-D — Hook registration

Merge the six hook commands into `settings.json` without duplicating any, and take the old capture and close steps off Stop (DSGN-D). Depends on: IMPL-A for claiming the hook scripts. Blocks: IMPL-F's hook removal.

Verify: `test_install.bats` "no shipped on-* hook is left unregistered", "does not add a second SessionEnd hook when one is present", and "takes an earlier install's capture and close off Stop, keeping the user's hooks" pass.

## IMPL-E — Update replays the recorded answers

Read the mode and command selection from the manifest and pass them to the installer (DSGN-F). Depends on: IMPL-A. Blocks: nothing.

Verify: `test_update.bats` "resolves the install mode from the manifest, not coworker.yaml" and "update reuses the recorded skill selection instead of re-asking" pass.

## IMPL-F — Uninstall reverses the manifest

Remove claimed paths and walter-worker hooks, refuse a version-1 manifest, and support `--restore-pristine` (DSGN-G). Depends on: IMPL-A, IMPL-B, and IMPL-D. Blocks: nothing.

Verify: `test_uninstall.bats` "refuses to remove files from a pre-schema_version manifest", "uninstall keeps the user's own CLAUDE.md and their own hooks", and "install saves a pristine snapshot that uninstall can restore" pass.

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-04 | Draft (never committed) |
| 0.2 | 2026-11-24 | Rewritten as a record of shipped work with Verify lines; added Acceptance Criteria (ARD-D) |
| 0.3 | 2026-11-24 | Global Constraints corrected; Acceptance Criteria gated on the blocking open questions (ARD-E) |
| 0.4 | 2026-11-24 | IMPL-D after PR #22 (six hooks, tests renamed); Depends on and Blocks labels; IMPL-A blocks IMPL-B and IMPL-C |
