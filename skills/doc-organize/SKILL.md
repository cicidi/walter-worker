---
name: doc-organize
description: |
  Use when creating, moving, reorganizing, or merging documentation. Use when
  the user needs to decide where a doc goes, how to name it, or how to resolve
  merge conflicts between doc versions. Auto-detects whether organizing or
  merging is needed.
license: MIT
compatibility: claude-code,opencode
metadata:
  triggers:
    - organize docs
    - doc organize
    - where should this go
    - move document
    - rename document
    - merge docs
    - doc merge
    - resolve conflicts
    - INDEX.md
    - mkdocs
    - initiative to book
---

# doc-organize

Two-mode skill. Organize mode determines document placement, naming, and
INDEX.md maintenance. Merge mode resolves conflicts between two versions
of a document, preserving PROTECTED blocks.

## When to Use

- Creating a new document and not sure where it belongs
- Reorganizing misplaced docs into the correct structure
- Merging two versions of a doc after upstream sync
- Consolidating initiative docs into a book (MkDocs)
- Maintaining INDEX.md

## When NOT to Use

- Writing document content — just write it
- Reviewing doc quality → use /doc-review design
- Code merge conflicts → use git merge tools, not this skill

## Process

### Step 0: Determine Mode

Auto-detect or ask ONE question:

- User mentions "merge", "conflict", "two versions" → Merge mode
- User mentions "organize", "where", "move", "rename", "book", "index" → Organize mode
- If unclear, ask: "Organize (placement/naming) or merge (resolve conflicts)?"

---

## Branch A: Organize — Document Placement & Structure

### Determine Document Type

Identify the document type from these 10 categories:
`prd`, `research`, `design`, `spec`, `impl-plan`, `test-plan`,
`decision-history`, `retro`, `how-to`, `state`

### Determine Path

1. Identify initiative (ask if unclear)
2. Generate path: `docs/initiatives/<initiative>/<type>/<topic>-<type>.md`
3. Naming convention: `<topic>-<type>.md` separates topic from type

### State Frontmatter

Every document gets `state: draft` or `state: final` in its frontmatter.
`final` requires `final_date`. After `final`, code becomes source of truth.

### INDEX.md Maintenance

After every create, move, or rename: regenerate INDEX.md by walking the
docs tree and reading each file's first heading + first paragraph.

### Reorganize Existing Docs

1. Scan for misplaced files (wrong type dir, wrong naming)
2. Scan for orphaned project folders
3. Propose moves + deletions
4. Update INDEX.md Move Log after each move

### Initiative-to-Book Consolidation

When consolidating an initiative into a book:
1. Scan initiative source docs — only `state: final` docs qualify
2. Only 4 of 10 types enter the book: `prd`, `design`, `spec`, `how-to`
3. Distill each doc: 2-3 paragraph overview, key decisions, API highlights
4. Update `mkdocs.yml` nav config
5. Update INDEX.md

---

## Branch B: Merge — Resolve Document Conflicts

Merge two versions of a markdown document after upstream sync conflicts.

### Steps

1. **Identify** — which two files/versions? Read both, find conflict markers
   (`<<<<<<<`, `=======`, `>>>>>>>`)
2. **Merge strategy:**
   - PROTECTED blocks → always kept unchanged (never modified)
   - Headings → preserve structure from the newer version
   - New content from either version → kept
   - Conflicting content → show both, ask the user to choose
   - Formatting → normalize to consistent markdown
3. **Validate:**
   - Heading hierarchy (no skipped levels)
   - All links valid
   - No duplicate sections
   - PROTECTED blocks intact
4. **Output** — show diff summary: "Added X sections, resolved Y conflicts,
   kept Z PROTECTED blocks." Do NOT auto-commit; user must review first.

### PROTECTED Blocks

Content wrapped in `<!-- PROTECTED START -->` / `<!-- PROTECTED END -->` is
never modified during merge. These blocks survive all operations intact.

## Quality Gates

### Organize MUST
- [ ] Document type correctly identified from 10 categories
- [ ] State frontmatter present (`draft` or `final`)
- [ ] INDEX.md updated after every create/move/rename
- [ ] Book only includes `state: final` docs (prd, design, spec, how-to only)

### Merge MUST
- [ ] All PROTECTED blocks intact after merge
- [ ] No data loss — all unique content from both versions accounted for
- [ ] Heading hierarchy valid (no skipped levels)
- [ ] User reviewed output before any commit
