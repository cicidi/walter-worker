# Actian VectorAI DB — Reference Documentation

> Source: https://www.actian.com/databases/vectorai-db/
> Launched: April 2026 at AI Dev 26 x SF
> Company: Actian (data and AI division of HCLSoftware)

## Overview

Portable, local-first vector database for production AI in regulated, disconnected, and edge environments.

## Architecture
- Single Docker container, no underlying relational DB dependency
- HNSW ANN indexing for efficient high-accuracy search
- 1M vectors at 768 dims fits in ~1.7GB RAM (vs ~11GB for pgvector+Postgres)
- Same architecture from prototype to production across any environment

## Deployment Targets
- Edge devices: NVIDIA Jetson, Raspberry Pi, industrial edge servers
- Air-gapped environments: factory floors, plant floors
- On-premises servers: hospital data centers, clinic servers
- Hybrid: edge + cloud, multi-site distributed

## Performance
| Metric | Value |
|---|---|
| QPS at 10M vectors | 1,000 QPS (22× higher than alternatives) |
| Recall at scale | 99% |
| p99 latency | 13ms |
| Local queries | Sub-15ms |

## Model Support
Model-agnostic: OpenAI, Anthropic, Cohere, Hugging Face, custom/fine-tuned models
Multimodal: text, images, audio, video embeddings

## Edge Features
- Offline-first: works without internet, syncs when connected
- Sub-15ms local queries (vs 200-400ms cloud round-trips)

## Pricing
| Tier | Capacity | Price |
|------|----------|-------|
| Community | 5K vectors | Free |
| Starter | 1M vectors | $417/mo |
| Growth | 5M vectors | $1,250/mo |
| Enterprise | 10M+ | Custom |
| Edge | Custom | Custom |

## Compliance
AES-256 encryption, HIPAA, GDPR, ISO 27001, SOC 2 Type II
Data stays under organizational control — no third-party cloud processing
