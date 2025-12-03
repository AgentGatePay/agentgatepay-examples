#!/usr/bin/env python3
"""
AgentGatePay + LangChain Integration - BUYER MONITORING DASHBOARD

Monitor your payment activity as a BUYER (outgoing payments):
- Spending analytics and budget tracking
- Payment history (what you paid to merchants)
- Active mandates and budget utilization
- Smart alerts (budget warnings, mandate expiration, failed payments)
- Commission tracking (what you paid to the gateway)
- Live CURL command execution with results

This is for buyers who SEND payments. For sellers who RECEIVE payments,
use 6b_monitoring_seller.py instead.

Features (Buyer-Focused):
- Total spent, payment count, average payment
- Budget tracking and mandate management
- Outgoing payment history (what you paid)
- Budget alerts and spending trends
- Mandate expiration warnings
- Commission breakdown per transaction
- Live API execution and results

Usage:
    # Standalone mode (will prompt for credentials)
    python 6a_monitoring_buyer.py

    # With arguments
    python 6a_monitoring_buyer.py --api-key pk_live_... --wallet 0xABC...

Requirements:
- pip install agentgatepay-sdk>=1.1.3 python-dotenv requests
- .env file with BUYER_API_KEY and BUYER_WALLET
"""

import os
import sys
import argparse
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
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

def fetch_buyer_analytics(api_url, api_key):
    """Fetch buyer spending analytics"""
    try:
        response = requests.get(
            f"{api_url}/v1/analytics/me",
            headers={"x-api-key": api_key},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"⚠️  Failed to fetch analytics: {e}")
        return {}


def fetch_payment_list(api_url, api_key, wallet=None, limit=100):
    """Fetch payment list for buyer"""
    return []


def fetch_audit_logs(api_url, api_key, wallet=None, hours=24, limit=100, event_type=None):
    """Fetch audit logs for payment events"""
    try:
        params = {"hours": hours, "limit": limit}
        if event_type:
            params["event_type"] = event_type
        if wallet:
            params["client_id"] = wallet

        response = requests.get(
            f"{api_url}/audit/logs",
            headers={"x-api-key": api_key},
            params=params,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return data.get('logs', [])
    except Exception as e:
        print(f"⚠️  Failed to fetch audit logs: {e}")
        return []


def fetch_mandates(api_url, api_key, wallet=None, hours=720):
    """Fetch active mandates from audit logs"""
    try:
        params = {
            "event_type": "mandate_issued",
            "hours": hours,
            "limit": 100
        }
        if wallet:
            params["client_id"] = wallet

        response = requests.get(
            f"{api_url}/audit/logs",
            headers={"x-api-key": api_key},
            params=params,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return data.get('logs', [])
    except Exception as e:
        print(f"⚠️  Failed to fetch mandates: {e}")
        return []


def calculate_buyer_stats(analytics, payments, mandates, logs):
    """Calculate buyer-specific statistics"""
    # Spending stats - Calculate from actual payment data
    total_spent = sum(float(p.get('amount_usd', 0)) for p in payments)
    payment_count = len(payments)
    average_payment = total_spent / payment_count if payment_count > 0 else 0

    # Recent activity (24h)
    one_day_ago = datetime.now() - timedelta(hours=24)

    payments_24h = [
        p for p in payments
        if datetime.fromisoformat(p.get('timestamp', p.get('created_at', '2000-01-01')).replace('Z', '+00:00')) > one_day_ago
    ]
    spent_24h = sum(float(p.get('amount_usd', 0)) for p in payments_24h)

    # Budget stats
    budget_total = sum(
        float(json.loads(m.get('details', '{}')).get('budget_usd', 0)) if isinstance(m.get('details'), str)
        else float(m.get('details', {}).get('budget_usd', 0))
        for m in mandates
    )
    budget_remaining = sum(
        float(json.loads(m.get('details', '{}')).get('budget_remaining', 0)) if isinstance(m.get('details'), str)
        else float(m.get('details', {}).get('budget_remaining', 0))
        for m in mandates
    )
    budget_utilization = ((budget_total - budget_remaining) / budget_total * 100) if budget_total > 0 else 0

    # Active mandates count
    active_mandates = len([
        m for m in mandates
        if (json.loads(m.get('details', '{}')).get('status', '') == 'active' if isinstance(m.get('details'), str)
            else m.get('details', {}).get('status', '') == 'active')
    ])

    # Payment success rate
    successful = len([p for p in payments if p.get('status') in ['completed', 'confirmed']])
    failed = len([p for p in payments if p.get('status') == 'failed'])
    total_status = successful + failed
    success_rate = (successful / total_status * 100) if total_status > 0 else 100

    # Spending trend
    if spent_24h > average_payment * 2:
        spending_trend = "📈 High (2x+ average)"
    elif spent_24h < average_payment * 0.5:
        spending_trend = "📉 Low (<50% average)"
    else:
        spending_trend = "➡️  Normal"

    return {
        'total_spent': total_spent,
        'payment_count': payment_count,
        'average_payment': average_payment,
        'payments_24h': len(payments_24h),
        'spent_24h': spent_24h,
        'budget_total': budget_total,
        'budget_remaining': budget_remaining,
        'budget_utilization': budget_utilization,
        'active_mandates': active_mandates,
        'success_rate': success_rate,
        'failed_payments': failed,
        'spending_trend': spending_trend,
        'total_events': len(logs)
    }


def generate_buyer_alerts(stats, payments, mandates):
    """Generate buyer-specific alerts"""
    alerts = []

    # Budget warnings
    if stats['budget_utilization'] > 90:
        alerts.append({
            'severity': 'high',
            'message': f"⚠️  BUDGET CRITICAL: {stats['budget_utilization']:.1f}% utilization",
            'action': 'Issue new mandate or reduce spending'
        })
    elif stats['budget_utilization'] > 70:
        alerts.append({
            'severity': 'medium',
            'message': f"⚠️  Budget warning: {stats['budget_utilization']:.1f}% utilization",
            'action': 'Monitor budget usage closely'
        })

    # No active mandates
    if stats['active_mandates'] == 0 and stats['payment_count'] > 0:
        alerts.append({
            'severity': 'high',
            'message': '❌ No active mandates - cannot make payments',
            'action': 'Issue new mandate to enable payments'
        })

    # Failed payments
    if stats['failed_payments'] > 0:
        alerts.append({
            'severity': 'high',
            'message': f"❌ PAYMENT FAILURES: {stats['failed_payments']} failed payment(s)",
            'action': 'Check mandate budget and payment details'
        })

    # Low success rate
    if stats['success_rate'] < 90 and stats['payment_count'] > 10:
        alerts.append({
            'severity': 'high',
            'message': f"⚠️  LOW SUCCESS RATE: {stats['success_rate']:.1f}% ({stats['failed_payments']} failures)",
            'action': 'Review payment errors and mandate configuration'
        })

    # Mandate expiration warning
    for mandate in mandates:
        details = mandate.get('details', {})
        if isinstance(details, str):
            try:
                details = json.loads(details)
            except:
                continue

        expires_at = details.get('expires_at')
        if expires_at:
            try:
                expire_time = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                time_left = expire_time - datetime.now(expire_time.tzinfo)
                if time_left.total_seconds() < 3600:  # < 1 hour
                    alerts.append({
                        'severity': 'high',
                        'message': f"⏰ Mandate expires in {int(time_left.total_seconds() / 60)} minutes",
                        'action': 'Issue new mandate to continue payments'
                    })
                elif time_left.total_seconds() < 86400:  # < 24 hours
                    alerts.append({
                        'severity': 'medium',
                        'message': f"⏰ Mandate expires in {int(time_left.total_seconds() / 3600)} hours",
                        'action': 'Plan mandate renewal'
                    })
            except:
                pass

    # Spending spike
    if stats['spent_24h'] > stats['average_payment'] * 10 and stats['payment_count'] > 10:
        alerts.append({
            'severity': 'medium',
            'message': f"📈 Spending Spike: ${stats['spent_24h']:.2f} in 24h (10x average)",
            'action': 'Review recent payment activity'
        })

    return alerts


# ========================================
# MAIN
# ========================================

if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(description='AgentGatePay Buyer Monitoring Dashboard')
    parser.add_argument('--api-key', help='AgentGatePay API key', default=None)
    parser.add_argument('--wallet', help='Buyer wallet address', default=None)
    parser.add_argument('--no-alerts', action='store_true', help='Disable alerts')

    args = parser.parse_args()

    print("=" * 70)
    print("📊 BUYER MONITORING DASHBOARD (Outgoing Payments)")
    print("=" * 70)
    print()
    print("This dashboard tracks your SPENDING as a buyer:")
    print("  ✅ Total spent and payment count")
    print("  ✅ Budget tracking and mandate status")
    print("  ✅ Payment history (what you paid to merchants)")
    print("  ✅ Spending alerts and budget warnings")
    print("  ✅ Commission tracking (what you paid to gateway)")
    print()
    print("For REVENUE tracking (incoming payments), use 6b_monitoring_seller.py")
    print()
    print("=" * 70)

    # Get API key
    api_key = args.api_key or os.getenv('BUYER_API_KEY') or os.getenv('AGENTGATEPAY_API_KEY')

    if not api_key:
        print("\n⚠️  Buyer API key required!")
        print()
        api_key = input("Enter your buyer API key (pk_live_...): ").strip()

        if not api_key or not api_key.startswith('pk_'):
            print("❌ Invalid API key format. Expected: pk_live_...")
            sys.exit(1)

    # Get wallet address (optional but recommended)
    wallet = args.wallet or os.getenv('BUYER_WALLET')

    if not wallet:
        print()
        wallet_input = input("Enter your buyer wallet address (0x...) [optional, press Enter to skip]: ").strip()
        if wallet_input:
            wallet = wallet_input

    # Fetch buyer data
    print()
    print("🔄 Fetching buyer data from AgentGatePay API...")
    print()

    try:
        analytics = fetch_buyer_analytics(AGENTPAY_API_URL, api_key)
        logs = fetch_audit_logs(AGENTPAY_API_URL, api_key, wallet=wallet, hours=720, event_type="x402_payment_settled")
        mandates = fetch_mandates(AGENTPAY_API_URL, api_key, wallet=wallet, hours=720)

        # Build payments list from logs
        payments = []
        for log in logs:
            details = log.get('details', {})
            if isinstance(details, str):
                try:
                    details = json.loads(details)
                except:
                    continue

            tx_hash = details.get('merchant_tx_hash') or details.get('tx_hash')
            if tx_hash:
                payments.append({
                    'tx_hash': tx_hash,
                    'amount_usd': details.get('merchant_amount_usd') or details.get('amount_usd', 0),
                    'status': details.get('status', 'completed'),
                    'timestamp': datetime.fromtimestamp(int(details.get('timestamp', 0))).isoformat() if details.get('timestamp') else log.get('timestamp'),
                    'receiver_address': details.get('receiver_address') or details.get('merchant_address'),
                    'receiver': details.get('receiver_address') or details.get('merchant_address'),
                    'created_at': datetime.fromtimestamp(int(details.get('timestamp', 0))).isoformat() if details.get('timestamp') else log.get('timestamp')
                })

        logs_24h = fetch_audit_logs(AGENTPAY_API_URL, api_key, wallet=wallet, hours=24, event_type="x402_payment_settled")
    except Exception as e:
        print(f"❌ Failed to fetch data: {e}")
        print()
        print("Please check:")
        print("  - Buyer API key is valid")
        print("  - Buyer wallet address is correct (if provided)")
        print("  - Network connection is working")
        sys.exit(1)

    stats = calculate_buyer_stats(analytics, payments, mandates, logs_24h)
    alerts = generate_buyer_alerts(stats, payments, mandates)

    # ========================================
    # DISPLAY BUYER DASHBOARD
    # ========================================

    print("\n" + "=" * 70)
    print("📊 BUYER MONITORING DASHBOARD")
    print("=" * 70)
    print(f"\nGenerated: {datetime.now().isoformat()}")
    if wallet:
        print(f"Buyer Wallet: {wallet[:10]}...{wallet[-8:]}")
    print()

    # Key Metrics - BUYER FOCUS
    print("━" * 70)
    print("💰 SPENDING SUMMARY")
    print("━" * 70)
    print(f"Total Spent: ${stats['total_spent']:.2f} USD")
    print(f"Payment Count: {stats['payment_count']} (outgoing payments)")
    print(f"Average Payment: ${stats['average_payment']:.2f} USD")
    print(f"Last 24h: {stats['payments_24h']} payments (${stats['spent_24h']:.2f} USD)")
    print(f"Spending Trend: {stats['spending_trend']}")
    print()

    # Budget Status - BUYER FOCUS
    print("━" * 70)
    print("🔑 BUDGET STATUS")
    print("━" * 70)
    print(f"Total Allocated: ${stats['budget_total']:.2f} USD")
    print(f"Remaining: ${stats['budget_remaining']:.2f} USD")
    print(f"Utilization: {stats['budget_utilization']:.1f}%")
    print(f"Active Mandates: {stats['active_mandates']}")
    print()

    # Payment Metrics
    print("━" * 70)
    print("📊 PAYMENT METRICS")
    print("━" * 70)
    print(f"Success Rate: {stats['success_rate']:.1f}%")
    print(f"Failed Payments: {stats['failed_payments']}")
    print(f"Total Events (24h): {stats['total_events']}")
    print()

    # Alerts - BUYER FOCUS
    if not args.no_alerts and alerts:
        print("━" * 70)
        print(f"🚨 BUYER ALERTS ({len(alerts)})")
        print("━" * 70)
        for i, alert in enumerate(alerts, 1):
            print(f"{i}. [{alert['severity'].upper()}] {alert['message']}")
            print(f"   Action: {alert['action']}")
            if i < len(alerts):
                print()
        print()

    # Recent Payments - BUYER FOCUS (what you paid)
    if payments:
        print("━" * 70)
        print("💳 OUTGOING PAYMENTS (Last 10)")
        print("━" * 70)
        print("(Payments YOU sent to merchants)\n")
        for i, payment in enumerate(payments[:10], 1):
            timestamp = payment.get('timestamp', payment.get('created_at', 'N/A'))
            amount = float(payment.get('amount_usd', 0))
            status = payment.get('status', 'unknown')
            tx_hash = payment.get('tx_hash', 'N/A')

            # Get receiver/merchant address
            receiver = (payment.get('receiver_address') or
                       payment.get('receiver') or
                       payment.get('to_address', 'Unknown'))

            print(f"{i}. YOU PAID ${amount:.2f} → {receiver} | {timestamp} | {status} | TX {tx_hash}")
        print()

    # Mandates - BUYER FOCUS
    if mandates:
        print("━" * 70)
        print(f"🎫 ACTIVE MANDATES ({len(mandates)})")
        print("━" * 70)
        print("(Budget allocations for your payments)\n")
        for i, mandate in enumerate(mandates[:5], 1):
            details = mandate.get('details', {})
            if isinstance(details, str):
                try:
                    details = json.loads(details)
                except:
                    continue

            mandate_id = details.get('mandate_id', 'N/A')[:30]
            budget = details.get('budget_usd', 0)
            remaining = details.get('budget_remaining', 0)
            status = details.get('status', 'N/A')
            expires_at = details.get('expires_at', 'N/A')

            print(f"{i}. {mandate_id}... | Budget: ${budget:.2f} | Remaining: ${remaining:.2f} | {status} | Expires: {expires_at}")
        if len(mandates) > 5:
            print(f"... and {len(mandates) - 5} more mandates")
        print()

    # Payment breakdown with commission
    if logs_24h:
        buyer_payments = []
        commission_payments = []

        for log in logs_24h:
            details = log.get('details', {})
            if isinstance(details, str):
                try:
                    details = json.loads(details)
                except:
                    continue

            # Extract merchant and commission info
            merchant_tx = details.get('merchant_tx_hash')
            commission_tx = details.get('commission_tx_hash')

            # Get amounts
            merchant_amount = details.get('merchant_amount_usd') or details.get('amount_usd', 0)
            commission_amount = details.get('commission_amount_usd') or details.get('commission_usd', 0)

            # Convert timestamp
            timestamp_unix = details.get('timestamp', log.get('timestamp', 0))
            try:
                if isinstance(timestamp_unix, str):
                    timestamp_readable = timestamp_unix
                else:
                    timestamp_readable = datetime.fromtimestamp(int(timestamp_unix)).isoformat()
            except:
                timestamp_readable = str(timestamp_unix)

            # Extract merchant address
            merchant = (details.get('receiver_address') or
                       details.get('receiver') or
                       details.get('to_address', 'Unknown'))

            if merchant_tx:
                buyer_payments.append({
                    'tx_hash': merchant_tx,
                    'amount_usd': float(merchant_amount),
                    'timestamp': timestamp_readable,
                    'merchant': merchant
                })

            if commission_tx:
                commission_payments.append({
                    'tx_hash': commission_tx,
                    'amount_usd': float(commission_amount),
                    'timestamp': timestamp_readable,
                    'merchant': merchant
                })

        # Display payments sent to merchants
        if buyer_payments:
            print("━" * 70)
            print(f"💸 PAYMENTS SENT TO MERCHANTS (Last {min(20, len(buyer_payments))})")
            print("━" * 70)
            print("(99.5% of each payment goes to merchant)\n")
            for i, payment in enumerate(buyer_payments[:20], 1):
                tx_hash = payment['tx_hash']
                amount = payment.get('amount_usd', 0)
                merchant = str(payment.get('merchant', 'Unknown'))
                timestamp = payment.get('timestamp', 'N/A')
                print(f"{i}. YOU SENT ${amount:.4f} → {merchant} | {timestamp} | TX {tx_hash}")
            print()

        # Display commission payments
        if commission_payments:
            print("━" * 70)
            print(f"💳 COMMISSION PAID TO GATEWAY (Last {min(20, len(commission_payments))})")
            print("━" * 70)
            print("(0.5% gateway commission on each transaction)\n")
            for i, payment in enumerate(commission_payments[:20], 1):
                tx_hash = payment['tx_hash']
                commission = payment.get('amount_usd', 0)
                merchant = str(payment.get('merchant', 'Unknown'))
                timestamp = payment.get('timestamp', 'N/A')
                print(f"{i}. ${commission:.4f} → Gateway (for payment to {merchant}) | {timestamp} | TX {tx_hash}")
            print()

    # Calculate total commission paid
    print("━" * 70)
    print("💡 ADDITIONAL METRICS")
    print("━" * 70)

    # Unique merchants (all time, matching total_spent)
    unique_merchants = set()
    for log in logs:
        details = log.get('details', {})
        if isinstance(details, str):
            try:
                details = json.loads(details)
            except:
                continue
        merchant = (details.get('receiver_address') or
                   details.get('receiver') or
                   details.get('to_address'))
        if merchant:
            unique_merchants.add(merchant)

    # Calculate commission total (all time, matching total_spent)
    total_commission = sum(
        float(details.get('commission_amount_usd', 0)) if isinstance(details, dict) else 0
        for log in logs
        for details in [json.loads(log.get('details', '{}')) if isinstance(log.get('details'), str) else log.get('details', {})]
    )

    # Calculate original amounts (merchant + commission = total you paid)
    merchant_received = stats['total_spent']
    total_you_paid = merchant_received + total_commission

    print(f"Unique Merchants: {len(unique_merchants)}")
    print(f"Total You Paid (100%): ${total_you_paid:.2f} USD")
    print(f"Merchant Received (99.5%): ${merchant_received:.2f} USD")
    print(f"Commission Paid (0.5%): ${total_commission:.4f} USD")
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

    # 1. Buyer analytics
    print("1️⃣  BUYER SPENDING ANALYTICS (All Time)\n")
    print(f"curl '{AGENTPAY_API_URL}/v1/analytics/me' \\")
    print(f"  -H 'x-api-key: {api_key}'\n")
    print("🔄 Executing...\n")
    try:
        response = requests.get(
            f"{AGENTPAY_API_URL}/v1/analytics/me",
            headers={"x-api-key": api_key},
            timeout=10
        )
        if response.status_code == 200:
            analytics_data = response.json()
            clean_data = hide_gateway_info(analytics_data)
            print(f"✅ Response (JSON):")
            print(json.dumps(clean_data, indent=2))
        else:
            print(f"❌ Failed (HTTP {response.status_code})")
    except Exception as e:
        print(f"❌ Error: {e}")
    print("\n" + "━" * 70 + "\n")

    # 2-4. Payment events (24h, 7d, 30d)
    for idx, (time_label, hours) in enumerate([("24h", 24), ("7 days", 168), ("30 days", 720)], start=2):
        print(f"{idx}️⃣  PAYMENT EVENTS (Last {time_label}) - Showing Last 10\n")
        params_str = f"event_type=x402_payment_settled&hours={hours}"
        if wallet:
            params_str += f"&client_id={wallet}"
        print(f"curl '{AGENTPAY_API_URL}/audit/logs?{params_str}' \\")
        print(f"  -H 'x-api-key: {api_key}'\n")
        print("🔄 Executing...\n")
        try:
            params = {"event_type": "x402_payment_settled", "hours": hours}
            if wallet:
                params["client_id"] = wallet
            response = requests.get(
                f"{AGENTPAY_API_URL}/audit/logs",
                headers={"x-api-key": api_key},
                params=params,
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

    # 5. Commission events
    print("5️⃣  COMMISSION EVENTS (Last 30 days) - Showing Last 10\n")
    params_str = "event_type=x402_payment_settled&hours=720"
    if wallet:
        params_str += f"&client_id={wallet}"
    print(f"curl '{AGENTPAY_API_URL}/audit/logs?{params_str}' \\")
    print(f"  -H 'x-api-key: {api_key}'\n")
    print("💡 Note: Filtering for events with commission data embedded\n")
    print("🔄 Executing...\n")
    try:
        params = {"event_type": "x402_payment_settled", "hours": 720}
        if wallet:
            params["client_id"] = wallet
        response = requests.get(
            f"{AGENTPAY_API_URL}/audit/logs",
            headers={"x-api-key": api_key},
            params=params,
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
                    commission_logs.append({
                        'id': log.get('id'),
                        'timestamp': log.get('timestamp'),
                        'commission_tx_hash': details.get('commission_tx_hash'),
                        'commission_amount_usd': details.get('commission_amount_usd'),
                        'related_merchant': details.get('receiver_address') or details.get('receiver'),
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

    # 6. Active mandates
    print("6️⃣  ACTIVE MANDATES (Last 30 days)\n")
    params_str = "event_type=mandate_issued&hours=720"
    if wallet:
        params_str += f"&client_id={wallet}"
    print(f"curl '{AGENTPAY_API_URL}/audit/logs?{params_str}' \\")
    print(f"  -H 'x-api-key: {api_key}'\n")
    print("🔄 Executing...\n")
    result = {'mandates': mandates[:10], 'count': len(mandates), 'showing': len(mandates[:10])}
    clean_data = hide_gateway_info(result)
    print(f"✅ Response (showing first 10 of {len(mandates)} total):")
    print(json.dumps(clean_data, indent=2))
    print("\n" + "━" * 70 + "\n")

    # 7. Payment verification
    if payments and len(payments) > 0:
        latest_tx = payments[0].get('tx_hash')
        if latest_tx:
            print("7️⃣  PAYMENT VERIFICATION (Latest Payment)\n")
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

    # Additional manual commands
    print("➕ ADDITIONAL COMMANDS (Templates)\n")
    print("   Verify specific payment (replace YOUR_TX_HASH):")
    print(f"   curl '{AGENTPAY_API_URL}/v1/payments/verify/YOUR_TX_HASH' \\")
    print(f"     -H 'x-api-key: {api_key}'\n")
    print("   Get audit logs by transaction (replace YOUR_TX_HASH):")
    print(f"   curl '{AGENTPAY_API_URL}/audit/logs/transaction/YOUR_TX_HASH' \\")
    print(f"     -H 'x-api-key: {api_key}'\n")
    print("   Issue new mandate:")
    print(f"   curl -X POST '{AGENTPAY_API_URL}/mandates/issue' \\")
    print(f"     -H 'x-api-key: {api_key}' \\")
    print("     -d '{\"subject\": \"buyer\", \"budget_usd\": 100, \"scope\": \"*\", \"ttl_minutes\": 43200}'\n")

    print("=" * 70)
    print("✅ BUYER MONITORING COMPLETE")
    print("=" * 70)
    print()
