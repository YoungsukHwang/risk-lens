# RiskLens — Spec Summary

## Overview

RiskLens is an AI-powered financial risk analysis API monetized via Coinbase's x402 protocol on Base Sepolia. AI agents pay per call in USDC, with tiered pricing based on analysis depth.

## Kiro-Generated Specs

The `llm-client-wrapper` component was spec-driven using Kiro:

- **[requirements.md](specs/llm-client-wrapper/requirements.md)** — Functional requirements for the LLM client abstraction
- **[design.md](specs/llm-client-wrapper/design.md)** — Technical design: provider abstraction, API contract, error handling
- **[tasks.md](specs/llm-client-wrapper/tasks.md)** — Implementation tasks and acceptance criteria

The resulting `server/llm_client.py` is a thin abstraction over the Anthropic Messages API, designed so swapping to AWS Bedrock (or any other provider) requires editing only this one file.

## Hand-Built Components

The remaining components were built directly (not spec-driven):

| Component | File | Description |
|---|---|---|
| Prompt templates | `server/prompts.py` | Domain-specific analyst prompts + depth tiers |
| Mock data | `server/mock_data.py` | Realistic sample data for 4 domains |
| API server | `server/main.py` | FastAPI + x402 payment middleware |
| Demo client | `client/demo_client.py` | Stakes-based routing demonstration |

## Presentation Note

The Kiro spec workflow is highlighted on one slide to show how AI-assisted specification can accelerate component design. The rest of the system demonstrates rapid hand-built iteration for hackathon pace.
