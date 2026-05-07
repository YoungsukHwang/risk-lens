"""RiskLens demo client — stakes-based routing for AI agent risk analysis.

Demonstrates how an AI agent decides whether (and at what depth) to call
the RiskLens API based on capital at risk.  Payment is handled by the x402
protocol; this demo uses a stub X-PAYMENT header for presentation purposes.
In production, the x402 SDK client would sign a real on-chain payment.

Run:  python -m client.demo_client
Requires the RiskLens server running on localhost:4021.
"""

from __future__ import annotations

import json
import sys
import textwrap

import requests

SERVER_URL = "http://localhost:4021"

# ── Pricing table (mirrors server ROUTE_CONFIG) ──────────────────────────
TIERS = {
    "quick":    {"endpoint": "/risk-analysis-quick",    "cost_usd": 0.50},
    "standard": {"endpoint": "/risk-analysis-standard", "cost_usd": 3.00},
    "deep":     {"endpoint": "/risk-analysis-deep",     "cost_usd": 10.00},
}


# ── Stakes-based router ──────────────────────────────────────────────────
def stakes_based_router(capital_usd: float) -> dict:
    """Decide whether to call the API and at what depth, based on capital at risk.

    Returns:
        dict with keys: action ("skip" | "call"), depth, cost_usd, reason
    """
    if capital_usd < 10_000:
        return {
            "action": "skip",
            "depth": None,
            "cost_usd": 0.0,
            "reason": "Capital < $10K — free public data sufficient",
        }
    elif capital_usd < 100_000:
        return {
            "action": "call",
            "depth": "quick",
            "cost_usd": TIERS["quick"]["cost_usd"],
            "reason": "Capital $10K-$100K — quick risk score justifies $0.50",
        }
    elif capital_usd < 1_000_000:
        return {
            "action": "call",
            "depth": "standard",
            "cost_usd": TIERS["standard"]["cost_usd"],
            "reason": "Capital $100K-$1M — structured analysis justifies $3.00",
        }
    else:
        return {
            "action": "call",
            "depth": "deep",
            "cost_usd": TIERS["deep"]["cost_usd"],
            "reason": "Capital > $1M — full stress test justifies $10.00",
        }


# ── Evaluate a single scenario ───────────────────────────────────────────
def evaluate(
    scenario_name: str,
    capital_usd: float,
    domain: str,
    target: str,
) -> None:
    """Run one end-to-end scenario: route → decide → call (if needed) → print."""

    sep = "=" * 72
    print(f"\n{sep}")
    print(f"  SCENARIO: {scenario_name}")
    print(f"  Capital at risk: ${capital_usd:,.0f}")
    print(f"  Target: {domain} / {target}")
    print(sep)

    decision = stakes_based_router(capital_usd)

    print(f"\n  Agent decision : {decision['action'].upper()}")
    print(f"  Depth          : {decision['depth'] or 'N/A'}")
    print(f"  Cost           : ${decision['cost_usd']:.2f}")
    print(f"  Reason         : {decision['reason']}")

    if decision["action"] == "skip":
        print("\n  >> Skipping API call — no payment needed.\n")
        return

    # ── Make the API call ──
    depth = decision["depth"]
    tier = TIERS[depth]
    url = f"{SERVER_URL}{tier['endpoint']}"
    payload = {"domain": domain, "target": target}

    print(f"\n  >> Calling {tier['endpoint']} ...")

    try:
        # In production, this header would be a signed x402 payment payload
        # created via x402ClientSync with a Base Sepolia wallet.
        # For this demo, we send a stub header. If the server has x402 enabled
        # it will return 402 (expected — no real on-chain payment). If running
        # with the manual fallback middleware, any non-empty header is accepted.
        resp = requests.post(
            url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "X-PAYMENT": "demo-stub-payment",
            },
            timeout=60,
        )

        if resp.status_code == 402:
            print("  >> 402 Payment Required (expected in demo without real wallet)")
            print("     x402 payment flow verified — server correctly gates access.")
            # Pretty-print the payment requirements if available
            pr_header = resp.headers.get("payment-required")
            if pr_header:
                import base64
                try:
                    decoded = json.loads(base64.b64decode(pr_header))
                    print(f"     Payment info: scheme={decoded['accepts'][0]['scheme']}, "
                          f"network={decoded['accepts'][0]['network']}, "
                          f"amount={decoded['accepts'][0]['amount']}")
                except Exception:
                    pass
            print()
            return

        if resp.status_code != 200:
            print(f"  >> Error: HTTP {resp.status_code}")
            print(f"     {resp.text[:200]}")
            print()
            return

        data = resp.json()
        analysis = data.get("analysis", "")
        print(f"  >> Analysis received ({data.get('depth', '?')} tier, "
              f"max_tokens={data.get('max_tokens', '?')}):\n")
        # Wrap for terminal readability
        for line in analysis.split("\n"):
            print(f"     {line}")
        print()

    except requests.ConnectionError:
        print("  >> ERROR: Cannot connect to server. Is it running on port 4021?")
        print("     Start with: uvicorn server.main:app --port 4021")
        print()


# ── Main: run all four demo scenarios ─────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "~" * 72)
    print("  RiskLens Demo — Stakes-Based Routing for AI Agent Risk Analysis")
    print("  Pay-per-call via x402 on Base Sepolia")
    print("~" * 72)

    scenarios = [
        ("Retail User",    5_000,     "lending_pool", "Maple_USDC_Institutional"),
        ("LP",             50_000,    "lending_pool", "Goldfinch_Senior_Pool"),
        ("Treasury",       500_000,   "protocol",     "Aave_v3"),
        ("Institutional",  5_000_000, "rwa_asset",    "Centrifuge_TradeInvoice_Pool_A"),
    ]

    for name, capital, domain, target in scenarios:
        evaluate(name, capital, domain, target)

    print("~" * 72)
    print("  Demo complete. In production, agents pay per call via x402.")
    print("  Higher stakes → deeper analysis → higher cost → better decisions.")
    print("~" * 72 + "\n")
