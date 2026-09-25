# src/coworker/constants.py
# Single source of truth for doc conventions used by init, features, and static blocks.

# Documentation structure — organized by feature, then by doc type:
#   docs/features/<feature-name>/prd/              ← product requirements
#   docs/features/<feature-name>/spec/             ← technical spec, incl. design
#   docs/features/<feature-name>/impl-plan/        ← implementation plan
#   docs/features/<feature-name>/test-plan/        ← how it is verified
#   docs/features/<feature-name>/decision-history/ ← every decision, in order
#   docs/features/<feature-name>/how-to/           ← operational instructions
# Matches the doc-organize standard. `state/` also lives here but is gitignored
# and deliberately not scaffolded as a committed type.
DOCS_DISCIPLINES = (
    "prd",
    "spec",
    "impl-plan",
    "test-plan",
    "decision-history",
    "how-to",
)
STATE_DIR = "docs/state"

# The feature several modules reach for by path — the wrong-history directory,
# the auto-worker's state dir, find-issues' default output. It was written out
# in five places, and when the initiatives→features move landed, all five broke
# silently at once. One definition, so the next move breaks in one place and
# says so.
SELF_EVOLVING_FEATURE = "self-evolving-agent"
SELF_EVOLVING_DOCS = f"docs/features/{SELF_EVOLVING_FEATURE}"
