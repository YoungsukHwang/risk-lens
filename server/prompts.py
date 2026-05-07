"""Prompt templates for risk analysis at varying depths."""

from __future__ import annotations

import json

DOMAIN_PROMPTS: dict[str, str] = {
    "lending_pool": (
        "You are a senior credit analyst specializing in DeFi lending protocols. "
        "Assess borrower concentration, collateral quality, utilization rates, "
        "and smart-contract risk for the following lending pool."
    ),
    "rwa_asset": (
        "You are a structured-finance analyst specializing in tokenized real-world assets. "
        "Evaluate legal structure, collateral performance, servicer quality, "
        "and on-chain settlement risk for the following RWA pool."
    ),
    "protocol": (
        "You are a DeFi protocol risk researcher. Evaluate governance, smart-contract "
        "audit history, oracle dependencies, liquidity depth, and composability risk "
        "for the following protocol."
    ),
    "wallet": (
        "You are a portfolio risk analyst for on-chain wallets. Assess concentration, "
        "correlation, liquidity risk, and protocol exposure for the following wallet."
    ),
}

DEPTH_INSTRUCTIONS: dict[str, str] = {
    "quick": (
        "Provide a brief risk assessment: a score from 0 (safest) to 100 (riskiest), "
        "a letter rating (A/B/C/D), and one sentence identifying the top concern. "
        "Keep your response under 80 words total."
    ),
    "standard": (
        "Provide a structured risk analysis covering:\n"
        "1. Credit Risk — counterparty exposure, default probability\n"
        "2. Liquidity Risk — withdrawal capacity, lock-up constraints\n"
        "3. Market Risk — price sensitivity, correlation to ETH/BTC\n"
        "Include a composite risk score (0-100), letter rating (A-D), "
        "and a 2-3 sentence summary recommendation."
    ),
    "deep": (
        "Provide a comprehensive stress-test analysis with three scenarios:\n"
        "• Baseline — current market conditions continue\n"
        "• Moderate Stress — 30% market drawdown, rising rates, reduced liquidity\n"
        "• Severe Stress — 60% crash, counterparty defaults, protocol exploit\n\n"
        "For each scenario estimate: expected loss (%), probability, and recovery timeline. "
        "Conclude with a composite risk score (0-100), letter rating (A-D), "
        "position sizing recommendation, and hedging strategies."
    ),
}

DEPTH_TOKENS: dict[str, int] = {
    "quick": 400,
    "standard": 1500,
    "deep": 3000,
}


def build_prompt(domain: str, target_data: dict, depth: str) -> str:
    """Assemble a full prompt from domain context, target data, and depth instructions."""
    if domain not in DOMAIN_PROMPTS:
        raise ValueError(f"Unknown domain: {domain}. Valid: {list(DOMAIN_PROMPTS)}")
    if depth not in DEPTH_INSTRUCTIONS:
        raise ValueError(f"Unknown depth: {depth}. Valid: {list(DEPTH_INSTRUCTIONS)}")

    parts = [
        DOMAIN_PROMPTS[domain],
        "",
        "=== TARGET DATA ===",
        json.dumps(target_data, indent=2),
        "",
        "=== INSTRUCTIONS ===",
        DEPTH_INSTRUCTIONS[depth],
    ]
    return "\n".join(parts)


if __name__ == "__main__":
    sample_data = {"name": "Test Pool", "tvl_usd": 50_000_000, "apy": 0.08}
    for depth in DEPTH_INSTRUCTIONS:
        prompt = build_prompt("lending_pool", sample_data, depth)
        print(f"\n{'='*60}")
        print(f"DEPTH: {depth} | max_tokens: {DEPTH_TOKENS[depth]}")
        print(f"{'='*60}")
        print(prompt[:300], "..." if len(prompt) > 300 else "")
