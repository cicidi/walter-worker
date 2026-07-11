# src/coworker/constants.py
# Single source of truth for doc conventions used by init, initiatives, and static blocks.

# Documentation structure — organized by initiative/topic:
#   docs/<initiative-name>/prd/     ← product requirements
#   docs/<initiative-name>/plan/    ← implementation plans
#   docs/<initiative-name>/spec/    ← design specs
DOCS_DISCIPLINES = ("prd", "plan", "spec")
STATE_DIR = "docs/state"
