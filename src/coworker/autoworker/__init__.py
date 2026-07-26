"""Auto-worker module — autonomous QA agent that audits and self-improves.

Uses Claude SDK agents (not deterministic scripts) to investigate
issues, decide fixes, and take action. The agent reasons about what
to do — the Python code just provides the launch environment.
"""

from coworker.autoworker.state import (
    has_been_checked,
    mark_checked,
    add_open_question,
    get_open_questions,
    load_checked_ids,
)
from coworker.autoworker.rules import (
    Finding,
    GapCheck,
    DeadCodeDetector,
    RequirementAuditor,
    StateFile,
    VisionCheck,
    ResearchAdvisor,
    ContextLoader,
)
from coworker.autoworker.engine import (
    AutoWorkerAgent,
    run_autoworker_loop,
    run_validation_harness,
)

__all__ = [
    # State management (backward-compat)
    "has_been_checked",
    "mark_checked",
    "add_open_question",
    "get_open_questions",
    "load_checked_ids",
    # Rules (spec §12.3)
    "Finding",
    "GapCheck",
    "DeadCodeDetector",
    "RequirementAuditor",
    "StateFile",
    "VisionCheck",
    "ResearchAdvisor",
    "ContextLoader",
    # Engine (spec §12.1-12.2)
    "AutoWorkerAgent",
    "run_autoworker_loop",
    "run_validation_harness",
]
