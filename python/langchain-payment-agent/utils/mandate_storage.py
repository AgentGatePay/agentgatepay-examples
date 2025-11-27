"""
Simple mandate storage - stores mandate tokens to reuse across runs
"""
import json
import os
from datetime import datetime
from pathlib import Path

STORAGE_FILE = Path(__file__).parent.parent / ".agentgatepay_mandates.json"

def save_mandate(agent_id: str, mandate_data: dict):
    """Save mandate for reuse"""
    storage = _load_storage()
    storage[agent_id] = {
        'mandate_token': mandate_data.get('mandate_token'),
        'expires_at': mandate_data.get('expires_at'),
        'budget_remaining': mandate_data.get('budget_remaining') or mandate_data.get('budget_usd'),
        'budget_usd': mandate_data.get('budget_usd'),
        'saved_at': datetime.now().isoformat()
    }
    _save_storage(storage)

def get_mandate(agent_id: str) -> dict:
    """Get stored mandate if valid"""
    storage = _load_storage()
    if agent_id not in storage:
        return None

    mandate = storage[agent_id]
    expires_at = mandate.get('expires_at', 0)

    if datetime.now().timestamp() > expires_at:
        del storage[agent_id]
        _save_storage(storage)
        return None

    return mandate

def clear_mandate(agent_id: str):
    """Clear stored mandate"""
    storage = _load_storage()
    if agent_id in storage:
        del storage[agent_id]
        _save_storage(storage)

def _load_storage() -> dict:
    if not STORAGE_FILE.exists():
        return {}
    try:
        return json.loads(STORAGE_FILE.read_text())
    except:
        return {}

def _save_storage(data: dict):
    STORAGE_FILE.write_text(json.dumps(data, indent=2))
