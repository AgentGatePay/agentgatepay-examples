#!/usr/bin/env python3
"""
AgentGatePay + LangChain Integration - Buyer/Seller Interaction (REST API)

This example demonstrates a complete marketplace interaction using:
- BUYER AGENT: Autonomous agent that discovers and purchases resources
- SELLER AGENT: Resource provider that enforces payment before delivery
- AgentGatePay REST API for payment orchestration
- Two-transaction commission model (merchant + gateway)

Flow (matches n8n workflow pattern):
1. [BUYER] Issue AP2 mandate ($100 budget, 7 days TTL)
2. [BUYER] Discover resource from seller → 402 Payment Required
3. [BUYER] Sign blockchain transactions (merchant + commission)
4. [BUYER] Submit payment proof to seller
5. [SELLER] Verify payment via AgentGatePay API
6. [SELLER] Deliver resource → 200 OK
7. [BUYER] Retrieve audit logs for transaction history

Requirements:
- pip install agentgatepay-sdk langchain langchain-openai web3 python-dotenv flask
- Two AgentGatePay accounts (buyer + seller)
- .env file with configuration (see .env.example)
"""

import os
import time
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from agentgatepay_sdk import AgentGatePay
import threading
from flask import Flask, request, jsonify

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
SELLER_API_KEY = os.getenv('SELLER_API_KEY')
BASE_RPC_URL = os.getenv('BASE_RPC_URL', 'https://mainnet.base.org')
BUYER_PRIVATE_KEY = os.getenv('BUYER_PRIVATE_KEY')
SELLER_WALLET = os.getenv('SELLER_WALLET')
COMMISSION_ADDRESS = os.getenv('AGENTPAY_COMMISSION_ADDRESS', '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEbB')

# Payment configuration
MANDATE_BUDGET_USD = 100.0
COMMISSION_RATE = 0.005  # 0.5%

# USDC contract on Base
USDC_CONTRACT_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
USDC_DECIMALS = 6

# Seller API port
SELLER_API_PORT = 8000

# ========================================
# SELLER AGENT: RESOURCE API
# ========================================

class SellerAgent:
    """
    Seller agent that provides resources behind payment wall.
    Implements HTTP 402 Payment Required protocol.
    """

    def __init__(self):
        # Initialize AgentGatePay client with seller credentials
        self.agentpay = AgentGatePay(
            api_url=AGENTPAY_API_URL,
            api_key=SELLER_API_KEY
        )

        # Resource catalog
        self.catalog = {
            "research-paper-2025": {
                "id": "research-paper-2025",
                "price_usd": 10.0,
                "description": "AI Research Paper: Agent Payments in 2025",
                "data": {
                    "title": "Autonomous Agent Payment Systems: A 2025 Perspective",
                    "authors": ["Dr. AI Researcher", "Prof. Blockchain Expert"],
                    "abstract": "This paper explores the evolution of payment systems for autonomous AI agents...",
                    "pages": 42,
                    "url": "https://research.example.com/paper-2025.pdf"
                }
            },
            "market-data-premium": {
                "id": "market-data-premium",
                "price_usd": 5.0,
                "description": "Real-time premium market data feed",
                "data": {
                    "service": "Market Data API",
                    "endpoints": ["GET /v1/prices", "GET /v1/volume"],
                    "rate_limit": "1000 req/hour",
                    "api_key": "premium_abc123xyz"
                }
            }
        }

        print(f"💲 Seller Agent initialized")
        print(f"   Catalog: {len(self.catalog)} resources")
        print(f"   Wallet: {SELLER_WALLET}")

    def handle_resource_request(self, resource_id: str, payment_header: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle resource request with HTTP 402 protocol.

        Args:
            resource_id: Resource identifier
            payment_header: x-payment header (tx_hash,tx_hash_commission)

        Returns:
            Response dict with status code and body
        """
        # Check if resource exists
        resource = self.catalog.get(resource_id)
        if not resource:
            return {
                "status": 404,
                "body": {"error": "Resource not found", "available": list(self.catalog.keys())}
            }

        # If no payment provided → Return 402 Payment Required
        if not payment_header:
            print(f"\n💳 [SELLER] Payment required for: {resource_id}")
            print(f"   Price: ${resource['price_usd']}")

            return {
                "status": 402,
                "body": {
                    "error": "Payment Required",
                    "message": "This resource requires payment before access",
                    "resource": {
                        "id": resource['id'],
                        "description": resource['description'],
                        "price_usd": resource['price_usd']
                    },
                    "payment_info": {
                        "recipient": SELLER_WALLET,
                        "chain": "base",
                        "token": "USDC",
                        "commission_address": COMMISSION_ADDRESS,
                        "commission_rate": COMMISSION_RATE,
                        "total_amount": resource['price_usd']
                    }
                }
            }

        # Payment provided → Verify
        print(f"\n🔍 [SELLER] Verifying payment for: {resource_id}")

        try:
            # Parse payment header (format: "tx_hash,tx_hash_commission")
            parts = payment_header.split(',')
            if len(parts) != 2:
                return {
                    "status": 400,
                    "body": {"error": "Invalid payment header format. Expected: tx_hash,tx_hash_commission"}
                }

            tx_hash = parts[0].strip()
            tx_hash_commission = parts[1].strip()

            print(f"   Merchant TX: {tx_hash[:20]}...")
            print(f"   Commission TX: {tx_hash_commission[:20]}...")

            # Verify merchant payment via AgentGatePay API
            verification = self.agentpay.payments.verify(tx_hash)

            if not verification.get('verified'):
                print(f"   ❌ Payment verification failed")
                return {
                    "status": 403,
                    "body": {
                        "error": "Payment verification failed",
                        "message": verification.get('error', 'Unknown error')
                    }
                }

            # Verify amount matches resource price
            paid_amount = float(verification.get('amount_usd', 0))
            expected_amount = resource['price_usd'] * (1 - COMMISSION_RATE)  # Merchant portion

            if abs(paid_amount - expected_amount) > 0.01:  # Allow $0.01 tolerance
                print(f"   ❌ Amount mismatch: expected ${expected_amount:.2f}, got ${paid_amount:.2f}")
                return {
                    "status": 403,
                    "body": {
                        "error": "Payment amount mismatch",
                        "expected": expected_amount,
                        "received": paid_amount
                    }
                }

            # Payment verified → Deliver resource
            print(f"   ✅ Payment verified successfully")
            print(f"   💰 Amount: ${paid_amount}")
            print(f"   📦 Delivering resource...")

            return {
                "status": 200,
                "body": {
                    "message": "Resource access granted",
                    "resource": resource['data'],
                    "payment": {
                        "tx_hash": tx_hash,
                        "tx_hash_commission": tx_hash_commission,
                        "amount_usd": paid_amount,
                        "verified": True,
                        "explorer_url": f"https://basescan.org/tx/{tx_hash}"
                    }
                }
            }

        except Exception as e:
            print(f"   ❌ Verification error: {str(e)}")
            return {
                "status": 500,
                "body": {"error": "Internal server error", "message": str(e)}
            }


# Flask app for seller API
seller_app = Flask(__name__)
seller_agent = SellerAgent()


@seller_app.route('/resource', methods=['GET'])
def resource_endpoint():
    """Seller API endpoint"""
    resource_id = request.args.get('resource_id')
    payment_header = request.headers.get('x-payment')

    response = seller_agent.handle_resource_request(resource_id, payment_header)
    return jsonify(response['body']), response['status']


def start_seller_api():
    """Start seller API in background thread"""
    print(f"\n🚀 Starting Seller API on http://localhost:{SELLER_API_PORT}/resource")
    seller_app.run(host='0.0.0.0', port=SELLER_API_PORT, debug=False, use_reloader=False)


# ========================================
# BUYER AGENT: AUTONOMOUS PAYMENT BOT
# ========================================

class BuyerAgent:
    """
    Buyer agent that autonomously discovers and purchases resources.
    """

    def __init__(self):
        # Initialize AgentGatePay client with buyer credentials
        self.agentpay = AgentGatePay(
            api_url=AGENTPAY_API_URL,
            api_key=BUYER_API_KEY
        )

        # Initialize Web3 for blockchain interaction
        self.web3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))
        self.buyer_account = Account.from_key(BUYER_PRIVATE_KEY)

        # State
        self.current_mandate = None
        self.last_payment_tx = None

        print(f"\n🤖 Buyer Agent initialized")
        print(f"   Wallet: {self.buyer_account.address}")
        print(f"   API: {AGENTPAY_API_URL}")

    def issue_mandate(self, budget_usd: float) -> str:
        """Issue AP2 payment mandate"""
        print(f"\n🔐 [BUYER] Issuing mandate with ${budget_usd} budget...")

        mandate = self.agentpay.mandates.issue(
            subject=f"buyer-agent-{self.buyer_account.address}",
            budget_usd=budget_usd,
            scope="resource.read,payment.execute",
            ttl_hours=168
        )

        self.current_mandate = mandate
        print(f"✅ Mandate issued: {mandate['mandateToken'][:50]}...")
        return f"Mandate issued with ${budget_usd} budget. Token: {mandate['mandateToken'][:50]}..."

    def discover_resource(self, resource_id: str) -> str:
        """Discover resource and get payment requirements"""
        import requests

        print(f"\n🔍 [BUYER] Discovering resource: {resource_id}")

        try:
            response = requests.get(
                f"http://localhost:{SELLER_API_PORT}/resource",
                params={"resource_id": resource_id},
                headers={"x-agent-id": f"buyer-{self.buyer_account.address}"}
            )

            if response.status_code == 402:
                # Payment required
                data = response.json()
                print(f"💳 Payment required:")
                print(f"   Price: ${data['resource']['price_usd']}")
                print(f"   Recipient: {data['payment_info']['recipient'][:20]}...")
                return f"Resource found: {data['resource']['description']}. Price: ${data['resource']['price_usd']}. Payment required to access."

            elif response.status_code == 200:
                print(f"✅ Resource already accessed")
                return f"Resource accessed successfully (already paid)"

            else:
                error = response.json().get('error', 'Unknown error')
                print(f"❌ Discovery failed: {error}")
                return f"Discovery failed: {error}"

        except Exception as e:
            error_msg = f"Discovery error: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    def execute_payment(self, amount_usd: float, recipient: str) -> str:
        """Execute blockchain payment (2 transactions)"""
        print(f"\n💳 [BUYER] Executing payment: ${amount_usd} to {recipient[:10]}...")

        try:
            # Calculate amounts
            commission_amount_usd = amount_usd * COMMISSION_RATE
            merchant_amount_usd = amount_usd - commission_amount_usd

            merchant_amount_atomic = int(merchant_amount_usd * (10 ** USDC_DECIMALS))
            commission_amount_atomic = int(commission_amount_usd * (10 ** USDC_DECIMALS))

            # ERC-20 transfer function
            transfer_sig = self.web3.keccak(text="transfer(address,uint256)")[:4]

            # TX 1: Merchant payment
            print(f"   📤 Transaction 1: ${merchant_amount_usd:.4f} to merchant")
            merchant_data = transfer_sig + \
                           self.web3.to_bytes(hexstr=recipient).rjust(32, b'\x00') + \
                           merchant_amount_atomic.to_bytes(32, byteorder='big')

            merchant_tx = {
                'nonce': self.web3.eth.get_transaction_count(self.buyer_account.address),
                'to': USDC_CONTRACT_BASE,
                'value': 0,
                'gas': 100000,
                'gasPrice': self.web3.eth.gas_price,
                'data': merchant_data,
                'chainId': 8453
            }

            signed_merchant_tx = self.buyer_account.sign_transaction(merchant_tx)
            tx_hash_merchant = self.web3.eth.send_raw_transaction(signed_merchant_tx.rawTransaction)
            print(f"   ✅ Merchant TX: {tx_hash_merchant.hex()}")

            # Wait for confirmation
            receipt_merchant = self.web3.eth.wait_for_transaction_receipt(tx_hash_merchant, timeout=60)
            print(f"   ✅ Confirmed in block {receipt_merchant['blockNumber']}")

            # TX 2: Commission payment
            print(f"   📤 Transaction 2: ${commission_amount_usd:.4f} to gateway")
            commission_data = transfer_sig + \
                             self.web3.to_bytes(hexstr=COMMISSION_ADDRESS).rjust(32, b'\x00') + \
                             commission_amount_atomic.to_bytes(32, byteorder='big')

            commission_tx = {
                'nonce': self.web3.eth.get_transaction_count(self.buyer_account.address),
                'to': USDC_CONTRACT_BASE,
                'value': 0,
                'gas': 100000,
                'gasPrice': self.web3.eth.gas_price,
                'data': commission_data,
                'chainId': 8453
            }

            signed_commission_tx = self.buyer_account.sign_transaction(commission_tx)
            tx_hash_commission = self.web3.eth.send_raw_transaction(signed_commission_tx.rawTransaction)
            print(f"   ✅ Commission TX: {tx_hash_commission.hex()}")

            # Wait for confirmation
            receipt_commission = self.web3.eth.wait_for_transaction_receipt(tx_hash_commission, timeout=60)
            print(f"   ✅ Confirmed in block {receipt_commission['blockNumber']}")

            # Store transaction hashes
            self.last_payment_tx = {
                "merchant": tx_hash_merchant.hex(),
                "commission": tx_hash_commission.hex()
            }

            return f"Payment sent! Merchant TX: {tx_hash_merchant.hex()}, Commission TX: {tx_hash_commission.hex()}"

        except Exception as e:
            error_msg = f"Payment failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    def claim_resource(self, resource_id: str) -> str:
        """Claim resource after payment"""
        import requests

        if not self.last_payment_tx:
            return "Error: No payment executed yet"

        print(f"\n📦 [BUYER] Claiming resource: {resource_id}")

        try:
            # Submit payment proof to seller
            payment_header = f"{self.last_payment_tx['merchant']},{self.last_payment_tx['commission']}"

            response = requests.get(
                f"http://localhost:{SELLER_API_PORT}/resource",
                params={"resource_id": resource_id},
                headers={"x-payment": payment_header}
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Resource delivered!")
                print(f"   Title: {data['resource'].get('title', 'N/A')}")
                return f"Resource received: {data['message']}"

            else:
                error = response.json().get('error', 'Unknown error')
                print(f"❌ Claim failed: {error}")
                return f"Claim failed: {error}"

        except Exception as e:
            error_msg = f"Claim error: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    def get_audit_logs(self) -> str:
        """Retrieve audit logs for buyer"""
        print(f"\n📊 [BUYER] Retrieving audit logs...")

        try:
            logs = self.agentpay.audit.list_logs(
                event_type="payment_completed",
                limit=10
            )

            print(f"✅ Retrieved {len(logs.get('logs', []))} audit logs")
            return f"Audit logs retrieved: {len(logs.get('logs', []))} events"

        except Exception as e:
            error_msg = f"Audit log error: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg


# Initialize buyer agent
buyer_agent_instance = BuyerAgent()

# Define LangChain tools
tools = [
    Tool(
        name="issue_mandate",
        func=lambda budget: buyer_agent_instance.issue_mandate(float(budget)),
        description="Issue AP2 payment mandate with specified budget (USD). Use FIRST before purchasing."
    ),
    Tool(
        name="discover_resource",
        func=buyer_agent_instance.discover_resource,
        description="Discover resource and check if payment is required. Input: resource_id string."
    ),
    Tool(
        name="execute_payment",
        func=lambda params: buyer_agent_instance.execute_payment(*[float(params.split(',')[0]), params.split(',')[1]]),
        description="Execute blockchain payment. Input: 'amount_usd,recipient_address'"
    ),
    Tool(
        name="claim_resource",
        func=buyer_agent_instance.claim_resource,
        description="Claim resource after payment. Input: resource_id string."
    ),
    Tool(
        name="get_audit_logs",
        func=lambda _: buyer_agent_instance.get_audit_logs(),
        description="Retrieve audit logs for transaction history. No input needed."
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
1. Issue mandate (budget)
2. Discover resource (check price)
3. Execute payment (if price acceptable)
4. Claim resource (submit payment proof)
5. Get audit logs (verify transaction)

Think step by step:
{agent_scratchpad}
""")

# Create agent
llm = ChatOpenAI(model="gpt-4", temperature=0, openai_api_key=os.getenv('OPENAI_API_KEY'))
agent = create_react_agent(llm=llm, tools=tools, prompt=agent_prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=15, handle_parsing_errors=True)

# ========================================
# MAIN EXECUTION
# ========================================

if __name__ == "__main__":
    print("=" * 80)
    print("🤖 AGENTGATEPAY + LANGCHAIN: BUYER/SELLER DEMO (REST API)")
    print("=" * 80)
    print()
    print("This demo shows a complete marketplace interaction:")
    print("  - BUYER: Autonomous agent discovering and purchasing resources")
    print("  - SELLER: Resource API enforcing payment before delivery")
    print("  - AgentGatePay: Payment orchestration and verification")
    print()
    print("=" * 80)

    # Start seller API in background
    seller_thread = threading.Thread(target=start_seller_api, daemon=True)
    seller_thread.start()
    time.sleep(2)  # Wait for seller API to start

    # Buyer agent task
    task = f"""
    Purchase the research paper "research-paper-2025" from the seller.

    Steps:
    1. Issue a mandate with ${MANDATE_BUDGET_USD} budget
    2. Discover the resource and check its price
    3. If price is acceptable (under $15), execute payment to {SELLER_WALLET}
    4. Claim the resource by submitting payment proof
    5. Retrieve audit logs to confirm transaction
    """

    try:
        # Run buyer agent
        result = agent_executor.invoke({"input": task})

        print("\n" + "=" * 80)
        print("✅ MARKETPLACE INTERACTION COMPLETED")
        print("=" * 80)
        print(f"\nResult: {result['output']}")

        # Display final status
        if buyer_agent_instance.current_mandate:
            print(f"\n📊 Final Status:")
            print(f"   Mandate: {buyer_agent_instance.current_mandate.get('mandateToken', 'N/A')[:50]}...")
            print(f"   Budget remaining: ${buyer_agent_instance.current_mandate.get('budgetRemaining', 'N/A')}")

        if buyer_agent_instance.last_payment_tx:
            print(f"   Merchant TX: https://basescan.org/tx/{buyer_agent_instance.last_payment_tx['merchant']}")
            print(f"   Commission TX: https://basescan.org/tx/{buyer_agent_instance.last_payment_tx['commission']}")

    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
