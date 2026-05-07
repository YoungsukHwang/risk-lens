"""Mock data for risk analysis targets across all domains."""

from __future__ import annotations

MOCK_DB: dict[str, dict[str, dict]] = {
    "lending_pool": {
        "Maple_USDC_Institutional": {
            "name": "Maple USDC Institutional Pool",
            "protocol": "Maple Finance v2",
            "chain": "Ethereum",
            "tvl_usd": 124_500_000,
            "apy_percent": 8.2,
            "utilization_rate": 0.78,
            "collateral_type": "Uncollateralized (institutional credit)",
            "borrower_count": 12,
            "top_borrower_concentration": 0.35,
            "avg_loan_duration_days": 90,
            "historical_default_rate": 0.02,
            "last_audit": "2025-11-15",
            "auditor": "Trail of Bits",
            "insurance_coverage_usd": 15_000_000,
            "governance_token": "MPL",
            "pool_delegate": "Maven 11 Capital",
        },
        "Goldfinch_Senior_Pool": {
            "name": "Goldfinch Senior Pool",
            "protocol": "Goldfinch v3",
            "chain": "Ethereum",
            "tvl_usd": 87_200_000,
            "apy_percent": 7.1,
            "utilization_rate": 0.92,
            "collateral_type": "Off-chain real-world loans (emerging markets)",
            "borrower_count": 28,
            "top_borrower_concentration": 0.18,
            "avg_loan_duration_days": 365,
            "historical_default_rate": 0.045,
            "last_audit": "2025-09-20",
            "auditor": "OpenZeppelin",
            "insurance_coverage_usd": 5_000_000,
            "governance_token": "GFI",
            "geographic_exposure": {"LatAm": 0.40, "Africa": 0.30, "SEA": 0.30},
        },
    },
    "rwa_asset": {
        "Centrifuge_TradeInvoice_Pool_A": {
            "name": "Centrifuge Trade Invoice Pool A",
            "protocol": "Centrifuge / Tinlake",
            "chain": "Ethereum (Centrifuge Chain bridge)",
            "tvl_usd": 34_800_000,
            "apy_percent": 5.9,
            "asset_type": "Trade receivables / invoices",
            "avg_invoice_tenor_days": 60,
            "obligor_count": 145,
            "top_obligor_concentration": 0.08,
            "historical_default_rate": 0.012,
            "advance_rate": 0.85,
            "junior_tranche_percent": 0.20,
            "legal_structure": "Delaware SPV → on-chain NFT tokenization",
            "servicer": "NewSilver",
            "last_audit": "2025-10-01",
            "auditor": "Quantstamp",
            "recovery_rate_historical": 0.92,
        },
    },
    "protocol": {
        "Aave_v3": {
            "name": "Aave v3",
            "chain": "Multi-chain (Ethereum, Polygon, Arbitrum, Optimism, Base)",
            "tvl_usd": 12_400_000_000,
            "governance_token": "AAVE",
            "audit_count": 14,
            "last_audit": "2025-12-01",
            "auditors": ["Trail of Bits", "Certora", "SigmaPrime"],
            "oracle_provider": "Chainlink",
            "oracle_fallback": "Uniswap TWAP",
            "bug_bounty_usd": 2_000_000,
            "active_markets": 85,
            "liquidation_mechanism": "Automated (variable close factor)",
            "flash_loan_volume_30d_usd": 890_000_000,
            "governance_proposals_90d": 7,
            "historical_exploits": [],
            "composability_dependencies": ["Chainlink", "Balancer", "Uniswap"],
            "e_mode_categories": ["Stablecoins", "ETH-correlated", "Low-vol"],
        },
    },
    "wallet": {
        "demo_wallet_diversified": {
            "address": "0x742d...F4a1 (demo)",
            "total_value_usd": 2_350_000,
            "positions": [
                {"protocol": "Aave v3", "asset": "USDC supply", "value_usd": 800_000},
                {"protocol": "Lido", "asset": "stETH", "value_usd": 650_000},
                {"protocol": "Maple", "asset": "USDC Pool", "value_usd": 400_000},
                {"protocol": "Uniswap v3", "asset": "ETH/USDC LP", "value_usd": 300_000},
                {"protocol": "Eigen Layer", "asset": "Restaked ETH", "value_usd": 200_000},
            ],
            "chain_exposure": {"Ethereum": 0.75, "Arbitrum": 0.15, "Base": 0.10},
            "stablecoin_percent": 0.51,
            "eth_correlation": 0.62,
            "largest_single_position_percent": 0.34,
            "defi_protocol_count": 5,
            "last_activity": "2026-05-05",
        },
    },
}


def get_mock_data(domain: str, target: str) -> dict | None:
    """Look up mock data by domain and target key. Returns None if not found."""
    return MOCK_DB.get(domain, {}).get(target)


if __name__ == "__main__":
    for domain, targets in MOCK_DB.items():
        for target_name in targets:
            data = get_mock_data(domain, target_name)
            tvl = data.get("tvl_usd") or data.get("total_value_usd", "N/A")
            print(f"[{domain}] {target_name}: value=${tvl:,}" if isinstance(tvl, (int, float)) else f"[{domain}] {target_name}: value={tvl}")
    # Test missing
    print(f"\nMissing lookup: {get_mock_data('lending_pool', 'nonexistent')}")
