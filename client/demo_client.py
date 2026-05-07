"""RiskLens demo client — stakes-based routing with REAL x402 payment on Base Sepolia.

Demonstrates how an AI agent decides whether (and at what depth) to call
the RiskLens API based on capital at risk.  Payment is handled automatically
by the x402 SDK: on 402 response, the client signs an EIP-3009 USDC transfer
authorization, attaches it as a payment header, and retries — the server's
facilitator verifies and settles on-chain.

Run:  python -m client.demo_client
Requires:
  - RiskLens server running on localhost:4021
  - CLIENT_PRIVATE_KEY in .env (Base Sepolia wallet with USDC + ETH for gas)
"""

from __future__ import annotations

import json
import os
import traceback

import requests
from dotenv import load_dotenv
from eth_account import Account

from x402 import x402ClientSync
from x402.mechanisms.evm.exact.client import ExactEvmScheme
from x402.http.clients.requests import wrapRequestsWithPayment

load_dotenv()

SERVER_URL = "http://localhost:4021"
NETWORK = "eip155:84532"  # Base Sepolia

# ── x402 client setup ────────────────────────────────────────────────────
_PRIVATE_KEY = os.environ.get("CLIENT_PRIVATE_KEY", "")
if not _PRIVATE_KEY:
    raise EnvironmentError(
        "CLIENT_PRIVATE_KEY not set in .env. "
        "Provide a Base Sepolia wallet private key with USDC balance."
    )

_account = Account.from_key(_PRIVATE_KEY)
print(f"  [x402] Client wallet: {_account.address}")

# ExactEvmScheme auto-wraps LocalAccount via EthAccountSigner
_evm_scheme = ExactEvmScheme(signer=_account)

_x402_client = x402ClientSync()
_x402_client.register(NETWORK, _evm_scheme)

# Create a requests.Session that auto-handles 402 → sign → retry
_session = wrapRequestsWithPayment(requests.Session(), _x402_client)

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
    """Run one end-to-end scenario: route → decide → pay → analyze → print."""

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

    # ── Make the API call with x402 auto-payment ──
    depth = decision["depth"]
    tier = TIERS[depth]
    url = f"{SERVER_URL}{tier['endpoint']}"
    payload = {"domain": domain, "target": target}

    print(f"\n  >> Calling {tier['endpoint']} with x402 payment ...")

    try:
        resp = _session.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=90,
        )

        if resp.status_code == 402:
            # Payment was attempted but failed (insufficient funds, sig error, etc.)
            print("  >> 402 Payment Required — payment was rejected")
            print(f"     Response headers: {dict(resp.headers)}")
            print(f"     Body: {resp.text[:500]}")
            print()
            return

        if resp.status_code != 200:
            print(f"  >> Error: HTTP {resp.status_code}")
            print(f"     {resp.text[:500]}")
            print()
            return

        # ── Success! Payment settled, analysis received ──
        data = resp.json()
        analysis = data.get("analysis", "")

        # Check for settlement proof in response headers
        payment_response = resp.headers.get("payment-response") or resp.headers.get("x-payment-response")

        print(f"  >> Payment settled on Base Sepolia!")
        if payment_response:
            import base64
            try:
                pr_data = json.loads(base64.b64decode(payment_response))
                tx_hash = pr_data.get("transaction", pr_data.get("txHash", ""))
                if tx_hash:
                    print(f"     Tx: {tx_hash}")
                    print(f"     Explorer: https://sepolia.basescan.org/tx/{tx_hash}")
            except Exception:
                print(f"     Payment-Response: {payment_response[:80]}...")

        report_url = data.get("report_url", "")
        if report_url:
            print(f"     Report: {report_url}")

        print(f"\n  >> Analysis received ({data.get('depth', '?')} tier, "
              f"max_tokens={data.get('max_tokens', '?')}):\n")
        for line in analysis.split("\n"):
            print(f"     {line}")
        print()

    except requests.ConnectionError:
        print("  >> ERROR: Cannot connect to server. Is it running on port 4021?")
        print("     Start with: uvicorn server.main:app --port 4021")
        print()
    except Exception as exc:
        print(f"  >> ERROR: {type(exc).__name__}: {exc}")
        traceback.print_exc()
        print()


# ── Main: run all four demo scenarios ─────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "~" * 72)
    print("  RiskLens Demo — Stakes-Based Routing for AI Agent Risk Analysis")
    print("  LIVE x402 payments on Base Sepolia (real USDC transfers)")
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
    print("  Demo complete. Real USDC payments settled on Base Sepolia.")
    print("  Higher stakes → deeper analysis → higher cost → better decisions.")
    print("~" * 72 + "\n")
