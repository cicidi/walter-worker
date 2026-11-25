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
| **ARD-H** | 2026-11-24 | The session summary (memory capture, then close) runs once per session from a detached SessionEnd hook; the Stop hook no longer runs capture or close. |
| **ARD-G** | 2026-11-24 | This feature's documents describe the memory code as it behaves at `a0f4ce0` and are the authority for current behavior; the older memory design and memory-graph-spec.md under docs/features/self-evolving-agent/ remain as design history and are not edited here. |
| **ARD-F** | 2026-11-24 | The review-fix pass for this backfill is applied as edits larger than the 10-line/200-character limit, authorized by the owner's 2026-11-24 instruction to decide the approach ("你自己看着弄"). |
| **ARD-D** | 2026-11-24 | Where the code does not meet a requirement, the PRD keeps the requirement, the design states what the code does today, and the gap is a design Open Question for the owner to decide. |
| **ARD-A** | 2026-11-24 | The uncommitted 2026-11-04 drafts are rewritten whole in their first commit. Their IDs were never published, so no old-to-new table is kept. |
| **ARD-C** | 2026-07-27 | Capture writes graph facts to a pending dump; a separate merge step folds dumps into `graph.json` with atomic writes. |
| **ARD-E** | 2026-07-25 | Skill staging is limited to three per 24 hours by a circuit breaker, and promotion needs human approval. |
| **ARD-B** | 2026-07-25 | Lessons are stored in mem0 over a local vector database with local embeddings; language-model calls go to DeepSeek, with Gemini as fallback. |

## Evidence Appendix

### ARD-H

The owner decided on 2026-11-24: "stop hook 只记录chat history 不做summary". The owner then chose to run the summary once per session ("run once"). The code states why: Stop fires after every reply, so capture made one 15-20 s model call per reply (`on-session-end.sh:4-7` at `a91ebbd`). The hook detaches the run because, as its comment says, Claude Code cancels a SessionEnd hook after 1.5 s (`on-session-end.sh:9-12`); newer Claude Code releases may differ. Rejected: keeping capture and close on Stop. Evidence: walter-worker PR #22, merged as `a91ebbd`; the owner's words of 2026-11-24.

### ARD-G

The 2026-11-24 review found a second, older design for the same subsystem: the [older memory design](../../self-evolving-agent/design/memory-platform-design.md) and the [memory graph spec](../../self-evolving-agent/spec/memory-graph-spec.md). The code still cites the second one as its specification, in `src/coworker/memory/graph.py` line 3 at `a0f4ce0`. The two disagree with this feature on facts; for example, the older design's overview figure puts `coworker memory sync` in the capture layer on its per-turn path, while in the code `memory sync` imports Graphify output. One fact needs one home, so this feature's documents state current behavior and the older ones are kept only as history. Rejected: editing the older documents in this pass, because that is outside this pass's scope, and retiring them now, which would go through doc-organize and needs the owner. Evidence: `raw/review/2026-11-24-spec-review-memory-platform-gaps.md`, finding I3.

### ARD-F

The review listed 16 findings rated 3 or more, and most of them change several paragraphs and tables at once. Applying them under the 10-line and 200-character limit would take many dozens of edits that cannot be reviewed apart from each other. The owner told the agent on 2026-11-24 to decide the approach ("你自己看着弄"). Rejected: splitting the pass into edits within the limit. Evidence: `raw/review/2026-11-24-spec-review-memory-platform-gaps.md`; the owner's instruction of 2026-11-24.

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
| 0.2 | 2026-11-24 | Review fixes: ARD-F (edit-size authorization for the review-fix pass) and ARD-G (this feature is the authority for current behavior) added |
| 0.3 | 2026-11-24 | ARD-H added: the summary runs once per session from a SessionEnd hook; the 1.5 s limit attributed to the hook's comment |
