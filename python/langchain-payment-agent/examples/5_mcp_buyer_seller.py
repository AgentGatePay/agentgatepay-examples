#!/usr/bin/env python3
"""
AgentGatePay + LangChain Integration - BUYER/SELLER MARKETPLACE (MCP Tools)

This demonstrates the complete marketplace flow using AgentGatePay's 15 MCP tools
instead of the REST API SDK. The MCP approach provides:
- Native tool discovery (frameworks auto-list all 15 tools)
- Standardized JSON-RPC 2.0 protocol
- Future-proof (Anthropic-backed standard)

This example shows the BUYER side using MCP tools to:
1. Issue AP2 mandate (budget control)
2. Discover resources from seller
3. Submit blockchain payment
4. Verify payment and claim resource

For production: Seller would be a separate service (like 2b_api_seller_agent.py)
but using MCP tools for payment verification.

Usage:
    python 5_mcp_buyer_seller.py

Requirements:
- pip install langchain langchain-openai web3 python-dotenv requests
- .env file with BUYER_API_KEY, BUYER_PRIVATE_KEY, BUYER_WALLET
- AgentGatePay MCP endpoint running
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
BUYER_API_KEY = os.getenv('BUYER_API_KEY')
BUYER_PRIVATE_KEY = os.getenv('BUYER_PRIVATE_KEY')

# MCP endpoint (using dedicated MCP subdomain)
MCP_ENDPOINT = f"{MCP_API_URL}/mcp/tools/call"

# Payment configuration (from .env via chain_config)
RPC_URL = chain_config.rpc_url
CHAIN_ID = chain_config.chain_id
TOKEN_CONTRACT = chain_config.token_contract
TOKEN_DECIMALS = chain_config.decimals
CHAIN_NAME = chain_config.chain
TOKEN_NAME = chain_config.token

MANDATE_BUDGET_USD = float(os.getenv('MANDATE_BUDGET_USD', 100.0))
SELLER_WALLET = os.getenv('SELLER_WALLET', '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb2')
COMMISSION_RATE = 0.005

# ========================================
# HELPER FUNCTIONS
# ========================================

def get_commission_config() -> dict:
    """Fetch commission configuration from AgentGatePay API"""
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

# ========================================
# MCP HELPER FUNCTIONS
# ========================================

def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call AgentGatePay MCP tool via JSON-RPC 2.0.

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
# BUYER AGENT CLASS (MCP VERSION)
# ========================================

class BuyerAgentMCP:
    """
    Autonomous buyer agent using AgentGatePay MCP tools.

    Features:
    - AP2 mandate management via MCP
    - Payment submission via MCP
    - Payment verification via MCP
    - Multi-seller support
    """

    def __init__(self):
        # Initialize Web3 for blockchain signing
        self.web3 = Web3(Web3.HTTPProvider(RPC_URL))
        self.account = Account.from_key(BUYER_PRIVATE_KEY)

        # State
        self.current_mandate = None
        self.last_payment = None
        self.simulated_catalog = [
            {
                "resource_id": "research-paper-2025",
                "name": "AI Research Paper 2025",
                "description": "Latest AI research findings",
                "price_usd": 0.01,
                "seller_wallet": SELLER_WALLET
            },
            {
                "resource_id": "dataset-climate-2025",
                "name": "Climate Dataset 2025",
                "description": "Comprehensive climate data",
                "price_usd": 25.0,
                "seller_wallet": SELLER_WALLET
            }
        ]

        print(f"\n🤖 BUYER AGENT (MCP) INITIALIZED")
        print(f"=" * 60)
        print(f"Wallet: {self.account.address}")
        print(f"MCP Endpoint: {MCP_ENDPOINT}")
        print(f"=" * 60)

    def mcp_issue_mandate(self, budget_usd: float) -> str:
        """Issue AP2 mandate using MCP tool"""
        print(f"\n🔐 [MCP] Issuing mandate with ${budget_usd} budget...")

        try:
            mandate = call_mcp_tool("agentpay_issue_mandate", {
                "subject": f"buyer-agent-{self.account.address}",
                "budget_usd": budget_usd,
                "scope": "resource.read,payment.execute",
                "ttl_hours": 168
            })

            self.current_mandate = mandate
            print(f"✅ Mandate issued via MCP")
            print(f"   Token: {mandate['mandate_token'][:50]}...")
            print(f"   Budget: ${mandate['budget_usd']}")

            return f"Mandate issued via MCP. Budget: ${budget_usd}, Token: {mandate['mandate_token'][:50]}..."

        except Exception as e:
            error_msg = f"MCP mandate issue failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    def discover_catalog_simulated(self) -> str:
        """
        Simulate catalog discovery.

        In production, this would call a seller's API.
        For this demo, we use a simulated catalog.
        """
        print(f"\n🔍 [SIMULATED] Discovering catalog...")

        print(f"✅ Discovered {len(self.simulated_catalog)} resources:")
        for res in self.simulated_catalog:
            print(f"   - {res['name']} (${res['price_usd']})")

        total_value = sum(r['price_usd'] for r in self.simulated_catalog)
        return f"Found {len(self.simulated_catalog)} resources. Total catalog value: ${total_value:.2f}"

    def request_resource_simulated(self, resource_id: str) -> str:
        """
        Simulate resource request.

        In production, this would call seller's API and get 402 response.
        """
        print(f"\n📋 [SIMULATED] Requesting resource: {resource_id}")

        # Find resource in catalog
        resource = next((r for r in self.simulated_catalog if r['resource_id'] == resource_id), None)

        if not resource:
            return f"Error: Resource '{resource_id}' not found in catalog"

        print(f"💳 Payment required:")
        print(f"   Resource: {resource['name']}")
        print(f"   Price: ${resource['price_usd']}")
        print(f"   Recipient: {resource['seller_wallet'][:20]}...")

        # Store payment info
        self.last_payment = {
            "resource_id": resource_id,
            "resource_name": resource['name'],
            "price_usd": resource['price_usd'],
            "recipient": resource['seller_wallet']
        }

        return f"Resource '{resource['name']}' costs ${resource['price_usd']}. Payment required to access."

    def sign_and_pay_blockchain(self) -> str:
        """Sign and execute blockchain payment (2 transactions)"""
        if not self.last_payment:
            return "Error: No payment request pending."

        payment_info = self.last_payment
        print(f"\n💳 [BLOCKCHAIN] Executing payment: ${payment_info['price_usd']} to {payment_info['recipient'][:10]}...")

        try:
            # Fetch commission configuration from API
            commission_config = get_commission_config()
            if not commission_config:
                return "Error: Failed to fetch commission configuration"

            commission_address = commission_config.get('commission_address')
            commission_rate = commission_config.get('commission_rate', COMMISSION_RATE)

            print(f"   Using commission address: {commission_address[:10]}...")
            print(f"   Commission rate: {commission_rate * 100}%")

            # Calculate amounts
            total_usd = payment_info['price_usd']
            commission_usd = total_usd * commission_rate
            merchant_usd = total_usd - commission_usd

            merchant_atomic = int(merchant_usd * (10 ** TOKEN_DECIMALS))
            commission_atomic = int(commission_usd * (10 ** TOKEN_DECIMALS))

            print(f"   Merchant: ${merchant_usd:.4f} ({merchant_atomic} atomic)")
            print(f"   Commission: ${commission_usd:.4f} ({commission_atomic} atomic)")

            # ERC-20 transfer function signature
            transfer_sig = self.web3.keccak(text="transfer(address,uint256)")[:4]

            # TX 1: Merchant payment
            print(f"   📤 Signing merchant transaction...")
            merchant_data = transfer_sig + \
                           self.web3.to_bytes(hexstr=payment_info['recipient']).rjust(32, b'\x00') + \
                           merchant_atomic.to_bytes(32, byteorder='big')

            # Get nonce once for both transactions
            nonce = self.web3.eth.get_transaction_count(self.account.address)

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
            print(f"   ✅ TX 1/2 sent: {tx_hash_merchant_str[:20]}...")

            # TX 2: Commission payment
            print(f"   📤 Signing commission transaction...")
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
            print(f"   ✅ TX 2/2 sent: {tx_hash_commission_str[:20]}...")

            print(f"\n💳 Processing payment...")

            def verify_locally():
                """Verify TXs on-chain in background thread"""
                try:
                    print(f"   🔍 Verifying transactions on-chain...")
                    receipt_merchant = self.web3.eth.wait_for_transaction_receipt(tx_hash_merchant_raw, timeout=60)
                    print(f"   ✅ Merchant TX confirmed (block {receipt_merchant['blockNumber']})")

                    receipt_commission = self.web3.eth.wait_for_transaction_receipt(tx_hash_commission_raw, timeout=60)
                    print(f"   ✅ Commission TX confirmed (block {receipt_commission['blockNumber']})")
                except Exception as e:
                    print(f"   ⚠️  Verification failed: {e}")

            # Start verification in background thread
            verify_thread = threading.Thread(target=verify_locally)
            verify_thread.start()

            # Store transaction hashes in proper format
            self.last_payment['merchant_tx'] = tx_hash_merchant_str
            self.last_payment['commission_tx'] = tx_hash_commission_str

            print(f"✅ Payment executed successfully!")
            return f"Payment executed! Merchant TX: {tx_hash_merchant_str}, Commission TX: {tx_hash_commission_str}"

        except Exception as e:
            error_msg = f"Payment failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    def mcp_submit_payment(self) -> str:
        """Submit payment proof using MCP tool"""
        if not self.last_payment or 'merchant_tx' not in self.last_payment:
            return "Error: No payment executed. Sign and pay first."

        payment_info = self.last_payment
        print(f"\n📤 [MCP] Submitting payment proof to AgentGatePay...")

        try:
            # Submit payment via MCP tool
            result = call_mcp_tool("agentpay_submit_payment", {
                "mandate_token": self.current_mandate['mandate_token'],
                "tx_hash_merchant": payment_info['merchant_tx'],
                "tx_hash_commission": payment_info['commission_tx'],
                "chain": CHAIN_NAME,
                "token": TOKEN_NAME
            })

            print(f"✅ Payment submitted via MCP")
            print(f"   Charge ID: {result.get('chargeId', 'N/A')}")
            print(f"   Status: {result.get('status', 'N/A')}")

            self.last_payment['charge_id'] = result.get('chargeId')

            return f"Payment proof submitted via MCP. Charge ID: {result.get('chargeId')}"

        except Exception as e:
            error_msg = f"MCP payment submission failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    def mcp_verify_payment(self, tx_hash: str) -> str:
        """Verify payment using MCP tool"""
        print(f"\n🔍 [MCP] Verifying payment: {tx_hash[:20]}...")

        try:
            result = call_mcp_tool("agentpay_verify_payment", {
                "tx_hash": tx_hash,
                "chain": CHAIN_NAME
            })

            verified = result.get('verified', False)

            if verified:
                print(f"✅ Payment verified via MCP")
                print(f"   Amount: ${result.get('amount_usd', 'N/A')}")
                print(f"   Sender: {result.get('sender_address', 'N/A')[:20]}...")
                return f"Payment verified! Amount: ${result.get('amount_usd')} USD"
            else:
                print(f"❌ Payment NOT verified")
                return "Payment verification failed via MCP"

        except Exception as e:
            error_msg = f"MCP payment verification failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    def claim_resource_simulated(self) -> str:
        """
        Simulate resource delivery.

        In production, seller would verify payment and deliver resource.
        """
        if not self.last_payment or 'charge_id' not in self.last_payment:
            return "Error: No payment submitted. Submit payment first."

        payment_info = self.last_payment
        print(f"\n📦 [SIMULATED] Claiming resource: {payment_info['resource_name']}")

        # Simulate resource delivery
        print(f"✅ Resource delivered!")
        print(f"   Resource: {payment_info['resource_name']}")
        print(f"   Payment verified: ${payment_info['price_usd']} USD")

        return f"Resource '{payment_info['resource_name']}' received successfully!"


# ========================================
# LANGCHAIN AGENT
# ========================================

buyer = BuyerAgentMCP()

# Define tools
tools = [
    Tool(
        name="mcp_issue_mandate",
        func=lambda budget: buyer.mcp_issue_mandate(float(budget)),
        description="Issue AP2 payment mandate using MCP tool. Input: budget amount as number."
    ),
    Tool(
        name="discover_catalog",
        func=lambda _: buyer.discover_catalog_simulated(),
        description="Discover resource catalog (simulated). No input needed."
    ),
    Tool(
        name="request_resource",
        func=buyer.request_resource_simulated,
        description="Request specific resource (simulated 402 response). Input: resource_id string."
    ),
    Tool(
        name="sign_and_pay",
        func=lambda _: buyer.sign_and_pay_blockchain(),
        description="Sign and execute blockchain payment (2 transactions). No input needed."
    ),
    Tool(
        name="mcp_submit_payment",
        func=lambda _: buyer.mcp_submit_payment(),
        description="Submit payment proof to AgentGatePay using MCP tool. No input needed."
    ),
    Tool(
        name="mcp_verify_payment",
        func=lambda tx_hash: buyer.mcp_verify_payment(tx_hash),
        description="Verify payment using MCP tool. Input: tx_hash string."
    ),
    Tool(
        name="claim_resource",
        func=lambda _: buyer.claim_resource_simulated(),
        description="Claim resource (simulated delivery). No input needed."
    ),
]

# Agent prompt
agent_prompt = PromptTemplate.from_template("""
You are an autonomous buyer agent using AgentGatePay MCP tools.

Available tools:
{tools}

Tool names: {tool_names}

Task: {input}

Workflow:
1. Issue mandate via MCP
2. Discover catalog (simulated)
3. Request resource (simulated 402)
4. Sign and pay blockchain
5. Submit payment via MCP
6. Verify payment via MCP (optional)
7. Claim resource (simulated)

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
    max_iterations=20,
    handle_parsing_errors=True
)

# ========================================
# MAIN
# ========================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🤖 BUYER AGENT - MCP TOOLS VERSION")
    print("=" * 60)
    print()
    print("This agent uses AgentGatePay's 15 MCP tools to:")
    print("- Issue mandates")
    print("- Submit payments")
    print("- Verify payments")
    print()
    print("Note: Catalog and seller interaction are simulated.")
    print("Focus is on demonstrating MCP tool integration.")
    print()
    print("=" * 60)

    # Agent task
    task = f"""
    Purchase the research paper "research-paper-2025" using MCP tools.

    Steps:
    1. Issue mandate with ${MANDATE_BUDGET_USD} budget (MCP)
    2. Discover catalog (simulated)
    3. Request resource "research-paper-2025" (simulated)
    4. If price is acceptable (under $15), sign and pay blockchain
    5. Submit payment proof (MCP)
    6. Verify payment (MCP)
    7. Claim resource (simulated)

    Complete the purchase autonomously using MCP tools.
    """

    try:
        # Run agent
        result = agent_executor.invoke({"input": task})

        print("\n" + "=" * 60)
        print("✅ BUYER AGENT COMPLETED (MCP)")
        print("=" * 60)
        print(f"\nResult: {result['output']}")

        # Display final status
        if buyer.current_mandate:
            print(f"\n📊 Final Status:")
            print(f"   Mandate budget: ${buyer.current_mandate.get('budget_usd', 'N/A')}")

        if buyer.last_payment and 'merchant_tx' in buyer.last_payment:
            explorer_url = chain_config.explorer
            print(f"   Merchant TX: {explorer_url}/tx/{buyer.last_payment['merchant_tx']}")
            print(f"   Commission TX: {explorer_url}/tx/{buyer.last_payment['commission_tx']}")

        if buyer.last_payment and 'charge_id' in buyer.last_payment:
            print(f"   Charge ID: {buyer.last_payment['charge_id']}")

        print("\n💡 MCP Tools Used:")
        print("   - agentpay_issue_mandate")
        print("   - agentpay_submit_payment")
        print("   - agentpay_verify_payment")

    except KeyboardInterrupt:
        print("\n\n⚠️  Buyer agent interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
