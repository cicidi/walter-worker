"""Auto-worker module — autonomous QA loop that validates and fixes issues.

State management, validation rules, and continuous loop engine.
"""

from coworker.autoworker.state import has_been_checked, mark_checked, add_open_question, get_open_questions, load_checked_ids
from coworker.autoworker.rules import validate_against_raw_data, detect_dead_skills, audit_requirement
from coworker.autoworker.engine import run_autoworker_loop

__all__ = [
    "has_been_checked",
    "mark_checked",
    "add_open_question",
    "get_open_questions",
    "load_checked_ids",
    "validate_against_raw_data",
    "detect_dead_skills",
    "audit_requirement",
    "run_autoworker_loop",
]
