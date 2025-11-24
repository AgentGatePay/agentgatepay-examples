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
from typing import Dict, Any
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from agentgatepay_sdk import AgentGatePay
import requests

# LangChain imports
from langchain.agents import Tool, AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

# Load environment variables
load_dotenv()

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

    def issue_mandate(self, budget_usd: float) -> str:
        """Issue AP2 payment mandate"""
        print(f"\n🔐 [BUYER] Issuing mandate with ${budget_usd} budget...")

        try:
            mandate = self.agentpay.mandates.issue(
                subject=f"buyer-agent-{self.account.address}",
                budget_usd=budget_usd,
                scope="resource.read,payment.execute",
                ttl_hours=168  # 7 days
            )

            self.current_mandate = mandate
            print(f"✅ Mandate issued successfully")
            print(f"   Token: {mandate['mandateToken'][:50]}...")
            print(f"   Budget: ${mandate['budgetUsd']}")

            return f"Mandate issued. Budget: ${budget_usd}, Token: {mandate['mandateToken'][:50]}..."

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
        """Sign and execute blockchain payment (2 transactions)"""
        if not self.last_payment:
            return "Error: No payment request pending. Call request_resource first."

        payment_info = self.last_payment
        print(f"\n💳 [BUYER] Executing payment: ${payment_info['price_usd']} to {payment_info['recipient'][:10]}...")

        try:
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
            tx_hash_merchant = self.web3.eth.send_raw_transaction(signed_merchant.rawTransaction)
            print(f"   ✅ Merchant TX sent: {tx_hash_merchant.hex()}")

            # Wait for confirmation
            print(f"   ⏳ Waiting for confirmation...")
            receipt_merchant = self.web3.eth.wait_for_transaction_receipt(tx_hash_merchant, timeout=60)
            print(f"   ✅ Confirmed in block {receipt_merchant['blockNumber']}")

            # TX 2: Commission payment
            print(f"   📤 Signing commission transaction...")
            commission_data = transfer_sig + \
                             self.web3.to_bytes(hexstr=payment_info['commission_address']).rjust(32, b'\x00') + \
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
            tx_hash_commission = self.web3.eth.send_raw_transaction(signed_commission.rawTransaction)
            print(f"   ✅ Commission TX sent: {tx_hash_commission.hex()}")

            # Wait for confirmation
            receipt_commission = self.web3.eth.wait_for_transaction_receipt(tx_hash_commission, timeout=60)
            print(f"   ✅ Confirmed in block {receipt_commission['blockNumber']}")

            # Store transaction hashes
            self.last_payment['merchant_tx'] = tx_hash_merchant.hex()
            self.last_payment['commission_tx'] = tx_hash_commission.hex()

            return f"Payment executed! Merchant TX: {tx_hash_merchant.hex()}, Commission TX: {tx_hash_commission.hex()}"

        except Exception as e:
            error_msg = f"Payment failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

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

# Define tools
tools = [
    Tool(
        name="issue_mandate",
        func=lambda budget: buyer.issue_mandate(float(budget)),
        description="Issue AP2 payment mandate with specified budget (USD). Use FIRST before any purchases. Input: budget amount as number."
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
        description="Sign and execute blockchain payment for last requested resource. No input needed."
    ),
    Tool(
        name="claim_resource",
        func=lambda _: buyer.claim_resource(),
        description="Claim resource after payment by submitting payment proof. No input needed."
    ),
]

# Agent prompt
agent_prompt = PromptTemplate.from_template("""
You are an autonomous buyer agent that discovers and purchases resources from sellers.

Available tools:
{tools}

Tool names: {tool_names}

Task: {input}

Workflow:
1. Issue mandate with budget
2. Discover catalog from seller
3. Request specific resource (gets payment requirements)
4. Sign and pay (blockchain transaction)
5. Claim resource (submit payment proof)

Think step by step:
{agent_scratchpad}
""")

# Create agent
llm = ChatOpenAI(
    model="gpt-4",
    temperature=0,
    openai_api_key=os.getenv('OPENAI_API_KEY')
)

agent = create_react_agent(llm=llm, tools=tools, prompt=agent_prompt)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    max_iterations=15,
    handle_parsing_errors=True
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

    # Agent task
    task = f"""
    Purchase the research paper "research-paper-2025" from the seller.

    Steps:
    1. Issue a mandate with ${MANDATE_BUDGET_USD} budget
    2. Discover the catalog from {SELLER_API_URL}
    3. Request the resource "research-paper-2025"
    4. If price is acceptable (under $15), sign and pay
    5. Claim the resource by submitting payment proof

    Make the purchase autonomously.
    """

    try:
        # Run agent
        result = agent_executor.invoke({"input": task})

        print("\n" + "=" * 60)
        print("✅ BUYER AGENT COMPLETED")
        print("=" * 60)
        print(f"\nResult: {result['output']}")

        # Display final status
        if buyer.current_mandate:
            print(f"\n📊 Final Status:")
            print(f"   Mandate budget: ${buyer.current_mandate.get('budgetUsd', 'N/A')}")

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
