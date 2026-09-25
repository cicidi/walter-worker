# src/coworker/constants.py
# Single source of truth for doc conventions used by init, features, and static blocks.

# Documentation structure — organized by feature/topic:
#   docs/<feature-name>/prd/     ← product requirements
#   docs/<feature-name>/plan/    ← implementation plans
#   docs/<feature-name>/spec/    ← design specs
DOCS_DISCIPLINES = ("prd", "plan", "spec")
STATE_DIR = "docs/state"
