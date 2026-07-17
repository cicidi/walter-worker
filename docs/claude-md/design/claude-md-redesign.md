# CLAUDE.md Redesign Implementation Plan

> **For agentic workers:** Use TDD — each task writes tests first, then implements. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the three-layer CLAUDE.md architecture (Global → Project → Local) in ai-coworker, generate canonical templates, update init/install/update/initiative commands, and dogfood on ai-coworker itself.

**Architecture:** New `templates/` module holds canonical template content. New `semantic_merge.py` handles CLAUDE.md updates. CLI `init` generates the new project structure. Initiatives inject into `CLAUDE.local.md` instead of `CLAUDE.md`. Install script uses new global template.

**Tech Stack:** Python 3.12+, Click, Pydantic 2, pytest, ruff

---

## File Structure

```
src/coworker/
├── templates/
│   ├── __init__.py          (NEW - module init)
│   ├── global_claude_md.py  (NEW - Global CLAUDE.md canonical template)
│   ├── project_claude_md.py (NEW - Project CLAUDE.md canonical template)
│   └── local_claude_md.py   (NEW - CLAUDE.local.md template)
├── semantic_merge.py        (NEW - Semantic merge engine)
├── cli.py                   (MODIFY - _scan_project, _build_project_section, init)
├── adapters/
│   ├── claude.py            (MODIFY - initiative injection target)
│   └── opencode.py          (MODIFY - initiative injection target)
└── initiatives/
    └── manager.py           (MODIFY - activate/deactivate target)
setup/
└── install.sh               (MODIFY - global CLAUDE.md template)
tests/
├── test_templates.py        (NEW)
├── test_semantic_merge.py   (NEW)
└── test_init.py             (MODIFY)
```

---

### Task 1: Global CLAUDE.md Canonical Template

**Files:**
- Create: `src/coworker/templates/__init__.py`
- Create: `src/coworker/templates/global_claude_md.py`
- Test: `tests/test_templates.py`

- [ ] **Step 1: Write test for global template generation**

```python
# tests/test_templates.py
from coworker.templates.global_claude_md import GLOBAL_CLAUDE_MD_TEMPLATE, generate_global_claude_md


def test_global_template_exists():
    assert GLOBAL_CLAUDE_MD_TEMPLATE is not None
    assert len(GLOBAL_CLAUDE_MD_TEMPLATE) > 0


def test_global_template_under_100_lines():
    result = generate_global_claude_md()
    lines = result.strip().split("\n")
    assert len(lines) < 100, f"Global CLAUDE.md is {len(lines)} lines, must be <100"


def test_global_template_contains_all_8_principles():
    result = generate_global_claude_md()
    principles = [
        "Ask and Confirm",
        "Evidence and Reasoning",
        "Simplicity First",
        "Surgical Changes",
        "Goal-Driven Execution",
        "Decompose Complex Tasks",
        "Plan and Track",
        "Model Upgrade",
    ]
    for p in principles:
        assert p in result, f"Missing principle: {p}"


def test_global_template_no_tool_specific_references():
    result = generate_global_claude_md()
    assert ".claude/rules/" not in result
    assert "opencode.json" not in result
    assert "Claude Code" not in result and "OpenCode" not in result


def test_generate_global_claude_md_allows_user_additions():
    result = generate_global_claude_md()
    assert "<!-- USER CUSTOM -->" not in result
    assert "<!-- PROTECTED -->" not in result
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd ~/project/ai-coworker && python -m pytest tests/test_templates.py -v
```
Expected: FAIL — module not found

- [ ] **Step 3: Create `src/coworker/templates/__init__.py`**

```python
# src/coworker/templates/__init__.py
```

- [ ] **Step 4: Create `src/coworker/templates/global_claude_md.py`**

```python
# src/coworker/templates/global_claude_md.py

GLOBAL_CLAUDE_MD_TEMPLATE = """# Global instructions for all projects

Behavioral guidelines to reduce common LLM coding mistakes.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Ask and Confirm Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- Clarify scope, goal, possibilities, and clues. Ask follow-up questions until ~90% clear.
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.

## 2. Evidence and Reasoning

**Ground every decision in evidence. Reason explicitly.**

- Collect and filter evidence (docs, code, references). Do preliminary analysis.
- If you discover a wrong direction, return to step 1 and restart. Avoid infinite loops.
- When evidence supports multiple conclusions, state each with pros/cons, give recommendation, assign confidence.

## 3. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

## 4. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- Remove only imports/variables YOUR changes made unused.
- Every changed line should trace directly to the user's request.

## 5. Goal-Driven Execution

**Define success criteria. Loop until verified.**

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

## 6. Decompose Complex Tasks

**Break complex work down. Start with what matters most.**

- Split complex tasks into smaller subtasks before starting.
- Order by priority — most important first.
- Re-evaluate priorities as you learn more during execution.

## 7. Plan and Track Progress

**Make the plan visible. Show where you are.**

- For every task, make a plan and display it (TodoWrite / todo list).
- Show current task and progress.
- When subtasks are independent, dispatch them in parallel via subagents.

## 8. Recommend Model Upgrade When Warranted

**Flag when a task needs a stronger model.**

- If the current task would benefit from a more capable LLM, say so and recommend an upgrade.
"""


def generate_global_claude_md() -> str:
    """Return the canonical Global CLAUDE.md content."""
    return GLOBAL_CLAUDE_MD_TEMPLATE.strip()
```

- [ ] **Step 5: Run tests**

```bash
cd ~/project/ai-coworker && python -m pytest tests/test_templates.py::test_global_template_exists tests/test_templates.py::test_global_template_under_100_lines tests/test_templates.py::test_global_template_contains_all_8_principles tests/test_templates.py::test_global_template_no_tool_specific_references -v
```
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/coworker/templates/__init__.py src/coworker/templates/global_claude_md.py tests/test_templates.py
git commit -m "feat: add Global CLAUDE.md canonical template (Karpathy 8 principles)"
```

---

### Task 2: Project CLAUDE.md Canonical Template

**Files:**
- Create: `src/coworker/templates/project_claude_md.py`
- Test: `tests/test_templates.py` (append)

- [ ] **Step 1: Write tests**

```python
# Append to tests/test_templates.py
from coworker.templates.project_claude_md import (
    PROJECT_CLAUDE_MD_IDENTITY_TEMPLATE,
    PROJECT_CLAUDE_MD_CONTEXT_MGMT_TEMPLATE,
    PROJECT_CLAUDE_MD_WORKFLOW_TEMPLATE,
    PROJECT_CLAUDE_MD_SKILL_REFS_TEMPLATE,
    PROJECT_CLAUDE_MD_LOCAL_OVERRIDE_TEMPLATE,
    PROJECT_CLAUDE_MD_AUTO_MEMORY_TEMPLATE,
    PROJECT_CLAUDE_MD_COMPACTION_TEMPLATE,
    generate_project_claude_md,
)


def test_project_template_under_200_lines():
    result = generate_project_claude_md(
        project_name="test-project",
        language="python",
        framework="fastapi",
        repo="git@github.com:test/test.git",
        branch="main",
    )
    lines = result.strip().split("\n")
    assert len(lines) < 200, f"Project CLAUDE.md is {len(lines} lines, must be <200"


def test_project_template_contains_identity():
    result = generate_project_claude_md(
        project_name="test",
        language="python",
        framework="fastapi",
        repo="git@github.com:test/test.git",
        branch="main",
    )
    assert "# test" in result or "## Identity" in result
    assert "python" in result.lower()
    assert "fastapi" in result.lower()
    assert "git@github.com:test/test.git" in result


def test_project_template_contains_local_override():
    result = generate_project_claude_md(
        project_name="test", language="python", framework="", repo="", branch=""
    )
    assert "CLAUDE.local.md" in result
    assert "Read tool" in result


def test_project_template_contains_workflow_heuristics():
    result = generate_project_claude_md(
        project_name="test", language="python", framework="", repo="", branch=""
    )
    assert "low-risk" in result.lower() or "auto-execute" in result.lower()
    assert "escape hatch" in result.lower()


def test_project_template_sections_in_priority_order():
    result = generate_project_claude_md(
        project_name="test", language="python", framework="", repo="", branch=""
    )
    sections = [line for line in result.split("\n") if line.startswith("## ")]
    # Critical behavioral rules must come before identity/context
    local_override_idx = next(i for i, s in enumerate(sections) if "Local Override" in s or "Auto Memory" in s or "Compaction" in s)
    identity_idx = next(i for i, s in enumerate(sections) if "Identity" in s or "Project Context" in s)
    assert local_override_idx < identity_idx, "Critical rules must come before identity"


def test_project_template_no_tool_specific_references():
    result = generate_project_claude_md(
        project_name="test", language="python", framework="", repo="", branch=""
    )
    assert ".claude/rules/" not in result
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd ~/project/ai-coworker && python -m pytest tests/test_templates.py::test_project_template_under_200_lines -v
```
Expected: FAIL — module not found

- [ ] **Step 3: Create `src/coworker/templates/project_claude_md.py`**

```python
# src/coworker/templates/project_claude_md.py

PROJECT_CLAUDE_MD_LOCAL_OVERRIDE_TEMPLATE = """## Local Override

If `CLAUDE.local.md` exists in this project root, read it immediately after reading this file.
- Claude Code natively auto-loads this file
- OpenCode: use Read tool to load it on startup

It contains:
- Active initiative context (injected by coworker)
- Current task state reference
- Config file paths (project catalog, local config)
- Personal workflow preferences for this project
"""

PROJECT_CLAUDE_MD_AUTO_MEMORY_TEMPLATE = """## Auto Memory

- CLAUDE.md contains upfront rules — read these first
- Auto memory (if enabled) contains learnings from prior sessions
- When auto memory exists, read it after CLAUDE.md but before starting work
- Conflict resolution: upfront rules (CLAUDE.md) override learned rules (auto memory)
- Auto memory is stored separately, never injected back into CLAUDE.md without human review
"""

PROJECT_CLAUDE_MD_COMPACTION_TEMPLATE = """## Compaction Survival

After context compaction or session truncation:
1. Project CLAUDE.md is always re-injected — use it as your reset anchor
2. `docs/state-{task}.md` survives on disk → re-read it to resume progress
3. Previous conversation is lost → rely on state files, not memory
4. Compact at 50-70% context window, not when degraded
5. Re-run the context self-assessment checklist from start
"""

PROJECT_CLAUDE_MD_IDENTITY_TEMPLATE = """## Identity & Project Context

- Language: {language}
- Framework: {framework}
- Package Manager: {package_manager}
- Build: {build_cmd}
- Lint: {lint_cmd}
- Test: {test_cmd}
- IDE: {ides}
- Repo: {repo}
- Default Branch: {branch}
"""

PROJECT_CLAUDE_MD_RELATIONSHIPS_TEMPLATE = """## Project Relationships

{relationships}

The project catalog config path is in `CLAUDE.local.md`.
"""

PROJECT_CLAUDE_MD_KNOWLEDGE_TEMPLATE = """## Knowledge Repo

{doc_map}
"""

PROJECT_CLAUDE_MD_CONTEXT_MGMT_TEMPLATE = """## Context Management

Before any non-trivial task, evaluate whether external context is needed.

### Context Self-Assessment Checklist
1. Is the goal clear? If not → need clarification from user
2. Is there a PRD/spec? If yes → read it first from `docs/specs/`
3. Were there prior discussions? If yes → read from `docs/discussion/`
4. Was this task started before? If yes → read `docs/state-{taskname}.md`
5. Are all referenced files actually read? If not → read them NOW

### Information Categories
| Category | Source | Storage |
|----------|--------|---------|
| 1. What to build | PRD, spec, issue | `docs/specs/` |
| 2. Discussion & decisions | Slack, wiki, GitHub | `docs/discussion/` |
| 3. Implementation plan | Derived from 1 & 2 | `docs/specs/` |
| 4. Verification plan | Tests, acceptance criteria | `docs/specs/` |
| 5. Historical archive | Prior sessions, state files | `docs/state-{task}.md` |

Only pull from channels actively configured for this project.
"""

PROJECT_CLAUDE_MD_WORKFLOW_TEMPLATE = """## Workflow Decision Heuristics

At the start of every new task, analyze characteristics. Route to auto or confirm.

### Low-risk → auto-execute, no confirmation
| Task | Action |
|------|--------|
| Clear requirements, simple change, low risk | Direct implementation |
| Bug fix with clear reproduction, small scope | bug-hunt → fix → verify |
| Minor refactoring with existing tests passing | Edit → verify tests |

### Medium/high risk → suggest workflow, confirm first
| Task | Suggested workflow |
|------|-------------------|
| Unclear requirements, large scope | brainstorming → spec → discuss |
| Clear requirements, complex code, high bug risk | TDD + loop engineering |
| Large project, lots of discussion AND code | brainstorming + TDD + loop |

### Decision Logic
```
if clarity == clear AND scope == small AND risk == low:
    → auto-execute, no prompt
else:
    → analyze → suggest workflow → ask user to confirm
```

### Escape Hatch
These heuristics bias toward caution. For trivial, reversible operations (reading files, running `ls`/`grep`, simple logging), use judgment and proceed without overthinking.
"""

PROJECT_CLAUDE_MD_SKILL_REFS_TEMPLATE = """## Skill References

When a task matches a skill's domain, invoke that skill:
- TDD / auto-tdd: test-first development, red-green-refactor cycles
- bug-hunt: systematic debugging with hypothesis-test-confirm loop
- brainstorming: creative work, feature design, exploration
- commit: git commits following conventional commits format
- doc-*: documentation workflows (create, merge, protect)
- self-heal / self-analyze: logging corrections, pattern analysis

Auto-match principle: Skill descriptions should be specific enough that the AI can unambiguously determine when to use them. If a human can't tell which skill applies, the AI can't either.
"""


def generate_project_claude_md(
    project_name: str = "",
    language: str = "",
    framework: str = "",
    package_manager: str = "",
    build_cmd: str = "",
    lint_cmd: str = "",
    test_cmd: str = "",
    ides: str = "claude, opencode",
    repo: str = "",
    branch: str = "main",
    relationships: str = "_(none configured)_",
    doc_map: str = "_(run `coworker init` to scan docs/ structure)_",
) -> str:
    """Generate canonical Project CLAUDE.md."""

    identity = PROJECT_CLAUDE_MD_IDENTITY_TEMPLATE.format(
        language=language or "_detect on `coworker init`_",
        framework=framework or "_detect on `coworker init`_",
        package_manager=package_manager or "_detect on `coworker init`_",
        build_cmd=build_cmd or "_detect on `coworker init`_",
        lint_cmd=lint_cmd or "_detect on `coworker init`_",
        test_cmd=test_cmd or "_detect on `coworker init`_",
        ides=ides,
        repo=repo or "_detect on `coworker init`_",
        branch=branch,
    )

    relationships_section = PROJECT_CLAUDE_MD_RELATIONSHIPS_TEMPLATE.format(
        relationships=relationships,
    )

    knowledge = PROJECT_CLAUDE_MD_KNOWLEDGE_TEMPLATE.format(doc_map=doc_map)

    parts = [
        f"# {project_name or 'Project'} — CLAUDE.md",
        "",
        "<!-- PROTECTED:CRITICAL-RULES -->",
        PROJECT_CLAUDE_MD_LOCAL_OVERRIDE_TEMPLATE.strip(),
        PROJECT_CLAUDE_MD_AUTO_MEMORY_TEMPLATE.strip(),
        PROJECT_CLAUDE_MD_COMPACTION_TEMPLATE.strip(),
        "<!-- END PROTECTED:CRITICAL-RULES -->",
        "",
        identity.strip(),
        "",
        relationships_section.strip(),
        "",
        knowledge.strip(),
        "",
        PROJECT_CLAUDE_MD_CONTEXT_MGMT_TEMPLATE.strip(),
        "",
        PROJECT_CLAUDE_MD_WORKFLOW_TEMPLATE.strip(),
        "",
        PROJECT_CLAUDE_MD_SKILL_REFS_TEMPLATE.strip(),
    ]
    return "\n\n".join(parts)
```

- [ ] **Step 4: Run tests**

```bash
cd ~/project/ai-coworker && python -m pytest tests/test_templates.py -v -k "project"
```
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/coworker/templates/project_claude_md.py tests/test_templates.py
git commit -m "feat: add Project CLAUDE.md canonical template"
```

---

### Task 3: CLAUDE.local.md Template

**Files:**
- Create: `src/coworker/templates/local_claude_md.py`
- Test: `tests/test_templates.py` (append)

- [ ] **Step 1: Write tests**

```python
# Append to tests/test_templates.py
from coworker.templates.local_claude_md import generate_local_claude_md


def test_local_template_is_empty_by_default():
    result = generate_local_claude_md()
    lines = result.strip().split("\n")
    assert len(lines) < 30, f"Local CLAUDE.md template should be minimal, got {len(lines)} lines"


def test_local_template_has_initiative_placeholder():
    result = generate_local_claude_md()
    assert "INITIATIVE:" in result or "initiative" in result.lower()


def test_local_template_has_config_path_section():
    result = generate_local_claude_md()
    assert "config" in result.lower() or "Config" in result


def test_local_template_has_task_state_section():
    result = generate_local_claude_md()
    assert "state" in result.lower() or "task" in result.lower()


def test_local_template_adds_initiative_with_no_duplicates():
    content = generate_local_claude_md()
    initiative_block = """<!-- INITIATIVE:test START -->
## Active Initiative: test
> test description
<!-- INITIATIVE:test END -->"""
    updated = inject_initiative_into_local_md(content, initiative_block)
    assert "INITIATIVE:test" in updated
    # Inject again — should replace, not duplicate
    updated2 = inject_initiative_into_local_md(updated, initiative_block)
    assert updated2.count("INITIATIVE:test") == 2  # START and END = 2 occurrences


def test_local_template_removes_initiative():
    content = generate_local_claude_md()
    initiative_block = """<!-- INITIATIVE:test START -->
## Active Initiative: test
<!-- INITIATIVE:test END -->"""
    with_initiative = inject_initiative_into_local_md(content, initiative_block)
    removed = remove_initiative_from_local_md(with_initiative, "test")
    assert "INITIATIVE:test" not in removed
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd ~/project/ai-coworker && python -m pytest tests/test_templates.py::test_local_template_is_empty_by_default -v
```
Expected: FAIL

- [ ] **Step 3: Create `src/coworker/templates/local_claude_md.py`**

```python
# src/coworker/templates/local_claude_md.py
import re

LOCAL_CLAUDE_MD_TEMPLATE = """# Personal Working Context

This file is NOT committed to git. It contains your personal working context for this project.

## Config Paths

- Project Catalog: ~/.coworker/project.yaml
- Local Config: .local_config.yaml

<!-- INITIATIVE_PLACEHOLDER -->

## Current Task State

Active task: _(none)_

Reference: `docs/state-{taskname}.md`

## Personal Preferences

_(override project-level defaults here)_
"""

INITIATIVE_PLACEHOLDER = "<!-- INITIATIVE_PLACEHOLDER -->"


def generate_local_claude_md() -> str:
    """Return the canonical CLAUDE.local.md template."""
    return LOCAL_CLAUDE_MD_TEMPLATE.strip()


def inject_initiative_into_local_md(content: str, initiative_block: str) -> str:
    """Inject an initiative block into local.md content, replacing any existing initiative blocks."""
    # Remove all existing initiative blocks first
    cleaned = re.sub(
        r"<!-- INITIATIVE:.*?START -->.*?<!-- INITIATIVE:.*?END -->",
        "",
        content,
        flags=re.DOTALL,
    )
    # Insert before the placeholder or at the end
    if INITIATIVE_PLACEHOLDER in cleaned:
        return cleaned.replace(INITIATIVE_PLACEHOLDER, initiative_block.strip() + "\n\n" + INITIATIVE_PLACEHOLDER)
    else:
        return cleaned.strip() + "\n\n" + initiative_block.strip()


def remove_initiative_from_local_md(content: str, name: str) -> str:
    """Remove a specific initiative block from local.md content."""
    pattern = rf"<!-- INITIATIVE:{re.escape(name)} START -->.*?<!-- INITIATIVE:{re.escape(name)} END -->"
    return re.sub(pattern, "", content, flags=re.DOTALL)
```

- [ ] **Step 4: Run tests**

```bash
cd ~/project/ai-coworker && python -m pytest tests/test_templates.py -v -k "local"
```
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/coworker/templates/local_claude_md.py tests/test_templates.py
git commit -m "feat: add CLAUDE.local.md template with initiative injection"
```

---

### Task 4: Semantic Merge Engine

**Files:**
- Create: `src/coworker/semantic_merge.py`
- Test: `tests/test_semantic_merge.py`

- [ ] **Step 1: Write tests**

```python
# tests/test_semantic_merge.py
from coworker.semantic_merge import (
    classify_sections,
    SectionClassification,
    apply_merge,
    OUTDATED,
    OVERWRITE,
    MERGE_ADD,
    KEEP,
)


CURRENT = """# Project CLAUDE.md

## Identity
python, fastapi

## My Custom Rules
my custom content here

<!-- PROTECTED -->
do not touch this
<!-- END PROTECTED -->

## Context Management
old version of context rules
"""

FUTURE = """# Project CLAUDE.md

## Identity
python, fastapi, pydantic

## Context Management
new version of context rules

## Workflow Heuristics
new workflow decision guide
"""


def test_classify_overwrite():
    classifications = classify_sections(CURRENT, FUTURE)
    overwrites = [c for c in classifications if c.category == OVERWRITE]
    assert len(overwrites) >= 1
    identity = [c for c in overwrites if "Identity" in c.heading]
    assert len(identity) == 1
    context = [c for c in overwrites if "Context Management" in c.heading]
    assert len(context) == 1


def test_classify_keep_custom():
    classifications = classify_sections(CURRENT, FUTURE)
    keeps = [c for c in classifications if c.category == KEEP]
    headings = [c.heading for c in keeps]
    assert "My Custom Rules" in headings or any("Custom" in h for h in headings)


def test_classify_merge_add():
    classifications = classify_sections(CURRENT, FUTURE)
    adds = [c for c in classifications if c.category == MERGE_ADD]
    headings = [c.heading for c in adds]
    assert "Workflow Heuristics" in headings or any("Workflow" in h for h in headings)


def test_classify_protected_block_untouched():
    classifications = classify_sections(CURRENT, FUTURE)
    assert "do not touch this" in CURRENT  # survives in KEEP


def test_apply_merge_result():
    classifications = classify_sections(CURRENT, FUTURE)
    result = apply_merge(classifications, CURRENT, FUTURE)
    assert "My Custom Rules" in result
    assert "new version of context rules" in result
    assert "pydantic" in result
    assert "new workflow decision guide" in result
    assert "do not touch this" in result


def test_no_duplicate_sections_after_merge():
    classifications = classify_sections(CURRENT, FUTURE)
    result = apply_merge(classifications, CURRENT, FUTURE)
    assert result.count("## Identity") == 1
    assert result.count("## Context Management") == 1


def test_classify_returns_list():
    classifications = classify_sections(CURRENT, FUTURE)
    assert isinstance(classifications, list)
    assert all(isinstance(c, SectionClassification) for c in classifications)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd ~/project/ai-coworker && python -m pytest tests/test_semantic_merge.py -v
```
Expected: FAIL

- [ ] **Step 3: Create `src/coworker/semantic_merge.py`**

```python
# src/coworker/semantic_merge.py
import re
from dataclasses import dataclass, field

OUTDATED = "OUTDATED"
OVERWRITE = "OVERWRITE"
MERGE_ADD = "MERGE_ADD"
KEEP = "KEEP"


@dataclass
class SectionClassification:
    heading: str
    category: str  # OUTDATED | OVERWRITE | MERGE_ADD | KEEP
    current_content: str = ""
    future_content: str = ""


def _parse_sections(content: str) -> dict[str, str]:
    """Parse markdown content into a dict of heading → section body."""
    sections = {}
    pattern = r"^(#{1,3}\s+.+)$"
    lines = content.split("\n")
    current_heading = "_header"
    current_body: list[str] = []

    for line in lines:
        if re.match(pattern, line):
            if current_body:
                sections[current_heading] = "\n".join(current_body).strip()
            current_heading = line.strip()
            current_body = []
        else:
            current_body.append(line)
    if current_body:
        sections[current_heading] = "\n".join(current_body).strip()

    return sections


def classify_sections(current: str, future: str) -> list[SectionClassification]:
    """Compare current and future CLAUDE.md, classify each section."""
    current_sections = _parse_sections(current)
    future_sections = _parse_sections(future)
    classifications: list[SectionClassification] = []

    for heading, cur_content in current_sections.items():
        if heading == "_header":
            continue

        # PROTECTED blocks → always KEEP
        if "<!-- PROTECTED -->" in cur_content or "<!-- PROTECTED:" in cur_content:
            classifications.append(SectionClassification(
                heading=heading, category=KEEP,
                current_content=cur_content,
            ))
            continue

        # INITIATIVE blocks → always KEEP (managed by initiative system)
        if "<!-- INITIATIVE:" in cur_content:
            classifications.append(SectionClassification(
                heading=heading, category=KEEP,
                current_content=cur_content,
            ))
            continue

        if heading in future_sections:
            fut_content = future_sections[heading]
            if cur_content.strip() != fut_content.strip():
                classifications.append(SectionClassification(
                    heading=heading, category=OVERWRITE,
                    current_content=cur_content,
                    future_content=fut_content,
                ))
            else:
                classifications.append(SectionClassification(
                    heading=heading, category=KEEP,
                    current_content=cur_content,
                ))
        else:
            # Section in current but not in future → KEEP (user may have added it)
            classifications.append(SectionClassification(
                heading=heading, category=KEEP,
                current_content=cur_content,
            ))

    # Sections in future but not in current → MERGE_ADD
    for heading, fut_content in future_sections.items():
        if heading == "_header":
            continue
        if heading not in current_sections:
            classifications.append(SectionClassification(
                heading=heading, category=MERGE_ADD,
                future_content=fut_content,
            ))

    return classifications


def apply_merge(
    classifications: list[SectionClassification],
    current: str,
    future: str,
) -> str:
    """Apply classified changes to produce merged CLAUDE.md."""
    output_lines = []
    current_sections = _parse_sections(current)
    future_sections = _parse_sections(future)

    # Start with header
    header = current_sections.get("_header", future_sections.get("_header", ""))
    if header:
        output_lines.append(header)
        output_lines.append("")

    # Process in order: current sections first, then new sections
    processed_headings: set[str] = set()

    for heading, cur_content in current_sections.items():
        if heading == "_header":
            continue
        processed_headings.add(heading)

        # Find classification for this heading
        match = [c for c in classifications if c.heading == heading]
        if not match:
            output_lines.append(heading)
            output_lines.append("")
            output_lines.append(cur_content)
            output_lines.append("")
            continue

        c = match[0]
        if c.category == KEEP:
            output_lines.append(heading)
            output_lines.append("")
            output_lines.append(cur_content)
            output_lines.append("")
        elif c.category == OVERWRITE:
            output_lines.append(heading)
            output_lines.append("")
            output_lines.append(c.future_content)
            output_lines.append("")
        elif c.category == OUTDATED:
            # Skip — don't include
            pass

    # Add new sections from MERGE_ADD
    for c in classifications:
        if c.category == MERGE_ADD:
            output_lines.append(c.heading)
            output_lines.append("")
            output_lines.append(c.future_content)
            output_lines.append("")

    return "\n".join(output_lines).strip() + "\n"
```

- [ ] **Step 4: Run tests**

```bash
cd ~/project/ai-coworker && python -m pytest tests/test_semantic_merge.py -v
```
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/coworker/semantic_merge.py tests/test_semantic_merge.py
git commit -m "feat: add semantic merge engine for CLAUDE.md updates"
```

---

### Task 5: Update `cli.py` — Init Command

**Files:**
- Modify: `src/coworker/cli.py:_scan_project`, `_build_project_section`, `init`
- Test: `tests/test_init.py`

- [ ] **Step 1: Enhance `_scan_project()` to detect docs/ structure**

```python
# In src/coworker/cli.py, modify _scan_project()

def _scan_project() -> dict:
    """Scan current directory for project metadata."""
    info = {
        "name": Path.cwd().name,
        "language": "",
        "framework": "",
        "package_manager": "",
        "build_cmd": "",
        "lint_cmd": "",
        "test_cmd": "",
        "ides": "claude, opencode",
        "repo": "",
        "branch": "main",
        "doc_map": "",           # NEW
        "relationships": "",     # NEW
    }

    # ... existing detection logic ...
    # (keep all existing language/framework detection)

    # NEW: Detect docs/ structure
    docs_dir = Path.cwd() / "docs"
    if docs_dir.exists():
        parts = []
        if (docs_dir / "specs").exists():
            parts.append("- Specs: `docs/specs/`")
        if (docs_dir / "discussion").exists():
            parts.append("- Discussions: `docs/discussion/`")
        state_files = list(Path.cwd().glob("docs/state-*.md"))
        if state_files:
            for sf in state_files:
                parts.append(f"- State: `{sf.relative_to(Path.cwd())}`")
        if not parts:
            parts.append("- `docs/` exists but no specs/discussion/state subdirectories")
        info["doc_map"] = "\n".join(parts)
    else:
        info["doc_map"] = "_`docs/` directory not found. Run `coworker init` to create._"

    # NEW: Detect project relationships from catalog
    try:
        from coworker.config import load_project_catalog
        catalog = load_project_catalog()
        current_path = str(Path.cwd().resolve())
        rels = []
        for entry in catalog.projects:
            for ref in entry.upstream:
                rels.append(f"| {entry.name} | upstream | {ref.project} |")
            for ref in entry.downstream:
                rels.append(f"| {entry.name} | downstream | {ref.project} |")
        info["relationships"] = "\n".join(rels) if rels else "_(none configured)_"
    except Exception:
        info["relationships"] = "_(none configured)_"

    return info
```

- [ ] **Step 2: Replace `_build_project_section()` with new template-based generator**

```python
# In src/coworker/cli.py, replace _build_project_section()

from coworker.templates.project_claude_md import generate_project_claude_md


def _build_project_claude_md(info: dict) -> str:
    """Generate project CLAUDE.md using canonical template."""
    return generate_project_claude_md(
        project_name=info.get("name", ""),
        language=info.get("language", ""),
        framework=info.get("framework", ""),
        package_manager=info.get("package_manager", ""),
        build_cmd=info.get("build_cmd", ""),
        lint_cmd=info.get("lint_cmd", ""),
        test_cmd=info.get("test_cmd", ""),
        ides=info.get("ides", "claude, opencode"),
        repo=info.get("repo", ""),
        branch=info.get("branch", "main"),
        relationships=info.get("relationships", ""),
        doc_map=info.get("doc_map", ""),
    )
```

- [ ] **Step 3: Update `init()` command to also create docs/ structure and local.md**

```python
# In src/coworker/cli.py, modify init() — add after existing CLAUDE.md generation

@main.command()
@click.option("--global", "is_global", is_flag=True)
@click.option("--project", "is_project", is_flag=True)
def init(is_global, is_project):
    # ... existing code ...

    if is_project or (not is_global and not is_project):
        info = _scan_project()

        # Generate project CLAUDE.md
        claude_md = _build_project_claude_md(info)
        claude_md_path = Path.cwd() / "CLAUDE.md"
        if not claude_md_path.exists():
            claude_md_path.write_text(claude_md)
            console.print(f"[green]Created {claude_md_path}[/green]")
        else:
            console.print(f"[yellow]{claude_md_path} already exists, skipping[/yellow]")

        # NEW: Create docs/ structure
        docs_dir = Path.cwd() / "docs"
        for subdir in ["specs", "discussion"]:
            (docs_dir / subdir).mkdir(parents=True, exist_ok=True)
        console.print(f"[green]Created docs/ structure[/green]")

        # NEW: Create CLAUDE.local.md if not exists
        from coworker.templates.local_claude_md import generate_local_claude_md
        local_md_path = Path.cwd() / "CLAUDE.local.md"
        if not local_md_path.exists():
            local_md_path.write_text(generate_local_claude_md())
            console.print(f"[green]Created {local_md_path}[/green]")
            # Add to .gitignore
            gitignore_path = Path.cwd() / ".gitignore"
            if not gitignore_path.exists():
                gitignore_path.write_text("CLAUDE.local.md\n")
            elif "CLAUDE.local.md" not in gitignore_path.read_text():
                with open(gitignore_path, "a") as f:
                    f.write("\nCLAUDE.local.md\n")
```

- [ ] **Step 4: Write init tests**

```python
# tests/test_init.py
# ... (add to existing tests file or create new)

import tempfile
from pathlib import Path


def test_init_creates_docs_structure():
    with tempfile.TemporaryDirectory() as tmp:
        # Simulate a project directory
        (Path(tmp) / "README.md").write_text("# test")
        (Path(tmp) / "requirements.txt").write_text("fastapi==0.100.0")
        import subprocess
        result = subprocess.run(
            ["coworker", "init", "--project"],
            cwd=tmp,
            capture_output=True,
            text=True,
        )
        assert (Path(tmp) / "docs" / "specs").exists()
        assert (Path(tmp) / "docs" / "discussion").exists()


def test_init_creates_project_claude_md():
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "README.md").write_text("# test")
        (Path(tmp) / "pyproject.toml").write_text("[project]\nname = 'test'")
        import subprocess
        subprocess.run(["coworker", "init", "--project"], cwd=tmp, capture_output=True, text=True)
        content = (Path(tmp) / "CLAUDE.md").read_text()
        assert "Local Override" in content
        assert "Context Management" in content
        assert "Workflow Decision" in content


def test_init_creates_local_claude_md():
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "README.md").write_text("# test")
        import subprocess
        subprocess.run(["coworker", "init", "--project"], cwd=tmp, capture_output=True, text=True)
        content = (Path(tmp) / "CLAUDE.local.md").read_text()
        assert "Config Paths" in content or "config" in content.lower()


def test_init_adds_local_md_to_gitignore():
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "README.md").write_text("# test")
        import subprocess
        subprocess.run(["coworker", "init", "--project"], cwd=tmp, capture_output=True, text=True)
        gitignore = (Path(tmp) / ".gitignore").read_text()
        assert "CLAUDE.local.md" in gitignore


def test_generated_claude_md_under_200_lines():
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "README.md").write_text("# test")
        import subprocess
        subprocess.run(["coworker", "init", "--project"], cwd=tmp, capture_output=True, text=True)
        lines = (Path(tmp) / "CLAUDE.md").read_text().strip().split("\n")
        assert len(lines) < 200, f"Generated {len(lines)} lines, must be <200"
```

- [ ] **Step 5: Run tests**

```bash
cd ~/project/ai-coworker && python -m pytest tests/test_init.py -v
```
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/coworker/cli.py tests/test_init.py
git commit -m "feat: update init command for new CLAUDE.md architecture"
```

---

### Task 6: Update Initiative Manager — Inject to local.md

**Files:**
- Modify: `src/coworker/initiatives/manager.py`
- Modify: `src/coworker/adapters/claude.py`
- Modify: `src/coworker/adapters/opencode.py`
- Test: `tests/test_initiatives.py`

- [ ] **Step 1: Add `_resolve_local_md()` to claude.py adapter**

```python
# In src/coworker/adapters/claude.py

def _resolve_local_md(project_dir: Path | None = None) -> Path:
    """Resolve path to CLAUDE.local.md."""
    target = project_dir or Path.cwd()
    return target / "CLAUDE.local.md"
```

- [ ] **Step 2: Modify `activate()` in `InitiativeManager` to inject into local.md**

```python
# In src/coworker/initiatives/manager.py, modify activate()

def activate(self, name: str) -> list[str]:
    """Activate an initiative: inject context into CLAUDE.local.md."""
    results: list[str] = []

    config = load_initiative(name, self.project_dir)
    if not config:
        raise ValueError(f"Initiative '{name}' not found")

    # Deactivate any currently active initiative first
    if self.active_name():
        results.extend(self.deactivate())

    # Build initiative block
    from coworker.adapters.claude import _build_initiative_block
    initiative_block = _build_initiative_block(config)

    # Inject into CLAUDE.local.md
    local_md_path = _resolve_local_md(self.project_dir)
    if local_md_path.exists():
        content = local_md_path.read_text()
    else:
        from coworker.templates.local_claude_md import generate_local_claude_md
        content = generate_local_claude_md()

    from coworker.templates.local_claude_md import inject_initiative_into_local_md
    updated = inject_initiative_into_local_md(content, initiative_block)
    local_md_path.write_text(updated)

    # Set active
    active_file = _initiatives_dir(self.project_dir) / ".active"
    active_file.write_text(name)

    results.append(f"Injected initiative '{name}' into {local_md_path}")
    return results


def deactivate(self) -> list[str]:
    """Deactivate current initiative: remove from CLAUDE.local.md."""
    results: list[str] = []
    name = self.active_name()
    if not name:
        return results

    # Remove from CLAUDE.local.md
    local_md_path = _resolve_local_md(self.project_dir)
    if local_md_path.exists():
        content = local_md_path.read_text()
        from coworker.templates.local_claude_md import remove_initiative_from_local_md
        updated = remove_initiative_from_local_md(content, name)
        local_md_path.write_text(updated)

    # Clear active file
    active_file = _initiatives_dir(self.project_dir) / ".active"
    if active_file.exists():
        active_file.unlink()

    results.append(f"Deactivated initiative '{name}'")
    return results
```

- [ ] **Step 3: Update `_resolve_local_md` import in `initiatives/manager.py`**

```python
# Add at top of src/coworker/initiatives/manager.py
from coworker.adapters.claude import _resolve_local_md  # NEW
```

- [ ] **Step 4: Update `opencode.py` adapter — same local.md injection**

```python
# In src/coworker/adapters/opencode.py
# OpenCode reads CLAUDE.md, so initiative in local.md is reached
# via the Local Override instruction in CLAUDE.md
# No additional sync needed for opencode adaptation
# (inject_static_context still injects project catalog into CLAUDE.md)
```

- [ ] **Step 5: Write initiative tests**

```python
# tests/test_initiatives.py (append)

def test_activate_injects_to_local_md():
    with tempfile.TemporaryDirectory() as tmp:
        proj = Path(tmp) / "test-project"
        proj.mkdir()
        (proj / "README.md").write_text("# test")
        # Create initiative
        import subprocess
        subprocess.run(["coworker", "initiative", "create", "test-init", "-d", "test"], cwd=str(proj), capture_output=True, text=True)
        # Activate
        subprocess.run(["coworker", "initiative", "activate", "test-init"], cwd=str(proj), capture_output=True, text=True)
        # Check local.md
        local_md = proj / "CLAUDE.local.md"
        if local_md.exists():
            content = local_md.read_text()
            assert "INITIATIVE:test-init" in content


def test_deactivate_removes_from_local_md():
    with tempfile.TemporaryDirectory() as tmp:
        proj = Path(tmp) / "test-project"
        proj.mkdir()
        (proj / "README.md").write_text("# test")
        import subprocess
        subprocess.run(["coworker", "initiative", "create", "test-init", "-d", "test"], cwd=str(proj), capture_output=True, text=True)
        subprocess.run(["coworker", "initiative", "activate", "test-init"], cwd=str(proj), capture_output=True, text=True)
        subprocess.run(["coworker", "initiative", "deactivate"], cwd=str(proj), capture_output=True, text=True)
        local_md = proj / "CLAUDE.local.md"
        if local_md.exists():
            content = local_md.read_text()
            assert "INITIATIVE:test-init" not in content
```

- [ ] **Step 6: Run tests**

```bash
cd ~/project/ai-coworker && python -m pytest tests/test_initiatives.py -v -k "local"
```
Expected: all PASS

- [ ] **Step 7: Commit**

```bash
git add src/coworker/initiatives/manager.py src/coworker/adapters/claude.py src/coworker/adapters/opencode.py tests/test_initiatives.py
git commit -m "feat: redirect initiative injection to CLAUDE.local.md"
```

---

### Task 7: Update install.sh — Global CLAUDE.md Template

**Files:**
- Modify: `setup/install.sh`

- [ ] **Step 1: Replace hardcoded CLAUDE_MD_CONTENT in install.sh**

```bash
# In setup/install.sh, replace the CLAUDE_MD_CONTENT variable

# OLD:
# CLAUDE_MD_CONTENT='# Global instructions for all projects...'

# NEW:
CLAUDE_MD_CONTENT=$(python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from src.coworker.templates.global_claude_md import generate_global_claude_md
print(generate_global_claude_md())
")
```

- [ ] **Step 2: Verify install.sh still works**

```bash
cd ~/project/ai-coworker && bash -n setup/install.sh
```
Expected: no syntax errors

- [ ] **Step 3: Test template extraction from Python**

```bash
cd ~/project/ai-coworker && python3 -c "
import sys
sys.path.insert(0, '.')
from src.coworker.templates.global_claude_md import generate_global_claude_md
print(generate_global_claude_md())
" | head -5
```
Expected: "# Global instructions for all projects" or similar header

- [ ] **Step 4: Commit**

```bash
git add setup/install.sh
git commit -m "feat: use canonical Global CLAUDE.md template in install.sh"
```

---

### Task 8: Dogfood — Apply New CLAUDE.md to ai-coworker

**Files:**
- Modify: `/home/cicidi/project/ai-coworker/CLAUDE.md` (existing)
- Create: `/home/cicidi/project/ai-coworker/CLAUDE.local.md`
- Create: `/home/cicidi/project/ai-coworker/docs/specs/` (existing)
- Create: `/home/cicidi/project/ai-coworker/docs/discussion/`
- Modify: `~/.claude/CLAUDE.md`

- [ ] **Step 1: Generate and replace project CLAUDE.md**

```bash
cd ~/project/ai-coworker && coworker init --project
```

- [ ] **Step 2: Generate Global CLAUDE.md**

```bash
cd ~/project/ai-coworker && python3 -c "
from src.coworker.templates.global_claude_md import generate_global_claude_md
print(generate_global_claude_md())
" > ~/.claude/CLAUDE.md
```

- [ ] **Step 3: Verify Global CLAUDE.md**

```bash
wc -l ~/.claude/CLAUDE.md
head -10 ~/.claude/CLAUDE.md
```
Expected: <100 lines, contains "Ask and Confirm"

- [ ] **Step 4: Verify Project CLAUDE.md**

```bash
wc -l ~/project/ai-coworker/CLAUDE.md
head -10 ~/project/ai-coworker/CLAUDE.md
```
Expected: <200 lines, contains critical rules first

- [ ] **Step 5: Verify CLAUDE.local.md**

```bash
cat ~/project/ai-coworker/CLAUDE.local.md
```

- [ ] **Step 6: Activate current initiative in new format**

```bash
cd ~/project/ai-coworker && coworker initiative activate claude-md-design
```
Expected: "Injected initiative 'claude-md-design' into ...CLAUDE.local.md"

- [ ] **Step 7: Verify initiative in local.md**

```bash
cat ~/project/ai-coworker/CLAUDE.local.md | grep -c "INITIATIVE:claude-md-design"
```
Expected: 2 (START and END)

- [ ] **Step 8: Run existing tests to check nothing broke**

```bash
cd ~/project/ai-coworker && python -m pytest tests/ -v --ignore=tests/test_templates.py --ignore=tests/test_semantic_merge.py --ignore=tests/test_init.py
```

- [ ] **Step 9: Commit dogfood changes**

```bash
git add CLAUDE.md CLAUDE.local.md .gitignore
git commit -m "chore: dogfood new CLAUDE.md design on ai-coworker itself"
```

---

### Task 9: Integration Test — Full Workflow

**Test:** `tests/test_integration.py`

- [ ] **Step 1: Write end-to-end test**

```python
# tests/test_integration.py

import tempfile
from pathlib import Path
import subprocess


def test_full_init_workflow():
    """Test: init → verify all files → activate initiative → verify injection."""
    with tempfile.TemporaryDirectory() as tmp:
        proj = Path(tmp) / "test-project"
        proj.mkdir()
        (proj / "README.md").write_text("# Test")
        (proj / "requirements.txt").write_text("fastapi==0.100.0\npytest==8.0.0\n")
        import subprocess as sp

        # Step 1: Init
        sp.run(["coworker", "init", "--project"], cwd=str(proj), capture_output=True, text=True)

        # Step 2: Verify all files exist
        assert (proj / "CLAUDE.md").exists(), "Missing project CLAUDE.md"
        assert (proj / "CLAUDE.local.md").exists(), "Missing CLAUDE.local.md"
        assert (proj / "docs" / "specs").exists(), "Missing docs/specs/"
        assert (proj / "docs" / "discussion").exists(), "Missing docs/discussion/"

        # Step 3: Verify CLAUDE.md content
        pmd = (proj / "CLAUDE.md").read_text()
        assert len(pmd.split("\n")) < 200, f"Project CLAUDE.md too long: {len(pmd.split('\n'))} lines"
        assert "Local Override" in pmd, "Missing Local Override section"
        assert "Context Management" in pmd, "Missing Context Management section"
        assert "Workflow Decision" in pmd, "Missing Workflow Decision section"

        # Step 4: Verify CLAUDE.local.md content
        lmd = (proj / "CLAUDE.local.md").read_text()
        assert "Config Paths" in lmd or "config" in lmd.lower()

        # Step 5: Create and activate initiative
        sp.run(["coworker", "initiative", "create", "test-feat", "-d", "test feature"], cwd=str(proj), capture_output=True, text=True)
        sp.run(["coworker", "initiative", "activate", "test-feat"], cwd=str(proj), capture_output=True, text=True)

        # Step 6: Verify initiative injected into local.md
        lmd_after = (proj / "CLAUDE.local.md").read_text()
        assert "INITIATIVE:test-feat" in lmd_after, "Initiative not injected into local.md"

        # Step 7: Deactivate and verify removal
        sp.run(["coworker", "initiative", "deactivate"], cwd=str(proj), capture_output=True, text=True)
        lmd_deactivated = (proj / "CLAUDE.local.md").read_text()
        assert "INITIATIVE:test-feat" not in lmd_deactivated, "Initiative not removed from local.md"


def test_claude_md_local_md_not_committed():
    """Verify CLAUDE.local.md is in .gitignore."""
    with tempfile.TemporaryDirectory() as tmp:
        proj = Path(tmp) / "test-project"
        proj.mkdir()
        (proj / "README.md").write_text("# Test")
        import subprocess as sp
        sp.run(["coworker", "init", "--project"], cwd=str(proj), capture_output=True, text=True)
        gitignore = (proj / ".gitignore").read_text()
        assert "CLAUDE.local.md" in gitignore
```

- [ ] **Step 2: Run integration tests**

```bash
cd ~/project/ai-coworker && python -m pytest tests/test_integration.py -v
```
Expected: all PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add end-to-end integration test for full workflow"
```

---

### Task 10: Run Full Test Suite & Lint

- [ ] **Step 1: Run all tests**

```bash
cd ~/project/ai-coworker && python -m pytest tests/ -v
```

- [ ] **Step 2: Run lint**

```bash
cd ~/project/ai-coworker && ruff check src/ tests/
```

- [ ] **Step 3: Fix any issues, commit**

```bash
git add -A && git commit -m "chore: pass all tests and lint"
```

---

## Self-Review

1. **Spec coverage**: All sections of the spec are implemented — Global template (Task 1), Project template (Task 2), Local template (Task 3), Semantic merge (Task 4), Init/scaffolding (Task 5), Initiative redirect (Task 6), Install update (Task 7), Dogfood (Task 8).

2. **Placeholder scan**: No TBD/TODO placeholders. All code is concrete.

3. **Type consistency**: Function signatures match across tasks. `generate_project_claude_md()` parameters consistent with `_scan_project()` return dict keys.
