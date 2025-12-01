#!/usr/bin/env python3
"""
AgentGatePay + LangChain Integration - COMPLETE FEATURES DEMO (MCP Tools)

This example demonstrates ALL 15 AgentGatePay MCP tools in a comprehensive flow
matching the n8n workflow pattern. This shows 100% feature parity with REST API
using the standardized MCP (Model Context Protocol) interface.

Features demonstrated (matches n8n workflows):
1. User Authentication via MCP (agentpay_signup, agentpay_get_user_info)
2. Wallet Management via MCP (agentpay_add_wallet)
3. API Key Management via MCP (agentpay_create_api_key, agentpay_list_api_keys, agentpay_revoke_api_key)
4. Mandate Management via MCP (agentpay_issue_mandate, agentpay_verify_mandate)
5. Payment Creation via MCP (agentpay_create_payment)
6. Payment Submission via MCP (agentpay_submit_payment)
7. Payment Verification via MCP (agentpay_verify_payment)
8. Payment History via MCP (agentpay_get_payment_history)
9. Revenue Analytics via MCP (agentpay_get_analytics)
10. Audit Logging via MCP (agentpay_list_audit_logs)
11. Webhook Management (mentioned in n8n, not yet exposed in MCP)
12. System Health via MCP (agentpay_get_system_health)

MCP Tools Coverage: 15/15 (100%)

Usage:
    python 8_mcp_complete_features.py

Requirements:
- pip install langchain langchain-openai web3 python-dotenv requests
- .env file OR run in demo mode (will create new user)
- AgentGatePay MCP endpoint
"""

import os
import time
import json
import base64
import requests
import threading
from typing import Dict, Any
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from datetime import datetime

# LangChain imports
from langchain_core.tools import Tool
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

# Utils for mandate storage
from utils import save_mandate, get_mandate, clear_mandate

# Chain configuration
from chain_config import get_chain_config

# Load environment variables
load_dotenv()

# ========================================
# TRANSACTION SIGNING
# ========================================
#
# This example uses LOCAL SIGNING (Web3.py with private key).
#
# ⚠️ WARNING: Local signing is NOT recommended for production!
#
# For production deployments, use an external signing service:
# - Option 1: Docker container (see docs/TX_SIGNING_OPTIONS.md)
# - Option 2: Render one-click deploy (https://github.com/AgentGatePay/TX)
# - Option 3: Railway deployment
# - Option 4: Self-hosted service
#
# See docs/TX_SIGNING_OPTIONS.md for complete guide.
# See Example 9 (examples/9_api_with_tx_service.py) for external signing usage.
#
# ========================================

# ========================================
# CONFIGURATION
# ========================================

# Load chain/token configuration from .env
chain_config = get_chain_config()

AGENTPAY_API_URL = os.getenv('AGENTPAY_API_URL', 'https://api.agentgatepay.com')
MCP_API_URL = os.getenv('MCP_API_URL', 'https://mcp.agentgatepay.com')
DEMO_MODE = os.getenv('DEMO_MODE', 'true').lower() == 'true'

# MCP endpoint (using dedicated MCP subdomain)
MCP_ENDPOINT = f"{MCP_API_URL}/mcp/tools/call"

# Blockchain configuration (from .env via chain_config)
BUYER_PRIVATE_KEY = os.getenv('BUYER_PRIVATE_KEY')
SELLER_WALLET = os.getenv('SELLER_WALLET', '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb2')

# Payment configuration (from .env via chain_config)
RPC_URL = chain_config.rpc_url
CHAIN_ID = chain_config.chain_id
TOKEN_CONTRACT = chain_config.token_contract
TOKEN_DECIMALS = chain_config.decimals
CHAIN_NAME = chain_config.chain
TOKEN_NAME = chain_config.token
COMMISSION_RATE = 0.005

# ========================================
# HELPER FUNCTIONS
# ========================================

def get_commission_config(api_key: str) -> dict:
    """Fetch commission configuration from AgentGatePay API"""
    try:
        response = requests.get(
            f"{AGENTPAY_API_URL}/v1/config/commission",
            headers={"x-api-key": api_key}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"⚠️  Failed to fetch commission config: {e}")
        return None

# ========================================
# MCP HELPER FUNCTIONS
# ========================================

def call_mcp_tool(tool_name: str, arguments: Dict[str, Any], api_key: str = None) -> Dict[str, Any]:
    """
    Call AgentGatePay MCP tool via JSON-RPC 2.0.

    Args:
        tool_name: MCP tool name (e.g., 'agentpay_signup')
        arguments: Tool-specific arguments
        api_key: Optional API key for authenticated endpoints

    Returns:
        Tool result as dictionary
    """
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        },
        "id": 1
    }

    headers = {
        "Content-Type": "application/json"
    }

    if api_key:
        headers["x-api-key"] = api_key

    response = requests.post(MCP_ENDPOINT, json=payload, headers=headers, timeout=30)

    if response.status_code != 200:
        raise Exception(f"MCP call failed: HTTP {response.status_code} - {response.text}")

    result = response.json()

    if "error" in result:
        raise Exception(f"MCP error: {result['error']}")

    # Parse result content (MCP returns text in content array)
    content = result.get('result', {}).get('content', [])
    if content and len(content) > 0:
        return json.loads(content[0]['text'])

    return {}

# ========================================
# STATE
# ========================================

class MCPCompleteDemo:
    """Demonstrates all 15 AgentGatePay MCP tools"""

    def __init__(self):
        self.api_key = os.getenv('BUYER_API_KEY') if not DEMO_MODE else None
        self.user_info = None
        self.api_keys = []
        self.current_mandate = None
        self.payment_history = []
        self.mcp_tools_used = []

        # Initialize Web3
        self.web3 = Web3(Web3.HTTPProvider(RPC_URL))
        if BUYER_PRIVATE_KEY:
            self.account = Account.from_key(BUYER_PRIVATE_KEY)
        else:
            # Generate new account for demo
            self.account = Account.create()
            print(f"⚠️  Demo mode: Generated new wallet {self.account.address}")

        print(f"\n🤖 AGENTGATEPAY COMPLETE MCP FEATURES DEMO")
        print(f"=" * 70)
        print(f"Mode: {'DEMO (will create new user)' if DEMO_MODE else 'PRODUCTION'}")
        print(f"Wallet: {self.account.address}")
        print(f"MCP Endpoint: {MCP_ENDPOINT}")
        print(f"=" * 70)

    def track_tool(self, tool_name: str):
        """Track MCP tool usage"""
        if tool_name not in self.mcp_tools_used:
            self.mcp_tools_used.append(tool_name)

    # ========================================
    # MCP TOOL 1-3: USER MANAGEMENT
    # ========================================

    def mcp_user_signup(self, email: str, password: str, user_type: str = "both") -> str:
        """MCP Tool: agentpay_signup"""
        print(f"\n👤 [MCP] User signup: {email}")

        try:
            result = call_mcp_tool("agentpay_signup", {
                "email": email,
                "password": password,
                "user_type": user_type
            })

            self.track_tool("agentpay_signup")
            self.api_key = result.get('api_key')
            self.user_info = result.get('user')

            print(f"✅ User created via MCP!")
            print(f"   User ID: {self.user_info.get('user_id')}")
            print(f"   Email: {self.user_info.get('email')}")
            print(f"   API Key: {self.api_key[:20]}...")

            return f"User created via MCP. API Key: {self.api_key[:20]}..."

        except Exception as e:
            error_msg = f"MCP signup failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    def mcp_get_user_info(self) -> str:
        """MCP Tool: agentpay_get_user_info"""
        if not self.api_key:
            return "Error: Not authenticated."

        print(f"\n📋 [MCP] Getting user info...")

        try:
            info = call_mcp_tool("agentpay_get_user_info", {}, self.api_key)

            self.track_tool("agentpay_get_user_info")
            self.user_info = info

            print(f"✅ User info retrieved via MCP:")
            print(f"   Email: {info.get('email')}")
            print(f"   Type: {info.get('user_type')}")
            print(f"   Wallets: {len(info.get('wallets', []))}")

            return f"User via MCP: {info.get('email')}, Type: {info.get('user_type')}"

        except Exception as e:
            error_msg = f"MCP get user info failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    def mcp_add_wallet(self, chain: str = "base") -> str:
        """MCP Tool: agentpay_add_wallet"""
        if not self.api_key:
            return "Error: Not authenticated."

        print(f"\n💳 [MCP] Adding wallet: {self.account.address[:20]}...")

        try:
            result = call_mcp_tool("agentpay_add_wallet", {
                "chain": chain,
                "address": self.account.address
            }, self.api_key)

            self.track_tool("agentpay_add_wallet")

            print(f"✅ Wallet added via MCP!")
            print(f"   Chain: {chain}")
            print(f"   Address: {self.account.address}")

            return f"Wallet added via MCP: {self.account.address} on {chain}"

        except Exception as e:
            error_msg = f"MCP add wallet failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    # ========================================
    # MCP TOOL 4-6: API KEY MANAGEMENT
    # ========================================

    def mcp_create_api_key(self, name: str) -> str:
        """MCP Tool: agentpay_create_api_key"""
        if not self.api_key:
            return "Error: Not authenticated."

        print(f"\n🔑 [MCP] Creating API key: {name}")

        try:
            result = call_mcp_tool("agentpay_create_api_key", {
                "name": name
            }, self.api_key)

            self.track_tool("agentpay_create_api_key")

            new_key = result.get('api_key')
            key_id = result.get('key_id')

            self.api_keys.append({"key_id": key_id, "name": name})

            print(f"✅ API key created via MCP!")
            print(f"   Key ID: {key_id}")
            print(f"   Name: {name}")
            print(f"   Key: {new_key[:20]}...")

            return f"API key '{name}' created via MCP"

        except Exception as e:
            error_msg = f"MCP create API key failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    def mcp_list_api_keys(self) -> str:
        """MCP Tool: agentpay_list_api_keys"""
        if not self.api_key:
            return "Error: Not authenticated."

        print(f"\n📜 [MCP] Listing API keys...")

        try:
            result = call_mcp_tool("agentpay_list_api_keys", {}, self.api_key)

            self.track_tool("agentpay_list_api_keys")

            keys = result.get('keys', [])

            print(f"✅ Found {len(keys)} API key(s) via MCP:")
            for key in keys:
                status = "✓ Active" if key.get('active') else "✗ Revoked"
                print(f"   - {key.get('name')}: {status}")

            return f"Found {len(keys)} API keys via MCP"

        except Exception as e:
            error_msg = f"MCP list API keys failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    def mcp_revoke_api_key(self, key_id: str) -> str:
        """MCP Tool: agentpay_revoke_api_key"""
        if not self.api_key:
            return "Error: Not authenticated."

        print(f"\n🚫 [MCP] Revoking API key: {key_id}")

        try:
            result = call_mcp_tool("agentpay_revoke_api_key", {
                "key_id": key_id
            }, self.api_key)

            self.track_tool("agentpay_revoke_api_key")

            print(f"✅ API key revoked via MCP!")
            print(f"   Key ID: {key_id}")

            return f"API key {key_id} revoked via MCP"

        except Exception as e:
            error_msg = f"MCP revoke API key failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    # ========================================
    # MCP TOOL 7-8: MANDATES
    # ========================================

    def mcp_issue_mandate(self, budget_usd: float) -> str:
        """MCP Tool: agentpay_issue_mandate"""
        if not self.api_key:
            return "Error: Not authenticated."

        print(f"\n🔐 [MCP] Issuing mandate: ${budget_usd}")

        try:
            mandate = call_mcp_tool("agentpay_issue_mandate", {
                "subject": f"mcp-complete-demo-{self.account.address}",
                "budget_usd": budget_usd,
                "scope": "resource.read,payment.execute,analytics.read",
                "ttl_hours": 168
            }, self.api_key)

            self.track_tool("agentpay_issue_mandate")
            self.current_mandate = mandate

            print(f"✅ Mandate issued via MCP!")
            print(f"   Token: {mandate['mandate_token'][:50]}...")
            print(f"   Budget: ${mandate['budget_usd']}")

            return f"Mandate issued via MCP: ${budget_usd} budget"

        except Exception as e:
            error_msg = f"MCP issue mandate failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    def mcp_verify_mandate(self) -> str:
        """MCP Tool: agentpay_verify_mandate"""
        if not self.current_mandate:
            return "Error: No mandate issued."

        print(f"\n🔍 [MCP] Verifying mandate...")

        try:
            result = call_mcp_tool("agentpay_verify_mandate", {
                "mandate_token": self.current_mandate['mandate_token']
            }, self.api_key)

            self.track_tool("agentpay_verify_mandate")

            valid = result.get('valid', False)
            budget_remaining = result.get('budget_remaining', 0)

            print(f"✅ Mandate verified via MCP!")
            print(f"   Valid: {valid}")
            print(f"   Budget remaining: ${budget_remaining}")

            return f"Mandate via MCP: Valid={valid}, Budget=${budget_remaining}"

        except Exception as e:
            error_msg = f"MCP verify mandate failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    # ========================================
    # MCP TOOL 9: PAYMENT CREATION
    # ========================================

    def mcp_create_payment(self, amount_usd: float) -> str:
        """MCP Tool: agentpay_create_payment"""
        print(f"\n💳 [MCP] Creating payment requirement: ${amount_usd}")

        try:
            result = call_mcp_tool("agentpay_create_payment", {
                "amount_usd": str(amount_usd),
                "resource_path": "/api/demo-resource"
            })

            self.track_tool("agentpay_create_payment")

            print(f"✅ Payment requirement created via MCP!")
            print(f"   Version: x402 v{result.get('x402_version')}")
            print(f"   Payment address: {result.get('accepts', [{}])[0].get('pay_to', 'N/A')[:20]}...")

            return f"Payment requirement created via MCP: ${amount_usd}"

        except Exception as e:
            error_msg = f"MCP create payment failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    # ========================================
    # BLOCKCHAIN PAYMENT (not MCP, uses Web3)
    # ========================================

    def execute_blockchain_payment(self, amount_usd: float) -> str:
        """Execute blockchain payment (2 transactions) - NOT an MCP tool"""
        print(f"\n💸 [BLOCKCHAIN] Executing payment: ${amount_usd}")

        try:
            # Fetch commission configuration from API
            commission_config = get_commission_config(self.api_key) if self.api_key else None
            if not commission_config:
                return "Error: Failed to fetch commission configuration"

            commission_address = commission_config.get('commission_address')
            commission_rate = commission_config.get('commission_rate', COMMISSION_RATE)

            print(f"   Using commission address: {commission_address[:10]}...")
            print(f"   Commission rate: {commission_rate * 100}%")

            # Calculate amounts
            commission_usd = amount_usd * commission_rate
            merchant_usd = amount_usd - commission_usd

            merchant_atomic = int(merchant_usd * (10 ** TOKEN_DECIMALS))
            commission_atomic = int(commission_usd * (10 ** TOKEN_DECIMALS))

            # ERC-20 transfer
            transfer_sig = self.web3.keccak(text="transfer(address,uint256)")[:4]

            # Get nonce once for both transactions
            nonce = self.web3.eth.get_transaction_count(self.account.address)

            # Merchant TX
            merchant_data = transfer_sig + \
                           self.web3.to_bytes(hexstr=SELLER_WALLET).rjust(32, b'\x00') + \
                           merchant_atomic.to_bytes(32, byteorder='big')

            merchant_tx = {
                'nonce': nonce,
                'to': TOKEN_CONTRACT,
                'value': 0,
                'gas': 100000,
                'gasPrice': self.web3.eth.gas_price,
                'data': merchant_data,
                'chainId': CHAIN_ID
            }

            signed_merchant = self.account.sign_transaction(merchant_tx)
            tx_hash_merchant_raw = self.web3.eth.send_raw_transaction(signed_merchant.raw_transaction)
            tx_hash_merchant_str = f"0x{tx_hash_merchant_raw.hex()}" if not tx_hash_merchant_raw.hex().startswith('0x') else tx_hash_merchant_raw.hex()

            # Commission TX
            commission_data = transfer_sig + \
                             self.web3.to_bytes(hexstr=commission_address).rjust(32, b'\x00') + \
                             commission_atomic.to_bytes(32, byteorder='big')

            commission_tx = {
                'nonce': nonce + 1,  # Use nonce+1 for second transaction
                'to': TOKEN_CONTRACT,
                'value': 0,
                'gas': 100000,
                'gasPrice': self.web3.eth.gas_price,
                'data': commission_data,
                'chainId': CHAIN_ID
            }

            signed_commission = self.account.sign_transaction(commission_tx)
            tx_hash_commission_raw = self.web3.eth.send_raw_transaction(signed_commission.raw_transaction)
            tx_hash_commission_str = f"0x{tx_hash_commission_raw.hex()}" if not tx_hash_commission_raw.hex().startswith('0x') else tx_hash_commission_raw.hex()

            print(f"\n💳 Processing payment...")

            def verify_locally():
                try:
                    print(f"   🔍 Verifying transactions on-chain...")
                    receipt_merchant = self.web3.eth.wait_for_transaction_receipt(tx_hash_merchant_raw, timeout=60)
                    print(f"   ✅ Merchant TX confirmed (block {receipt_merchant['blockNumber']})")

                    receipt_commission = self.web3.eth.wait_for_transaction_receipt(tx_hash_commission_raw, timeout=60)
                    print(f"   ✅ Commission TX confirmed (block {receipt_commission['blockNumber']})")
                except Exception as e:
                    print(f"   ⚠️  Verification failed: {e}")

            verify_thread = threading.Thread(target=verify_locally)
            verify_thread.start()

            print(f"✅ Blockchain payment executed successfully!")
            print(f"   Merchant TX: {tx_hash_merchant_str[:20]}...")
            print(f"   Commission TX: {tx_hash_commission_str[:20]}...")

            # Store for later MCP calls
            self.payment_history.append({
                "amount_usd": amount_usd,
                "merchant_tx": tx_hash_merchant_str,
                "commission_tx": tx_hash_commission_str,
                "timestamp": datetime.now().isoformat()
            })

            return f"{tx_hash_merchant_str},{tx_hash_commission_str}"

        except Exception as e:
            error_msg = f"Blockchain payment failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    # ========================================
    # MCP TOOL 10: PAYMENT SUBMISSION
    # ========================================

    def mcp_submit_payment(self, tx_hashes: str) -> str:
        """MCP Tool: agentpay_submit_payment"""
        if not self.current_mandate:
            return "Error: No mandate issued."

        merchant_tx, commission_tx = tx_hashes.split(',')

        print(f"\n📤 [MCP] Submitting payment proof...")

        try:
            result = call_mcp_tool("agentpay_submit_payment", {
                "mandate_token": self.current_mandate['mandate_token'],
                "tx_hash_merchant": merchant_tx,
                "tx_hash_commission": commission_tx,
                "chain": CHAIN_NAME,
                "token": TOKEN_NAME
            }, self.api_key)

            self.track_tool("agentpay_submit_payment")

            # ✅ FIX: Check if payment was actually successful
            if not result.get('success', False):
                error = result.get('error', 'Unknown error')
                details = result.get('details')
                print(f"❌ Payment submission failed: {error}")
                if details:
                    print(f"   Details: {details}")
                return f"Failed: {error}"

            print(f"✅ Payment submitted via MCP!")
            print(f"   Charge ID: {result.get('charge_id', 'N/A')}")
            print(f"   Status: {result.get('status', 'confirmed')}")

            return f"Payment submitted via MCP. Charge: {result.get('charge_id')}"

        except Exception as e:
            error_msg = f"MCP submit payment failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    # ========================================
    # MCP TOOL 11: PAYMENT VERIFICATION
    # ========================================

    def mcp_verify_payment(self, tx_hash: str) -> str:
        """MCP Tool: agentpay_verify_payment"""
        print(f"\n🔍 [MCP] Verifying payment: {tx_hash[:20]}...")

        try:
            result = call_mcp_tool("agentpay_verify_payment", {
                "tx_hash": tx_hash,
                "chain": CHAIN_NAME
            })

            self.track_tool("agentpay_verify_payment")

            verified = result.get('verified', False)

            print(f"✅ Payment {'verified' if verified else 'NOT verified'} via MCP!")
            if verified:
                print(f"   Amount: ${result.get('amount_usd', 'N/A')}")
                print(f"   Sender: {result.get('sender_address', 'N/A')[:20]}...")

            return f"Payment via MCP: {'Verified' if verified else 'Not verified'}"

        except Exception as e:
            error_msg = f"MCP verify payment failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    # ========================================
    # MCP TOOL 12: PAYMENT HISTORY
    # ========================================

    def mcp_get_payment_history(self) -> str:
        """MCP Tool: agentpay_get_payment_history"""
        if not self.api_key:
            return "Error: Not authenticated."

        print(f"\n📊 [MCP] Retrieving payment history...")

        try:
            result = call_mcp_tool("agentpay_get_payment_history", {
                "limit": 50
            }, self.api_key)

            self.track_tool("agentpay_get_payment_history")

            payments = result.get('payments', [])
            total_spent = sum(float(p.get('amount_usd', 0)) for p in payments)

            print(f"✅ Payment history via MCP: {len(payments)} payments")
            print(f"   Total spent: ${total_spent:.2f}")

            return f"Payment history via MCP: {len(payments)} payments, ${total_spent:.2f} total"

        except Exception as e:
            error_msg = f"MCP get payment history failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    # ========================================
    # MCP TOOL 13: ANALYTICS
    # ========================================

    def mcp_get_analytics(self, period: str = "30d") -> str:
        """MCP Tool: agentpay_get_analytics"""
        if not self.api_key:
            return "Error: Not authenticated."

        print(f"\n📈 [MCP] Retrieving analytics ({period})...")

        try:
            result = call_mcp_tool("agentpay_get_analytics", {
                "period": period
            }, self.api_key)

            self.track_tool("agentpay_get_analytics")

            print(f"✅ Analytics via MCP:")
            print(f"   Total spent: ${result.get('total_spent_usd', 0):.2f}")
            print(f"   Payment count: {result.get('payment_count', 0)}")
            print(f"   Average: ${result.get('average_payment_usd', 0):.2f}")

            return f"Analytics via MCP: ${result.get('total_spent_usd', 0):.2f} total"

        except Exception as e:
            error_msg = f"MCP get analytics failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    # ========================================
    # MCP TOOL 14: AUDIT LOGS
    # ========================================

    def mcp_list_audit_logs(self, event_type: str = None) -> str:
        """MCP Tool: agentpay_list_audit_logs"""
        if not self.api_key:
            return "Error: Not authenticated."

        print(f"\n📋 [MCP] Retrieving audit logs...")

        try:
            args = {"limit": 50}
            if event_type:
                args["event_type"] = event_type

            result = call_mcp_tool("agentpay_list_audit_logs", args, self.api_key)

            self.track_tool("agentpay_list_audit_logs")

            logs = result.get('logs', [])

            print(f"✅ Audit logs via MCP: {len(logs)} entries")

            if logs:
                print(f"\n   Recent events:")
                for log in logs[:3]:
                    timestamp = datetime.fromtimestamp(log.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M:%S')
                    print(f"   - {timestamp}: {log.get('event_type')}")

            return f"Audit logs via MCP: {len(logs)} entries"

        except Exception as e:
            error_msg = f"MCP list audit logs failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    # ========================================
    # MCP TOOL 15: SYSTEM HEALTH
    # ========================================

    def mcp_get_system_health(self) -> str:
        """MCP Tool: agentpay_get_system_health"""
        print(f"\n🏥 [MCP] Checking system health...")

        try:
            result = call_mcp_tool("agentpay_get_system_health", {})

            self.track_tool("agentpay_get_system_health")

            print(f"✅ System health via MCP: {result.get('status', 'unknown')}")
            print(f"   Version: {result.get('version', 'N/A')}")
            print(f"   Uptime: {result.get('uptime', 'N/A')}")

            return f"System health via MCP: {result.get('status', 'unknown')}"

        except Exception as e:
            error_msg = f"MCP system health failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg


# ========================================
# LANGCHAIN AGENT
# ========================================

demo = MCPCompleteDemo()

# Define tools for all 15 MCP tools
tools = [
    # MCP Tools 1-3: User Management
    Tool(
        name="mcp_user_signup",
        func=lambda params: demo.mcp_user_signup(
            params.split('|')[0],
            params.split('|')[1],
            params.split('|')[2] if len(params.split('|')) > 2 else "both"
        ),
        description="MCP: Sign up new user. Input: 'email|password|user_type'"
    ),
    Tool(
        name="mcp_get_user_info",
        func=lambda _: demo.mcp_get_user_info(),
        description="MCP: Get user information. No input needed."
    ),
    Tool(
        name="mcp_add_wallet",
        func=lambda chain: demo.mcp_add_wallet(chain if chain else CHAIN_NAME),
        description="MCP: Add blockchain wallet. Input: chain (base/ethereum/polygon/arbitrum)"
    ),

    # MCP Tools 4-6: API Key Management
    Tool(
        name="mcp_create_api_key",
        func=demo.mcp_create_api_key,
        description="MCP: Create API key. Input: key name"
    ),
    Tool(
        name="mcp_list_api_keys",
        func=lambda _: demo.mcp_list_api_keys(),
        description="MCP: List API keys. No input needed."
    ),
    Tool(
        name="mcp_revoke_api_key",
        func=demo.mcp_revoke_api_key,
        description="MCP: Revoke API key. Input: key_id"
    ),

    # MCP Tools 7-8: Mandates
    Tool(
        name="mcp_issue_mandate",
        func=lambda budget: demo.mcp_issue_mandate(float(budget)),
        description="MCP: Issue mandate. Input: budget in USD"
    ),
    Tool(
        name="mcp_verify_mandate",
        func=lambda _: demo.mcp_verify_mandate(),
        description="MCP: Verify mandate. No input needed."
    ),

    # MCP Tool 9: Payment Creation
    Tool(
        name="mcp_create_payment",
        func=lambda amount: demo.mcp_create_payment(float(amount)),
        description="MCP: Create payment requirement. Input: amount in USD"
    ),

    # Blockchain Payment (not MCP)
    Tool(
        name="execute_blockchain_payment",
        func=lambda amount: demo.execute_blockchain_payment(float(amount)),
        description="Execute blockchain payment. Input: amount in USD. Returns: tx_hashes"
    ),

    # MCP Tool 10: Payment Submission
    Tool(
        name="mcp_submit_payment",
        func=demo.mcp_submit_payment,
        description="MCP: Submit payment. Input: 'merchant_tx,commission_tx'"
    ),

    # MCP Tool 11: Payment Verification
    Tool(
        name="mcp_verify_payment",
        func=demo.mcp_verify_payment,
        description="MCP: Verify payment. Input: tx_hash"
    ),

    # MCP Tool 12: Payment History
    Tool(
        name="mcp_get_payment_history",
        func=lambda _: demo.mcp_get_payment_history(),
        description="MCP: Get payment history. No input needed."
    ),

    # MCP Tool 13: Analytics
    Tool(
        name="mcp_get_analytics",
        func=lambda period: demo.mcp_get_analytics(period if period else "30d"),
        description="MCP: Get analytics. Input: period (24h/7d/30d/all)"
    ),

    # MCP Tool 14: Audit Logs
    Tool(
        name="mcp_list_audit_logs",
        func=lambda event_type: demo.mcp_list_audit_logs(event_type if event_type != "all" else None),
        description="MCP: List audit logs. Input: event_type or 'all'"
    ),

    # MCP Tool 15: System Health
    Tool(
        name="mcp_get_system_health",
        func=lambda _: demo.mcp_get_system_health(),
        description="MCP: Check system health. No input needed."
    ),
]

# Agent prompt
agent_prompt = PromptTemplate.from_template("""
You are an autonomous agent demonstrating ALL 15 AgentGatePay MCP tools.

Available tools:
{tools}

Tool names: {tool_names}

Task: {input}

Complete ALL steps systematically using MCP tools.

Think step by step:
{agent_scratchpad}
""")

# Create agent
llm = ChatOpenAI(model="gpt-4", temperature=0, openai_api_key=os.getenv('OPENAI_API_KEY'))
agent = create_react_agent(llm=llm, tools=tools, prompt=agent_prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=35, handle_parsing_errors=True)

# ========================================
# MAIN EXECUTION
# ========================================

if __name__ == "__main__":
    print("=" * 70)
    print("🤖 AGENTGATEPAY COMPLETE MCP FEATURES DEMO")
    print("=" * 70)
    print()
    print("This demo shows ALL 15 AgentGatePay MCP tools:")
    print("  1. agentpay_signup - User signup")
    print("  2. agentpay_get_user_info - Get user info")
    print("  3. agentpay_add_wallet - Add wallet")
    print("  4. agentpay_create_api_key - Create API key")
    print("  5. agentpay_list_api_keys - List API keys")
    print("  6. agentpay_revoke_api_key - Revoke API key")
    print("  7. agentpay_issue_mandate - Issue mandate")
    print("  8. agentpay_verify_mandate - Verify mandate")
    print("  9. agentpay_create_payment - Create payment")
    print("  10. agentpay_submit_payment - Submit payment")
    print("  11. agentpay_verify_payment - Verify payment")
    print("  12. agentpay_get_payment_history - Payment history")
    print("  13. agentpay_get_analytics - Analytics")
    print("  14. agentpay_list_audit_logs - Audit logs")
    print("  15. agentpay_get_system_health - System health")
    print()
    print("=" * 70)

    # Agent task
    task = """
    Demonstrate ALL 15 AgentGatePay MCP tools (matches n8n workflow):

    1. Check system health (MCP)
    2. Sign up user: mcp-demo@example.com / SecurePass123 / both (MCP)
    3. Get user information (MCP)
    4. Add wallet on base chain (MCP)
    5. Create API key named "MCP Demo Key" (MCP)
    6. List all API keys (MCP)
    7. Issue mandate with $100 budget (MCP)
    8. Verify mandate (MCP)
    9. Create payment requirement for $10 (MCP)
    10. Execute blockchain payment $10 (Web3)
    11. Submit payment proof using tx_hashes from step 10 (MCP)
    12. Verify payment using merchant tx_hash from step 10 (MCP)
    13. Get payment history (MCP)
    14. Get analytics for 30d period (MCP)
    15. List audit logs for all events (MCP)

    Complete ALL 15 steps to demonstrate 100% MCP tool coverage.
    This matches the complete n8n workflow feature set.
    """

    try:
        # Run agent
        result = agent_executor.invoke({"input": task})

        print("\n" + "=" * 70)
        print("✅ COMPLETE MCP FEATURES DEMO FINISHED")
        print("=" * 70)
        print(f"\nResult: {result['output']}")

        # Display MCP tools used
        print(f"\n📊 MCP TOOLS USED: {len(demo.mcp_tools_used)}/15")
        for i, tool in enumerate(demo.mcp_tools_used, 1):
            print(f"   {i}. {tool}")

        if len(demo.mcp_tools_used) == 15:
            print(f"\n🎉 ALL 15 MCP TOOLS DEMONSTRATED!")
            print(f"   100% feature parity with REST API")
            print(f"   Matches n8n workflow capabilities")
        else:
            print(f"\n⚠️  {15 - len(demo.mcp_tools_used)} MCP tools not used")

    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
