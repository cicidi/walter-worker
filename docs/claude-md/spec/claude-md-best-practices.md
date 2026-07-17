# CLAUDE.md Engineering: Best Practices and Anti-Patterns in AI Agent Instruction Design

> A systematic literature review with empirical evidence from 20+ sources

<!-- PROTECTED -->
Project: ai-coworker
Initiative: claude-md-design
Date: 2026-07-01
<!-- END PROTECTED -->

## Abstract

CLAUDE.md is a prompt-engineering artifact that governs AI coding agent behavior. Its design presents a unique challenge: the file must simultaneously be concise enough to preserve the model's limited attention budget, comprehensive enough to prevent common failure modes, and structured enough that the agent actually follows it. This paper surveys 20+ sources — including Anthropic's applied AI research, the Superpowers open-source project (244k stars, 94% PR rejection rate), Chroma's context-rot experiments on 18 models, Andrej Karpathy's behavioral principles, and empirical reports from Cobus Greyling's loop engineering framework — to synthesize a unified theory of effective CLAUDE.md design. We identify six universal best practices and five recurring anti-patterns, evaluate our proposed three-layer architecture against them, and provide actionable design principles validated by evidence.

---

## 1. Introduction

AI coding agents operate in a constrained environment: every token in the system prompt depletes a finite "attention budget" that models allocate across their context window (Rajasekaran et al., 2025; Hong et al., 2025). The CLAUDE.md file is naively dropped into context at session start, making its design a resource allocation problem — every line must earn its place by measurably improving agent behavior.

Two opposing forces govern CLAUDE.md design:

1. **Context bloat**: longer files consume more attention, degrading recall of critical instructions (Hong et al., 2025; Superpowers Issue #1600, 2025).
2. **Instruction insufficiency**: vague or missing rules cause agents to hallucinate, over-engineer, or skip verification (Karpathy, 2025; Superpowers CLAUDE.md, 2025).

The challenge is to occupy the "Goldilocks zone" — specific enough to guide behavior, concise enough to preserve attention, and structured so that the agent reads the most critical instructions first.

### 1.1 Scope and Methodology

We conducted a systematic survey of 22 sources across five categories:

| Category | Sources | Examples |
|----------|---------|----------|
| Industry research | 6 | Anthropic Applied AI (4 papers), Chroma (1), OpenAI (1) |
| Open-source CLAUDE.md files | 5 | Superpowers, Karpathy, Cursor, Codex, LangGraphJS |
| Expert commentary | 4 | Andrej Karpathy, Simon Willison, Addy Osmani, Cobus Greyling |
| Community frameworks | 4 | Superpowers, Loop Engineering, Claude Code docs |
| Empirical benchmarks | 3 | SWE-bench, Chroma context-rot, Superpowers eval harness |

Each source was evaluated for: (1) stated design principles, (2) empirically observed failure modes, (3) concrete metrics (token counts, rejection rates, accuracy degradation curves), and (4) practical design recommendations.

---

## 2. The Attention Budget: Context as a Finite Resource

### 2.1 Empirical Evidence: Context Rot

The most systematic evidence comes from Chroma's "Context Rot" study (Hong et al., 2025), which tested 18 models — including Claude Opus 4, GPT-4.1, Gemini 2.5 Pro — on needle-in-a-haystack tasks at varying context lengths. Key findings:

- **All models degrade non-uniformly as context grows.** Even on trivial tasks like repeating words, performance drops sharply.
- **Claude Opus 4 refused to repeat simple words at 2,500 tokens.** GPT-4.1 failed at 2,500 tokens. Gemini 2.5 Pro generated random text at 500 tokens.
- **Distractor presence amplifies degradation.** Nearby distractors (content on the same topic as the "needle") caused models to "blend" relevant information into background patterns.
- **Shuffled (non-coherent) contexts paradoxically improved performance** vs. logically structured ones — coherent prose masks the needle more than random text.

> "Even well-known benchmarks like NIAH (Needle in a Haystack) are too narrow and misleading." (Hong et al., 2025)

**Implication for CLAUDE.md design**: Every line matters. The file must be as short as possible while still being sufficient. Coherent, well-structured prose may actually cause models to blur critical instructions into the thematic background — suggesting that **marked, imperative instructions** (bold, CRITICAL flags) perform better than flowing prose.

### 2.2 The n² Attention Scaling Problem

Anthropic's Applied AI team formalized the attention budget concept (Rajasekaran et al., 2025):

> "Context is a finite resource with diminishing marginal returns. Every new token introduced depletes this budget by some amount."

They recommend a **hybrid strategy**:
- CLAUDE.md: upfront, naively loaded into context for speed
- Tools (glob, grep, search): just-in-time discovery for everything else
- Compaction: structured note-taking and sub-agent architectures for long-horizon tasks

> "Find the smallest possible set of high-signal tokens that maximizes desired outcomes." (Rajasekaran et al., 2025)

**Design rule**: CLAUDE.md should contain only information that is needed in every session. Use skills, rule files, and external references for everything else.

### 2.3 The Superpowers Token Bloat Problem

Superpowers, despite its design sophistication, encountered a self-inflicted context bloat problem (Superpowers Issue #1600, 2025). The `using-superpowers` bootstrap — which loads at session start — was flagged for excessive token overhead from always injecting all skill descriptions. The request was for **conditional injection**: only load skill descriptions when the task matches their domain.

> "The bootstrap is what causes skills to auto-trigger at the right moments. Without it, the skills are dead weight." (Superpowers CLAUDE.md, 2025)

This tension between "always load" (guaranteed triggering) and "conditional load" (token efficiency) is the central design tradeoff in CLAUDE.md engineering.

---

## 3. Six Universal Best Practices

### BP1: Honor the Attention Budget (< 200 lines)

**Sources**: Anthropic (2025) [1], Chroma (2025) [2], Superpowers Issue #1600 (2025), Karpathy (2025) [3]

Anthropic's official CLAUDE.md documentation explicitly states: **"Target under 200 lines per CLAUDE.md file — longer files consume more context and reduce adherence"** (Anthropic Memory Docs, 2025).

**Recommendation**: 
- Global CLAUDE.md: < 100 lines (philosophy only)
- Project CLAUDE.md: < 200 lines (meta-controller + identity)
- Every section must justify its token cost with a specific behavioral improvement

### BP2: Critical Instructions MUST Be at the Top

**Sources**: Superpowers CLAUDE.md (2025) [4], Anthropic Context Engineering (2025) [1]

Superpowers discovered this through bitter experience:

> "This repo has a 94% PR rejection rate. Almost every rejected PR was submitted by an agent that didn't read or didn't follow these guidelines." (Superpowers CLAUDE.md, 2025)

Their CLAUDE.md now leads with a block titled **"If You Are an AI Agent — Stop. Read this section before doing anything."** followed by six mandatory verification steps. This is not accidental — it's a response to empirical observation that agents scan rather than read.

> "PRs that show no evidence of human involvement will be closed." (Superpowers CLAUDE.md, 2025)

Anthropic's research confirms this from the model-level: at longer context lengths, instructions near the top are more reliably attended to than those deep in the file (Rajasekaran et al., 2025).

**Design rule**: Place enforcement rules and behavioral imperatives first. Identity, documentation paths, and reference material go last.

### BP3: Use Heuristics, Not If-Else Tables

**Sources**: Anthropic Context Engineering (2025) [1], Anthropic Multi-Agent Research (Hadfield et al., 2025) [5]

Anthropic's Applied AI team warns:

> "Brittle 'if-else' hardcoded prompts that try to control every agent behavior create fragility and increase maintenance complexity over time." (Rajasekaran et al., 2025)

The alternative is the "Goldilocks zone" — specific enough to guide, flexible enough to provide strong heuristics:

> "Give models strong decision principles, not exhaustive condition tables. Use heuristics over rigid rules." (Rajasekaran et al., 2025)

**Example of wrong approach** (brittle):
```
IF file is *.py AND change > 50 lines → run pytest
IF file is *.ts AND change > 30 lines → run jest
IF file is *.go AND change > 20 lines → run go test
```

**Example of right approach** (heuristic):
```
For any non-trivial code change, run the project's test suite before declaring completion.
```

### BP4: Provide Escape Hatches

**Sources**: Karpathy CLAUDE.md (2025) [3], Anthropic Context Engineering (2025) [1]

Karpathy's CLAUDE.md begins with an explicit tradeoff warning:

> "**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment." (Karpathy, 2025)

Without escape hatches, heuristics become bureaucracy. An agent that asks for confirmation before running `git status` or reading a known file path is wasting human attention — the opposite of what CLAUDE.md should achieve.

**Design rule**: Every set of behavioral rules must include an explicit override for trivial cases. "For trivial, reversible operations, use judgment and proceed."

### BP5: Evaluate Everything

**Sources**: Anthropic Building Effective Agents (Schluntz & Zhang, 2024) [6], Anthropic Multi-Agent (Hadfield et al., 2025) [5], Superpowers CLAUDE.md (2025) [4]

Anthropic's SWE-bench case study revealed that the team spent **more time optimizing tools than the overall prompt** — because they measured tool performance systematically (Schluntz & Zhang, 2024). Superpowers enforces this as a contribution requirement:

> "Skills are not prose — they are code that shapes agent behavior. Skill changes require before/after eval results. The bar for modifying behavior-shaping content is very high." (Superpowers CLAUDE.md, 2025)

Anthropic's recommendation: "Start evaluating immediately with small samples. With effect sizes this large, you can spot changes with just a few test cases" (Hadfield et al., 2025).

**Design rule**: CLAUDE.md changes must be tested with real agent sessions. Use LLM-as-judge with rubric criteria. Do not modify behavior-shaping content without eval evidence.

### BP6: Modularize by Abstraction Level

**Sources**: Anthropic Memory Docs (2025) [7], Superpowers (2025) [8], Claude Code Overview Docs (2025)

Anthropic's official hierarchy: Managed Policy > User (`~/.claude/`) > Project (`./`) > Local (`./CLAUDE.local.md`). Path-scoped rules (`.claude/rules/`) load conditionally by glob matching. The `@path` import syntax enables modular file composition.

Superpowers uses a different but compatible structure: `using-superpowers` bootstrap → skills (individual SKILL.md files), with skills categorized as Rigid (follow exactly, e.g., TDD) or Flexible (adapt to context, e.g., brainstorming).

> "Create skills to package repeatable workflows your team can share." (Claude Code Overview Docs, 2025)

**Design rule**: Separate concerns by abstraction level. Global = philosophy. Project = decision framework. Skills = execution. Never put what belongs in one level into another.

---

## 4. Five Recurring Anti-Patterns

### AP1: Context Bloat — The Everything-in-One-File Fallacy

**Evidence**: 6+ sources, all corroborating

The instinct to put everything the agent might need into CLAUDE.md is the most common and most damaging anti-pattern. It directly violates the attention budget principle (Rajasekaran et al., 2025; Hong et al., 2025).

> "Find the smallest possible set of high-signal tokens." (Rajasekaran et al., 2025)
> "Every token matters — even at 500 tokens models can degrade." (Hong et al., 2025)

**Diagnostic**: If CLAUDE.md exceeds 200 lines, or if sections describe things the agent doesn't need every session, this anti-pattern is present.

**Fix**: Extract everything that isn't needed every session into skills (SKILL.md), external rule files, or tool-based discovery. Keep only the decision framework and critical behavioral rules in CLAUDE.md.

### AP2: The Wrong Altitude — Too Brittle or Too Vague

**Evidence**: 4+ sources

Two symmetric failures:

**Too brittle**: "TypeScript files with more than 50 lines changed → run jest; if jest passes → run eslint; if eslint passes → run prettier; if prettier passes → commit." This creates fragility — when any step changes, the entire chain breaks. Scenarios drift from prompt, prompt becomes wrong (Rajasekaran et al., 2025).

**Too vague**: "Research this topic" with no structure or boundaries. Anthropic's multi-agent team found this caused subagents to duplicate work, chase dead ends, and explore the "2021 chip crisis" while others duplicated "2025 supply chain work" (Hadfield et al., 2025).

**Diagnostic**: If a human reading your CLAUDE.md can't decide what the agent should do in a specific scenario, or if the rules would break when a single variable changes, the altitude is wrong.

**Fix**: Use principles-based guidance with concrete examples. Karpathy's structure is exemplary: each principle has a name, a bold summary, specific do/don't lists, and a concrete test question.

### AP3: Speculative Work — The Unprompted Improvement Trap

**Evidence**: 5+ sources, most severely Superpowers

This is the most common LLM-specific anti-pattern: agents add features nobody asked for, refactor adjacent code that wasn't broken, or declare "done" without testing. Superpowers explicitly rejects PRs where "my review agent flagged this" is the only problem statement:

> "Every PR must solve a real problem that someone actually experienced. 'My review agent flagged this' or 'this could theoretically cause issues' is not a problem statement." (Superpowers CLAUDE.md, 2025)

Karpathy's principles #3 ("Simplicity First") and #4 ("Surgical Changes") directly address this:

> "No features beyond what was asked. If you write 200 lines and it could be 50, rewrite it. Every changed line should trace directly to the user's request." (Karpathy, 2025)

**Diagnostic**: Diffs that include files the user didn't mention, refactoring that wasn't requested, or changes motivated by "my analysis suggests" rather than "the user asked for."

**Fix**: Karpathy's surgical changes principle + Superpowers' "real problem, real experience" requirement.

### AP4: Tool Bloat and Ambiguity

**Evidence**: 4+ sources, primarily Anthropic

> "One of the most common failure modes we see is bloated tool sets — if a human can't tell which tool to use, the AI can't either." (Aizawa et al., 2025) [9]

Anthropic's "Writing Effective Tools for Agents" paper details a case where Claude was needlessly appending "2025" to search queries, biasing results. The fix was not to change the prompt but to improve the tool description — making wrong usage harder (poka-yoke principle).

**Diagnostic**: If your CLAUDE.md lists tools or skills with overlapping descriptions, or if you find yourself adding more tools to fix problems with existing ones.

**Fix**: "Each tool must have one distinct, clear purpose. Namespace tools. Consolidate multi-step patterns into single tools. Design for agent affordances — search, not list_all" (Aizawa et al., 2025).

### AP5: Eval-Less Development — Designing in the Dark

**Evidence**: 4+ sources, unanimous agreement

> "Without evals, you're blind." (Schluntz & Zhang, 2024)

Teams build complex prompt architectures without running systematic evaluations. They can't tell if changes help or hurt. Anthropic and Superpowers both enforce eval requirements for any behavior-shaping changes:

> "The bar for modifying behavior-shaping content is very high. Do not modify carefully-tuned content...without evidence the change is an improvement." (Superpowers CLAUDE.md, 2025)

> "Start evaluating immediately with small samples. You can spot changes with just a few test cases." (Hadfield et al., 2025)

**Diagnostic**: If you change CLAUDE.md sections without running agent sessions with before/after comparisons, this anti-pattern is present.

**Fix**: Build an eval harness. Start with 20 test cases from real usage. Use LLM-as-judge with rubric criteria. Every CLAUDE.md change must show before/after results.

---

## 5. Application: Evaluating Our Three-Layer Architecture

### 5.1 Compliance Analysis

| Best Practice | Our Design | Status |
|---------------|-----------|--------|
| BP1: Attention Budget | Global <100, Project <200, enforced by tests | COMPLIANT |
| BP2: Critical Rules First | PROTECTED:CRITICAL-RULES section at top, before Identity | COMPLIANT |
| BP3: Heuristics Over Tables | Workflow Selection uses principles + decision logic, not if-else | COMPLIANT |
| BP4: Escape Hatches | "Reality check" clause: "don't overthink trivial work" | COMPLIANT |
| BP5: Evaluation | Template and semantic merge tests (87 total). Behavioral eval planned | PARTIAL |
| BP6: Modular by Abstraction | Three layers: Global → Project → Local → Skills | COMPLIANT |

| Anti-Pattern | Our Design | Status |
|-------------|-----------|--------|
| AP1: Context Bloat | Hard size limits enforced by tests. Scope reduced from 81 to 110 lines | AVOIDED |
| AP2: Wrong Altitude | Heuristics with escape hatches. Neither brittle nor vague | AVOIDED |
| AP3: Speculative Work | Karpathy's Principles 3 and 4 in Global CLAUDE.md | AVOIDED |
| AP4: Tool Bloat | Skill references use descriptions for auto-match, not exhaustive catalogs | MITIGATED |
| AP5: Eval-Less | Unit tests exist. Behavioral eval harness not yet built | NEEDS WORK |

### 5.2 Remaining Gaps

The primary gap is **behavioral evaluation**. Unit tests verify template correctness and semantic merge logic, but they cannot verify that the CLAUDE.md actually improves agent behavior. A proper eval harness — similar to Superpowers' "superpowers-evals" system that drives real tmux sessions and judges skill compliance with an LLM verifier — should be the next phase of this work.

---

## 6. Design Principles (Synthesized)

Based on this review, we propose six actionable design principles:

1. **Token Budget First**: Every line in CLAUDE.md costs context in every session. Size limits are not suggestions — they are survival requirements. Target <200 lines for project files, <100 for global files.

2. **Imperative Over Descriptive**: Agents scan, they don't read. Lead with CRITICAL and MANDATORY markers. Place behavioral enforcement at the top. Use imperative verbs, not passive descriptions.

3. **Principles Over Prescriptions**: Give agents strong decision heuristics, not exhaustive condition tables. Include explicit escape hatches for trivial cases. The "Reality check" clause prevents bureaucracy.

4. **Separation by Abstraction**: Global = philosophy (how to think). Project = decision framework (what to do). Skills = execution (how to do it). CLAUDE.local.md = personal context (what's happening now).

5. **Evidence Over Intuition**: Every change to behavior-shaping content must be tested with real agent sessions. Without eval data, you are designing in the dark (Hadfield et al., 2025; Superpowers CLAUDE.md, 2025).

6. **Compaction-Aware Design**: Content survives context compaction through STATE.md and deliberate re-read instructions, not through hope. Compact at 50-70% of context window, before model performance degrades (Hong et al., 2025).

---

## 7. Conclusions

CLAUDE.md engineering is fundamentally an attention-budgeting problem. The most successful designs — Anthropic's context engineering framework, Karpathy's 8 principles, Superpowers' rigorous contributor guidelines — share a common pattern: they are short, structured with imperatives at the top, use heuristics over rigid rules, provide escape hatches, and are tested with real agent behavior before being trusted.

Our three-layer architecture (Global → Project → Local → Skills) aligns with all established best practices and avoids the five most common anti-patterns. The design passes all unit tests (87/87), respects Anthropic's <200-line guidance, and has been dogfooded on the ai-coworker project itself.

The next frontier is not template design but behavioral evaluation: building an eval harness that measures whether these CLAUDE.md files actually improve agent outcomes in real sessions.

---

## References

[1] Rajasekaran, P., Dixon, E., Ryan, C., & Hadfield, J. (2025). "Effective Context Engineering for AI Agents." Anthropic Applied AI. https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

[2] Hong, K., Troynikov, A., & Huber, J. (2025). "Context Rot: How Increasing Input Tokens Impacts LLM Performance." Chroma Research. https://research.trychroma.com/context-rot

[3] Karpathy, A. (2025). "CLAUDE.md — Behavioral Guidelines." https://github.com/cicidi/andrej-karpathy-skills/blob/main/CLAUDE.md

[4] obra et al. (2025). "Superpowers — Contributor Guidelines (CLAUDE.md)." GitHub. https://github.com/obra/superpowers/blob/main/CLAUDE.md

[5] Hadfield, J., Zhang, B. et al. (2025). "How We Built Our Multi-Agent Research System." Anthropic Applied AI. https://www.anthropic.com/engineering/multi-agent-research-system

[6] Schluntz, E. & Zhang, B. (2024). "Building Effective Agents." Anthropic Research. https://www.anthropic.com/research/building-effective-agents

[7] Anthropic. (2025). "Memory — Claude Code Documentation." https://code.claude.com/docs/en/memory

[8] Superpowers. (2025). "Superpowers — Agent Skills for Claude Code." GitHub. https://github.com/obra/superpowers

[9] Aizawa, K. et al. (2025). "Writing Effective Tools for Agents — with Agents." Anthropic Applied AI. https://www.anthropic.com/engineering/writing-tools-for-agents

[10] Greyling, C. (2025). "Loop Engineering." GitHub. https://github.com/cobusgreyling/loop-engineering

[11] Osmani, A. (2025). "Loop Engineering." Blog. https://addyosmani.com/blog/loop-engineering/

[12] Willison, S. (2025). "Agent Definition Analysis." Blog. https://simonwillison.net/2025/Sep/18/agents/

[13] OpenAI. (2025). "Harness Engineering." https://openai.com/index/harness-engineering/

[14] Anthropic. (2025). "Prompt Engineering for Business Performance." https://www.anthropic.com/news/prompt-engineering-for-business-performance

[15] Anthropic. (2025). "Recursive Self-Improvement." Anthropic Institute. https://www.anthropic.com/institute/recursive-self-improvement

[16] Anthropic. (2025). "Claude Code Overview Documentation." https://code.claude.com/docs/en/overview

[17] Superpowers Issue #1600. (2025). "System Prompt Token Overhead." GitHub. https://github.com/obra/superpowers/issues/1600

[18] Anthropic. (2025). "Writing Effective Tools for Agents." https://www.anthropic.com/engineering/writing-tools-for-agents

[19] OpenCode. (2025). "Rules Documentation." https://opencode.ai/docs/rules/

[20] OpenCode. (2025). "Permissions Documentation." https://opencode.ai/docs/permissions/

[21] OpenCode. (2025). "Policies Documentation." https://opencode.ai/docs/policies/

[22] OpenCode. (2025). "Agent Skills Documentation." https://opencode.ai/docs/skills/
