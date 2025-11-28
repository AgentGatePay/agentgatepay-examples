#!/usr/bin/env python3
"""
AgentGatePay + LangChain Integration - MONITORING DASHBOARD (Standalone)

This is a standalone monitoring tool for tracking AgentGatePay payments, similar to
the n8n monitoring workflow. Run this AFTER making payments to see analytics.

Features:
- Multi-chain/token support (Ethereum, Base, Polygon, Arbitrum + USDC/USDT/DAI)
- Spending analytics and budget tracking
- Smart alerts (budget warnings, mandate expiration, failed payments)
- Payment history with merchant vs commission breakdown
- CSV/JSON exports
- curl commands for further exploration

Usage:
    # Standalone mode (will prompt for credentials)
    python 10_monitoring_dashboard.py

    # With arguments
    python 10_monitoring_dashboard.py --api-key pk_live_... --wallet 0xABC...

    # Import as module
    from monitoring import MonitoringDashboard
    from chain_config import get_chain_config
    config = get_chain_config()
    dashboard = MonitoringDashboard(api_url, api_key, wallet, config)
    dashboard.print_dashboard()

Requirements:
- pip install agentgatepay-sdk>=1.1.3 python-dotenv
- .env file with API_KEY (optional if passed as argument)
"""

import os
import sys
import argparse
from dotenv import load_dotenv
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Chain configuration from .env
from chain_config import get_chain_config

# Import monitoring module (for dashboard features only)
from monitoring import (
    MonitoringDashboard,
    CSVExporter,
    JSONExporter
)

# Load environment variables
load_dotenv()

# ========================================
# CONFIGURATION
# ========================================

AGENTPAY_API_URL = os.getenv('AGENTPAY_API_URL', 'https://api.agentgatepay.com')


# ========================================
# MAIN
# ========================================

if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(description='AgentGatePay Monitoring Dashboard')
    parser.add_argument('--api-key', help='AgentGatePay API key', default=None)
    parser.add_argument('--wallet', help='Wallet address', default=None)
    parser.add_argument('--export-csv', action='store_true', help='Export CSV report')
    parser.add_argument('--export-json', action='store_true', help='Export JSON report')
    parser.add_argument('--no-alerts', action='store_true', help='Disable alerts')

    args = parser.parse_args()

    print("=" * 70)
    print("📊 AGENTGATEPAY MONITORING DASHBOARD (Standalone)")
    print("=" * 70)
    print()
    print("This tool analyzes your AgentGatePay payment activity and provides:")
    print("  - Spending analytics and budget tracking")
    print("  - Smart alerts (budget warnings, failed payments)")
    print("  - Payment history with merchant/commission breakdown")
    print("  - CSV/JSON exports")
    print()
    print("=" * 70)

    # Get API key
    api_key = args.api_key or os.getenv('BUYER_API_KEY') or os.getenv('AGENTGATEPAY_API_KEY')

    if not api_key:
        print("\n⚠️  API key required!")
        print()
        api_key = input("Enter your AgentGatePay API key (pk_live_...): ").strip()

        if not api_key or not api_key.startswith('pk_'):
            print("❌ Invalid API key format. Expected: pk_live_...")
            sys.exit(1)

    # Get wallet address (optional)
    wallet = args.wallet or os.getenv('BUYER_WALLET')

    if not wallet:
        print()
        wallet_input = input("Enter your wallet address (0x...) [optional, press Enter to skip]: ").strip()
        if wallet_input:
            wallet = wallet_input

    # Get chain/token configuration from .env
    print()
    config = get_chain_config()

    print(f"\nUsing configuration from .env:")
    print(f"  Chain: {config.chain.title()} (ID: {config.chain_id})")
    print(f"  Token: {config.token} ({config.decimals} decimals)")
    print(f"  RPC: {config.rpc_url[:50]}...")
    print(f"\nTo change: Edit PAYMENT_CHAIN and PAYMENT_TOKEN in .env file")

    # Create monitoring dashboard
    print()
    print("🔄 Fetching data from AgentGatePay API...")
    print()

    dashboard = MonitoringDashboard(
        api_url=AGENTPAY_API_URL,
        api_key=api_key,
        wallet=wallet,
        config=config
    )

    # Fetch all data
    try:
        dashboard.fetch_analytics()
        dashboard.fetch_payment_history(limit=100)
        dashboard.fetch_audit_logs(hours=24, limit=100)
        dashboard.fetch_mandates()
    except Exception as e:
        print(f"❌ Failed to fetch data: {e}")
        print()
        print("Please check:")
        print("  - API key is valid")
        print("  - Wallet address is correct (if provided)")
        print("  - Network connection is working")
        sys.exit(1)

    # Generate report
    report = dashboard.generate_report()
    stats = report['stats']
    alerts = report['alerts']

    # ========================================
    # DISPLAY DASHBOARD
    # ========================================

    print("\n" + "=" * 70)
    print("📊 AGENTGATEPAY MONITORING DASHBOARD")
    print("=" * 70)
    print(f"\nGenerated: {report['generated_at']}")
    print(f"Chain: {report['config']['chain'].upper()}")
    print(f"Token: {report['config']['token']}")
    if wallet:
        print(f"Wallet: {wallet[:10]}...{wallet[-8:]}")
    print()

    # Key Metrics
    print("━" * 70)
    print("💰 SPENDING SUMMARY")
    print("━" * 70)
    print(f"Total Spent: ${stats['total_spent']:.2f} USD")
    print(f"Payment Count: {stats['payment_count']}")
    print(f"Average Payment: ${stats['average_payment']:.2f} USD")
    print(f"Last 24h: {stats['payments_last_24h']} payments (${stats['spent_last_24h']:.2f} USD)")
    print(f"Spending Trend: {stats['spending_trend']}")
    print()

    # Budget Status
    print("━" * 70)
    print("🔑 BUDGET STATUS")
    print("━" * 70)
    print(f"Total Allocated: ${stats['budget_total']:.2f} USD")
    print(f"Remaining: ${stats['budget_remaining']:.2f} USD")
    print(f"Utilization: {stats['budget_utilization_pct']:.1f}%")
    print(f"Active Mandates: {stats['active_mandates']}")
    print()

    # Alerts
    if not args.no_alerts and alerts:
        print("━" * 70)
        print(f"🚨 ALERTS ({len(alerts)})")
        print("━" * 70)
        alert_summary = dashboard.alert_engine.get_alert_summary()
        print(f"Critical: {alert_summary['critical']} | High: {alert_summary['high']} | " +
              f"Medium: {alert_summary['medium']} | Low: {alert_summary['low']}")
        print()
        for i, alert in enumerate(alerts[:10], 1):  # Show top 10
            print(f"{i}. [{alert.severity.value.upper()}] {alert.message}")
            print(f"   Action: {alert.action}")
            if i < len(alerts):
                print()
        if len(alerts) > 10:
            print(f"\n... and {len(alerts) - 10} more alerts")
        print()

    # Recent Payments
    if dashboard.payments:
        print("━" * 70)
        print("💳 RECENT PAYMENTS (Last 10)")
        print("━" * 70)
        for i, payment in enumerate(dashboard.payments[:10], 1):
            timestamp = payment.get('timestamp', payment.get('created_at', 'N/A'))
            amount = float(payment.get('amount_usd', 0))
            status = payment.get('status', 'unknown')
            tx_hash = payment.get('tx_hash', 'N/A')[:20]
            receiver = payment.get('receiver', payment.get('receiver_address', 'N/A'))[:12]

            print(f"{i}. ${amount:.2f} → {receiver}... | {status} | {tx_hash}...")
        print()

    # Mandates
    if dashboard.mandates:
        print("━" * 70)
        print(f"🎫 ACTIVE MANDATES ({len(dashboard.mandates)})")
        print("━" * 70)
        for i, mandate in enumerate(dashboard.mandates[:5], 1):
            details = mandate.get('details', {})
            if isinstance(details, str):
                import json
                details = json.loads(details)

            mandate_id = details.get('mandate_id', 'N/A')[:30]
            budget = details.get('budget_usd', 0)
            status = details.get('status', 'N/A')

            print(f"{i}. {mandate_id}... | ${budget:.2f} | {status}")
        if len(dashboard.mandates) > 5:
            print(f"... and {len(dashboard.mandates) - 5} more mandates")
        print()

    # API Links
    print("━" * 70)
    print("🔗 EXPLORE YOUR DATA (CURL COMMANDS)")
    print("━" * 70)
    print("\nCopy-paste these commands to explore your payment data:\n")

    client_id = wallet if wallet else os.getenv('BUYER_EMAIL', 'YOUR_EMAIL')

    print(f"# Last 24 hours of activity")
    print(f"curl '{AGENTPAY_API_URL}/audit/logs?client_id={client_id}&hours=24' \\")
    print(f"  -H 'x-api-key: {api_key[:15]}...'\n")

    print(f"# Payment events only")
    print(f"curl '{AGENTPAY_API_URL}/audit/logs?client_id={client_id}&event_type=x402_payment_settled' \\")
    print(f"  -H 'x-api-key: {api_key[:15]}...'\n")

    print(f"# User analytics")
    print(f"curl '{AGENTPAY_API_URL}/v1/analytics/me' \\")
    print(f"  -H 'x-api-key: {api_key[:15]}...'\n")

    print(f"# Payment history")
    print(f"curl '{AGENTPAY_API_URL}/v1/payments/list' \\")
    print(f"  -H 'x-api-key: {api_key[:15]}...'\n")

    # Exports
    print("━" * 70)
    print("📥 EXPORT OPTIONS")
    print("━" * 70)

    if args.export_csv or args.export_json:
        try:
            if args.export_csv:
                csv_path = dashboard.export_csv()
                print(f"✅ CSV Report: {csv_path}")

            if args.export_json:
                json_path = dashboard.export_json()
                print(f"✅ JSON Report: {json_path}")
        except Exception as e:
            print(f"⚠️  Export failed: {e}")
    else:
        print("Run with --export-csv or --export-json to export reports")
        print(f"Example: python {os.path.basename(__file__)} --export-csv --export-json")

    print()
    print("=" * 70)
    print("✅ MONITORING COMPLETE")
    print("=" * 70)
    print()
    print(f"💡 Next Steps:")
    print(f"   - Check alerts above and take recommended actions")
    print(f"   - Use curl commands to explore your data")
    print(f"   - Export CSV/JSON for detailed analysis")
    print(f"   - Run this script anytime to check payment status")
    print()
