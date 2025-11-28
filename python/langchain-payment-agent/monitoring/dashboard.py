"""
Monitoring Dashboard Module

Main MonitoringDashboard class for fetching analytics, generating reports, and tracking payments.
"""

import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from .alerts import AlertEngine, Alert
from .exports import CSVExporter, JSONExporter
from .config import ChainConfig, load_config


class MonitoringDashboard:
    """
    Complete monitoring dashboard for AgentGatePay payments

    Features:
    - Analytics fetching
    - Payment history tracking
    - Smart alerts
    - Budget monitoring
    - CSV/JSON exports
    """

    def __init__(
        self,
        api_url: str,
        api_key: str,
        wallet: str = None,
        config: ChainConfig = None
    ):
        """
        Initialize monitoring dashboard

        Args:
            api_url: AgentGatePay API URL
            api_key: User API key
            wallet: User wallet address (optional)
            config: ChainConfig object (optional, will load from file if not provided)
        """
        self.api_url = api_url
        self.api_key = api_key
        self.wallet = wallet
        self.config = config or load_config()

        self.alert_engine = AlertEngine()
        self.csv_exporter = CSVExporter()
        self.json_exporter = JSONExporter()

        self.analytics = {}
        self.payments = []
        self.mandates = []
        self.audit_logs = []
        self.alerts = []

    def fetch_analytics(self) -> Dict:
        """Fetch user analytics from API"""
        try:
            response = requests.get(
                f"{self.api_url}/v1/analytics/me",
                headers={"x-api-key": self.api_key},
                timeout=10
            )
            response.raise_for_status()
            self.analytics = response.json()
            return self.analytics
        except Exception as e:
            print(f"⚠️  Failed to fetch analytics: {e}")
            return {}

    def fetch_payment_history(self, limit: int = 50) -> List[Dict]:
        """Fetch payment history from MCP endpoint"""
        try:
            response = requests.post(
                f"{self.api_url}/mcp",
                headers={
                    "x-api-key": self.api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "agentpay_get_payment_history",
                        "arguments": {"limit": limit}
                    }
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            # Parse MCP response
            if data.get('result') and data['result'].get('content'):
                import json
                content = data['result']['content'][0]['text']
                parsed = json.loads(content)
                self.payments = parsed.get('payments', [])
                return self.payments
            else:
                self.payments = []
                return []

        except Exception as e:
            print(f"⚠️  Failed to fetch payment history: {e}")
            return []

    def fetch_audit_logs(self, hours: int = 24, limit: int = 50) -> List[Dict]:
        """Fetch audit logs"""
        try:
            params = {
                "hours": hours,
                "limit": limit
            }

            if self.wallet:
                params["client_id"] = self.wallet

            response = requests.get(
                f"{self.api_url}/audit/logs",
                headers={"x-api-key": self.api_key},
                params=params,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            self.audit_logs = data.get('logs', [])
            return self.audit_logs
        except Exception as e:
            print(f"⚠️  Failed to fetch audit logs: {e}")
            return []

    def fetch_mandates(self) -> List[Dict]:
        """Fetch active mandates from audit logs"""
        try:
            response = requests.get(
                f"{self.api_url}/audit/logs",
                headers={"x-api-key": self.api_key},
                params={"event_type": "mandate_issued", "limit": 50},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            self.mandates = data.get('logs', [])
            return self.mandates
        except Exception as e:
            print(f"⚠️  Failed to fetch mandates: {e}")
            return []

    def calculate_statistics(self) -> Dict:
        """Calculate monitoring statistics"""
        # Fetch data if not already loaded
        if not self.analytics:
            self.fetch_analytics()
        if not self.payments:
            self.fetch_payment_history()
        if not self.audit_logs:
            self.fetch_audit_logs()
        if not self.mandates:
            self.fetch_mandates()

        # Use analytics data
        total_spent = self.analytics.get('total_spent_usd', 0)
        payment_count = self.analytics.get('transaction_count', 0)
        average_payment = total_spent / payment_count if payment_count > 0 else 0

        # Calculate 24h activity
        one_day_ago = datetime.now() - timedelta(hours=24)
        payments_24h = [
            p for p in self.payments
            if datetime.fromisoformat(p.get('timestamp', p.get('created_at', '2000-01-01')).replace('Z', '+00:00')) > one_day_ago
        ]
        spent_24h = sum(float(p.get('amount_usd', 0)) for p in payments_24h)

        # Budget calculation
        budget_total = sum(
            float(m.get('details', {}).get('budget_usd', 0)) if isinstance(m.get('details'), dict)
            else float(eval(m.get('details', '{}')).get('budget_usd', 0))
            for m in self.mandates
        )
        budget_remaining = budget_total - total_spent
        budget_utilization_pct = ((total_spent / budget_total) * 100) if budget_total > 0 else 0

        # Active mandates
        active_mandates = len([
            m for m in self.mandates
            if (m.get('details', {}) if isinstance(m.get('details'), dict) else eval(m.get('details', '{}'))).get('status') in ['active', 'issued']
        ])

        stats = {
            "total_spent": total_spent,
            "payment_count": payment_count,
            "average_payment": average_payment,
            "payments_last_24h": len(payments_24h),
            "spent_last_24h": spent_24h,
            "budget_total": budget_total,
            "budget_remaining": budget_remaining,
            "budget_utilization_pct": budget_utilization_pct,
            "active_mandates": active_mandates,
            "total_events_24h": len(self.audit_logs),
            "spending_trend": "increasing" if spent_24h > average_payment else "stable"
        }

        return stats

    def generate_alerts(self, stats: Dict) -> List[Alert]:
        """Generate alerts based on statistics"""
        self.alerts = self.alert_engine.check_all(
            budget_total=stats['budget_total'],
            budget_remaining=stats['budget_remaining'],
            mandates=self.mandates,
            payments=self.payments,
            spent_24h=stats['spent_last_24h'],
            average_payment=stats['average_payment'],
            payments_24h=stats['payments_last_24h']
        )
        return self.alerts

    def generate_report(self) -> Dict:
        """
        Generate complete monitoring report

        Returns:
            Dictionary containing all monitoring data
        """
        stats = self.calculate_statistics()
        alerts = self.generate_alerts(stats)

        report = {
            "generated_at": datetime.now().isoformat(),
            "config": {
                "chain": self.config.chain if self.config else "unknown",
                "token": self.config.token if self.config else "unknown",
                "explorer": self.config.explorer if self.config else "unknown"
            },
            "stats": stats,
            "alerts": alerts,
            "payments": self.payments[:20],  # Last 20
            "mandates": self.mandates,
            "alert_summary": self.alert_engine.get_alert_summary()
        }

        return report

    def export_csv(self, filepath: str = None) -> str:
        """Export monitoring report to CSV"""
        stats = self.calculate_statistics()
        alerts = self.alerts or self.generate_alerts(stats)

        return self.csv_exporter.export_full_report(
            stats=stats,
            payments=self.payments,
            alerts=alerts,
            mandates=self.mandates,
            filepath=filepath
        )

    def export_json(self, filepath: str = None) -> str:
        """Export monitoring report to JSON"""
        stats = self.calculate_statistics()
        alerts = self.alerts or self.generate_alerts(stats)

        config_dict = {
            "chain": self.config.chain if self.config else "unknown",
            "token": self.config.token if self.config else "unknown",
            "explorer": self.config.explorer if self.config else "unknown"
        }

        return self.json_exporter.export_report(
            stats=stats,
            payments=self.payments,
            alerts=alerts,
            mandates=self.mandates,
            config=config_dict,
            filepath=filepath
        )

    def print_dashboard(self):
        """Print formatted dashboard to console"""
        report = self.generate_report()
        stats = report['stats']
        alerts = report['alerts']

        print("\n" + "=" * 60)
        print("📊 AGENTGATEPAY MONITORING DASHBOARD")
        print("=" * 60)
        print(f"\nGenerated: {report['generated_at']}")
        print(f"Chain: {report['config']['chain'].upper()}")
        print(f"Token: {report['config']['token']}")

        print("\n" + "-" * 60)
        print("💰 SPENDING SUMMARY")
        print("-" * 60)
        print(f"Total Spent: ${stats['total_spent']:.2f} USD")
        print(f"Payment Count: {stats['payment_count']}")
        print(f"Average Payment: ${stats['average_payment']:.2f} USD")
        print(f"Last 24h: {stats['payments_last_24h']} payments (${stats['spent_last_24h']:.2f} USD)")

        print("\n" + "-" * 60)
        print("🔑 BUDGET STATUS")
        print("-" * 60)
        print(f"Allocated: ${stats['budget_total']:.2f} USD")
        print(f"Remaining: ${stats['budget_remaining']:.2f} USD")
        print(f"Utilization: {stats['budget_utilization_pct']:.1f}%")
        print(f"Active Mandates: {stats['active_mandates']}")

        if alerts:
            print("\n" + "-" * 60)
            print(f"🚨 ALERTS ({len(alerts)})")
            print("-" * 60)
            for alert in alerts[:5]:  # Show top 5
                print(f"[{alert.severity.value.upper()}] {alert.message}")
                print(f"   Action: {alert.action}")

        print("\n" + "=" * 60)
