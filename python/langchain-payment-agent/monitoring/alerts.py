"""
Alert Engine Module

Generates smart alerts based on payment activity, budget status, and spending patterns.
"""

from enum import Enum
from typing import List, Dict, Any
from dataclasses import dataclass


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Alert data structure"""
    severity: AlertSeverity
    type: str
    message: str
    action: str
    details: Dict[str, Any] = None


class AlertEngine:
    """
    Alert engine for monitoring payment activity and budgets
    """

    def __init__(self):
        self.alerts: List[Alert] = []

    def check_budget_alerts(self, budget_total: float, budget_remaining: float) -> List[Alert]:
        """
        Check for budget-related alerts

        Args:
            budget_total: Total budget allocated
            budget_remaining: Remaining budget

        Returns:
            List of Alert objects
        """
        alerts = []

        if budget_total <= 0:
            return alerts

        utilization = ((budget_total - budget_remaining) / budget_total) * 100

        # Critical: < $1 remaining or > 95% used
        if budget_remaining < 1.0 or utilization > 95:
            alerts.append(Alert(
                severity=AlertSeverity.CRITICAL,
                type="budget_critical",
                message=f"⚠️  CRITICAL: Only ${budget_remaining:.2f} remaining ({utilization:.1f}% used)",
                action="Issue new mandate or stop spending immediately",
                details={"budget_total": budget_total, "budget_remaining": budget_remaining, "utilization": utilization}
            ))

        # High: > 90% used
        elif utilization > 90:
            alerts.append(Alert(
                severity=AlertSeverity.HIGH,
                type="budget_low",
                message=f"⚠️  BUDGET WARNING: Only ${budget_remaining:.2f} remaining ({utilization:.1f}% used)",
                action="Issue new mandate or reduce spending",
                details={"budget_total": budget_total, "budget_remaining": budget_remaining, "utilization": utilization}
            ))

        # Medium: > 75% used
        elif utilization > 75:
            alerts.append(Alert(
                severity=AlertSeverity.MEDIUM,
                type="budget_warning",
                message=f"ℹ️  Budget Notice: ${budget_remaining:.2f} remaining ({utilization:.1f}% used)",
                action="Monitor spending",
                details={"budget_total": budget_total, "budget_remaining": budget_remaining, "utilization": utilization}
            ))

        return alerts

    def check_mandate_expiration(self, mandates: List[Dict]) -> List[Alert]:
        """
        Check for mandate expiration alerts

        Args:
            mandates: List of mandate dictionaries with ttl_remaining_hours

        Returns:
            List of Alert objects
        """
        alerts = []

        for mandate in mandates:
            details = mandate.get('details', {})
            if isinstance(details, str):
                import json
                details = json.loads(details)

            ttl_remaining = details.get('ttl_remaining_hours')
            mandate_id = details.get('mandate_id', 'Unknown')

            if ttl_remaining is None:
                continue

            # Critical: < 2 hours
            if ttl_remaining < 2:
                alerts.append(Alert(
                    severity=AlertSeverity.CRITICAL,
                    type="mandate_expiring_soon",
                    message=f"⏰ CRITICAL: Mandate {mandate_id} expires in {ttl_remaining} hours",
                    action="Renew mandate immediately",
                    details={"mandate_id": mandate_id, "ttl_remaining_hours": ttl_remaining}
                ))

            # High: < 24 hours
            elif ttl_remaining < 24:
                alerts.append(Alert(
                    severity=AlertSeverity.HIGH,
                    type="mandate_expiring",
                    message=f"⏰ Mandate {mandate_id} expires in {ttl_remaining} hours",
                    action="Renew mandate before expiration",
                    details={"mandate_id": mandate_id, "ttl_remaining_hours": ttl_remaining}
                ))

            # Medium: < 7 days
            elif ttl_remaining < 168:
                alerts.append(Alert(
                    severity=AlertSeverity.MEDIUM,
                    type="mandate_expiration_warning",
                    message=f"ℹ️  Mandate {mandate_id} expires in {ttl_remaining / 24:.1f} days",
                    action="Plan mandate renewal",
                    details={"mandate_id": mandate_id, "ttl_remaining_hours": ttl_remaining}
                ))

        return alerts

    def check_payment_failures(self, payments: List[Dict]) -> List[Alert]:
        """
        Check for failed payments

        Args:
            payments: List of payment dictionaries

        Returns:
            List of Alert objects
        """
        alerts = []

        failed_payments = [p for p in payments if p.get('status') == 'failed']

        if len(failed_payments) > 0:
            failed_txs = [p.get('tx_hash', 'N/A') for p in failed_payments]

            alerts.append(Alert(
                severity=AlertSeverity.HIGH,
                type="payment_failures",
                message=f"❌ FAILED PAYMENTS: {len(failed_payments)} payment(s) failed",
                action="Review failed transactions",
                details={"failed_count": len(failed_payments), "failed_txs": failed_txs}
            ))

        return alerts

    def check_high_spending(self, spent_24h: float, average_payment: float, payment_count: int) -> List[Alert]:
        """
        Check for unusually high spending

        Args:
            spent_24h: Amount spent in last 24 hours
            average_payment: Average payment amount
            payment_count: Total payment count

        Returns:
            List of Alert objects
        """
        alerts = []

        # Only alert if we have enough history
        if payment_count < 5:
            return alerts

        # Alert if 24h spending is > 10x average
        if spent_24h > average_payment * 10:
            alerts.append(Alert(
                severity=AlertSeverity.MEDIUM,
                type="high_spending",
                message=f"📈 High Spending: ${spent_24h:.2f} spent in 24h (10x average)",
                action="Verify spending is intentional",
                details={"spent_24h": spent_24h, "average_payment": average_payment, "multiplier": spent_24h / average_payment}
            ))

        return alerts

    def check_no_activity(self, payments_24h: int, total_payments: int) -> List[Alert]:
        """
        Check for no recent activity

        Args:
            payments_24h: Payments in last 24 hours
            total_payments: Total payments ever

        Returns:
            List of Alert objects
        """
        alerts = []

        # Only alert if there's historical activity but none recently
        if total_payments > 0 and payments_24h == 0:
            alerts.append(Alert(
                severity=AlertSeverity.LOW,
                type="no_activity",
                message="ℹ️  No payments in last 24 hours",
                action="Normal - no action needed",
                details={"total_payments": total_payments, "payments_24h": payments_24h}
            ))

        return alerts

    def check_all(
        self,
        budget_total: float,
        budget_remaining: float,
        mandates: List[Dict],
        payments: List[Dict],
        spent_24h: float,
        average_payment: float,
        payments_24h: int
    ) -> List[Alert]:
        """
        Run all alert checks

        Returns:
            List of all Alert objects
        """
        all_alerts = []

        all_alerts.extend(self.check_budget_alerts(budget_total, budget_remaining))
        all_alerts.extend(self.check_mandate_expiration(mandates))
        all_alerts.extend(self.check_payment_failures(payments))
        all_alerts.extend(self.check_high_spending(spent_24h, average_payment, len(payments)))
        all_alerts.extend(self.check_no_activity(payments_24h, len(payments)))

        # Sort by severity
        severity_order = {
            AlertSeverity.CRITICAL: 0,
            AlertSeverity.HIGH: 1,
            AlertSeverity.MEDIUM: 2,
            AlertSeverity.LOW: 3
        }

        all_alerts.sort(key=lambda a: severity_order[a.severity])

        self.alerts = all_alerts
        return all_alerts

    def get_alert_summary(self) -> Dict[str, int]:
        """Get count of alerts by severity"""
        summary = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "total": len(self.alerts)
        }

        for alert in self.alerts:
            summary[alert.severity.value] += 1

        return summary
