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
- pip install langchain langchain-openai web3 python-dotenv requests
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

# LangChain imports
from langchain_core.tools import Tool
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

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

    mcp_endpoint = f"{MCP_API_URL}/mcp/tools/call"
    response = requests.post(mcp_endpoint, json=payload, headers=headers, timeout=30)

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
    - Resource discovery from seller APIs
    - AP2 mandate management via MCP
    - Blockchain payment signing
    - Payment submission via MCP
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

        print(f"\n🤖 BUYER AGENT (MCP) INITIALIZED")
        print(f"=" * 60)
        print(f"Wallet: {self.account.address}")
        print(f"Chain: {config.chain.upper()} (ID: {config.chain_id})")
        print(f"Token: {config.token} ({config.decimals} decimals)")
        print(f"RPC: {config.rpc_url[:50]}...")
        print(f"MCP URL: {MCP_API_URL}")
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

    def sign_and_pay_blockchain(self) -> str:
        """Sign and execute blockchain payment (2 transactions)"""
        if not self.last_payment:
            return "Error: No payment request pending. Call request_resource first."

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
            nonce = self.web3.eth.get_transaction_count(self.account.address)
            print(f"   📊 Current nonce: {nonce}")

            # TX 1: Merchant payment
            print(f"   📤 Signing merchant transaction...")
            merchant_data = transfer_sig + \
                           self.web3.to_bytes(hexstr=payment_info['recipient']).rjust(32, b'\x00') + \
                           merchant_atomic.to_bytes(32, byteorder='big')

            merchant_tx = {
                'nonce': nonce,
                'to': self.config.token_contract,
                'value': 0,
                'gas': 100000,
                'gasPrice': self.web3.eth.gas_price,
                'data': merchant_data,
                'chainId': self.config.chain_id
            }

            signed_merchant = self.account.sign_transaction(merchant_tx)
            tx_hash_merchant = self.web3.eth.send_raw_transaction(signed_merchant.raw_transaction)
            tx_hash_merchant_hex = self.web3.to_hex(tx_hash_merchant)
            print(f"   ✅ Merchant TX sent: {tx_hash_merchant_hex}")

            # TX 2: Commission payment
            print(f"   📤 Signing commission transaction...")
            commission_data = transfer_sig + \
                             self.web3.to_bytes(hexstr=commission_address).rjust(32, b'\x00') + \
                             commission_atomic.to_bytes(32, byteorder='big')

            commission_tx = {
                'nonce': nonce + 1,
                'to': self.config.token_contract,
                'value': 0,
                'gas': 100000,
                'gasPrice': self.web3.eth.gas_price,
                'data': commission_data,
                'chainId': self.config.chain_id
            }

            signed_commission = self.account.sign_transaction(commission_tx)
            tx_hash_commission = self.web3.eth.send_raw_transaction(signed_commission.raw_transaction)
            tx_hash_commission_hex = self.web3.to_hex(tx_hash_commission)
            print(f"   ✅ Commission TX sent: {tx_hash_commission_hex}")

            print(f"\n💳 Processing payment...")

            # Background verification thread
            def verify_locally():
                """Verify TXs on-chain in background thread"""
                try:
                    print(f"   🔍 Verifying transactions on-chain...")
                    receipt_merchant = self.web3.eth.wait_for_transaction_receipt(tx_hash_merchant, timeout=120)
                    print(f"   ✅ Merchant TX confirmed (block {receipt_merchant['blockNumber']})")

                    receipt_commission = self.web3.eth.wait_for_transaction_receipt(tx_hash_commission, timeout=120)
                    print(f"   ✅ Commission TX confirmed (block {receipt_commission['blockNumber']})")
                except Exception as e:
                    print(f"   ⚠️  Verification failed: {e}")

            # Start verification in background thread
            verify_thread = threading.Thread(target=verify_locally)
            verify_thread.start()

            # Store transaction hashes
            self.last_payment['merchant_tx'] = tx_hash_merchant_hex
            self.last_payment['commission_tx'] = tx_hash_commission_hex

            print(f"✅ Payment executed successfully!")
            return f"Payment executed! Merchant TX: {tx_hash_merchant_hex}, Commission TX: {tx_hash_commission_hex}"

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
                "tx_hash": payment_info['merchant_tx'],
                "tx_hash_commission": payment_info['commission_tx'],
                "chain": self.config.chain,
                "token": self.config.token
            })

            print(f"✅ Payment submitted via MCP")
            print(f"   Charge ID: {result.get('chargeId', 'N/A')}")
            print(f"   Status: {result.get('status', 'N/A')}")

            self.last_payment['charge_id'] = result.get('chargeId')

            return f"Payment proof submitted via MCP. Charge ID: {result.get('chargeId')}. IMPORTANT: Now call claim_resource to get the resource."

        except Exception as e:
            error_msg = f"MCP payment submission failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    def claim_resource(self) -> str:
        """Claim resource by submitting payment proof to seller (with retry logic)"""
        if not self.last_payment or 'merchant_tx' not in self.last_payment:
            return "Error: No payment executed. Call sign_and_pay first."

        payment_info = self.last_payment
        print(f"\n📦 [BUYER] Claiming resource: {payment_info['resource_name']}")

        # Retry claim up to 12 times with 10-second delays
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
                    timeout=30
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
                        print(f"   Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        # Last attempt failed
                        print(f"❌ Claim failed after {max_retries} attempts: {error}")
                        return f"Claim failed: {error}"

            except Exception as e:
                # If this is not the last attempt, retry after delay
                if attempt < max_retries - 1:
                    print(f"⚠️  Claim attempt {attempt + 1} error: {str(e)}")
                    print(f"   Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                else:
                    # Last attempt failed
                    error_msg = f"Claim error: {str(e)}"
                    print(f"❌ {error_msg}")
                    return error_msg

        return "Claim failed: Maximum retries exceeded"


# ========================================
# MAIN
# ========================================

# Global variables (will be set in main())
buyer = None

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🤖 BUYER AGENT - MCP TOOLS VERSION")
    print("=" * 60)
    print()
    print("This agent uses AgentGatePay's MCP tools to:")
    print("- Issue mandates (agentpay_issue_mandate)")
    print("- Submit payments (agentpay_submit_payment)")
    print()
    print("Blockchain signing and seller interaction use REST APIs.")
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

    # Initialize buyer agent
    buyer = BuyerAgentMCP(config)

    # Define tools after buyer is initialized
    tools = [
        Tool(
            name="issue_mandate",
            func=lambda budget: buyer.mcp_issue_mandate(float(budget)),
            description="Issue AP2 mandate using MCP tool. Input: budget amount as number."
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
            func=lambda _: buyer.sign_and_pay_blockchain(),
            description="Sign and execute blockchain payment (2 transactions). No input needed."
        ),
        Tool(
            name="submit_payment",
            func=lambda _: buyer.mcp_submit_payment(),
            description="Submit payment proof to AgentGatePay using MCP tool. No input needed. After this succeeds, you MUST call claim_resource."
        ),
        Tool(
            name="claim_resource",
            func=lambda _: buyer.claim_resource(),
            description="Claim resource by submitting payment proof to seller. No input needed."
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
1. Issue mandate via MCP (issue_mandate)
2. Discover catalog from seller (discover_catalog)
3. Request resource - USE THE 'ID' FIELD FROM CATALOG (request_resource)
4. Sign and pay blockchain (sign_and_pay)
5. Submit payment via MCP (submit_payment)
6. Claim resource from seller (claim_resource)

CRITICAL: After submit_payment succeeds, you MUST call claim_resource to complete purchase.

Think step by step:
{agent_scratchpad}
""")

    # Create agent
    llm = ChatOpenAI(
        model="gpt-4o-mini",
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

    # Get mandate budget from user
    budget_input = input("\n💰 Enter mandate budget in USD (default: 100): ").strip()
    mandate_budget = float(budget_input) if budget_input else MANDATE_BUDGET_USD

    # Agent task
    task = f"""
    Purchase the research paper "research-paper-2025" using MCP tools.

    Steps:
    1. Issue mandate with ${mandate_budget} budget (MCP)
    2. Discover catalog from {SELLER_API_URL}
    3. Request resource "research-paper-2025"
    4. If price is acceptable (under ${mandate_budget}), sign and pay blockchain
    5. Submit payment proof (MCP)
    6. Claim resource from seller

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
            print(f"   Merchant TX: {config.explorer}/tx/{buyer.last_payment['merchant_tx']}")
            print(f"   Commission TX: {config.explorer}/tx/{buyer.last_payment['commission_tx']}")

        if buyer.last_payment and 'charge_id' in buyer.last_payment:
            print(f"   Charge ID: {buyer.last_payment['charge_id']}")

        if buyer.last_payment and 'resource_data' in buyer.last_payment:
            print(f"\n📦 Received Resource:")
            resource = buyer.last_payment['resource_data']
            if 'title' in resource:
                print(f"   Title: {resource.get('title')}")
                print(f"   Authors: {', '.join(resource.get('authors', []))}")

        print("\n💡 MCP Tools Used:")
        print("   - agentpay_issue_mandate")
        print("   - agentpay_submit_payment")

        # Display gateway audit logs with curl commands
        if buyer.last_payment and 'merchant_tx' in buyer.last_payment:
            print(f"\n📋 Gateway Audit Logs (copy-paste these commands):")
            print(f"\n# All payment logs:")
            print(f"curl '{AGENTPAY_API_URL}/audit/logs?event_type=x402_payment_settled&limit=10' \\")
            print(f"  -H 'x-api-key: {BUYER_API_KEY}' | python3 -m json.tool")
            print(f"\n# This specific transaction:")
            print(f"curl '{AGENTPAY_API_URL}/audit/logs/transaction/{buyer.last_payment['merchant_tx']}' \\")
            print(f"  -H 'x-api-key: {BUYER_API_KEY}' | python3 -m json.tool")
            print(f"\n# Audit stats:")
            print(f"curl '{AGENTPAY_API_URL}/audit/stats' \\")
            print(f"  -H 'x-api-key: {BUYER_API_KEY}' | python3 -m json.tool")

    except KeyboardInterrupt:
        print("\n\n⚠️  Buyer agent interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
