#!/usr/bin/env python3
"""
AgentGatePay + LangChain Integration - BUYER AGENT (MCP TOOLS)

This is the BUYER side of the marketplace interaction using MCP tools.
Run the seller agent FIRST (4b_mcp_seller_agent.py), then run this buyer.

The buyer agent:
- Autonomously discovers resources from seller APIs
- Issues payment mandates via MCP tools
- Signs blockchain transactions (2 TX: merchant + commission)
- Submits payment proofs via MCP tools
- Retrieves purchased resources

Usage:
    # Make sure seller is running first!
    python 4b_mcp_seller_agent.py  # In another terminal

    # Then run buyer
    python 4a_mcp_buyer_agent.py

Requirements:
- pip install langchain langchain-openai web3 python-dotenv
- .env file with BUYER_API_KEY, BUYER_PRIVATE_KEY, BUYER_WALLET
- Seller API running on http://localhost:8000
"""

import os
import sys
import time
import json
import base64
import requests
import threading
from typing import Dict, Any
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account

# LangChain imports (LangChain 1.x compatible)
from langchain_core.tools import Tool, StructuredTool
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

# Add parent directory to path for utils import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Utils for mandate storage
from utils import save_mandate, get_mandate, clear_mandate

# Chain configuration from .env
from chain_config import get_chain_config, ChainConfig

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

AGENTPAY_API_URL = os.getenv('AGENTPAY_API_URL', 'https://api.agentgatepay.com')
MCP_API_URL = os.getenv('MCP_API_URL', 'https://mcp.agentgatepay.com')
BUYER_API_KEY = os.getenv('BUYER_API_KEY')
BUYER_PRIVATE_KEY = os.getenv('BUYER_PRIVATE_KEY')

# Seller API URL (can be changed to discover from multiple sellers)
SELLER_API_URL = os.getenv('SELLER_API_URL', 'http://localhost:8000')

# Payment configuration
MANDATE_BUDGET_USD = float(os.getenv('MANDATE_BUDGET_USD', 100.0))

# Chain/token configuration - loaded from .env in main()
CHAIN_CONFIG = None  # Set in main() from chain_config

# ========================================
# MCP HELPER FUNCTIONS
# ========================================

def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call AgentGatePay MCP tool via JSON-RPC 2.0 protocol.

    Args:
        tool_name: MCP tool name (e.g., 'agentpay_issue_mandate')
        arguments: Tool-specific arguments

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
        "Content-Type": "application/json",
        "x-api-key": BUYER_API_KEY
    }

    response = requests.post(MCP_API_URL, json=payload, headers=headers, timeout=30)

    if response.status_code != 200:
        raise Exception(f"MCP call failed: HTTP {response.status_code} - {response.text}")

    result = response.json()

    if "error" in result:
        raise Exception(f"MCP error: {result['error']}")

    # MCP response format: result.content[0].text (JSON string)
    content_text = result['result']['content'][0]['text']
    return json.loads(content_text)


# ========================================
# BUYER AGENT CLASS
# ========================================

class BuyerAgent:
    """
    Autonomous buyer agent that discovers and purchases resources.

    Features:
    - Resource discovery from seller APIs
    - AP2 mandate management
    - Blockchain payment signing
    - Multi-seller support
    """

    def __init__(self, config: ChainConfig):
        # Store chain/token config
        self.config = config

        # Initialize Web3 with config RPC
        self.web3 = Web3(Web3.HTTPProvider(config.rpc_url))
        self.account = Account.from_key(BUYER_PRIVATE_KEY)

        # State
        self.current_mandate = None
        self.last_payment = None
        self.discovered_resources = []

        print(f"\n🤖 BUYER AGENT INITIALIZED")
        print(f"=" * 60)
        print(f"Wallet: {self.account.address}")
        print(f"Chain: {config.chain.upper()} (ID: {config.chain_id})")
        print(f"Token: {config.token} ({config.decimals} decimals)")
        print(f"RPC: {config.rpc_url[:50]}...")
        print(f"API URL: {AGENTPAY_API_URL}")
        print(f"Seller API: {SELLER_API_URL}")
        print(f"=" * 60)

    def get_commission_config(self) -> dict:
        """Fetch live commission configuration from AgentGatePay API"""
        try:
            response = requests.get(
                f"{AGENTPAY_API_URL}/v1/config/commission",
                headers={"x-api-key": BUYER_API_KEY}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"⚠️  Failed to fetch commission config: {e}")
            return None

    def decode_mandate_token(self, token: str) -> dict:
        """Decode AP2 mandate token to extract payload"""
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return {}
            payload_b64 = parts[1]
            # Add padding if needed
            padding = 4 - (len(payload_b64) % 4)
            if padding != 4:
                payload_b64 += '=' * padding
            payload_json = base64.urlsafe_b64decode(payload_b64)
            return json.loads(payload_json)
        except:
            return {}

    def issue_mandate(self, budget_usd: float, ttl_minutes: int = 10080, purpose: str = "general purchases") -> str:
        """Issue AP2 payment mandate and fetch live budget"""
        print(f"\n🔐 [BUYER] Issuing mandate with ${budget_usd} budget for {ttl_minutes} minutes...")
        print(f"   Purpose: {purpose}")

        try:
            # Check if mandate already exists
            agent_id = f"buyer-agent-{self.account.address}"
            existing_mandate = get_mandate(agent_id)

            if existing_mandate:
                token = existing_mandate.get('mandate_token')

                # Get LIVE budget from gateway
                print(f"   🔍 Fetching live budget from API...")
                verify_response = requests.post(
                    f"{AGENTPAY_API_URL}/mandates/verify",
                    headers={"x-api-key": BUYER_API_KEY, "Content-Type": "application/json"},
                    json={"mandate_token": token}
                )

                if verify_response.status_code == 200:
                    verify_data = verify_response.json()
                    budget_remaining = verify_data.get('budget_remaining', 'Unknown')
                else:
                    token_data = self.decode_mandate_token(token)
                    budget_remaining = token_data.get('budget_remaining', existing_mandate.get('budget_usd', 'Unknown'))

                print(f"♻️  Reusing existing mandate (Budget: ${budget_remaining})")
                self.current_mandate = existing_mandate
                self.current_mandate['budget_remaining'] = budget_remaining
                return f"MANDATE_TOKEN:{token}"

            # Create new mandate via MCP
            mandate = call_mcp_tool("agentpay_issue_mandate", {
                "subject": agent_id,
                "budget_usd": budget_usd,
                "scope": "resource.read,payment.execute",
                "ttl_minutes": ttl_minutes
            })

            # Fetch live budget from API
            token = mandate['mandate_token']
            print(f"   🔍 Fetching live budget from API...")
            verify_response = requests.post(
                f"{AGENTPAY_API_URL}/mandates/verify",
                headers={"x-api-key": BUYER_API_KEY, "Content-Type": "application/json"},
                json={"mandate_token": token}
            )

            if verify_response.status_code == 200:
                verify_data = verify_response.json()
                budget_remaining = verify_data.get('budget_remaining', budget_usd)
            else:
                token_data = self.decode_mandate_token(token)
                budget_remaining = token_data.get('budget_remaining', str(budget_usd))

            mandate_with_budget = {
                **mandate,
                'budget_usd': budget_usd,
                'budget_remaining': budget_remaining,
                'purpose': purpose  # Store purpose for future runs
            }

            self.current_mandate = mandate_with_budget
            save_mandate(agent_id, mandate_with_budget)

            print(f"✅ Mandate issued successfully")
            print(f"   Token: {mandate['mandate_token'][:50]}...")
            print(f"   Budget: ${budget_usd}")
            print(f"   Purpose: {purpose}")

            return f"MANDATE_TOKEN:{token}"

        except Exception as e:
            error_msg = f"Failed to issue mandate: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    def discover_catalog(self, seller_url: str) -> str:
        """Discover resource catalog from seller"""
        print(f"\n🔍 [BUYER] Discovering catalog from: {seller_url}")

        try:
            response = requests.get(f"{seller_url}/catalog", timeout=10)

            if response.status_code == 200:
                catalog = response.json()
                self.discovered_resources = catalog.get('catalog', [])

                print(f"✅ Discovered {len(self.discovered_resources)} resources:")
                for res in self.discovered_resources:
                    print(f"   - {res['name']} (${res['price_usd']}) [ID: {res['id']}]")

                # Return detailed resource info with IDs for agent to parse
                resources_list = []
                for res in self.discovered_resources:
                    resources_list.append(f"ID: '{res['id']}', Name: '{res['name']}', Price: ${res['price_usd']}, Description: '{res['description']}'")

                return f"Found {len(self.discovered_resources)} resources:\n" + "\n".join(resources_list) + f"\n\nIMPORTANT: Use the 'ID' field (e.g., 'market-data-api') when calling request_resource, NOT the name or description."

            else:
                error_msg = f"Catalog discovery failed: HTTP {response.status_code}"
                print(f"❌ {error_msg}")
                return error_msg

        except Exception as e:
            error_msg = f"Catalog discovery error: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    def request_resource(self, resource_id: str) -> str:
        """Request resource and get payment requirements"""
        print(f"\n📋 [BUYER] Requesting resource: {resource_id}")

        try:
            response = requests.get(
                f"{SELLER_API_URL}/resource",
                params={"resource_id": resource_id},
                timeout=10
            )

            if response.status_code == 402:
                # Payment required
                data = response.json()
                payment_info = data.get('payment_info', {})

                print(f"💳 Payment required:")
                print(f"   Resource: {data['resource']['name']}")
                print(f"   Price: ${data['resource']['price_usd']}")
                print(f"   Recipient: {payment_info['recipient_wallet'][:20]}...")

                # Store payment info for later
                self.last_payment = {
                    "resource_id": resource_id,
                    "resource_name": data['resource']['name'],
                    "price_usd": data['resource']['price_usd'],
                    "recipient": payment_info['recipient_wallet'],
                    "commission_address": payment_info['commission_address'],
                    "commission_rate": payment_info['commission_rate']
                }

                return f"Resource '{data['resource']['name']}' costs ${data['resource']['price_usd']}. Payment required to access."

            elif response.status_code == 200:
                # Already paid (shouldn't happen on first request)
                print(f"✅ Resource already accessed")
                return f"Resource accessed successfully"

            elif response.status_code == 404:
                error = response.json().get('error', 'Resource not found')
                print(f"❌ {error}")
                return f"Error: {error}"

            else:
                error = response.json().get('error', 'Unknown error')
                print(f"❌ Request failed: {error}")
                return f"Request failed: {error}"

        except Exception as e:
            error_msg = f"Resource request error: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    def execute_payment(self) -> str:
        """Sign blockchain payment AND submit to gateway (combined for speed)"""
        if not self.last_payment:
            return "Error: No payment request pending. Call request_resource first."

        if not self.current_mandate:
            return "Error: No mandate issued. Call issue_mandate first."

        payment_info = self.last_payment
        print(f"\n💳 [BUYER] Executing payment: ${payment_info['price_usd']} to {payment_info['recipient'][:10]}...")

        try:
            # Fetch live commission config
            commission_config = self.get_commission_config()
            if commission_config:
                commission_address = commission_config.get('commission_address')
                print(f"   ✅ Using live commission address: {commission_address[:10]}...")
            else:
                return "Error: Failed to fetch commission configuration"

            # Calculate amounts (using config decimals)
            total_usd = payment_info['price_usd']
            commission_rate = payment_info['commission_rate']
            commission_usd = total_usd * commission_rate
            merchant_usd = total_usd - commission_usd

            merchant_atomic = int(merchant_usd * (10 ** self.config.decimals))
            commission_atomic = int(commission_usd * (10 ** self.config.decimals))

            print(f"   Merchant: ${merchant_usd:.4f} ({merchant_atomic} atomic)")
            print(f"   Commission: ${commission_usd:.4f} ({commission_atomic} atomic)")

            # ERC-20 transfer function
            transfer_sig = self.web3.keccak(text="transfer(address,uint256)")[:4]

            # Get nonce ONCE before both transactions
            merchant_nonce = self.web3.eth.get_transaction_count(self.account.address)
            print(f"   📊 Current nonce: {merchant_nonce}")

            # TX 1: Merchant payment
            print(f"   📤 Signing merchant transaction...")
            merchant_data = transfer_sig + \
                           self.web3.to_bytes(hexstr=payment_info['recipient']).rjust(32, b'\x00') + \
                           merchant_atomic.to_bytes(32, byteorder='big')

            merchant_tx = {
                'nonce': merchant_nonce,
                'to': self.config.token_contract,
                'value': 0,
                'gas': 100000,
                'gasPrice': self.web3.eth.gas_price,
                'data': merchant_data,
                'chainId': self.config.chain_id
            }

            signed_merchant = self.account.sign_transaction(merchant_tx)
            tx_hash_merchant = self.web3.eth.send_raw_transaction(signed_merchant.raw_transaction)
            print(f"   ✅ Merchant TX sent: {tx_hash_merchant.hex()}")

            # TX 2: Commission payment (sign and send immediately - parallel execution)
            print(f"   📤 Signing commission transaction...")
            commission_data = transfer_sig + \
                             self.web3.to_bytes(hexstr=commission_address).rjust(32, b'\x00') + \
                             commission_atomic.to_bytes(32, byteorder='big')

            commission_tx = {
                'nonce': merchant_nonce + 1,
                'to': self.config.token_contract,
                'value': 0,
                'gas': 100000,
                'gasPrice': self.web3.eth.gas_price,
                'data': commission_data,
                'chainId': self.config.chain_id
            }

            signed_commission = self.account.sign_transaction(commission_tx)
            tx_hash_commission = self.web3.eth.send_raw_transaction(signed_commission.raw_transaction)
            print(f"   ✅ Commission TX sent: {tx_hash_commission.hex()}")

            # Store transaction hashes
            merchant_tx_hex = self.web3.to_hex(tx_hash_merchant)
            commission_tx_hex = self.web3.to_hex(tx_hash_commission)

            self.last_payment['merchant_tx'] = merchant_tx_hex
            self.last_payment['commission_tx'] = commission_tx_hex

            print(f"\n💳 Processing payment...")

            # Thread-safe container for gateway response
            gateway_result = {"response": None, "error": None}

            def submit_to_gateway():
                """Submit payment to gateway in parallel thread"""
                try:
                    print(f"   📤 Submitting payment to gateway...")
                    payment_payload = {
                        "scheme": "eip3009",
                        "tx_hash": merchant_tx_hex,
                        "tx_hash_commission": commission_tx_hex
                    }
                    payment_b64 = base64.b64encode(json.dumps(payment_payload).encode()).decode()

                    headers = {
                        "x-api-key": BUYER_API_KEY,
                        "x-mandate": self.current_mandate['mandate_token'],
                        "x-payment": payment_b64
                    }

                    url = f"{AGENTPAY_API_URL}/x402/resource?chain={self.config.chain}&token={self.config.token}&price_usd={total_usd}"
                    gateway_result["response"] = requests.get(url, headers=headers, timeout=120)
                    print(f"   ✅ Gateway response received")
                except Exception as e:
                    gateway_result["error"] = str(e)
                    print(f"   ❌ Gateway error: {e}")

            # Start gateway submission in parallel thread
            gateway_thread = threading.Thread(target=submit_to_gateway)
            gateway_thread.start()

            # Verify transactions on-chain (120s timeout for Ethereum public RPCs)
            print(f"   🔍 Verifying transactions on-chain...")
            try:
                receipt_merchant = self.web3.eth.wait_for_transaction_receipt(tx_hash_merchant, timeout=120)
                print(f"   ✅ Merchant TX confirmed (block {receipt_merchant['blockNumber']})")

                receipt_commission = self.web3.eth.wait_for_transaction_receipt(tx_hash_commission, timeout=120)
                print(f"   ✅ Commission TX confirmed (block {receipt_commission['blockNumber']})")
            except Exception as e:
                print(f"   ⚠️  Verification failed: {e}")

            # Wait for gateway thread to complete
            gateway_thread.join(timeout=90)  # Max 90 seconds for gateway

            if gateway_result["error"]:
                return f"Gateway error: {gateway_result['error']}"

            response = gateway_result["response"]
            if not response:
                return "Gateway timeout - please check payment status manually"

            if response.status_code >= 400:
                result = response.json() if response.text else {}
                error = result.get('error', response.text)
                print(f"❌ Gateway error ({response.status_code}): {error}")
                return f"Failed: {error}"

            result = response.json()
            print(f"   🔍 Gateway response: {result}")

            if result.get('message') or result.get('success') or result.get('paid') or result.get('status') in ['confirmed', 'pending']:
                status = result.get('status', 'unknown')
                if status == 'pending':
                    print(f"✅ Payment accepted (OPTIMISTIC MODE - pending background verification)")
                else:
                    print(f"✅ Payment recorded successfully")

                # Fetch updated budget
                print(f"   🔍 Fetching updated budget...")
                verify_response = requests.post(
                    f"{AGENTPAY_API_URL}/mandates/verify",
                    headers={"x-api-key": BUYER_API_KEY, "Content-Type": "application/json"},
                    json={"mandate_token": self.current_mandate['mandate_token']}
                )

                if verify_response.status_code == 200:
                    verify_data = verify_response.json()
                    new_budget = verify_data.get('budget_remaining', 'Unknown')
                    print(f"   ✅ Budget updated: ${new_budget}")

                    if self.current_mandate:
                        self.current_mandate['budget_remaining'] = new_budget
                        budget_allocated = verify_data.get('budget_allocated')
                        if budget_allocated is not None:
                            self.current_mandate['budget_usd'] = budget_allocated
                        agent_id = f"buyer-agent-{self.account.address}"
                        save_mandate(agent_id, self.current_mandate)

                    return f"Payment successful! Paid ${total_usd}, Budget remaining: ${new_budget}. IMPORTANT: Now call claim_resource to submit payment proof to seller and receive the resource."
                else:
                    return f"Payment successful! Paid ${total_usd}. IMPORTANT: Now call claim_resource to submit payment proof to seller and receive the resource."
            else:
                error = result.get('error', 'Unknown error')
                print(f"❌ Failed: {error}")
                return f"Failed: {error}"

        except Exception as e:
            error_msg = f"Payment failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    def claim_resource(self) -> str:
        """Claim resource by submitting payment proof (with retry logic for DynamoDB propagation delays)"""
        if not self.last_payment or 'merchant_tx' not in self.last_payment:
            return "Error: No payment executed. Call sign_and_pay first."

        payment_info = self.last_payment
        print(f"\n📦 [BUYER] Claiming resource: {payment_info['resource_name']}")

        # Retry claim up to 12 times with 10-second delays (handles gateway processing time)
        max_retries = 12
        retry_delay = 10

        for attempt in range(max_retries):
            try:
                # Submit payment proof to seller
                payment_header = f"{payment_info['merchant_tx']},{payment_info['commission_tx']}"

                response = requests.get(
                    f"{SELLER_API_URL}/resource",
                    params={"resource_id": payment_info['resource_id']},
                    headers={"x-payment": payment_header},
                    timeout=30  # Allow time for verification
                )

                if response.status_code == 200:
                    # SUCCESS - resource delivered
                    data = response.json()
                    print(f"✅ Resource delivered!")
                    print(f"   Resource: {payment_info['resource_name']}")
                    print(f"   Payment verified: {data['payment_confirmation']['amount_verified_usd']} USD")

                    # Store resource
                    self.last_payment['resource_data'] = data['resource']

                    return f"Resource '{payment_info['resource_name']}' received successfully! Payment verified: ${data['payment_confirmation']['amount_verified_usd']}"

                else:
                    error = response.json().get('error', 'Unknown error')

                    # If this is not the last attempt, retry after delay
                    if attempt < max_retries - 1:
                        print(f"⚠️  Claim attempt {attempt + 1} failed: {error}")
                        print(f"   Retrying in {retry_delay} seconds (payment may still be propagating)...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        # Last attempt failed
                        print(f"❌ Claim failed after {max_retries} attempts: {error}")
                        return f"Claim failed after {max_retries} retries: {error}. Payment was recorded, but seller couldn't verify it. Try claiming again manually."

            except Exception as e:
                # If this is not the last attempt, retry after delay
                if attempt < max_retries - 1:
                    print(f"⚠️  Claim attempt {attempt + 1} error: {str(e)}")
                    print(f"   Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                else:
                    # Last attempt failed
                    error_msg = f"Claim error after {max_retries} attempts: {str(e)}"
                    print(f"❌ {error_msg}")
                    return error_msg

        return "Claim failed: Maximum retries exceeded"


# ========================================
# LANGCHAIN AGENT
# ========================================

# Global variables (will be set in main())
buyer = None
mandate_ttl_minutes = 10080
mandate_purpose = "general purchases"

# ========================================
# MAIN
# ========================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🤖 BUYER AGENT - AUTONOMOUS RESOURCE PURCHASER")
    print("=" * 60)
    print()
    print("This agent autonomously discovers and purchases resources")
    print("from seller APIs using blockchain payments.")
    print()
    print("=" * 60)

    # ========================================
    # STEP 0: LOAD CHAIN AND TOKEN FROM .ENV
    # ========================================

    print("\n🔧 CHAIN & TOKEN CONFIGURATION")
    print("=" * 60)
    config = get_chain_config()

    print(f"\nUsing configuration from .env:")
    print(f"  Chain: {config.chain.title()} (ID: {config.chain_id})")
    print(f"  Token: {config.token} ({config.decimals} decimals)")
    print(f"  RPC: {config.rpc_url}")
    print(f"\nTo change: Edit PAYMENT_CHAIN and PAYMENT_TOKEN in .env file")
    print("=" * 60)

    # Initialize buyer agent (buyer is module-level, no global needed)
    buyer = BuyerAgent(config)

    # ========================================
    # STEP 1: CONFIGURE MANDATE FIRST
    # ========================================

    # Check for existing mandate
    agent_id = f"buyer-agent-{buyer.account.address}"
    existing_mandate = get_mandate(agent_id)

    if existing_mandate:
        token = existing_mandate.get('mandate_token')

        # Get LIVE budget from gateway
        verify_response = requests.post(
            f"{AGENTPAY_API_URL}/mandates/verify",
            headers={"x-api-key": BUYER_API_KEY, "Content-Type": "application/json"},
            json={"mandate_token": token}
        )

        if verify_response.status_code == 200:
            verify_data = verify_response.json()
            budget_remaining = verify_data.get('budget_remaining', 'Unknown')
        else:
            # Fallback to JWT if verify fails
            token_data = buyer.decode_mandate_token(token)
            budget_remaining = token_data.get('budget_remaining', existing_mandate.get('budget_usd', 'Unknown'))

        # Extract mandate purpose
        mandate_purpose = existing_mandate.get('purpose', 'general purchases')

        print(f"\n♻️  Using existing mandate")
        print(f"   Purpose: {mandate_purpose}")
        print(f"   Budget remaining: ${budget_remaining}")
        print(f"   Token: {existing_mandate.get('mandate_token', 'N/A')[:50]}...")
        print(f"   To delete: rm ../.agentgatepay_mandates.json\n")
        mandate_budget = float(budget_remaining) if budget_remaining != 'Unknown' else MANDATE_BUDGET_USD
        user_need = mandate_purpose  # Use mandate purpose for purchases
    else:
        budget_input = input("\n💰 Enter mandate budget in USD Coins (default: 100): ").strip()
        mandate_budget = float(budget_input) if budget_input else MANDATE_BUDGET_USD

        # Ask user for mandate TTL duration
        print(f"\n⏰ Set mandate duration (format: number + unit)")
        print(f"   Examples: 10m (10 minutes), 2h (2 hours), 7d (7 days)")
        ttl_input = input("   Enter duration (default: 7d): ").strip().lower()

        if not ttl_input:
            ttl_input = "7d"

        # Parse duration
        import re
        match = re.match(r'^(\d+)([mhd])$', ttl_input)

        if match:
            value = int(match.group(1))
            unit = match.group(2)

            if unit == 'm':
                mandate_ttl_minutes = value
                unit_name = "minutes"
            elif unit == 'h':
                mandate_ttl_minutes = value * 60
                unit_name = "hours"
            elif unit == 'd':
                mandate_ttl_minutes = value * 1440
                unit_name = "days"

            print(f"   ✅ Mandate will be valid for {value} {unit_name} ({mandate_ttl_minutes} minutes)")
        else:
            print(f"   ⚠️  Invalid format, using default: 7 days")
            mandate_ttl_minutes = 10080

        # Ask user for mandate PURPOSE - this defines what it can be spent on
        print(f"\n🎯 What is this mandate for? (This defines what resources can be purchased)")
        print(f"   Examples from our seller:")
        print(f"   1. Research papers and academic content")
        print(f"   2. Market data and API access")
        print(f"   3. AI training datasets")
        print(f"   Or enter custom purpose in natural language")
        purpose_input = input("\n   Enter mandate purpose (default: research papers): ").strip()

        if purpose_input in ['1']:
            user_need = "research papers and academic content"
        elif purpose_input in ['2']:
            user_need = "market data and API access"
        elif purpose_input in ['3']:
            user_need = "AI training datasets"
        elif purpose_input:
            user_need = purpose_input
        else:
            user_need = "research papers and academic content"

        print(f"   ✅ Mandate purpose: {user_need}")

        # Set global mandate_purpose for tool use
        mandate_purpose = user_need

    # Define tools after buyer is initialized
    tools = [
        Tool(
            name="issue_mandate",
            func=lambda budget: buyer.issue_mandate(float(budget), mandate_ttl_minutes, mandate_purpose),
            description="Issue AP2 payment mandate with specified budget (USD). Use FIRST before any purchases. Input: budget amount as number. Returns: MANDATE_TOKEN:{token}"
        ),
        Tool(
            name="discover_catalog",
            func=buyer.discover_catalog,
            description="Discover resource catalog from seller API. Input: seller_url (e.g., 'http://localhost:8000')"
        ),
        Tool(
            name="request_resource",
            func=buyer.request_resource,
            description="Request specific resource and get payment requirements. Input: resource_id string."
        ),
        StructuredTool.from_function(
            func=buyer.execute_payment,
            name="execute_payment",
            description="Execute blockchain payment (2 transactions) AND submit to gateway. No input needed. After this succeeds, you MUST call claim_resource to complete the purchase and get the resource."
        ),
        StructuredTool.from_function(
            func=buyer.claim_resource,
            name="claim_resource",
            description="Claim resource after payment by submitting payment proof to seller. No input needed."
        ),
    ]

    # System prompt for agent behavior
    system_prompt = """You are an autonomous buyer agent that discovers and purchases resources from sellers.

Workflow:
1. Issue mandate with budget - Returns MANDATE_TOKEN:{token}
2. Discover catalog from seller
3. Request ONE specific resource (gets payment requirements)
4. Execute payment - Signs blockchain TX AND submits to gateway (single step, optimized for speed)
5. Claim resource (submit payment proof to seller)

CRITICAL RULES:
- Buy ONE resource at a time (never request multiple resources simultaneously)
- Complete the full workflow (request → pay → claim) for one resource before considering another
- The execute_payment tool is optimized for micro-transactions - combines blockchain signing and gateway submission into ONE atomic operation

Think step by step and complete the workflow for ONE resource."""

    # Create LangChain agent
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key=os.getenv('OPENAI_API_KEY')
    )

    agent_executor = create_agent(
        llm,
        tools,
        system_prompt=system_prompt
    )

    # ========================================
    # STEP 2: CHECK SELLER AVAILABILITY
    # ========================================

    print(f"\n📡 Checking seller API: {SELLER_API_URL}")
    try:
        health = requests.get(f"{SELLER_API_URL}/health", timeout=5)
        if health.status_code == 200:
            print(f"✅ Seller API is running")
        else:
            print(f"⚠️  Seller API returned: HTTP {health.status_code}")
    except:
        print(f"❌ Seller API is NOT running!")
        print(f"   Please start the seller first: python 4b_mcp_seller_agent.py")
        exit(1)

    # ========================================
    # STEP 3: RUN AUTONOMOUS AGENT
    # ========================================

    # Agent task - let agent discover and choose autonomously
    task = f"""
    The user wants: "{user_need}"

    Your job is to autonomously find and purchase the best matching resource.

    Steps:
    1. Issue a mandate with ${mandate_budget} budget
    2. Discover the catalog from {SELLER_API_URL}
    3. Analyze the catalog and identify which resource best matches: "{user_need}"
    4. Request that resource to get payment details - USE THE 'ID' FIELD FROM CATALOG
    5. If price is acceptable (under ${mandate_budget}), execute payment (fast - one step!)
    6. Claim the resource by submitting payment proof to seller

    CRITICAL INSTRUCTIONS FOR STEP 4:
    - The catalog returns resources in this format:
      ID: 'market-data-api', Name: 'Premium Market Data API Access', Price: $5.0
    - When you call request_resource, you MUST use the 'ID' field (e.g., 'market-data-api')
    - DO NOT use the name, description, or purpose text
    - Example: request_resource('market-data-api') ✓
    - Example: request_resource('market data and API access') ✗ WRONG

    Choose the resource whose name/description best matches "{user_need}", then use its ID.
    """

    try:
        # Run agent (LangGraph format expects messages)
        result = agent_executor.invoke({"messages": [("user", task)]})

        print("\n" + "=" * 60)
        print("✅ BUYER AGENT COMPLETED")
        print("=" * 60)

        # Extract final message from LangGraph response
        if "messages" in result:
            final_message = result["messages"][-1].content if result["messages"] else "No output"
            print(f"\nResult: {final_message}")
        else:
            print(f"\nResult: {result}")

        # Display final status
        if buyer.current_mandate:
            print(f"\n📊 Final Status:")
            print(f"   Budget remaining: ${buyer.current_mandate.get('budget_remaining', 'N/A')}")

        if buyer.last_payment and 'merchant_tx' in buyer.last_payment:
            print(f"   Merchant TX: {config.explorer}/tx/{buyer.last_payment['merchant_tx']}")
            print(f"   Commission TX: {config.explorer}/tx/{buyer.last_payment['commission_tx']}")

            # Display gateway audit logs with curl commands
            print(f"\nGateway Audit Logs (copy-paste these commands):")
            print(f"\n# All payment logs (by wallet):")
            print(f"curl '{AGENTPAY_API_URL}/audit/logs?client_id={buyer.account.address}&event_type=x402_payment_settled&limit=10' \\")
            print(f"  -H 'x-api-key: {BUYER_API_KEY}' | python3 -m json.tool")
            print(f"\n# Recent payments (24h):")
            print(f"curl '{AGENTPAY_API_URL}/audit/logs?client_id={buyer.account.address}&event_type=x402_payment_settled&hours=24' \\")
            print(f"  -H 'x-api-key: {BUYER_API_KEY}' | python3 -m json.tool")
            print(f"\n# Payment verification (by tx_hash):")
            print(f"curl '{AGENTPAY_API_URL}/v1/payments/verify/{buyer.last_payment['merchant_tx']}' \\")
            print(f"  -H 'x-api-key: {BUYER_API_KEY}' | python3 -m json.tool")

        if buyer.last_payment and 'resource_data' in buyer.last_payment:
            print(f"\n📦 Received Resource:")
            resource = buyer.last_payment['resource_data']

            # Display resource data based on type (different resources have different fields)
            if 'title' in resource:
                # Research paper format
                print(f"   Title: {resource.get('title')}")
                print(f"   Authors: {', '.join(resource.get('authors', []))}")
                if 'abstract' in resource:
                    print(f"   Abstract: {resource.get('abstract')[:100]}...")
                if 'pdf_url' in resource:
                    print(f"   PDF: {resource.get('pdf_url')}")
            elif 'service' in resource:
                # API service format
                print(f"   Service: {resource.get('service')}")
                print(f"   Base URL: {resource.get('base_url')}")
                print(f"   API Key: {resource.get('api_key')}")
                print(f"   Rate Limit: {resource.get('rate_limit')}")
            elif 'name' in resource:
                # Dataset format
                print(f"   Name: {resource.get('name')}")
                print(f"   Samples: {resource.get('samples', 'N/A')}")
                if 'format' in resource:
                    print(f"   Format: {resource.get('format')}")
                if 'download_url' in resource:
                    print(f"   Download: {resource.get('download_url')}")
            else:
                # Generic format (fallback)
                print(f"   Data: {resource}")

    except KeyboardInterrupt:
        print("\n\n⚠️  Buyer agent interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
