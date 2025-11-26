#!/usr/bin/env python3
"""
AgentGatePay + LangChain Integration - BUYER AGENT (REST API)

This is the BUYER side of the marketplace interaction.
Run the seller agent FIRST (2b_api_seller_agent.py), then run this buyer.

The buyer agent:
- Autonomously discovers resources from seller APIs
- Issues payment mandates with budget control
- Signs blockchain transactions (2 TX: merchant + commission)
- Submits payment proofs to sellers
- Retrieves purchased resources

Usage:
    # Make sure seller is running first!
    python 2b_api_seller_agent.py  # In another terminal

    # Then run buyer
    python 2a_api_buyer_agent.py

Requirements:
- pip install agentgatepay-sdk>=1.1.3 langchain langchain-openai web3 python-dotenv
- .env file with BUYER_API_KEY, BUYER_PRIVATE_KEY, BUYER_WALLET
- Seller API running on http://localhost:8000
"""

import os
import sys
import time
import json
import base64
import requests
from typing import Dict, Any
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from agentgatepay_sdk import AgentGatePay

# LangChain imports (LangChain 1.x compatible)
from langchain_core.tools import Tool
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

# Add parent directory to path for utils import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Utils for mandate storage
from utils import save_mandate, get_mandate, clear_mandate

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
BUYER_API_KEY = os.getenv('BUYER_API_KEY')
BASE_RPC_URL = os.getenv('BASE_RPC_URL', 'https://mainnet.base.org')
BUYER_PRIVATE_KEY = os.getenv('BUYER_PRIVATE_KEY')

# Seller API URL (can be changed to discover from multiple sellers)
SELLER_API_URL = os.getenv('SELLER_API_URL', 'http://localhost:8000')

# Payment configuration
MANDATE_BUDGET_USD = float(os.getenv('MANDATE_BUDGET_USD', 100.0))

# USDC contract on Base
USDC_CONTRACT_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
USDC_DECIMALS = 6

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

    def __init__(self):
        # Initialize AgentGatePay client
        self.agentpay = AgentGatePay(
            api_url=AGENTPAY_API_URL,
            api_key=BUYER_API_KEY
        )

        # Initialize Web3
        self.web3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))
        self.account = Account.from_key(BUYER_PRIVATE_KEY)

        # State
        self.current_mandate = None
        self.last_payment = None
        self.discovered_resources = []

        print(f"\n🤖 BUYER AGENT INITIALIZED")
        print(f"=" * 60)
        print(f"Wallet: {self.account.address}")
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

    def issue_mandate(self, budget_usd: float, ttl_minutes: int = 10080) -> str:
        """Issue AP2 payment mandate and fetch live budget"""
        print(f"\n🔐 [BUYER] Issuing mandate with ${budget_usd} budget for {ttl_minutes} minutes...")

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
                    # Fallback to JWT if verify fails
                    token_data = self.decode_mandate_token(token)
                    budget_remaining = token_data.get('budget_remaining', existing_mandate.get('budget_usd', 'Unknown'))

                print(f"♻️  Reusing existing mandate (Budget: ${budget_remaining})")
                self.current_mandate = existing_mandate
                self.current_mandate['budget_remaining'] = budget_remaining
                return f"MANDATE_TOKEN:{token}"

            # Create new mandate
            mandate = self.agentpay.mandates.issue(
                subject=agent_id,
                budget=budget_usd,
                scope="resource.read,payment.execute",
                ttl_minutes=ttl_minutes
            )

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
                # Fallback to JWT decode
                token_data = self.decode_mandate_token(token)
                budget_remaining = token_data.get('budget_remaining', str(budget_usd))

            # Store with decoded budget (SDK doesn't return budget_usd, so we add it)
            mandate_with_budget = {
                **mandate,
                'budget_usd': budget_usd,
                'budget_remaining': budget_remaining
            }

            self.current_mandate = mandate_with_budget
            save_mandate(agent_id, mandate_with_budget)

            print(f"✅ Mandate issued successfully")
            print(f"   Token: {mandate['mandate_token'][:50]}...")
            print(f"   Budget: ${budget_usd}")
            print(f"   Remaining: ${budget_remaining}")

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
                    print(f"   - {res['name']} (${res['price_usd']})")

                return f"Found {len(self.discovered_resources)} resources. Total catalog value: ${sum(r['price_usd'] for r in self.discovered_resources):.2f}"

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

    def sign_and_pay(self) -> str:
        """Sign blockchain payment (2 transactions) but DON'T submit to gateway"""
        if not self.last_payment:
            return "Error: No payment request pending. Call request_resource first."

        if not self.current_mandate:
            return "Error: No mandate issued. Call issue_mandate first."

        payment_info = self.last_payment
        print(f"\n💳 [BUYER] Signing payment: ${payment_info['price_usd']} to {payment_info['recipient'][:10]}...")

        try:
            # Fetch live commission config
            commission_config = self.get_commission_config()
            if commission_config:
                commission_address = commission_config.get('commission_address')
                print(f"   ✅ Using live commission address: {commission_address[:10]}...")
            else:
                return "Error: Failed to fetch commission configuration"

            # Calculate amounts
            total_usd = payment_info['price_usd']
            commission_rate = payment_info['commission_rate']
            commission_usd = total_usd * commission_rate
            merchant_usd = total_usd - commission_usd

            merchant_atomic = int(merchant_usd * (10 ** USDC_DECIMALS))
            commission_atomic = int(commission_usd * (10 ** USDC_DECIMALS))

            print(f"   Merchant: ${merchant_usd:.4f} ({merchant_atomic} atomic)")
            print(f"   Commission: ${commission_usd:.4f} ({commission_atomic} atomic)")

            # ERC-20 transfer function
            transfer_sig = self.web3.keccak(text="transfer(address,uint256)")[:4]

            # TX 1: Merchant payment
            print(f"   📤 Signing merchant transaction...")
            merchant_data = transfer_sig + \
                           self.web3.to_bytes(hexstr=payment_info['recipient']).rjust(32, b'\x00') + \
                           merchant_atomic.to_bytes(32, byteorder='big')

            merchant_tx = {
                'nonce': self.web3.eth.get_transaction_count(self.account.address),
                'to': USDC_CONTRACT_BASE,
                'value': 0,
                'gas': 100000,
                'gasPrice': self.web3.eth.gas_price,
                'data': merchant_data,
                'chainId': 8453  # Base mainnet
            }

            signed_merchant = self.account.sign_transaction(merchant_tx)
            tx_hash_merchant = self.web3.eth.send_raw_transaction(signed_merchant.raw_transaction)
            print(f"   ✅ Merchant TX sent: {tx_hash_merchant.hex()}")

            # Wait for confirmation
            print(f"   ⏳ Waiting for confirmation...")
            receipt_merchant = self.web3.eth.wait_for_transaction_receipt(tx_hash_merchant, timeout=60)
            print(f"   ✅ Confirmed in block {receipt_merchant['blockNumber']}")

            # TX 2: Commission payment
            print(f"   📤 Signing commission transaction...")
            commission_data = transfer_sig + \
                             self.web3.to_bytes(hexstr=commission_address).rjust(32, b'\x00') + \
                             commission_atomic.to_bytes(32, byteorder='big')

            commission_tx = {
                'nonce': self.web3.eth.get_transaction_count(self.account.address),
                'to': USDC_CONTRACT_BASE,
                'value': 0,
                'gas': 100000,
                'gasPrice': self.web3.eth.gas_price,
                'data': commission_data,
                'chainId': 8453
            }

            signed_commission = self.account.sign_transaction(commission_tx)
            tx_hash_commission = self.web3.eth.send_raw_transaction(signed_commission.raw_transaction)
            print(f"   ✅ Commission TX sent: {tx_hash_commission.hex()}")

            # Wait for confirmation
            receipt_commission = self.web3.eth.wait_for_transaction_receipt(tx_hash_commission, timeout=60)
            print(f"   ✅ Confirmed in block {receipt_commission['blockNumber']}")

            # Store transaction hashes
            self.last_payment['merchant_tx'] = tx_hash_merchant.hex()
            self.last_payment['commission_tx'] = tx_hash_commission.hex()

            # Return formatted for submit_payment tool
            mandate_token = self.current_mandate['mandate_token']
            price_usd = payment_info['price_usd']
            return f"TX_HASHES:{tx_hash_merchant.hex()},{tx_hash_commission.hex()},{mandate_token},{price_usd}"

        except Exception as e:
            error_msg = f"Payment failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    def submit_payment(self, payment_data: str) -> str:
        """Submit payment to AgentGatePay gateway"""
        try:
            parts = payment_data.split(',')
            if len(parts) != 4:
                return f"Error: Invalid payment data format. Expected 4 parts, got {len(parts)}"

            merchant_tx = parts[0].strip()
            commission_tx = parts[1].strip()
            mandate_token = parts[2].strip()
            price_usd = float(parts[3].strip())

            print(f"\n📤 Submitting payment to gateway...")
            print(f"   Merchant TX: {merchant_tx[:20]}...")
            print(f"   Commission TX: {commission_tx[:20]}...")
            print(f"   Price: ${price_usd}")

            # Build payment payload
            payment_payload = {
                "scheme": "eip3009",
                "tx_hash": merchant_tx,
                "tx_hash_commission": commission_tx
            }
            payment_b64 = base64.b64encode(json.dumps(payment_payload).encode()).decode()

            headers = {
                "x-api-key": BUYER_API_KEY,
                "x-mandate": mandate_token,
                "x-payment": payment_b64
            }

            url = f"{AGENTPAY_API_URL}/x402/resource?chain=base&token=USDC&price_usd={price_usd}"
            response = requests.get(url, headers=headers)

            if response.status_code >= 400:
                result = response.json() if response.text else {}
                error = result.get('error', response.text)
                print(f"❌ Gateway error ({response.status_code}): {error}")
                return f"Failed: {error}"

            result = response.json()
            if result.get('message') or result.get('success') or result.get('paid') or result.get('status') == 'confirmed':
                print(f"✅ Payment recorded successfully")

                # Fetch updated budget
                print(f"   🔍 Fetching updated budget...")
                verify_response = requests.post(
                    f"{AGENTPAY_API_URL}/mandates/verify",
                    headers={"x-api-key": BUYER_API_KEY, "Content-Type": "application/json"},
                    json={"mandate_token": mandate_token}
                )

                if verify_response.status_code == 200:
                    verify_data = verify_response.json()
                    new_budget = verify_data.get('budget_remaining', 'Unknown')
                    print(f"   ✅ Budget updated: ${new_budget}")

                    if self.current_mandate:
                        self.current_mandate['budget_remaining'] = new_budget
                        agent_id = f"buyer-agent-{self.account.address}"
                        save_mandate(agent_id, self.current_mandate)

                    return f"Success! Paid: ${price_usd}, Remaining: ${new_budget}"
                else:
                    return f"Success! Paid: ${price_usd}"
            else:
                error = result.get('error', 'Unknown error')
                print(f"❌ Failed: {error}")
                return f"Failed: {error}"

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return f"Error: {str(e)}"

    def claim_resource(self) -> str:
        """Claim resource by submitting payment proof"""
        if not self.last_payment or 'merchant_tx' not in self.last_payment:
            return "Error: No payment executed. Call sign_and_pay first."

        payment_info = self.last_payment
        print(f"\n📦 [BUYER] Claiming resource: {payment_info['resource_name']}")

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
                data = response.json()
                print(f"✅ Resource delivered!")
                print(f"   Resource: {payment_info['resource_name']}")
                print(f"   Payment verified: {data['payment_confirmation']['amount_verified_usd']} USD")

                # Store resource
                self.last_payment['resource_data'] = data['resource']

                return f"Resource '{payment_info['resource_name']}' received successfully! Payment verified: ${data['payment_confirmation']['amount_verified_usd']}"

            else:
                error = response.json().get('error', 'Unknown error')
                print(f"❌ Claim failed: {error}")
                return f"Claim failed: {error}"

        except Exception as e:
            error_msg = f"Claim error: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg


# ========================================
# LANGCHAIN AGENT
# ========================================

buyer = BuyerAgent()

# Global variable to store TTL for mandate (will be set from user input)
mandate_ttl_minutes = 10080  # Default: 7 days

# Define tools
tools = [
    Tool(
        name="issue_mandate",
        func=lambda budget: buyer.issue_mandate(float(budget), mandate_ttl_minutes),
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
    Tool(
        name="sign_and_pay",
        func=lambda _: buyer.sign_and_pay(),
        description="Sign and execute blockchain payment (2 transactions). Returns: TX_HASHES:{merchant_tx},{commission_tx},{mandate},{price}. No input needed."
    ),
    Tool(
        name="submit_payment",
        func=buyer.submit_payment,
        description="Submit payment to AgentGatePay gateway. Input: TX_HASHES output from sign_and_pay. Returns updated budget."
    ),
    Tool(
        name="claim_resource",
        func=lambda _: buyer.claim_resource(),
        description="Claim resource after payment by submitting payment proof. No input needed."
    ),
]

# System prompt for agent behavior
system_prompt = """You are an autonomous buyer agent that discovers and purchases resources from sellers.

Workflow:
1. Issue mandate with budget - Returns MANDATE_TOKEN:{token}
2. Discover catalog from seller
3. Request specific resource (gets payment requirements)
4. Sign and pay (blockchain transaction) - Returns TX_HASHES:{tx1},{tx2},{mandate},{price}
5. Submit payment to gateway - Input: TX_HASHES output from step 4
6. Claim resource (submit payment proof)

CRITICAL: You MUST parse tool outputs and use them as inputs to subsequent tools.
- After issue_mandate, extract token from "MANDATE_TOKEN:{token}"
- After sign_and_pay, use entire "TX_HASHES:..." output as input to submit_payment

Think step by step and complete the workflow."""

# Create agent (LangChain 1.x with LangGraph backend)
llm = ChatOpenAI(
    model="gpt-4",
    temperature=0,
    openai_api_key=os.getenv('OPENAI_API_KEY')
)

agent_executor = create_agent(
    llm,
    tools,
    system_prompt=system_prompt
)

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

    # Check seller API is running
    print(f"\n📡 Checking seller API: {SELLER_API_URL}")
    try:
        health = requests.get(f"{SELLER_API_URL}/health", timeout=5)
        if health.status_code == 200:
            print(f"✅ Seller API is running")
        else:
            print(f"⚠️  Seller API returned: HTTP {health.status_code}")
    except:
        print(f"❌ Seller API is NOT running!")
        print(f"   Please start the seller first: python 2b_api_seller_agent.py")
        exit(1)

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

        print(f"\n♻️  Using existing mandate (Budget: ${budget_remaining})")
        print(f"   Token: {existing_mandate.get('mandate_token', 'N/A')[:50]}...")
        print(f"   To delete: Remove from ~/.agentgatepay_mandates.json\n")
        mandate_budget = float(budget_remaining) if budget_remaining != 'Unknown' else MANDATE_BUDGET_USD
    else:
        budget_input = input("\n💰 Enter mandate budget in USD (default: 100): ").strip()
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

    # Ask user what they want (natural language)
    print(f"\n🛒 What do you want to purchase?")
    print(f"   Examples:")
    print(f"   - 'research paper about AI agent payments'")
    print(f"   - 'market data API access'")
    print(f"   - 'AI training dataset'")
    user_need = input("\n   Describe what you need: ").strip()

    if not user_need:
        user_need = "research paper about AI agent payments"
        print(f"   Using default: {user_need}")

    # Agent task - let agent discover and choose autonomously
    task = f"""
    The user wants: "{user_need}"

    Your job is to autonomously find and purchase the best matching resource.

    Steps:
    1. Issue a mandate with ${mandate_budget} budget
    2. Discover the catalog from {SELLER_API_URL}
    3. Analyze the catalog and identify which resource best matches: "{user_need}"
    4. Request that resource to get payment details
    5. If price is acceptable (under ${mandate_budget}), sign and pay
    6. Submit payment to AgentGatePay gateway
    7. Claim the resource by submitting payment proof

    IMPORTANT: You must discover the catalog FIRST, then decide which resource_id to purchase.
    Do NOT hardcode resource IDs. Choose based on what the user needs.
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
            print(f"   Mandate budget: ${buyer.current_mandate.get('budget_usd', 'N/A')}")

        if buyer.last_payment and 'merchant_tx' in buyer.last_payment:
            print(f"   Merchant TX: https://basescan.org/tx/{buyer.last_payment['merchant_tx']}")
            print(f"   Commission TX: https://basescan.org/tx/{buyer.last_payment['commission_tx']}")

        if buyer.last_payment and 'resource_data' in buyer.last_payment:
            print(f"\n📦 Received Resource:")
            resource = buyer.last_payment['resource_data']
            print(f"   Title: {resource.get('title', 'N/A')}")
            print(f"   Authors: {', '.join(resource.get('authors', []))}")

    except KeyboardInterrupt:
        print("\n\n⚠️  Buyer agent interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
