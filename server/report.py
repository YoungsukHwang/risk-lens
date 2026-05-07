"""HTML report generation and S3 upload for RiskLens analyses."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

import boto3

S3_BUCKET = "amzn-s3-risk-lens-demo"
S3_REGION = "us-east-1"
S3_PREFIX = "reports"


def _md_to_html(text: str) -> str:
    """Convert markdown-ish analysis text to basic HTML."""
    html = text

    # Escape HTML entities first
    html = html.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Headers: ### h3, ## h2, # h1 (order matters — longest prefix first)
    html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)

    # Bold: **text**
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)

    # Italic: *text* (but not inside already-converted tags)
    html = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", html)

    # Inline code: `text`
    html = re.sub(r"`([^`]+)`", r"<code>\1</code>", html)

    # Code blocks: ```...```
    html = re.sub(
        r"```(\w*)\n(.*?)```",
        r'<pre><code>\2</code></pre>',
        html,
        flags=re.DOTALL,
    )

    # Simple table conversion
    lines = html.split("\n")
    in_table = False
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            # Skip separator rows (---|---|---)
            if all(re.match(r"^[-:]+$", c) for c in cells):
                continue
            if not in_table:
                result.append("<table>")
                # First row is header
                result.append("<tr>" + "".join(f"<th>{c}</th>" for c in cells) + "</tr>")
                in_table = True
            else:
                result.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
        else:
            if in_table:
                result.append("</table>")
                in_table = False
            result.append(line)
    if in_table:
        result.append("</table>")
    html = "\n".join(result)

    # Bullet points
    html = re.sub(r"^[\-\*] (.+)$", r"<li>\1</li>", html, flags=re.MULTILINE)
    html = re.sub(r"((?:<li>.*</li>\n?)+)", r"<ul>\1</ul>", html)

    # Checkmarks and warning signs (common in the analysis output)
    html = html.replace("✅", '<span class="check">&#x2705;</span>')
    html = html.replace("⚠️", '<span class="warn">&#x26A0;&#xFE0F;</span>')

    # Horizontal rules
    html = re.sub(r"^---+$", "<hr>", html, flags=re.MULTILINE)

    # Paragraphs: double newline → <p>
    html = re.sub(r"\n{2,}", "</p>\n<p>", html)
    # Single newlines → <br> (but not after block elements)
    html = re.sub(r"(?<!>)\n(?!<)", "<br>\n", html)

    return f"<p>{html}</p>"


def generate_html_report(
    metadata: dict,
    payment_info: dict,
    analysis_text: str,
) -> str:
    """Build a complete HTML report page.

    Args:
        metadata: target, domain, depth, timestamp
        payment_info: amount_usdc, tx_hash, network
        analysis_text: raw Claude response
    """
    ts = metadata.get("timestamp", datetime.now(timezone.utc).isoformat())
    domain = metadata.get("domain", "")
    target = metadata.get("target", "")
    depth = metadata.get("depth", "")

    amount = payment_info.get("amount_usdc", "")
    tx_hash = payment_info.get("tx_hash", "")
    network = payment_info.get("network", "Base Sepolia")

    tx_link = ""
    if tx_hash:
        tx_link = (
            f'<a href="https://sepolia.basescan.org/tx/{tx_hash}" '
            f'target="_blank">{tx_hash[:10]}...{tx_hash[-8:]}</a>'
        )

    analysis_html = _md_to_html(analysis_text)

    depth_labels = {
        "quick": "Quick ($0.50)",
        "standard": "Standard ($3.00)",
        "deep": "Deep ($10.00)",
    }

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RiskLens Report — {target}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; }}
  body {{
    font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
    background: #f5f6f8;
    color: #1a1a2e;
    margin: 0;
    padding: 0;
    line-height: 1.6;
  }}
  .header {{
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    color: #fff;
    padding: 2rem 2rem 1.5rem;
  }}
  .header h1 {{ margin: 0; font-size: 1.8rem; font-weight: 700; }}
  .header p {{ margin: 0.3rem 0 0; opacity: 0.7; font-size: 0.95rem; }}
  .container {{ max-width: 860px; margin: 0 auto; padding: 1.5rem; }}
  .meta-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    margin-bottom: 1.5rem;
  }}
  .card {{
    background: #fff;
    border-radius: 10px;
    padding: 1.25rem 1.5rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  }}
  .card h3 {{
    margin: 0 0 0.75rem;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #666;
  }}
  .card .row {{ display: flex; justify-content: space-between; padding: 0.3rem 0; }}
  .card .label {{ color: #888; font-size: 0.9rem; }}
  .card .value {{ font-weight: 600; font-size: 0.9rem; }}
  .card a {{ color: #4361ee; text-decoration: none; }}
  .card a:hover {{ text-decoration: underline; }}
  .analysis {{
    background: #fff;
    border-radius: 10px;
    padding: 2rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    margin-bottom: 1.5rem;
  }}
  .analysis h1 {{ font-size: 1.4rem; margin-top: 1.5rem; border-bottom: 2px solid #eee; padding-bottom: 0.5rem; }}
  .analysis h2 {{ font-size: 1.15rem; margin-top: 1.3rem; color: #302b63; }}
  .analysis h3 {{ font-size: 1rem; margin-top: 1rem; color: #555; }}
  .analysis table {{
    width: 100%;
    border-collapse: collapse;
    margin: 1rem 0;
    font-size: 0.9rem;
  }}
  .analysis th, .analysis td {{
    border: 1px solid #e0e0e0;
    padding: 0.5rem 0.75rem;
    text-align: left;
  }}
  .analysis th {{ background: #f8f8fa; font-weight: 600; }}
  .analysis pre {{
    background: #f5f6f8;
    border-radius: 6px;
    padding: 1rem;
    overflow-x: auto;
    font-size: 0.85rem;
  }}
  .analysis code {{ font-family: 'SF Mono', Menlo, Consolas, monospace; font-size: 0.88em; }}
  .analysis ul {{ padding-left: 1.5rem; }}
  .analysis li {{ margin-bottom: 0.3rem; }}
  .analysis hr {{ border: none; border-top: 1px solid #e0e0e0; margin: 1.5rem 0; }}
  .footer {{
    text-align: center;
    padding: 1.5rem;
    color: #999;
    font-size: 0.8rem;
  }}
  @media (max-width: 600px) {{
    .meta-grid {{ grid-template-columns: 1fr; }}
    .container {{ padding: 1rem; }}
  }}
</style>
</head>
<body>
<div class="header">
  <div class="container">
    <h1>RiskLens Risk Report</h1>
    <p>Pay-per-call risk analysis for AI agents</p>
  </div>
</div>
<div class="container">
  <div style="text-align:right;color:#888;font-size:0.85rem;margin-bottom:1rem;">
    Generated: {ts}
  </div>
  <div class="meta-grid">
    <div class="card">
      <h3>Analysis Metadata</h3>
      <div class="row"><span class="label">Target</span><span class="value">{target}</span></div>
      <div class="row"><span class="label">Domain</span><span class="value">{domain}</span></div>
      <div class="row"><span class="label">Depth</span><span class="value">{depth_labels.get(depth, depth)}</span></div>
    </div>
    <div class="card">
      <h3>Payment Proof</h3>
      <div class="row"><span class="label">Amount</span><span class="value">{amount} USDC</span></div>
      <div class="row"><span class="label">Network</span><span class="value">{network}</span></div>
      <div class="row"><span class="label">Tx Hash</span><span class="value">{tx_link or '<em>pending settlement</em>'}</span></div>
    </div>
  </div>
  <div class="analysis">
    {analysis_html}
  </div>
</div>
<div class="footer">
  Generated by RiskLens &middot; Built at EasyA Consensus Miami Hackathon &middot; x402 on Base Sepolia
</div>
</body>
</html>"""


def upload_report_to_s3(html_content: str) -> str:
    """Upload HTML report to S3 and return the public URL."""
    report_id = uuid.uuid4().hex
    key = f"{S3_PREFIX}/{report_id}.html"

    s3 = boto3.client("s3", region_name=S3_REGION)
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=html_content.encode("utf-8"),
        ContentType="text/html",
    )
    return f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{key}"


if __name__ == "__main__":
    # Standalone test
    test_meta = {
        "target": "Aave_v3",
        "domain": "protocol",
        "depth": "standard",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    test_payment = {
        "amount_usdc": "$3.00",
        "tx_hash": "0x4fae4b8eeeb1a7e5e38bd8bad970bb7fa9c832c606b196c154c65c5222d763fd",
        "network": "Base Sepolia",
    }
    test_analysis = (
        "# Protocol Risk Assessment: Aave v3\n\n"
        "## Executive Summary\n"
        "**Composite Risk Score:** 22/100\n"
        "**Rating:** A-\n\n"
        "Aave v3 is one of the most battle-tested DeFi protocols.\n\n"
        "---\n\n"
        "## Credit Risk\n"
        "| Factor | Score | Notes |\n"
        "|--------|-------|-------|\n"
        "| Counterparty | 18 | Low risk |\n"
        "| Default Prob | 12 | Very low |\n\n"
        "### Key Strengths\n"
        "- Proven liquidation engine\n"
        "- Real-time monitoring\n"
        "- $2M bug bounty\n"
    )

    html = generate_html_report(test_meta, test_payment, test_analysis)
    url = upload_report_to_s3(html)
    print(f"Test report uploaded: {url}")
