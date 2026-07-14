---
name: write-doc
version: 0.1.0
description: >
  Used when writing or modifying any documentation file (*.md, *.yaml) in the
  docs/ directory. Enforces change log appending at the end of every file.
triggers:
  - write doc
  - edit doc
  - create spec
  - update spec
  - modify doc
  - write spec
  - edit spec
  - create plan
  - update plan
  - document
  - prd
  - move file
when-to-use: >
  Used BEFORE writing or modifying any file under docs/ — ALWAYS append a
  Change Log entry at the end of the file. This is mandatory for all doc
  modifications, including file moves between directories.
aliases: []
---

# Write Doc

Every time a file in `docs/` is written or modified, append a **Change Log**
entry at the END of the file.

## Rules

1. **Append, never prepend.** The Change Log section goes at the very end of
   the file, below all other content.
2. **Every modification gets an entry.** Including file moves, renames,
   content updates, reclassification.
3. **Format is consistent.** Use a Markdown table with `Date` and `Change`
   columns.
4. **If no Change Log section exists,** create one at the end of the file.

## Change Log Format

```markdown
## Change Log

| Date | Change |
|------|--------|
| 2026-07-11 | Initial creation |
| 2026-07-11 | Moved from docs/specs/ to docs/spec/ |
```

The `## Change Log` header uses `##` (H2) to match existing document heading
hierarchy.

## What Counts as a Modification

- Creating a new file → add "Initial creation" entry
- Moving a file to a new directory → add "Moved from X to Y" entry
- Editing content → add brief description of the change
- Renaming a file → add "Renamed from X" entry

## Example Usage

```
User: move docs/specs/01-foo.md to docs/spec/01-foo.md
AI:
  1. Read docs/specs/01-foo.md
  2. Edit (append Change Log entry: "2026-07-11 | Moved from docs/specs/ to docs/spec/")
  3. Write to docs/spec/01-foo.md
  4. Delete docs/specs/01-foo.md (or git mv)
```

## Quality Gates

- [ ] Change Log section exists at end of every modified doc file
- [ ] New entry added with current date and brief description
- [ ] Existing Change Log entries are preserved (never delete old entries)
- [ ] Format matches the specification: `| YYYY-MM-DD | Description |`
