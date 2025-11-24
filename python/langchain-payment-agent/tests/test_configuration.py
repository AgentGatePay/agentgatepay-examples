#!/usr/bin/env python3
"""
Test environment configuration.

This test validates that configuration files exist and
environment variables are properly set.

Usage:
    pytest tests/test_configuration.py
"""

import os
import pytest
from pathlib import Path


def test_dotenv_example_exists():
    """Test .env.example file exists"""
    example_file = Path(__file__).parent.parent / ".env.example"
    assert example_file.exists(), ".env.example file not found"


def test_requirements_txt_exists():
    """Test requirements.txt file exists"""
    req_file = Path(__file__).parent.parent / "requirements.txt"
    assert req_file.exists(), "requirements.txt file not found"


def test_requirements_has_agentgatepay():
    """Test requirements.txt includes agentgatepay-sdk>=1.1.3"""
    req_file = Path(__file__).parent.parent / "requirements.txt"
    content = req_file.read_text()
    assert "agentgatepay-sdk>=1.1.3" in content, "requirements.txt missing agentgatepay-sdk>=1.1.3"


def test_examples_directory_exists():
    """Test examples directory exists"""
    examples_dir = Path(__file__).parent.parent / "examples"
    assert examples_dir.exists(), "examples/ directory not found"
    assert examples_dir.is_dir(), "examples/ is not a directory"


def test_all_example_files_exist():
    """Test all example files exist"""
    examples_dir = Path(__file__).parent.parent / "examples"

    required_files = [
        "1_api_basic_payment.py",
        "2a_api_buyer_agent.py",
        "2b_api_seller_agent.py",
        "3_api_with_audit.py",
        "4_mcp_basic_payment.py",
    ]

    for filename in required_files:
        filepath = examples_dir / filename
        assert filepath.exists(), f"Example file not found: {filename}"


def test_dotenv_template_has_required_vars():
    """Test .env.example has all required variables"""
    example_file = Path(__file__).parent.parent / ".env.example"
    content = example_file.read_text()

    required_vars = [
        "AGENTPAY_API_URL",
        "BUYER_API_KEY",
        "SELLER_API_KEY",
        "BASE_RPC_URL",
        "BUYER_PRIVATE_KEY",
        "BUYER_WALLET",
        "SELLER_WALLET",
        "OPENAI_API_KEY",
    ]

    for var in required_vars:
        assert var in content, f".env.example missing required variable: {var}"


def test_example_files_are_executable():
    """Test example files have shebang"""
    examples_dir = Path(__file__).parent.parent / "examples"

    for py_file in examples_dir.glob("*.py"):
        content = py_file.read_text()
        assert content.startswith("#!/usr/bin/env python3"), f"{py_file.name} missing shebang"


def test_no_hardcoded_secrets():
    """Test examples don't have hardcoded secrets"""
    examples_dir = Path(__file__).parent.parent / "examples"

    dangerous_patterns = [
        "pk_live_",  # API keys
        "0x" + "a" * 64,  # Private keys (example pattern)
        "sk-",  # OpenAI keys
    ]

    for py_file in examples_dir.glob("*.py"):
        content = py_file.read_text()

        for pattern in dangerous_patterns:
            # Allow pattern in comments/strings explaining format
            if pattern in content:
                # Check it's not in an actual assignment
                lines_with_pattern = [line for line in content.split('\n') if pattern in line]
                for line in lines_with_pattern:
                    stripped = line.strip()
                    # Skip comments and docstrings
                    if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
                        continue
                    # Skip .env.example references
                    if ".env.example" in line or "YOUR_" in line or "pk_live_YOUR" in line:
                        continue
                    # If we get here, might be a real secret
                    if '=' in stripped and not stripped.startswith('#'):
                        pytest.fail(f"Possible hardcoded secret in {py_file.name}: {line[:50]}...")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
