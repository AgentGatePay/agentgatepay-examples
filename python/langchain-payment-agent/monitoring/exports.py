"""
Export Module

Handles CSV and JSON exports of monitoring data and payment history.
"""

import csv
import json
import os
from datetime import datetime
from typing import Dict, List, Any


class CSVExporter:
    """CSV export functionality"""

    @staticmethod
    def export_payments(payments: List[Dict], filepath: str = None) -> str:
        """
        Export payments to CSV

        Args:
            payments: List of payment dictionaries
            filepath: Output file path (default: /tmp/agentpay_payments_<timestamp>.csv)

        Returns:
            Path to created CSV file
        """
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"/tmp/agentpay_payments_{timestamp}.csv"

        with open(filepath, 'w', newline='') as f:
            if not payments:
                f.write("No payments found\n")
                return filepath

            # Determine fields from first payment
            fieldnames = ['timestamp', 'amount_usd', 'status', 'tx_hash', 'receiver', 'type']

            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()

            for payment in payments:
                writer.writerow({
                    'timestamp': payment.get('timestamp', payment.get('created_at', 'N/A')),
                    'amount_usd': payment.get('amount_usd', 0),
                    'status': payment.get('status', 'unknown'),
                    'tx_hash': payment.get('tx_hash', 'N/A'),
                    'receiver': payment.get('receiver', payment.get('receiver_address', 'N/A')),
                    'type': payment.get('type', 'payment')
                })

        return filepath

    @staticmethod
    def export_full_report(
        stats: Dict,
        payments: List[Dict],
        alerts: List[Any],
        mandates: List[Dict],
        filepath: str = None
    ) -> str:
        """
        Export complete monitoring report to CSV

        Args:
            stats: Statistics dictionary
            payments: List of payments
            alerts: List of alerts
            mandates: List of mandates
            filepath: Output file path

        Returns:
            Path to created CSV file
        """
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"/tmp/agentpay_report_{timestamp}.csv"

        with open(filepath, 'w', newline='') as f:
            f.write("AgentGatePay Monitoring Report\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write("\n")

            # Summary section
            f.write("SUMMARY\n")
            f.write("Metric,Value\n")
            f.write(f"Total Spent,${stats.get('total_spent', 0):.2f}\n")
            f.write(f"Payment Count,{stats.get('payment_count', 0)}\n")
            f.write(f"Average Payment,${stats.get('average_payment', 0):.2f}\n")
            f.write(f"Budget Remaining,${stats.get('budget_remaining', 0):.2f}\n")
            f.write(f"Budget Utilization,{stats.get('budget_utilization_pct', 0)}%\n")
            f.write(f"Active Mandates,{stats.get('active_mandates', 0)}\n")
            f.write(f"Payments (24h),{stats.get('payments_last_24h', 0)}\n")
            f.write(f"Spent (24h),${stats.get('spent_last_24h', 0):.2f}\n")
            f.write("\n")

            # Alerts section
            if alerts:
                f.write("ALERTS\n")
                f.write("Severity,Type,Message,Action\n")
                for alert in alerts:
                    f.write(f"{alert.severity.value},{alert.type},\"{alert.message}\",\"{alert.action}\"\n")
                f.write("\n")

            # Payments section
            if payments:
                f.write("PAYMENTS (Last 20)\n")
                f.write("Timestamp,Amount USD,Status,TX Hash,Receiver\n")
                for payment in payments[:20]:
                    timestamp = payment.get('timestamp', payment.get('created_at', 'N/A'))
                    amount = payment.get('amount_usd', 0)
                    status = payment.get('status', 'unknown')
                    tx_hash = payment.get('tx_hash', 'N/A')
                    receiver = payment.get('receiver', payment.get('receiver_address', 'N/A'))
                    f.write(f"{timestamp},{amount},{status},{tx_hash},{receiver}\n")
                f.write("\n")

            # Mandates section
            if mandates:
                f.write("ACTIVE MANDATES\n")
                f.write("Mandate ID,Budget USD,Remaining USD,TTL Hours,Status\n")
                for mandate in mandates:
                    details = mandate.get('details', {})
                    if isinstance(details, str):
                        details = json.loads(details)

                    mandate_id = details.get('mandate_id', 'N/A')
                    budget_usd = details.get('budget_usd', 0)
                    budget_remaining = details.get('budget_remaining', 0)
                    ttl_hours = details.get('ttl_remaining_hours', 'N/A')
                    status = details.get('status', 'N/A')

                    f.write(f"{mandate_id},{budget_usd},{budget_remaining},{ttl_hours},{status}\n")

        return filepath


class JSONExporter:
    """JSON export functionality"""

    @staticmethod
    def export_report(
        stats: Dict,
        payments: List[Dict],
        alerts: List[Any],
        mandates: List[Dict],
        config: Dict = None,
        filepath: str = None
    ) -> str:
        """
        Export complete monitoring report to JSON

        Args:
            stats: Statistics dictionary
            payments: List of payments
            alerts: List of alerts
            mandates: List of mandates
            config: Configuration dictionary
            filepath: Output file path

        Returns:
            Path to created JSON file
        """
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"/tmp/agentpay_report_{timestamp}.json"

        report = {
            "generated_at": datetime.now().isoformat(),
            "version": "1.0",
            "config": config or {},
            "summary": stats,
            "alerts": [
                {
                    "severity": alert.severity.value,
                    "type": alert.type,
                    "message": alert.message,
                    "action": alert.action,
                    "details": alert.details
                }
                for alert in alerts
            ],
            "payments": payments,
            "mandates": mandates
        }

        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        return filepath
