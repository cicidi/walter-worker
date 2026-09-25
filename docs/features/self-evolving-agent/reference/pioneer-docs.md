# Pioneer.ai — Reference Documentation

> Source: https://docs.pioneer.ai | Promo code: HACKATHONSF0724
> Agent: https://agent.pioneer.ai
> Company: Fastino Labs (backed by $25M from Khosla Ventures, Insight Partners, M12/Microsoft, NEA)

## Overview

Pioneer is a platform that identifies model failures, retrains specialist models on user data, and routes traffic automatically — all behind OpenAI/Anthropic-compatible endpoints requiring no code changes.

## Core Capabilities

1. **Drop-in inference** — Clients point existing SDKs at Pioneer, preserving the same API surface and code.
2. **Automatic gap detection** — Traffic is clustered by use case; Pioneer highlights accuracy/cost/latency gaps.
3. **Specialist model training** — Fleet of small fine-tuned models (Qwen, Llama, DeepSeek, GLiNER, etc.) trained without user MLOps.
4. **User-controlled routing** — Lift, cost, latency metrics per specialist; routing decisions remain with user.

## Adaptive Inference (Self-Improving Loop)

Continuous improvement loop that:
- **Monitors** live inference traces for failure patterns
- **Clusters** production traffic by use case
- **Performs semantic triage** on failures (filtering poisoned/contradictory data)
- **Synthesizes corrective training curricula** (gold corrections, hard negatives, replay data)
- **Retrains and promotes** improved checkpoints behind same endpoint
- **Regression gates** ensure updates pass tests; auto-rolls back on degradation
- Each run produces downloadable PDF audit report

## Supported Models

### Encoder Models (Structured Extraction)
- GLiNER2 Large — NER, text classification, structured JSON extraction
- GLiGuard 300M — Content moderation/safety classification
- GLiNER2-PII — PII detection and redaction

### Decoder Models (LLMs)
- Qwen3 32B — Coding, multilingual, multi-step reasoning
- Llama — RAG, summarization, general chat
- DeepSeek V4 Pro — Coding-first, extended chain-of-thought, agentic planning
- Gemma — Fast, low-latency coding
- Nemotron — High-throughput coding/reasoning
- Kimi K2.6 — 256K-context, long-context retrieval

### Proprietary (Inference Only)
- Claude Sonnet 4.6 / Claude Opus 4.7
- GPT-4.1 / GPT-5.5

## API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/base-models` | GET | List available base models |
| `/inference` | POST | Run inference via OpenAI/Anthropic-compatible endpoint |
| `/felix/training-jobs` | POST | Start LoRA fine-tuning job |
| `/felix/evaluations` | POST | Benchmark fine-tuned vs base model |

## Workflow
1. Upload dataset (or use synthetic data generation)
2. Run inference via `POST /inference`
3. Fine-tune via `POST /felix/training-jobs`
4. Evaluate via `POST /felix/evaluations`
5. Deploy — route traffic by referencing training job ID

## Performance Highlights
- ARC-Challenge (Llama 3B): 5.3% → 72.6% after 11 autonomous iterations (~$36)
- SMS Spam (GLiNER2): F1 0.159 → 0.997
- HumanEval (Qwen 8B): 71.3% → 92.7%
- GSM8K with 15% poisoned logs: 75.9% → 81.2% (naive retraining dropped to 62.6%)

## Pricing
- Free: $75 usage credits, no credit card
- Paid: From $40/month
- Promo: HACKATHONSF0724

## Technical Report
- arXiv:2604.09791 — Pioneer Agent: Continual Improvement of Small Language Models in Production
