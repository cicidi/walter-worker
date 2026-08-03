# Cross-Project Gaps — 2026-07-26

> Generated from session decision extraction across 9 projects
> Total: 418 decisions extracted

## Completed Projects

| Project | Decisions | Decision-History | INDEX.md | Status |
|---------|-----------|-----------------|----------|--------|
| walter-worker | 155 | ✅ 16 files | ✅ | Partial (15/132 sessions) |
| skill-factory | 126 | ✅ 14 files | ✅ | Complete |
| mfangdai | 42 | ✅ 6 files | ✅ | Complete |
| hackathon-video-gen | 40 | ✅ 3 files | ✅ | Complete |
| mratequote | 15 | ✅ 2 files | ✅ | Complete |
| luma | 13 | ✅ 1 file | — | Complete |
| computer-config | 12 | ✅ 2 files | ✅ | Complete |
| video-gen | 9 | ✅ 1 file | — | Complete |
| deterministic-workflow | 6 | ✅ 1 file | — | Partial (5/179 sessions) |

## Gaps to Fix (Priority Order)

### 1. mratequote — Missing: PRD, Spec, Test Plan
- Repo: /home/cicidi/project/mratequote
- 15 decisions extracted, but no planning docs exist
- Generate: PRD (mortgage rate quote tool), Spec (API/UI), Test Plan

### 2. computer-config — Missing: PRD, Test Plan  
- Repo: /home/cicidi/project/computer-config
- 12 decisions, mostly about dotfiles, tmux, Ghostty, Toshy config
- Generate: PRD (dev environment setup), Test Plan

### 3. luma — Missing: PRD, Test Plan
- Repo: /home/cicidi/project/luma  
- 13 decisions about Luma event scout skill
- Generate: PRD, Test Plan

### 4. video-gen — Missing: Spec
- Repo: /home/cicidi/project/video-gen
- 9 decisions about video generation pipeline
- Generate: Spec

### 5. hackathon-video-gen — Missing: Test Plan
- Repo: /home/cicidi/project/hackathon-video-gen
- 40 decisions, has PRD and Spec
- Generate: Test Plan

### 6. skill-factory — Missing: PRD
- Repo: /home/cicidi/project/skill-factory
- 126 decisions, has extensive skills but no PRD
- Generate: PRD

### 7. deterministic-workflow — Needs full session extraction
- Only 5/179 sessions processed
- Continue extraction

### 8. walter-worker — Needs session extraction completion
- Only 15/132 sessions processed  
- Continue extraction

## Auto-Worker Instructions

For each project with missing docs:
1. Read existing code and decision-history
2. Generate missing document following doc-organize conventions
3. Place in `docs/<project-name>/<type>/<topic>-<type>.md`
4. Update INDEX.md
