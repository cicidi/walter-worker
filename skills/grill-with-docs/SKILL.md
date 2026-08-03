---
name: grill-with-docs
description: |
  Use when you need a relentless interview to sharpen a plan or design. Writes
  ADRs and glossary (CONTEXT.md) inline as terminology crystallizes. Composes
  /grilling and /domain-modeling into one session.
license: MIT
compatibility: claude-code,opencode
metadata:
  triggers:
    - grill with docs
    - sharpen plan
    - grilling session
    - domain interview
  when_to_use: |
    When a plan or design is fuzzy and needs relentless questioning to become
    sharp. When domain terminology must be captured and written to CONTEXT.md
    and ADRs during the conversation.
  when_not_to_use: |
    When requirements are already crystal clear. When the user just wants a
    quick answer, not a full interview session.
  audience:
    - developers
    - architects
  source_author: mattpocock
  source_url: https://github.com/mattpocock/skills/blob/main/skills/engineering/grill-with-docs/SKILL.md
---

# grill-with-docs

Run a `/grilling` session, using the `/domain-modeling` skill.
