#!/usr/bin/env python3
"""
AgentGatePay + LangChain Integration - SELLER MONITORING DASHBOARD

Monitor your revenue as a SELLER (incoming payments):
- Revenue analytics and payment tracking
- Incoming payments from buyers
- Webhook delivery status
- Top buyers analysis
- Smart alerts (payment failures, webhook issues)
- CSV/JSON exports

This is for sellers who RECEIVE payments. For buyers who SEND payments,
use 5a_monitoring_buyer.py instead.

Features (Seller-Focused):
- Total revenue, payment count, average payment
- Revenue trends and growth analysis
- Incoming payment history (what you received)
- Webhook configuration and delivery tracking
- Top buyers ranking
- Payment success rate monitoring

Usage:
    # Standalone mode (will prompt for credentials)
    python 5b_monitoring_seller.py

    # With arguments
    python 5b_monitoring_seller.py --api-key pk_live_... --wallet 0xDEF...

Requirements:
- pip install agentgatepay-sdk>=1.1.6 python-dotenv requests
- .env file with SELLER_API_KEY and SELLER_WALLET
"""

import os
import sys
import argparse
import requests
from dotenv import load_dotenv
from datetime import datetime
import json

# Load environment variables
load_dotenv()

# ========================================
# CONFIGURATION
# ========================================

AGENTPAY_API_URL = os.getenv('AGENTPAY_API_URL', 'https://api.agentgatepay.com')


# ========================================
# HELPER FUNCTIONS
# ========================================

def fetch_merchant_revenue(api_url, api_key, wallet):
    """Fetch merchant revenue analytics"""
    try:
        response = requests.get(
            f"{api_url}/v1/merchant/revenue",
            headers={"x-api-key": api_key},
            params={"wallet": wallet} if wallet else {},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"⚠️  Failed to fetch revenue: {e}")
        return {}


def fetch_payment_list(api_url, api_key, wallet=None, limit=50):
    """Fetch payment list (incoming payments for seller)"""
    try:
        params = {"limit": limit}
        if wallet:
            params["wallet"] = wallet

        response = requests.get(
            f"{api_url}/v1/payments/list",
            headers={"x-api-key": api_key},
            params=params,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return data.get('payments', [])
    except Exception as e:
        print(f"⚠️  Failed to fetch payments: {e}")
        return []


def fetch_webhooks(api_url, api_key):
    """Fetch configured webhooks"""
    try:
        response = requests.get(
            f"{api_url}/v1/webhooks/list",
            headers={"x-api-key": api_key},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return data.get('webhooks', [])
    except Exception as e:
        print(f"⚠️  Failed to fetch webhooks: {e}")
        return []


def fetch_audit_logs(api_url, api_key, hours=24, limit=50):
    """Fetch audit logs for payment events"""
    try:
        response = requests.get(
            f"{api_url}/audit/logs",
            headers={"x-api-key": api_key},
            params={
                "event_type": "x402_payment_settled",
                "hours": hours,
                "limit": limit
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return data.get('logs', [])
    except Exception as e:
        print(f"⚠️  Failed to fetch audit logs: {e}")
        return []


def calculate_seller_stats(revenue, payments, webhooks, logs):
    """Calculate seller-specific statistics"""
    # Revenue stats
    total_revenue = revenue.get('total_usd', 0)
    payment_count = revenue.get('count', 0)
    average_payment = revenue.get('average_usd', 0) if payment_count > 0 else 0
    revenue_this_month = revenue.get('revenue_this_month', 0)

    # Recent activity (24h)
    from datetime import datetime, timedelta
    one_day_ago = datetime.now() - timedelta(hours=24)

    payments_24h = [
        p for p in payments
        if datetime.fromisoformat(p.get('timestamp', p.get('created_at', '2000-01-01')).replace('Z', '+00:00')) > one_day_ago
    ]
    revenue_24h = sum(float(p.get('amount_usd', 0)) for p in payments_24h)

    # Webhook stats
    total_webhooks = len(webhooks)
    active_webhooks = len([w for w in webhooks if w.get('active', False)])

    # Top buyers
    top_buyers = revenue.get('top_buyers', [])[:5] if 'top_buyers' in revenue else []

    # Payment success rate
    successful = len([p for p in payments if p.get('status') in ['completed', 'confirmed']])
    failed = len([p for p in payments if p.get('status') == 'failed'])
    total_status = successful + failed
    success_rate = (successful / total_status * 100) if total_status > 0 else 100

    return {
        'total_revenue': total_revenue,
        'payment_count': payment_count,
        'average_payment': average_payment,
        'revenue_this_month': revenue_this_month,
        'payments_24h': len(payments_24h),
        'revenue_24h': revenue_24h,
        'total_webhooks': total_webhooks,
        'active_webhooks': active_webhooks,
        'top_buyers': top_buyers,
        'success_rate': success_rate,
        'failed_payments': failed,
        'total_events': len(logs)
    }


def generate_seller_alerts(stats, payments, webhooks):
    """Generate seller-specific alerts"""
    alerts = []

    # Webhook failures
    if stats['total_webhooks'] > 0 and stats['active_webhooks'] == 0:
        alerts.append({
            'severity': 'high',
            'message': f"⚠️  All webhooks inactive ({stats['total_webhooks']} total)",
            'action': 'Check webhook configuration and test delivery'
        })

    # No payments in 24h - check both payments list AND audit logs
    if stats['payments_24h'] == 0 and stats['total_events'] == 0 and stats['payment_count'] > 0:
        alerts.append({
            'severity': 'medium',
            'message': '⏰ No payments received in last 24 hours',
            'action': 'Review - may be normal or check if service is accessible'
        })

    # Failed payments
    if stats['failed_payments'] > 0:
        alerts.append({
            'severity': 'high',
            'message': f"❌ PAYMENT FAILURES: {stats['failed_payments']} failed payment(s)",
            'action': 'Review failed transactions and notify buyers'
        })

    # Low success rate
    if stats['success_rate'] < 90 and stats['payment_count'] > 10:
        alerts.append({
            'severity': 'high',
            'message': f"⚠️  LOW SUCCESS RATE: {stats['success_rate']:.1f}% ({stats['failed_payments']} failures)",
            'action': 'Investigate common failure causes'
        })

    # No webhooks configured
    if stats['total_webhooks'] == 0 and stats['payment_count'] > 5:
        alerts.append({
            'severity': 'medium',
            'message': 'ℹ️  No webhooks configured - missing payment notifications',
            'action': 'Configure webhook to receive real-time payment alerts'
        })

    # Revenue spike
    if stats['revenue_24h'] > stats['average_payment'] * 20 and stats['payment_count'] > 10:
        alerts.append({
            'severity': 'low',
            'message': f"📈 Revenue Spike: ${stats['revenue_24h']:.2f} in 24h (20x average)",
            'action': 'High demand detected - ensure service capacity'
        })

    return alerts


# ========================================
# MAIN
# ========================================

if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(description='AgentGatePay Seller Monitoring Dashboard')
    parser.add_argument('--api-key', help='AgentGatePay API key', default=None)
    parser.add_argument('--wallet', help='Seller wallet address', default=None)
    parser.add_argument('--no-alerts', action='store_true', help='Disable alerts')

    args = parser.parse_args()

    print("=" * 70)
    print("💲 SELLER MONITORING DASHBOARD (Incoming Payments)")
    print("=" * 70)
    print()
    print("This dashboard tracks your REVENUE as a seller:")
    print("  ✅ Total revenue and payment count")
    print("  ✅ Incoming payment history (what buyers paid you)")
    print("  ✅ Webhook delivery tracking")
    print("  ✅ Top buyers analysis")
    print("  ✅ Payment success rate monitoring")
    print()
    print("For SPENDING tracking (outgoing payments), use 5a_monitoring_buyer.py")
    print()
    print("=" * 70)

    # Get API key
    api_key = args.api_key or os.getenv('SELLER_API_KEY') or os.getenv('AGENTGATEPAY_API_KEY')

    if not api_key:
        print("\n⚠️  Seller API key required!")
        print()
        api_key = input("Enter your seller API key (pk_live_...): ").strip()

        if not api_key or not api_key.startswith('pk_'):
            print("❌ Invalid API key format. Expected: pk_live_...")
            sys.exit(1)

    # Get wallet address
    wallet = args.wallet or os.getenv('SELLER_WALLET')

    if not wallet:
        print()
        wallet_input = input("Enter your seller wallet address (0x...): ").strip()
        if not wallet_input:
            print("❌ Seller wallet address is required for revenue tracking")
            sys.exit(1)
        wallet = wallet_input

    # Fetch seller data
    print()
    print("🔄 Fetching seller data from AgentGatePay API...")
    print()

    try:
        revenue = fetch_merchant_revenue(AGENTPAY_API_URL, api_key, wallet)
        payments = fetch_payment_list(AGENTPAY_API_URL, api_key, wallet, limit=100)
        webhooks = fetch_webhooks(AGENTPAY_API_URL, api_key)
        logs = fetch_audit_logs(AGENTPAY_API_URL, api_key, hours=24, limit=100)
    except Exception as e:
        print(f"❌ Failed to fetch data: {e}")
        print()
        print("Please check:")
        print("  - Seller API key is valid")
        print("  - Seller wallet address is correct")
        print("  - Network connection is working")
        sys.exit(1)

    # Calculate stats
    stats = calculate_seller_stats(revenue, payments, webhooks, logs)
    alerts = generate_seller_alerts(stats, payments, webhooks)

    # ========================================
    # DISPLAY SELLER DASHBOARD
    # ========================================

    print("\n" + "=" * 70)
    print("💲 SELLER MONITORING DASHBOARD")
    print("=" * 70)
    print(f"\nGenerated: {datetime.now().isoformat()}")
    print(f"Seller Wallet: {wallet[:10]}...{wallet[-8:]}")
    print()

    # Key Metrics - SELLER FOCUS
    print("━" * 70)
    print("💰 REVENUE SUMMARY")
    print("━" * 70)
    print(f"Total Revenue: ${stats['total_revenue']:.2f} USD Coins")
    print(f"Payment Count: {stats['payment_count']} (incoming payments)")
    print(f"Average Payment: ${stats['average_payment']:.2f} USD Coins")
    print(f"This Month: ${stats['revenue_this_month']:.2f} USD Coins")
    print(f"Last 24h: {stats['payments_24h']} payments (${stats['revenue_24h']:.2f} USD Coins)")
    print()

    # Webhook Status - SELLER FOCUS
    print("━" * 70)
    print("🔗 WEBHOOK STATUS")
    print("━" * 70)
    print(f"Total Webhooks: {stats['total_webhooks']}")
    print(f"Active Webhooks: {stats['active_webhooks']}")
    if stats['total_webhooks'] > 0:
        print(f"\nConfigured webhooks:")
        for i, webhook in enumerate(webhooks[:5], 1):
            url = webhook.get('url', 'N/A')[:50]
            status = "✅ Active" if webhook.get('active', False) else "❌ Inactive"
            print(f"  {i}. {url}... | {status}")
    else:
        print("\n⚠️  No webhooks configured")
        print("   Run: curl -X POST '{AGENTPAY_API_URL}/v1/webhooks/configure' \\")
        print(f"          -H 'x-api-key: {api_key[:15]}...' \\")
        print("          -d '{\"url\": \"https://your-server.com/webhook\", \"events\": [\"payment.completed\"]}'")
    print()

    # Payment Success Rate - SELLER FOCUS
    print("━" * 70)
    print("📊 PAYMENT METRICS")
    print("━" * 70)
    print(f"Success Rate: {stats['success_rate']:.1f}%")
    print(f"Failed Payments: {stats['failed_payments']}")
    print(f"Total Events (24h): {stats['total_events']}")
    print()

    # Alerts - SELLER FOCUS
    if not args.no_alerts and alerts:
        print("━" * 70)
        print(f"🚨 SELLER ALERTS ({len(alerts)})")
        print("━" * 70)
        for i, alert in enumerate(alerts, 1):
            print(f"{i}. [{alert['severity'].upper()}] {alert['message']}")
            print(f"   Action: {alert['action']}")
            if i < len(alerts):
                print()
        print()

    # Recent Payments - SELLER FOCUS (what you received)
    if payments:
        print("━" * 70)
        print("💳 INCOMING PAYMENTS (Last 10)")
        print("━" * 70)
        print("(Payments buyers sent to YOU)\n")
        for i, payment in enumerate(payments[:10], 1):
            # API returns paid_at - handle both Unix timestamp (int) and ISO string
            paid_at = payment.get('paid_at', 0)
            if isinstance(paid_at, str):
                timestamp = paid_at  # Already formatted
            elif isinstance(paid_at, (int, float)) and paid_at > 0:
                timestamp = datetime.fromtimestamp(paid_at).isoformat()
            else:
                timestamp = 'N/A'

            amount = float(payment.get('amount_usd', 0))
            status = payment.get('status', 'unknown')
            tx_hash = payment.get('tx_hash', 'N/A')

            # API returns from_address - check that FIRST
            buyer = (payment.get('from_address') or
                    payment.get('payer_address') or
                    payment.get('payer') or
                    payment.get('sender_address') or
                    payment.get('client_id') or
                    'Unknown')

            print(f"{i}. YOU RECEIVED ${amount:.2f} ← {buyer} | {timestamp} | {status} | TX {tx_hash}")
        print()

    # Top Buyers - SELLER FOCUS
    if stats['top_buyers']:
        print("━" * 70)
        print(f"👥 TOP BUYERS ({len(stats['top_buyers'])})")
        print("━" * 70)
        print("(Buyers who paid you the most)\n")
        for i, buyer in enumerate(stats['top_buyers'], 1):
            buyer_id = buyer.get('buyer_id', 'N/A')[:20]
            total_spent = buyer.get('total_spent', 0)
            count = buyer.get('payment_count', 0)
            print(f"{i}. {buyer_id}... | ${total_spent:.2f} | {count} payments")
        print()

    # Payment breakdown with commission
    if logs:
        merchant_payments = []
        commission_payments = []

        for log in logs:
            details = log.get('details', {})
            if isinstance(details, str):
                try:
                    details = json.loads(details)
                except:
                    continue

            # Extract merchant and commission info
            merchant_tx = details.get('merchant_tx_hash')
            commission_tx = details.get('commission_tx_hash')

            # Get amounts - merchant gets amount_usd or merchant_amount_usd
            merchant_amount = details.get('merchant_amount_usd') or details.get('amount_usd', 0)
            commission_amount = details.get('commission_amount_usd') or details.get('commission_usd', 0)

            # Convert Unix timestamp to human-readable (details.timestamp is in seconds)
            timestamp_unix = details.get('timestamp', log.get('timestamp', 0))
            try:
                if isinstance(timestamp_unix, str):
                    timestamp_readable = timestamp_unix
                else:
                    from datetime import datetime
                    timestamp_readable = datetime.fromtimestamp(int(timestamp_unix)).isoformat()
            except:
                timestamp_readable = str(timestamp_unix)

            # Extract buyer address using comprehensive fallback
            buyer = (details.get('payer_address') or
                    details.get('sender_address') or
                    details.get('payer') or
                    log.get('client_id', 'Unknown'))

            if merchant_tx:
                merchant_payments.append({
                    'tx_hash': merchant_tx,
                    'amount_usd': float(merchant_amount),
                    'timestamp': timestamp_readable,
                    'buyer': buyer
                })

            if commission_tx:
                commission_payments.append({
                    'tx_hash': commission_tx,
                    'amount_usd': float(commission_amount),
                    'timestamp': timestamp_readable,
                    'buyer': buyer
                })

        # Display merchant payments received
        if merchant_payments:
            print("━" * 70)
            print(f"💰 PAYMENTS RECEIVED FROM BUYERS (Last {min(20, len(merchant_payments))})")
            print("━" * 70)
            print("(Full payment amounts you received from buyers)\n")
            for i, payment in enumerate(merchant_payments[:20], 1):
                tx_hash = payment['tx_hash']
                amount = payment.get('amount_usd', 0)
                buyer = str(payment.get('buyer', 'Unknown'))
                timestamp = payment.get('timestamp', 'N/A')
                print(f"{i}. YOU RECEIVED ${amount:.4f} ← {buyer} | {timestamp} | TX {tx_hash}")
            print()

        # Display commission payments deducted
        if commission_payments:
            print("━" * 70)
            print(f"💸 COMMISSION DEDUCTED BY GATEWAY (Last {min(20, len(commission_payments))})")
            print("━" * 70)
            print("(0.5% gateway commission on each transaction)\n")
            for i, payment in enumerate(commission_payments[:20], 1):
                tx_hash = payment['tx_hash']
                commission = payment.get('amount_usd', 0)
                buyer = str(payment.get('buyer', 'Unknown'))
                timestamp = payment.get('timestamp', 'N/A')
                print(f"{i}. ${commission:.4f} → Gateway (from {buyer}) | {timestamp} | TX {tx_hash}")
            print()

    # Calculate additional metrics
    print("━" * 70)
    print("💡 ADDITIONAL METRICS")
    print("━" * 70)

    # Calculate unique buyers
    unique_buyers = set()
    for log in logs:
        details = log.get('details', {})
        if isinstance(details, str):
            try:
                details = json.loads(details)
            except:
                continue
        buyer = (details.get('payer_address') or
                details.get('sender_address') or
                details.get('payer') or
                log.get('client_id'))
        if buyer:
            unique_buyers.add(buyer)

    # Calculate commission total
    total_commission = sum(
        float(details.get('commission_amount_usd', 0)) if isinstance(details, dict) else 0
        for log in logs
        for details in [json.loads(log.get('details', '{}')) if isinstance(log.get('details'), str) else log.get('details', {})]
    )

    # Calculate original amounts
    merchant_received = stats['total_revenue']
    original_amount = merchant_received / 0.995 if merchant_received > 0 else 0

    print(f"Unique Buyers: {len(unique_buyers)}")
    print(f"Original Amount (buyer paid): ${original_amount:.2f} USD Coins")
    print(f"Merchant Received (99.5%): ${merchant_received:.2f} USD Coins")
    print(f"Commission Deducted (0.5%): ${total_commission:.4f} USD Coins")
    print()

    # MANUAL CURL COMMANDS WITH LIVE OUTPUT
    print("━" * 70)
    print("📋 CURL COMMANDS & LIVE OUTPUT (Last 10 Results)")
    print("━" * 70)
    print("\n💡 Each section shows:")
    print("   1. Full CURL command (copy/paste to get ALL data)")
    print("   2. Live execution results (limited to last 10 for readability)\n")
    print("━" * 70)
    print()

    def hide_gateway_info(data):
        """Hide sensitive gateway information"""
        if isinstance(data, dict):
            return {k: hide_gateway_info(v) if k not in ['commission_address']
                    else '[HIDDEN]' for k, v in data.items()}
        elif isinstance(data, list):
            return [hide_gateway_info(item) for item in data]
        else:
            return data

    # 1. Seller revenue analytics
    print("1️⃣  SELLER REVENUE ANALYTICS (All Time)\n")
    print(f"curl '{AGENTPAY_API_URL}/v1/merchant/revenue?wallet={wallet}' \\")
    print(f"  -H 'x-api-key: {api_key}'\n")
    print("🔄 Executing...\n")
    try:
        response = requests.get(
            f"{AGENTPAY_API_URL}/v1/merchant/revenue",
            headers={"x-api-key": api_key},
            params={"wallet": wallet},
            timeout=10
        )
        if response.status_code == 200:
            rev_data = response.json()
            # Hide gateway info
            clean_data = hide_gateway_info(rev_data)
            print(f"✅ Response (JSON):")
            print(json.dumps(clean_data, indent=2))
        else:
            print(f"❌ Failed (HTTP {response.status_code})")
    except Exception as e:
        print(f"❌ Error: {e}")
    print("\n" + "━" * 70 + "\n")

    # 2. ALL payments received
    print("2️⃣  ALL PAYMENTS RECEIVED (Showing Last 10)\n")
    print(f"curl '{AGENTPAY_API_URL}/v1/payments/list?wallet={wallet}' \\")
    print(f"  -H 'x-api-key: {api_key}'\n")
    print("🔄 Executing...\n")
    try:
        response = requests.get(
            f"{AGENTPAY_API_URL}/v1/payments/list",
            headers={"x-api-key": api_key},
            params={"wallet": wallet},
            timeout=10
        )
        if response.status_code == 200:
            pay_data = response.json()
            pay_list = pay_data.get('payments', [])[:10]
            result = {'payments': pay_list, 'count': len(pay_data.get('payments', [])), 'showing': len(pay_list)}
            clean_data = hide_gateway_info(result)
            print(f"✅ Response (showing last 10 of {len(pay_data.get('payments', []))} total):")
            print(json.dumps(clean_data, indent=2))
        else:
            print(f"❌ Failed (HTTP {response.status_code})")
    except Exception as e:
        print(f"❌ Error: {e}")
    print("\n" + "━" * 70 + "\n")

    # 3-5. Payment events (24h, 7d, 30d)
    for idx, (time_label, hours) in enumerate([("24h", 24), ("7 days", 168), ("30 days", 720)], start=3):
        print(f"{idx}️⃣  PAYMENT EVENTS (Last {time_label}) - Showing Last 10\n")
        print(f"curl '{AGENTPAY_API_URL}/audit/logs?event_type=x402_payment_settled&hours={hours}' \\")
        print(f"  -H 'x-api-key: {api_key}'\n")
        print("🔄 Executing...\n")
        try:
            response = requests.get(
                f"{AGENTPAY_API_URL}/audit/logs",
                headers={"x-api-key": api_key},
                params={"event_type": "x402_payment_settled", "hours": hours},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                all_logs = data.get('logs', [])
                event_logs = all_logs[:10]
                result = {'logs': event_logs, 'count': len(all_logs), 'showing': len(event_logs)}
                clean_data = hide_gateway_info(result)
                print(f"✅ Response (showing last 10 of {len(all_logs)} total):")
                print(json.dumps(clean_data, indent=2))
            else:
                print(f"❌ No events found (HTTP {response.status_code})")
        except Exception as e:
            print(f"❌ Error: {e}")
        print("\n" + "━" * 70 + "\n")

    # 6. Commission events (extracted from payment_settled events)
    print("6️⃣  COMMISSION EVENTS (Last 30 days) - Showing Last 10\n")
    print(f"curl '{AGENTPAY_API_URL}/audit/logs?event_type=x402_payment_settled&hours=720' \\")
    print(f"  -H 'x-api-key: {api_key}'\n")
    print("💡 Note: Filtering for events with commission data embedded\n")
    print("🔄 Executing...\n")
    try:
        response = requests.get(
            f"{AGENTPAY_API_URL}/audit/logs",
            headers={"x-api-key": api_key},
            params={"event_type": "x402_payment_settled", "hours": 720},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            all_logs = data.get('logs', [])

            # Filter for logs with commission data
            commission_logs = []
            for log in all_logs:
                details = log.get('details', {})
                if isinstance(details, str):
                    try:
                        details = json.loads(details)
                    except:
                        continue

                # Only include if has commission data
                if details.get('commission_tx_hash'):
                    # Create clean commission-focused log entry
                    commission_logs.append({
                        'id': log.get('id'),
                        'timestamp': log.get('timestamp'),
                        'commission_tx_hash': details.get('commission_tx_hash'),
                        'commission_amount_usd': details.get('commission_amount_usd'),
                        'related_buyer': details.get('payer_address') or details.get('sender_address'),
                        'status': details.get('status', 'completed')
                    })

            comm_logs = commission_logs[:10]
            result = {'commission_events': comm_logs, 'count': len(commission_logs), 'showing': len(comm_logs)}
            clean_data = hide_gateway_info(result)
            print(f"✅ Response (showing last 10 of {len(commission_logs)} commission events):")
            print(json.dumps(clean_data, indent=2))
        else:
            print(f"❌ No payment events (HTTP {response.status_code})")
    except Exception as e:
        print(f"❌ Error: {e}")
    print("\n" + "━" * 70 + "\n")

    # 7. Payments from specific buyer
    if len(unique_buyers) > 0:
        example_buyer = list(unique_buyers)[0]
        print("7️⃣  PAYMENTS FROM SPECIFIC BUYER - Showing Last 10\n")
        print(f"curl '{AGENTPAY_API_URL}/audit/logs?event_type=x402_payment_settled&client_id={example_buyer}' \\")
        print(f"  -H 'x-api-key: {api_key}'\n")
        print("🔄 Executing...\n")
        try:
            response = requests.get(
                f"{AGENTPAY_API_URL}/audit/logs",
                headers={"x-api-key": api_key},
                params={"event_type": "x402_payment_settled", "client_id": example_buyer},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                all_logs = data.get('logs', [])
                buyer_logs = all_logs[:10]
                result = {'buyer': example_buyer, 'logs': buyer_logs, 'count': len(all_logs), 'showing': len(buyer_logs)}
                clean_data = hide_gateway_info(result)
                print(f"✅ Response (showing last 10 of {len(all_logs)} total from buyer):")
                print(json.dumps(clean_data, indent=2))
            else:
                print(f"❌ No payments from this buyer (HTTP {response.status_code})")
        except Exception as e:
            print(f"❌ Error: {e}")
        print("\n" + "━" * 70 + "\n")

    # 8. Webhook configuration
    print("8️⃣  WEBHOOK CONFIGURATION\n")
    print(f"curl '{AGENTPAY_API_URL}/v1/webhooks/list' \\")
    print(f"  -H 'x-api-key: {api_key}'\n")
    print("🔄 Executing...\n")
    result = {'webhooks': webhooks[:10], 'total': stats['total_webhooks'], 'active': stats['active_webhooks']}
    clean_data = hide_gateway_info(result)
    print(f"✅ Response (showing first 10):")
    print(json.dumps(clean_data, indent=2))
    print("\n" + "━" * 70 + "\n")

    # 9. Webhook delivery events
    print("9️⃣  WEBHOOK DELIVERY EVENTS (Last 30 days) - Showing Last 10\n")
    print(f"curl '{AGENTPAY_API_URL}/audit/logs?event_type=webhook_delivered&hours=720' \\")
    print(f"  -H 'x-api-key: {api_key}'\n")
    print("🔄 Executing...\n")
    try:
        response = requests.get(
            f"{AGENTPAY_API_URL}/audit/logs",
            headers={"x-api-key": api_key},
            params={"event_type": "webhook_delivered", "hours": 720},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            all_logs = data.get('logs', [])
            wh_logs = all_logs[:10]
            result = {'logs': wh_logs, 'count': len(all_logs), 'showing': len(wh_logs)}
            clean_data = hide_gateway_info(result)
            print(f"✅ Response (showing last 10 of {len(all_logs)} total):")
            print(json.dumps(clean_data, indent=2))
        else:
            print(f"❌ No webhook events (HTTP {response.status_code})")
    except Exception as e:
        print(f"❌ Error: {e}")
    print("\n" + "━" * 70 + "\n")

    # 10. Payment verification
    if payments and len(payments) > 0:
        latest_tx = payments[0].get('tx_hash')
        if latest_tx:
            print("🔟 PAYMENT VERIFICATION (Latest Payment)\n")
            print(f"curl '{AGENTPAY_API_URL}/v1/payments/verify/{latest_tx}' \\")
            print(f"  -H 'x-api-key: {api_key}'\n")
            print("🔄 Executing...\n")
            try:
                response = requests.get(
                    f"{AGENTPAY_API_URL}/v1/payments/verify/{latest_tx}",
                    headers={"x-api-key": api_key},
                    timeout=10
                )
                if response.status_code == 200:
                    verify_data = response.json()
                    clean_data = hide_gateway_info(verify_data)
                    print(f"✅ Response:")
                    print(json.dumps(clean_data, indent=2))
                else:
                    print(f"❌ Verification failed (HTTP {response.status_code})")
            except Exception as e:
                print(f"❌ Error: {e}")
            print("\n" + "━" * 70 + "\n")

    # Additional manual commands (templates for user)
    print("➕ ADDITIONAL COMMANDS (Templates)\n")
    print("   Verify specific payment (replace YOUR_TX_HASH):")
    print(f"   curl '{AGENTPAY_API_URL}/v1/payments/verify/YOUR_TX_HASH' \\")
    print(f"     -H 'x-api-key: {api_key}'\n")
    print("   Get audit logs by transaction (replace YOUR_TX_HASH):")
    print(f"   curl '{AGENTPAY_API_URL}/audit/logs/transaction/YOUR_TX_HASH' \\")
    print(f"     -H 'x-api-key: {api_key}'\n")

    print("=" * 70)
    print("✅ SELLER MONITORING COMPLETE")
    print("=" * 70)
    print()
