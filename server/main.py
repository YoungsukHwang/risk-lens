"""RiskLens FastAPI server with x402 payment-gated risk analysis endpoints.

Run: uvicorn server.main:app --port 4021 --reload
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

load_dotenv()

# ---------------------------------------------------------------------------
# x402 configuration
# ---------------------------------------------------------------------------
PAY_TO = os.environ.get("PAY_TO_ADDRESS", "")
FACILITATOR_URL = "https://x402.org/facilitator"
NETWORK = "eip155:84532"  # Base Sepolia

# Route → (price, depth key)
ROUTE_CONFIG = {
    "/risk-analysis-quick": ("$0.50", "quick"),
    "/risk-analysis-standard": ("$3.00", "standard"),
    "/risk-analysis-deep": ("$10.00", "deep"),
}

# ---------------------------------------------------------------------------
# Build x402 routes dict and attach middleware
# ---------------------------------------------------------------------------

app = FastAPI(title="RiskLens", version="0.1.0")

_x402_enabled = False

try:
    from x402 import x402ResourceServer
    from x402.http import HTTPFacilitatorClient
    from x402.http.middleware.fastapi import payment_middleware
    from x402.mechanisms.evm.exact.server import ExactEvmScheme

    facilitator = HTTPFacilitatorClient({"url": FACILITATOR_URL})
    server = x402ResourceServer(facilitator)
    server.register(NETWORK, ExactEvmScheme())

    routes = {}
    for path, (price, _depth) in ROUTE_CONFIG.items():
        routes[f"POST {path}"] = {
            "accepts": {
                "scheme": "exact",
                "network": NETWORK,
                "payTo": PAY_TO,
                "price": price,
            }
        }

    _mw = payment_middleware(routes, server)

    @app.middleware("http")
    async def x402_middleware(request: Request, call_next):
        return await _mw(request, call_next)

    _x402_enabled = True
    print("[RiskLens] x402 payment middleware enabled")

except Exception as exc:
    # -----------------------------------------------------------------------
    # FALLBACK: manual 402 middleware
    # If the x402 SDK fails to initialise (missing deps, network error, etc.)
    # we fall back to a minimal middleware that checks for an X-PAYMENT header.
    # Any non-empty value is accepted — this is for demo purposes only.
    # -----------------------------------------------------------------------
    print(f"[RiskLens] x402 SDK init failed ({exc}); using manual 402 fallback")

    @app.middleware("http")
    async def manual_402_middleware(request: Request, call_next):
        path = request.url.path
        method = request.method
        if method == "POST" and path in ROUTE_CONFIG:
            payment_header = request.headers.get("x-payment") or request.headers.get(
                "payment-signature"
            )
            if not payment_header:
                price, _depth = ROUTE_CONFIG[path]
                return JSONResponse(
                    status_code=402,
                    content={
                        "error": "X-PAYMENT header required",
                        "x402Version": 1,
                        "accepts": [
                            {
                                "scheme": "exact",
                                "network": NETWORK,
                                "payTo": PAY_TO,
                                "price": price,
                            }
                        ],
                    },
                )
        return await call_next(request)


# ---------------------------------------------------------------------------
# Imports for route handlers
# ---------------------------------------------------------------------------
from server.llm_client import call_llm  # noqa: E402
from server.mock_data import get_mock_data  # noqa: E402
from server.prompts import DEPTH_TOKENS, build_prompt  # noqa: E402
from server.report import generate_html_report, upload_report_to_s3  # noqa: E402


# ---------------------------------------------------------------------------
# Health / info endpoints (no payment required)
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    return {
        "service": "RiskLens",
        "version": "0.1.0",
        "description": "AI-powered financial risk analysis, pay-per-call via x402",
        "x402_enabled": _x402_enabled,
        "endpoints": list(ROUTE_CONFIG.keys()),
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Risk analysis endpoints
# ---------------------------------------------------------------------------
async def _handle_analysis(request: Request, depth: str) -> JSONResponse:
    """Shared handler for all three risk analysis tiers."""
    body = await request.json()
    domain = body.get("domain", "")
    target = body.get("target", "")

    data = get_mock_data(domain, target)
    if data is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"No data found for domain={domain!r}, target={target!r}"},
        )

    prompt = build_prompt(domain, data, depth)
    max_tokens = DEPTH_TOKENS[depth]

    analysis = call_llm(prompt, max_tokens=max_tokens)

    # Generate and upload HTML report to S3
    price_map = {"quick": "$0.50", "standard": "$3.00", "deep": "$10.00"}
    report_url = ""
    try:
        metadata = {
            "target": target,
            "domain": domain,
            "depth": depth,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        payment_info = {
            "amount_usdc": price_map.get(depth, ""),
            "tx_hash": "",  # tx hash is set by settlement after response
            "network": "Base Sepolia",
        }
        html = generate_html_report(metadata, payment_info, analysis)
        report_url = upload_report_to_s3(html)
    except Exception as exc:
        print(f"[RiskLens] Report upload failed: {exc}")

    return JSONResponse(
        content={
            "domain": domain,
            "target": target,
            "depth": depth,
            "max_tokens": max_tokens,
            "analysis": analysis,
            "report_url": report_url,
        }
    )


@app.post("/risk-analysis-quick")
async def risk_quick(request: Request):
    return await _handle_analysis(request, "quick")


@app.post("/risk-analysis-standard")
async def risk_standard(request: Request):
    return await _handle_analysis(request, "standard")


@app.post("/risk-analysis-deep")
async def risk_deep(request: Request):
    return await _handle_analysis(request, "deep")
