#!/usr/bin/env python3
"""
AgentGatePay + LangChain Integration - Basic Payment Flow (MCP TOOLS)

This example demonstrates the SAME payment flow as 1_api_basic_payment.py,
but using AgentGatePay's MCP (Model Context Protocol) tools instead of REST API.

MCP Advantages:
- Native tool discovery (framework can list all 15 AgentGatePay tools)
- Standardized JSON-RPC 2.0 protocol
- Future-proof (Anthropic-backed standard)
- Cleaner separation between agent logic and API calls

MCP Tools Used:
- agentpay_issue_mandate - Issue AP2 payment mandate
- agentpay_submit_payment - Submit blockchain payment proof
- agentpay_verify_mandate - Verify mandate is valid

Flow:
1. Issue AP2 mandate ($100 budget)
2. Sign blockchain transaction (USDC on Base)
3. Submit payment via MCP tool
4. Verify payment completion

Requirements:
- pip install langchain langchain-openai web3 python-dotenv requests
- .env file with configuration (see .env.example)
"""

import os
import time
import json
import base64
import requests
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
AGENTPAY_MCP_ENDPOINT = os.getenv('MCP_API_URL', 'https://mcp.agentgatepay.com')
BUYER_API_KEY = os.getenv('BUYER_API_KEY')
BASE_RPC_URL = os.getenv('BASE_RPC_URL', 'https://mainnet.base.org')
BUYER_PRIVATE_KEY = os.getenv('BUYER_PRIVATE_KEY')
SELLER_WALLET = os.getenv('SELLER_WALLET')

# Payment configuration
RESOURCE_PRICE_USD = 0.01
MANDATE_BUDGET_USD = 100.0
COMMISSION_RATE = 0.005

# USDC contract on Base
USDC_CONTRACT_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
USDC_DECIMALS = 6

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
# MCP TOOL WRAPPER
# ========================================

def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call AgentGatePay MCP tool via JSON-RPC 2.0 protocol.

    Args:
        tool_name: MCP tool name (e.g., "agentpay_issue_mandate")
        arguments: Tool arguments as dictionary

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

    print(f"   📡 Calling MCP tool: {tool_name}")

    response = requests.post(AGENTPAY_MCP_ENDPOINT, json=payload, headers=headers)
    response.raise_for_status()

    result = response.json()

    if "error" in result:
        raise Exception(f"MCP error: {result['error']}")

    # MCP response format: result.content[0].text (JSON string)
    content_text = result['result']['content'][0]['text']
    return json.loads(content_text)


# ========================================
# INITIALIZE WEB3
# ========================================

web3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))
buyer_account = Account.from_key(BUYER_PRIVATE_KEY)

print(f"✅ Initialized AgentGatePay MCP client")
print(f"   Endpoint: {AGENTPAY_MCP_ENDPOINT}")
print(f"   Buyer wallet: {buyer_account.address}\n")

# ========================================
# AGENT TOOLS (MCP-BASED)
# ========================================

# Global state
current_mandate = None
merchant_tx_hash = None
commission_tx_hash = None


def mcp_issue_mandate(budget_usd: float) -> str:
    """Issue mandate using MCP tool"""
    global current_mandate

    print(f"\n🔐 [MCP] Issuing mandate with ${budget_usd} budget...")

    mandate = call_mcp_tool("agentpay_issue_mandate", {
        "subject": f"research-assistant-{buyer_account.address}",
        "budget_usd": budget_usd,
        "scope": "resource.read,payment.execute",
        "ttl_hours": 168
    })

    current_mandate = mandate

    print(f"✅ Mandate issued via MCP")
    print(f"   Token: {mandate['mandate_token'][:50]}...")
    print(f"   Budget: ${mandate['budget_usd']}")

    return f"Mandate issued via MCP. Budget: ${budget_usd}, Token: {mandate['mandate_token'][:50]}..."


def sign_blockchain_payment(amount_usd: float, recipient: str) -> str:
    """
    Sign blockchain payment locally (same as API version).
    Note: Blockchain signing is NOT done via MCP (requires private key).
    """
    global merchant_tx_hash, commission_tx_hash

    print(f"\n💳 Signing blockchain payment: ${amount_usd} to {recipient[:10]}...")

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
        commission_amount_usd = amount_usd * commission_rate
        merchant_amount_usd = amount_usd - commission_amount_usd

        merchant_amount_atomic = int(merchant_amount_usd * (10 ** USDC_DECIMALS))
        commission_amount_atomic = int(commission_amount_usd * (10 ** USDC_DECIMALS))

        print(f"   Merchant: ${merchant_amount_usd:.4f}, Commission: ${commission_amount_usd:.4f}")

        # ERC-20 transfer function
        transfer_sig = web3.keccak(text="transfer(address,uint256)")[:4]

        # TX 1: Merchant payment
        print(f"   📤 Signing merchant transaction...")
        merchant_data = transfer_sig + \
                       web3.to_bytes(hexstr=recipient).rjust(32, b'\x00') + \
                       merchant_amount_atomic.to_bytes(32, byteorder='big')

        merchant_tx = {
            'nonce': web3.eth.get_transaction_count(buyer_account.address),
            'to': USDC_CONTRACT_BASE,
            'value': 0,
            'gas': 100000,
            'gasPrice': web3.eth.gas_price,
            'data': merchant_data,
            'chainId': 8453
        }

        signed_merchant = buyer_account.sign_transaction(merchant_tx)
        tx_hash_merchant_raw = web3.eth.send_raw_transaction(signed_merchant.raw_transaction)

        # Fix TX hash format
        tx_hash_merchant_str = f"0x{tx_hash_merchant_raw.hex()}" if not tx_hash_merchant_raw.hex().startswith('0x') else tx_hash_merchant_raw.hex()
        print(f"   ✅ Merchant TX sent: {tx_hash_merchant_str}")

        # Wait for confirmation
        receipt_merchant = web3.eth.wait_for_transaction_receipt(tx_hash_merchant_raw, timeout=60)
        print(f"   ✅ Confirmed in block {receipt_merchant['blockNumber']}")

        # TX 2: Commission payment
        print(f"   📤 Signing commission transaction...")
        commission_data = transfer_sig + \
                         web3.to_bytes(hexstr=commission_address).rjust(32, b'\x00') + \
                         commission_amount_atomic.to_bytes(32, byteorder='big')

        commission_tx = {
            'nonce': web3.eth.get_transaction_count(buyer_account.address),
            'to': USDC_CONTRACT_BASE,
            'value': 0,
            'gas': 100000,
            'gasPrice': web3.eth.gas_price,
            'data': commission_data,
            'chainId': 8453
        }

        signed_commission = buyer_account.sign_transaction(commission_tx)
        tx_hash_commission_raw = web3.eth.send_raw_transaction(signed_commission.raw_transaction)

        # Fix TX hash format
        tx_hash_commission_str = f"0x{tx_hash_commission_raw.hex()}" if not tx_hash_commission_raw.hex().startswith('0x') else tx_hash_commission_raw.hex()
        print(f"   ✅ Commission TX sent: {tx_hash_commission_str}")

        # Wait for confirmation
        receipt_commission = web3.eth.wait_for_transaction_receipt(tx_hash_commission_raw, timeout=60)
        print(f"   ✅ Confirmed in block {receipt_commission['blockNumber']}")

        # Store hashes in proper format
        merchant_tx_hash = tx_hash_merchant_str
        commission_tx_hash = tx_hash_commission_str

        return f"TX_HASHES:{merchant_tx_hash},{commission_tx_hash}"

    except Exception as e:
        error_msg = f"Payment failed: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg


def mcp_submit_payment() -> str:
    """Submit payment proof using MCP tool"""
    if not current_mandate or not merchant_tx_hash:
        return "Error: Must issue mandate and sign payment first"

    print(f"\n📤 [MCP] Submitting payment proof...")

    try:
        result = call_mcp_tool("agentpay_submit_payment", {
            "mandate_token": current_mandate['mandate_token'],
            "tx_hash": merchant_tx_hash,
            "tx_hash_commission": commission_tx_hash,
            "chain": "base",
            "token": "USDC"
        })

        print(f"✅ Payment submitted via MCP")
        print(f"   Status: {result.get('status', 'N/A')}")

        return f"Payment submitted via MCP! Status: {result.get('status')}, TX: {merchant_tx_hash[:20]}..."

    except Exception as e:
        error_msg = f"Payment submission failed: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg


def mcp_verify_mandate() -> str:
    """Verify mandate using MCP tool"""
    if not current_mandate:
        return "Error: No mandate issued yet"

    print(f"\n🔍 [MCP] Verifying mandate...")

    try:
        result = call_mcp_tool("agentpay_verify_mandate", {
            "mandate_token": current_mandate['mandate_token']
        })

        print(f"✅ Mandate verified via MCP")
        print(f"   Valid: {result.get('valid', False)}")
        print(f"   Budget remaining: ${result.get('budget_remaining', 'N/A')}")

        return f"Mandate valid: {result.get('valid')}. Budget remaining: ${result.get('budget_remaining')}"

    except Exception as e:
        error_msg = f"Mandate verification failed: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg


# Define LangChain tools
tools = [
    Tool(
        name="issue_mandate_mcp",
        func=lambda budget: mcp_issue_mandate(float(budget)),
        description="Issue AP2 mandate using MCP tool. Input: budget amount in USD."
    ),
    Tool(
        name="sign_payment",
        func=lambda params: sign_blockchain_payment(*[float(params.split(',')[0]), params.split(',')[1]]),
        description="Sign blockchain payment locally (Web3). Input: 'amount_usd,recipient_address'"
    ),
    Tool(
        name="submit_payment_mcp",
        func=lambda _: mcp_submit_payment(),
        description="Submit payment proof to AgentGatePay via MCP tool. No input needed."
    ),
    Tool(
        name="verify_mandate_mcp",
        func=lambda _: mcp_verify_mandate(),
        description="Verify mandate validity via MCP tool. No input needed."
    ),
]

# ========================================
# AGENT PROMPT
# ========================================

agent_prompt = PromptTemplate.from_template("""
You are an autonomous AI agent using AgentGatePay MCP tools for payments.

Available tools:
{tools}

Tool Names: {tool_names}

Task: {input}

Workflow:
1. Issue mandate using MCP tool (issue_mandate_mcp)
2. Sign blockchain payment locally (sign_payment)
3. Submit payment proof using MCP tool (submit_payment_mcp)
4. Verify mandate status using MCP tool (verify_mandate_mcp)

Think step by step:
{agent_scratchpad}
""")

# ========================================
# CREATE AGENT
# ========================================

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
    max_iterations=10,
    handle_parsing_errors=True
)

# ========================================
# EXECUTE PAYMENT WORKFLOW
# ========================================

if __name__ == "__main__":
    print("=" * 80)
    print("🤖 AGENTGATEPAY + LANGCHAIN: BASIC PAYMENT DEMO (MCP TOOLS)")
    print("=" * 80)
    print()
    print("This demo shows the SAME payment flow as the REST API version,")
    print("but using AgentGatePay's 15 MCP tools instead:")
    print("  - agentpay_issue_mandate (MCP tool)")
    print("  - agentpay_submit_payment (MCP tool)")
    print("  - agentpay_verify_mandate (MCP tool)")
    print()
    print("MCP Advantages: Native tool discovery, standardized protocol, future-proof")
    print("=" * 80)

    task = f"""
    Purchase a research resource for ${RESOURCE_PRICE_USD} USD using MCP tools.

    Steps:
    1. Issue a payment mandate with ${MANDATE_BUDGET_USD} budget using MCP
    2. Sign blockchain payment of ${RESOURCE_PRICE_USD} to {SELLER_WALLET}
    3. Submit payment proof via MCP tool
    4. Verify mandate status via MCP tool
    """

    try:
        # Run agent
        result = agent_executor.invoke({"input": task})

        print("\n" + "=" * 80)
        print("✅ MCP PAYMENT WORKFLOW COMPLETED")
        print("=" * 80)
        print(f"\nResult: {result['output']}")

        # Display final status
        if current_mandate:
            print(f"\n📊 Final Status:")
            print(f"   Mandate: {current_mandate.get('mandate_token', 'N/A')[:50]}...")

        if merchant_tx_hash:
            print(f"   Merchant TX: https://basescan.org/tx/{merchant_tx_hash}")
            print(f"   Commission TX: https://basescan.org/tx/{commission_tx_hash}")

        print(f"\n🎉 SUCCESS: Payment completed using MCP tools!")

    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
