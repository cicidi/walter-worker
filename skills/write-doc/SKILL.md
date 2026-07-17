---
name: write-doc
version: 0.1.0
description: Enforces Change Log on every docs/ file modification. Works with doc-organize for placement and naming. doc-organize decides WHERE and WHAT NAME; write-doc handles Change Log.
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
when-to-use: Before writing or modifying any file under docs/. ALWAYS append a Change Log. For new files, consult doc-organize first for correct path and naming.
aliases: []
---
# Write Doc

Every time a file in `docs/` is written or modified, append a **Change Log** at the END of the file.

## Integration with doc-organize

**CRITICAL**: Before creating a new file, invoke `doc-organize` to determine:
1. Correct initiative and type folder
2. Correct file name: `YYYY-MM-DD-<initiative>-<desc>.md`
3. Update `docs/INDEX.md`

write-doc handles ONLY the Change Log. doc-organize handles placement.

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
