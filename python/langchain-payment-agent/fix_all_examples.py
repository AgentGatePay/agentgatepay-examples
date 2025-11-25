#!/usr/bin/env python3
"""
Automated fix script for all Python examples
Applies critical fixes across all 9 example scripts
"""
import re
from pathlib import Path

EXAMPLES_DIR = Path(__file__).parent / "examples"

# Fix patterns
FIXES = [
    # 1. Fix imports - LangChain Tool import
    (
        r'from langchain\.agents import Tool,',
        'from langchain_core.tools import Tool\nfrom langchain.agents import'
    ),
    # 2. Add time import if missing
    (
        r'(import os\n)(?!import time)',
        r'import os\nimport time\n'
    ),
    # 3. Add utils import after langchain imports
    (
        r'(from langchain\.prompts import PromptTemplate)\n\n(# Load environment)',
        r'\1\n\n# Utils for mandate storage\nfrom utils import save_mandate, get_mandate, clear_mandate\n\n\2'
    ),
    # 4. Fix SDK API - budget_usd to budget
    (
        r'budget_usd=',
        'budget='
    ),
    # 5. Fix SDK API - ttl_hours to ttl_minutes (multiply by 60)
    (
        r'ttl_hours=(\d+)',
        lambda m: f'ttl_minutes={int(m.group(1)) * 60}'
    ),
    # 6. Fix Web3 API - rawTransaction to raw_transaction
    (
        r'\.rawTransaction',
        '.raw_transaction'
    ),
    # 7. Fix amounts - change $10 to $0.01
    (
        r'RESOURCE_PRICE_USD = 10\.0',
        'RESOURCE_PRICE_USD = 0.01'
    ),
    (
        r'"price_usd": 10\.0',
        '"price_usd": 0.01'
    ),
    # 8. Fix scope - wildcard to explicit permissions
    (
        r'scope="\*"',
        'scope="resource.read,payment.execute"'
    ),
    # 9. Fix mandate response keys - mandateToken to mandate_token
    (
        r"mandate\['mandateToken'\]",
        "mandate['mandate_token']"
    ),
    (
        r"mandate\.get\('mandateToken'",
        "mandate.get('mandate_token'"
    ),
    # 10. Fix budget keys
    (
        r"mandate\['budgetUsd'\]",
        "mandate['budget_usd']"
    ),
    (
        r"mandate\.get\('budgetUsd'",
        "mandate.get('budget_usd'"
    ),
    (
        r"mandate\.get\('budgetRemaining'",
        "mandate.get('budget_remaining'"
    ),
    # 11. Fix expires_at key
    (
        r"mandate\['expiresAt'\]",
        "mandate['expires_at']"
    ),
]

# Add nonce sleep after first TX
NONCE_FIX = """        # Get fresh nonce after first TX confirms
        time.sleep(2)

        # Transaction 2: Commission payment"""

def apply_fixes(file_path: Path):
    """Apply all fixes to a file"""
    print(f"\nFixing {file_path.name}...")

    content = file_path.read_text()
    original_content = content

    # Apply regex fixes
    for pattern, replacement in FIXES:
        if callable(replacement):
            content = re.sub(pattern, replacement, content)
        else:
            content = re.sub(pattern, replacement, content)

    # Add nonce sleep if not present
    if 'time.sleep(2)' not in content and 'commission payment' in content.lower():
        content = content.replace(
            '\n        # Transaction 2: Commission payment',
            f'\n{NONCE_FIX}'
        )

    # Write back if changed
    if content != original_content:
        file_path.write_text(content)
        print(f"  ✅ Fixed {file_path.name}")
        return True
    else:
        print(f"  ⏭️  No changes needed for {file_path.name}")
        return False

def main():
    print("=" * 70)
    print("🔧 FIXING ALL PYTHON EXAMPLES")
    print("=" * 70)

    files_to_fix = [
        "1_api_basic_payment.py",
        "2a_api_buyer_agent.py",
        "2b_api_seller_agent.py",
        "3_api_with_audit.py",
        "4_mcp_basic_payment.py",
        "5_mcp_buyer_seller.py",
        "6_mcp_with_audit.py",
        "7_api_complete_features.py",
        "8_mcp_complete_features.py",
    ]

    fixed_count = 0
    for filename in files_to_fix:
        file_path = EXAMPLES_DIR / filename
        if file_path.exists():
            if apply_fixes(file_path):
                fixed_count += 1
        else:
            print(f"  ❌ File not found: {filename}")

    print(f"\n{'=' * 70}")
    print(f"✅ FIXED {fixed_count}/{len(files_to_fix)} FILES")
    print("=" * 70)

if __name__ == "__main__":
    main()
