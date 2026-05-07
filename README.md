# RiskLens

**AI-powered financial risk analysis, pay-per-call via x402 on Base Sepolia.**

## Problem

AI agents making financial decisions need risk analysis — but existing APIs are either free-and-shallow or expensive-and-overkill. There's no way for agents to pay only for the depth they need. RiskLens solves this with tiered, pay-per-call risk analysis monetized through Coinbase's x402 protocol: agents route to the right tier based on capital at stake, and pay in USDC on Base Sepolia.

## Architecture

```
┌──────────────────┐          x402 payment          ┌────────────────────┐
│                  │  POST + Payment-Signature hdr   │                    │
│   Demo Client    │ ──────────────────────────────► │  FastAPI :4021     │
│   (AI Agent)     │                                 │                    │
│                  │ ◄────────────────────────────── │  x402 Middleware   │
│  Stakes-Based    │     402 or Analysis JSON        │         │          │
│  Router          │                                 │    ┌────▼─────┐    │
└──────────────────┘                                 │    │ Anthropic │   │
                                                     │    │ Claude    │   │
        Capital at Risk → Depth Tier                 │    └──────────┘   │
        < $10K     → skip (free data)                └────────────────────┘
        $10K-$100K → quick  ($0.50)                          │
        $100K-$1M  → standard ($3.00)                  Base Sepolia
        > $1M      → deep ($10.00)                    eip155:84532
```

## Endpoints

| Endpoint | Price (USDC) | Depth | Max Tokens |
|---|---|---|---|
| `POST /risk-analysis-quick` | $0.50 | Score + rating + one-liner | 400 |
| `POST /risk-analysis-standard` | $3.00 | Credit, liquidity, market risk | 1,500 |
| `POST /risk-analysis-deep` | $10.00 | 3-scenario stress test | 3,000 |
| `GET /` | Free | Service info | — |
| `GET /health` | Free | Health check | — |

Request body: `{"domain": "lending_pool|rwa_asset|protocol|wallet", "target": "<key>"}`

## Tech Stack

- **Server**: FastAPI + Uvicorn
- **Payments**: x402 SDK v2.9 (Coinbase x402 protocol) on Base Sepolia
- **AI**: Anthropic Claude (claude-sonnet-4-5 via direct API)
- **Client**: Python requests with stakes-based routing logic

> **Note on AWS Bedrock**: Originally built for AWS Bedrock compatibility — Bedrock was blocked on the hackathon AWS account. Switching is a one-line change in `server/llm_client.py`.

## Setup & Run

```bash
# 1. Clone and set up environment
conda create -n risk-lens python=3.11
conda activate risk-lens
pip install -r requirements.txt

# 2. Configure .env
cp .env.example .env  # then add your keys
# ANTHROPIC_API_KEY=sk-ant-...
# PAY_TO_ADDRESS=0x...  (your Base Sepolia address)

# 3. Start the server
uvicorn server.main:app --port 4021 --reload

# 4. Run the demo client (in another terminal)
conda activate risk-lens
python -m client.demo_client
```

## x402 Payment Flow

Without a valid x402 payment, protected endpoints return `402 Payment Required` with a `payment-required` header containing Base64-encoded payment requirements (scheme, network, asset, amount, payTo). Clients with a funded Base Sepolia wallet sign and attach a payment via the `X-PAYMENT` or `Payment-Signature` header. The x402 facilitator at `x402.org/facilitator` verifies and settles.

## Project Structure

```
server/
  main.py        — FastAPI app + x402 middleware
  llm_client.py  — Anthropic Claude abstraction
  prompts.py     — Domain prompts + depth instructions
  mock_data.py   — Realistic sample data (4 domains)
client/
  demo_client.py — Stakes-based routing demo
```

## Submission

**EasyA Consensus Miami Hackathon** — Coinbase x AWS Agentic Track
