---
feature: memory-platform
type: decision-history
state: draft
health: active
owner: cicidi
last_verified: 2026-11-24
---

# Memory Platform — Decision History

Decisions about memory capture, storage, and curation. Newest first. Each decision has an entry in the Evidence Appendix with its reason and the options it rejected.

## Decision Log

| ID | Date | Decision |
|---|---|---|
| **ARD-D** | 2026-11-24 | Where the code does not meet a requirement, the PRD keeps the requirement, the design states what the code does today, and the gap is a design Open Question for the owner to decide. |
| **ARD-A** | 2026-11-24 | The uncommitted 2026-11-04 drafts are rewritten whole in their first commit. Their IDs were never published, so no old-to-new table is kept. |
| **ARD-C** | 2026-07-27 | Capture writes graph facts to a pending dump; a separate merge step folds dumps into `graph.json` with atomic writes. |
| **ARD-E** | 2026-07-25 | Skill staging is limited to three per 24 hours by a circuit breaker, and promotion needs human approval. |
| **ARD-B** | 2026-07-25 | Lessons are stored in mem0 over a local vector database with local embeddings; language-model calls go to DeepSeek, with Gemini as fallback. |

## Evidence Appendix

### ARD-D

The 2026-11-24 fact pass found eight gaps (QUES-A to QUES-H), two of which can block or lose graph updates. The spec standard's conflict rule is to report and ask, never to pick a side silently. Rejected: lowering the requirements to match the code. Evidence: the design's Open Questions, each citing the code at `a0f4ce0`.

### ARD-A

The drafts omitted the whole graph pipeline, claimed safety gates on every destructive write and an audit log of every memory change, and said keys could come from `~/.coworker/.env`; the code does none of these. Rejected: correcting them in many small edits. Evidence: the drafts in the shared checkout at `docs/features/memory-platform/`; `src/coworker/memory/` at `a0f4ce0`.

### ARD-C

Merging into the graph means loading, deduplicating, and saving the whole file; doing that inside the capture hook would lengthen every session's end, and a crash mid-write could damage the graph. A pending file per session decouples the two, and writing through a temporary file and a rename keeps the graph whole. Rejected: merging in the capture hook. Evidence: walter-worker commit `c6cacd5`.

### ARD-E

An unattended loop that writes skills could flood the user's skill list. A small daily cap and a human approval step keep that bounded. Rejected: automatic promotion. Evidence: walter-worker commit `bde0ac9`.

### ARD-B

Local embeddings keep stored vectors on the machine and cost nothing per call; the language model is needed only for extraction. DeepSeek was chosen as the primary provider for cost. Rejected: a hosted vector service. Evidence: walter-worker commits `fb7018b` and `3eab5b8`.

## Change Log

| Version | Date | Description |
|---|---|---|
| 0.1 | 2026-11-24 | Created with ARD-A to ARD-E |
