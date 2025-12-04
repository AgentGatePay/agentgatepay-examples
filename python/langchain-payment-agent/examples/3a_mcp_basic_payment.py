#!/usr/bin/env python3
"""
AgentGatePay + LangChain Integration - Example 3a: MCP + Local Signing

This example demonstrates the SAME payment flow as Example 1a,
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
1. Issue AP2 mandate ($100 budget) via MCP
2. Sign blockchain transactions locally (Web3.py)
3. Submit payment and verify budget via MCP tools

Requirements:
- pip install langchain langchain-openai web3 python-dotenv requests
- .env file with configuration (see .env.example)

For Production: See Example 3b (MCP + external TX signing)
For REST API Version: See Example 1a (REST API + local signing)
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

# LangChain imports (updated for LangChain 1.x)
from langchain_core.tools import Tool
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

# Add parent directory to path for utils import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Utils for mandate storage
from utils import save_mandate, get_mandate, clear_mandate

# Load environment variables
load_dotenv()

# Import chain configuration
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from chain_config import get_chain_config

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
BUYER_PRIVATE_KEY = os.getenv('BUYER_PRIVATE_KEY')
SELLER_WALLET = os.getenv('SELLER_WALLET')

# Payment configuration
RESOURCE_PRICE_USD = 0.01
MANDATE_BUDGET_USD = 100.0

# Multi-chain/token configuration (set after interactive selection)
# To manually configure without interactive prompt, uncomment and set:
# config = ChainConfig(
#     chain="ethereum",           # Options: base, ethereum, polygon, arbitrum
#     token="USDT",               # Options: USDC, USDT, DAI (check availability per chain)
#     chain_id=1,
#     rpc_url="https://eth-mainnet.public.blastapi.io",
#     token_contract="0xdAC17F958D2ee523a2206206994597C13D831ec7",
#     decimals=6,
#     explorer="https://etherscan.io"
# )
# Note: USDT not available on Base. DAI uses 18 decimals. See CHAIN_TOKEN_GUIDE.md
config = None  # Will be set via get_chain_config() in main()

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

def decode_mandate_token(token: str) -> dict:
    """Decode AP2 mandate token to extract payload"""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return {}
        payload_b64 = parts[1]
        padding = 4 - (len(payload_b64) % 4)
        if padding != 4:
            payload_b64 += '=' * padding
        payload_json = base64.urlsafe_b64decode(payload_b64)
        return json.loads(payload_json)
    except:
        return {}

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
# INITIALIZE CLIENTS
# ========================================
# Note: Clients initialized in main() after chain/token configuration

web3 = None
buyer_account = None

# ========================================
# AGENT TOOLS (MCP-BASED)
# ========================================

# Global state
current_mandate = None
merchant_tx_hash = None
commission_tx_hash = None


def mcp_issue_mandate(budget_usd: float) -> str:
    """Issue mandate using MCP tool (with reuse logic matching Script 1)"""
    global current_mandate

    try:
        agent_id = f"research-assistant-{buyer_account.address}"
        existing_mandate = get_mandate(agent_id)

        if existing_mandate:
            token = existing_mandate.get('mandate_token')

            # Get LIVE budget from gateway (via MCP verify tool)
            try:
                verify_result = call_mcp_tool("agentpay_verify_mandate", {
                    "mandate_token": token
                })

                if verify_result.get('valid'):
                    budget_remaining = verify_result.get('budget_remaining', 'Unknown')
                else:
                    # Fallback to JWT decode if MCP verify fails
                    token_data = decode_mandate_token(token)
                    budget_remaining = token_data.get('budget_remaining', existing_mandate.get('budget_usd', 'Unknown'))
            except:
                # Fallback to JWT if MCP call fails
                token_data = decode_mandate_token(token)
                budget_remaining = token_data.get('budget_remaining', existing_mandate.get('budget_usd', 'Unknown'))

            print(f"\n♻️  Reusing mandate (Budget: ${budget_remaining})")
            current_mandate = existing_mandate
            current_mandate['budget_remaining'] = budget_remaining
            return f"MANDATE_TOKEN:{token}"

        print(f"\n🔐 Creating mandate (${budget_usd})...")

        mandate = call_mcp_tool("agentpay_issue_mandate", {
            "subject": agent_id,
            "budget_usd": budget_usd,
            "scope": "resource.read,payment.execute",
            "ttl_minutes": 168 * 60
        })

        # Store mandate with budget info (MCP response only includes token)
        token = mandate['mandate_token']
        mandate_with_budget = {
            **mandate,
            'budget_usd': budget_usd,
            'budget_remaining': budget_usd  # Initially, remaining = total
        }

        current_mandate = mandate_with_budget
        save_mandate(agent_id, mandate_with_budget)

        print(f"✅ Mandate created (Budget: ${budget_usd})")

        return f"MANDATE_TOKEN:{token}"

    except Exception as e:
        print(f"❌ Mandate failed: {str(e)}")
        return f"Failed: {str(e)}"


def sign_blockchain_payment(amount_usd: float, recipient: str) -> str:
    """
    Sign blockchain payment locally (same as API version).
    Note: Blockchain signing is NOT done via MCP (requires private key).
    """
    global merchant_tx_hash, commission_tx_hash

    print(f"\n💳 Signing payment (${amount_usd} {config.token})...")
    print(f"   Chain: {config.chain.title()} (ID: {config.chain_id})")
    print(f"   Token: {config.token} ({config.decimals} decimals)")

    try:
        # Fetch commission configuration from API
        commission_config = get_commission_config()
        if not commission_config:
            return "Error: Failed to fetch commission configuration"

        commission_address = commission_config['commission_address']
        commission_rate = commission_config['commission_rate']

        # Calculate amounts
        commission_amount_usd = amount_usd * commission_rate
        merchant_amount_usd = amount_usd - commission_amount_usd
        merchant_amount_atomic = int(merchant_amount_usd * (10 ** config.decimals))
        commission_amount_atomic = int(commission_amount_usd * (10 ** config.decimals))

        transfer_function_signature = web3.keccak(text="transfer(address,uint256)")[:4]

        # Fetch nonce once for both transactions
        nonce = web3.eth.get_transaction_count(buyer_account.address)

        print(f"   📤 TX 1/2 (merchant)...")
        recipient_clean = recipient.replace('0x', '').lower()
        recipient_bytes = bytes.fromhex(recipient_clean).rjust(32, b'\x00')

        merchant_data = transfer_function_signature + recipient_bytes + merchant_amount_atomic.to_bytes(32, byteorder='big')

        merchant_tx = {
            'nonce': nonce,
            'to': config.token_contract,
            'value': 0,
            'gas': 100000,
            'gasPrice': web3.eth.gas_price,
            'data': merchant_data,
            'chainId': config.chain_id
        }

        signed_merchant_tx = buyer_account.sign_transaction(merchant_tx)
        tx_hash_merchant_raw = web3.eth.send_raw_transaction(signed_merchant_tx.raw_transaction)
        tx_hash_merchant = f"0x{tx_hash_merchant_raw.hex()}" if not tx_hash_merchant_raw.hex().startswith('0x') else tx_hash_merchant_raw.hex()
        print(f"   ✅ TX 1/2 sent: {tx_hash_merchant[:20]}...")

        print(f"   📤 TX 2/2 (commission)...")
        commission_addr_clean = commission_address.replace('0x', '').lower()
        commission_addr_bytes = bytes.fromhex(commission_addr_clean).rjust(32, b'\x00')

        commission_data = transfer_function_signature + commission_addr_bytes + commission_amount_atomic.to_bytes(32, byteorder='big')

        commission_tx = {
            'nonce': nonce + 1,
            'to': config.token_contract,
            'value': 0,
            'gas': 100000,
            'gasPrice': web3.eth.gas_price,
            'data': commission_data,
            'chainId': config.chain_id
        }

        signed_commission_tx = buyer_account.sign_transaction(commission_tx)
        tx_hash_commission_raw = web3.eth.send_raw_transaction(signed_commission_tx.raw_transaction)
        tx_hash_commission = f"0x{tx_hash_commission_raw.hex()}" if not tx_hash_commission_raw.hex().startswith('0x') else tx_hash_commission_raw.hex()
        print(f"   ✅ TX 2/2 sent: {tx_hash_commission[:20]}...")

        merchant_tx_hash = tx_hash_merchant
        commission_tx_hash = tx_hash_commission

        return f"TX_HASHES:{tx_hash_merchant},{tx_hash_commission}"

    except Exception as e:
        print(f"❌ Payment failed: {str(e)}")
        raise Exception(f"Payment failed: {str(e)}")


def mcp_submit_and_verify_payment() -> str:
    """Submit payment proof using MCP tool and verify budget (combined)"""
    global current_mandate

    if not current_mandate or not merchant_tx_hash:
        return "Error: Must issue mandate and sign payment first"

    print(f"\n📤 [MCP] Submitting payment proof...")

    try:
        # Submit payment via MCP
        result = call_mcp_tool("agentpay_submit_payment", {
            "mandate_token": current_mandate['mandate_token'],
            "tx_hash": merchant_tx_hash,
            "tx_hash_commission": commission_tx_hash,
            "chain": config.chain,
            "token": config.token
        })

        print(f"✅ Payment submitted via MCP")
        print(f"   Status: {result.get('status', 'N/A')}")

        # Verify mandate to get updated budget
        print(f"   🔍 Fetching updated budget...")
        verify_result = call_mcp_tool("agentpay_verify_mandate", {
            "mandate_token": current_mandate['mandate_token']
        })

        if verify_result.get('valid'):
            new_budget = verify_result.get('budget_remaining', 'Unknown')
            print(f"   ✅ Budget updated: ${new_budget}")

            # Update and save mandate (matching Script 1)
            if current_mandate:
                current_mandate['budget_remaining'] = new_budget
                agent_id = f"research-assistant-{buyer_account.address}"
                save_mandate(agent_id, current_mandate)

            return f"Success! Paid: ${RESOURCE_PRICE_USD}, Remaining: ${new_budget}"
        else:
            print(f"   ⚠️  Could not fetch updated budget")
            return f"Success! Paid: ${RESOURCE_PRICE_USD}"

    except Exception as e:
        error_msg = f"Payment submission failed: {str(e)}"
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
        name="submit_and_verify_payment",
        func=lambda _: mcp_submit_and_verify_payment(),
        description="Submit payment proof via MCP and verify updated budget. No input needed."
    ),
]

# ========================================
# CREATE AGENT (LangChain 1.x)
# ========================================

# Initialize LLM
llm = ChatOpenAI(
    model="gpt-4",
    temperature=0,
    openai_api_key=os.getenv('OPENAI_API_KEY')
)

# System prompt for agent behavior
system_prompt = """You are an autonomous AI agent using AgentGatePay MCP tools for payments.

Follow this workflow:
1. Issue mandate using MCP tool (issue_mandate_mcp) with the specified budget
   - The tool returns: "Mandate issued via MCP. Budget: $X, Token: ..."
   - Extract the mandate information from the response
2. Sign blockchain payment locally (sign_payment) for the specified amount to the recipient
   - Input format: 'amount_usd,recipient_address'
   - The tool returns: "TX_HASHES:{merchant_tx},{commission_tx}"
   - Extract both transaction hashes after the colon
3. Submit payment and verify budget using MCP tool (submit_and_verify_payment)
   - This tool automatically uses the mandate and transaction hashes from previous steps
   - Returns updated budget after payment

IMPORTANT:
- All three steps must complete successfully
- Parse tool outputs to extract values
- If any tool returns an error, STOP immediately and report the error
- Do NOT retry failed operations"""

# Create agent (LangChain 1.x with LangGraph backend)
agent_executor = create_agent(
    llm,
    tools,
    system_prompt=system_prompt
)

# ========================================
# EXECUTE PAYMENT WORKFLOW
# ========================================

if __name__ == "__main__":
    print("=" * 80)
    print("AGENTGATEPAY + LANGCHAIN: BASIC PAYMENT DEMO (MCP TOOLS)")
    print("=" * 80)
    print()
    print("This demo shows an autonomous agent making a blockchain payment using:")
    print("  - AgentGatePay MCP tools (JSON-RPC 2.0)")
    print("  - LangChain agent framework")
    print("  - Multi-chain blockchain payments (Base/Ethereum/Polygon/Arbitrum)")
    print("  - Multi-token support (USDC/USDT/DAI)")
    print()

    # Load chain/token configuration from .env
    print("\nCHAIN & TOKEN CONFIGURATION")
    print("=" * 80)

    config = get_chain_config()

    print(f"\nUsing configuration from .env:")
    print(f"  Chain: {config.chain.title()} (ID: {config.chain_id})")
    print(f"  Token: {config.token} ({config.decimals} decimals)")
    print(f"  RPC: {config.rpc_url}")
    print(f"  Contract: {config.token_contract}")
    print(f"\nTo change chain/token: Edit PAYMENT_CHAIN and PAYMENT_TOKEN in .env file")
    print("=" * 80)

    # Initialize clients with selected configuration
    web3 = Web3(Web3.HTTPProvider(config.rpc_url))
    buyer_account = Account.from_key(BUYER_PRIVATE_KEY)

    print(f"\nInitialized AgentGatePay MCP client: {AGENTPAY_MCP_ENDPOINT}")
    print(f"Initialized Web3 client: {config.chain.title()} network")
    print(f"Buyer wallet: {buyer_account.address}\n")

    agent_id = f"research-assistant-{buyer_account.address}"
    existing_mandate = get_mandate(agent_id)

    if existing_mandate:
        token = existing_mandate.get('mandate_token')

        # Get LIVE budget from gateway (via MCP verify tool)
        try:
            verify_result = call_mcp_tool("agentpay_verify_mandate", {
                "mandate_token": token
            })

            if verify_result.get('valid'):
                budget_remaining = verify_result.get('budget_remaining', 'Unknown')
            else:
                # Fallback to JWT decode if MCP verify fails
                token_data = decode_mandate_token(token)
                budget_remaining = token_data.get('budget_remaining', 'Unknown')
        except:
            # Fallback to JWT if MCP call fails
            token_data = decode_mandate_token(token)
            budget_remaining = token_data.get('budget_remaining', 'Unknown')

        print(f"\n♻️  Using existing mandate (Budget: ${budget_remaining})")
        print(f"   Token: {existing_mandate.get('mandate_token', 'N/A')[:50]}...")
        print(f"   To delete: rm ../.agentgatepay_mandates.json\n")
        mandate_budget = float(budget_remaining) if budget_remaining != 'Unknown' else MANDATE_BUDGET_USD
        purpose = "research resource"
    else:
        budget_input = input("\n💰 Enter mandate budget in USD (default: 100): ").strip()
        mandate_budget = float(budget_input) if budget_input else MANDATE_BUDGET_USD
        purpose = input("📝 Enter payment purpose (default: research resource): ").strip()
        purpose = purpose if purpose else "research resource"

    # Agent task
    task = f"""
    Purchase a {purpose} for ${RESOURCE_PRICE_USD} USD.

    Steps:
    1. Issue a payment mandate with a ${mandate_budget} budget (or reuse existing)
    2. Sign blockchain payment of ${RESOURCE_PRICE_USD} to seller: {SELLER_WALLET}
    3. Submit payment proof to AgentGatePay with mandate token

    The mandate token and transaction hashes will be available after steps 1 and 2.
    """

    try:
        # Run agent (LangGraph format expects messages)
        result = agent_executor.invoke({"messages": [("user", task)]})

        print("\n" + "=" * 80)
        print("PAYMENT WORKFLOW COMPLETED")
        print("=" * 80)

        # Extract final message from LangGraph response
        if "messages" in result:
            final_message = result["messages"][-1].content if result["messages"] else "No output"
            print(f"\nResult: {final_message}")
        else:
            print(f"\nResult: {result}")

        # Display final status
        if current_mandate:
            print(f"\nFinal Status:")
            print(f"  Mandate: {current_mandate.get('mandate_token', 'N/A')[:50]}...")
            print(f"  Budget remaining: ${current_mandate.get('budget_remaining', 'N/A')}")

        if 'merchant_tx_hash' in globals():
            print(f"\nBlockchain Transactions:")
            print(f"  Merchant TX: {config.explorer}/tx/{merchant_tx_hash}")
            print(f"  Commission TX: {config.explorer}/tx/{commission_tx_hash}")

            # Display gateway audit logs with curl commands
            print(f"\nGateway Audit Logs (copy-paste these commands):")
            print(f"\n# All payment logs (by wallet):")
            print(f"curl '{AGENTPAY_API_URL}/audit/logs?client_id={buyer_account.address}&event_type=x402_payment_settled&limit=10' \\")
            print(f"  -H 'x-api-key: {BUYER_API_KEY}' | python3 -m json.tool")
            print(f"\n# Recent payments (24h):")
            print(f"curl '{AGENTPAY_API_URL}/audit/logs?client_id={buyer_account.address}&event_type=x402_payment_settled&hours=24' \\")
            print(f"  -H 'x-api-key: {BUYER_API_KEY}' | python3 -m json.tool")
            print(f"\n# Payment verification (by tx_hash):")
            print(f"curl '{AGENTPAY_API_URL}/v1/payments/verify/{merchant_tx_hash}' \\")
            print(f"  -H 'x-api-key: {BUYER_API_KEY}' | python3 -m json.tool")

    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
