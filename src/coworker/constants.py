# src/coworker/constants.py
# Single source of truth for doc conventions used by init, initiatives, and static blocks.

# Documentation structure — 2-tier layout:
#   Project level: docs/{prd,spec,plan,test}/
#   Initiative level: docs/initiatives/<name>/<name>-spec.md, <name>-plan.md
DOCS_DISCIPLINES = ("prd", "plan", "spec", "test")
INITIATIVES_DIR_NAME = "initiatives"
STATE_DIR = "docs/state"
