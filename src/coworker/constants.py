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
