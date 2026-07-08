# SKILL.md Frontmatter Schema

Every skill's `SKILL.md` MUST have the following YAML frontmatter.

```yaml
---
# REQUIRED
name: skill-name
version: 0.1.0
description: >
  One or two sentences describing what the skill does and when it should be
  invoked. Written as a YAML multiline string (> or |) when it exceeds one
  line.
triggers:
  - trigger phrase 1
  - trigger phrase 2
when-to-use: >
  Clear, direct guidance on when this skill applies. The AI reads this field
  to decide whether to invoke the skill. Answer: "In what situation should I
  use this skill?" Usually 1-3 sentences.

# OPTIONAL
aliases:
  - alias-1
license: MIT
compatibility:
  - claude-code
  - opencode
  - gemini
---
```

**Rules:**
- `name`: kebab-case, unique within the repo.
- `version`: semantic versioning. Must be bumped when the skill body changes.
- `description`: plain text. The AI reads this to understand what the skill does.
- `triggers`: list of phrases (case-insensitive, lowercase). The AI ORs them — if any phrase appears in the user's request, the skill is relevant.
- `when-to-use`: plain text. Provides additional context beyond trigger matching. The AI uses this to rule out false positives.
- `aliases`: alternative trigger phrases (deprecated/subset of triggers; kept for backward compat). optional.
- `license`: SPDX identifier. optional.
- `compatibility`: list of IDE/tool names this skill is designed for. optional.
- No other keys are permitted in the frontmatter.
