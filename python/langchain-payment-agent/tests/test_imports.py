#!/usr/bin/env python3
"""
Test all imports work correctly.

This test validates that all required dependencies are installed
and can be imported without errors.

Usage:
    pytest tests/test_imports.py
"""

import sys
import pytest


def test_agentgatepay_sdk_import():
    """Test AgentGatePay SDK can be imported"""
    try:
        from agentgatepay_sdk import AgentGatePay
        from agentgatepay_sdk.exceptions import (
            RateLimitError,
            AuthenticationError,
            MandateExpiredError
        )
        assert True
    except ImportError as e:
        pytest.fail(f"AgentGatePay SDK import failed: {e}")


def test_langchain_imports():
    """Test LangChain imports"""
    try:
        from langchain.agents import Tool, AgentExecutor, create_react_agent
        from langchain.prompts import PromptTemplate
        from langchain_openai import ChatOpenAI
        assert True
    except ImportError as e:
        pytest.fail(f"LangChain import failed: {e}")


def test_web3_imports():
    """Test Web3 imports"""
    try:
        from web3 import Web3
        from eth_account import Account
        assert True
    except ImportError as e:
        pytest.fail(f"Web3 import failed: {e}")


def test_flask_import():
    """Test Flask import (for seller agent)"""
    try:
        from flask import Flask, request, jsonify
        assert True
    except ImportError as e:
        pytest.fail(f"Flask import failed: {e}")


def test_dotenv_import():
    """Test python-dotenv import"""
    try:
        from dotenv import load_dotenv
        assert True
    except ImportError as e:
        pytest.fail(f"python-dotenv import failed: {e}")


def test_requests_import():
    """Test requests import"""
    try:
        import requests
        assert True
    except ImportError as e:
        pytest.fail(f"requests import failed: {e}")


def test_sdk_version():
    """Test AgentGatePay SDK version is >= 1.1.3"""
    try:
        import agentgatepay_sdk
        version = agentgatepay_sdk.__version__

        # Parse version
        major, minor, patch = map(int, version.split('.'))

        # Check >= 1.1.3
        assert major >= 1, f"SDK major version too old: {version}"
        if major == 1:
            assert minor >= 1, f"SDK minor version too old: {version}"
            if minor == 1:
                assert patch >= 3, f"SDK patch version too old: {version} (requires >= 1.1.3)"

        print(f"✅ AgentGatePay SDK version: {version}")

    except ImportError:
        pytest.skip("AgentGatePay SDK not installed")
    except AttributeError:
        pytest.skip("SDK version not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
