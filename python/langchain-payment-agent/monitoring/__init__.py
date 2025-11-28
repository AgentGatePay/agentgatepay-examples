"""
AgentGatePay Monitoring Module

Provides monitoring, analytics, and reporting capabilities for AgentGatePay payments.

Components:
- config: Chain/token configuration loader
- dashboard: MonitoringDashboard class for analytics
- alerts: Alert engine for warnings and notifications
- exports: CSV/JSON export functionality
"""

from .config import ChainConfig, load_config, save_config, get_supported_chains, get_supported_tokens
from .dashboard import MonitoringDashboard
from .alerts import AlertEngine, Alert, AlertSeverity
from .exports import CSVExporter, JSONExporter

__version__ = "1.0.0"
__all__ = [
    "ChainConfig",
    "load_config",
    "save_config",
    "get_supported_chains",
    "get_supported_tokens",
    "MonitoringDashboard",
    "AlertEngine",
    "Alert",
    "AlertSeverity",
    "CSVExporter",
    "JSONExporter",
]
