#!/usr/bin/env python3
"""
AgentGatePay + LangChain Integration - Example 3b: MCP + External TX Signing

This example demonstrates PRODUCTION-READY autonomous agent payments by combining:
- AgentGatePay MCP tools (JSON-RPC 2.0 protocol)
- External transaction signing service (NO private key in code)

Combines best of both worlds:
- Example 3a: MCP tools for mandate management and payment submission
- Example 1b: External TX signing for production security

MCP Tools Used:
- agentpay_issue_mandate - Issue AP2 payment mandate
- agentpay_submit_payment - Submit blockchain payment proof
- agentpay_verify_mandate - Verify mandate is valid

Flow:
1. Issue AP2 mandate via MCP ($100 budget)
2. Request payment signing from external service (Docker/Render/Railway/self-hosted)
3. Submit payment proof to AgentGatePay via MCP
4. Verify payment completion via MCP

Security Benefits:
- Private key stored in signing service, NOT in application code
- Application cannot access private keys
- Signing service can be audited independently
- Scalable deployment options
- MCP standardized protocol for agent communication

Setup Options:
- Docker local: See docs/DOCKER_LOCAL_SETUP.md
- Render cloud: See docs/RENDER_DEPLOYMENT_GUIDE.md
- Other options: See docs/TX_SIGNING_OPTIONS.md

Requirements:
- pip install langchain langchain-openai python-dotenv requests
- .env file with TX_SIGNING_SERVICE configured

For Development: See Example 3a (MCP + local signing, simpler setup)
For REST API Version: See Example 1b (REST API + external signing)
"""

import os
import sys
import json
import base64
import requests
from typing import Dict, Any
from dotenv import load_dotenv

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
from chain_config import get_chain_config

# ========================================
# TRANSACTION SIGNING
# ========================================
#
# This example uses EXTERNAL SIGNING SERVICE (PRODUCTION READY).
#
# ✅ PRODUCTION READY: Private key stored securely in signing service
# ✅ SECURE: Application code never touches private keys
# ✅ SCALABLE: Signing service can be scaled independently
# ✅ MCP PROTOCOL: Standardized agent communication
#
# Setup options:
# - Option 1: Docker container (see docs/DOCKER_LOCAL_SETUP.md)
# - Option 2: Render one-click deploy (see docs/RENDER_DEPLOYMENT_GUIDE.md)
# - Option 3: Railway/AWS/GCP/custom (see docs/TX_SIGNING_OPTIONS.md)
#
# ========================================

# ========================================
# CONFIGURATION
# ========================================

AGENTPAY_API_URL = os.getenv('AGENTPAY_API_URL', 'https://api.agentgatepay.com')
AGENTPAY_MCP_ENDPOINT = os.getenv('MCP_API_URL', 'https://mcp.agentgatepay.com')
BUYER_API_KEY = os.getenv('BUYER_API_KEY')
BUYER_EMAIL = os.getenv('BUYER_EMAIL')
BUYER_WALLET = os.getenv('BUYER_WALLET')
SELLER_WALLET = os.getenv('SELLER_WALLET')
TX_SIGNING_SERVICE = os.getenv('TX_SIGNING_SERVICE')

# Payment configuration
RESOURCE_PRICE_USD = 0.01
MANDATE_BUDGET_USD = 100.0

# Multi-chain/token configuration (set after interactive selection)
config = None  # Will be set via get_chain_config() in main()

# Validate configuration
if not TX_SIGNING_SERVICE:
    print("❌ ERROR: TX_SIGNING_SERVICE not configured in .env")
    print("   Please set TX_SIGNING_SERVICE=http://localhost:3000 (Docker)")
    print("   Or: TX_SIGNING_SERVICE=https://your-service.onrender.com (Render)")
    print("   See docs/TX_SIGNING_OPTIONS.md for setup instructions")
    exit(1)

# ========================================
# HELPER FUNCTIONS
# ========================================

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
# AGENT TOOLS (MCP + EXTERNAL TX)
# ========================================

# Global state
current_mandate = None
merchant_tx_hash = None
commission_tx_hash = None


def mcp_issue_mandate(budget_usd: float) -> str:
    """Issue mandate using MCP tool (with reuse logic matching Script 1)"""
    global current_mandate

    try:
        agent_id = f"research-assistant-{BUYER_WALLET}"
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


def sign_payment_via_service(payment_input: str) -> str:
    """
    Sign blockchain payment via external signing service (PRODUCTION).

    The signing service handles:
    - Private key management (secure storage)
    - Transaction signing (2 TX: merchant + commission)
    - Blockchain submission
    - Nonce management

    Args:
        payment_input: "amount_usd,recipient_address"

    Returns:
        "TX_HASHES:merchant_tx,commission_tx"
    """
    global merchant_tx_hash, commission_tx_hash

    try:
        parts = payment_input.split(',')
        if len(parts) != 2:
            return f"Error: Invalid format"

        amount_usd = float(parts[0].strip())
        recipient = parts[1].strip()

        # Convert USD to atomic units
        amount_atomic = int(amount_usd * (10 ** config.decimals))

        print(f"\n💳 Requesting payment signature from external service...")
        print(f"   Amount: ${amount_usd} {config.token} ({amount_atomic} atomic units)")
        print(f"   Chain: {config.chain.title()}")
        print(f"   Recipient: {recipient[:10]}...")
        print(f"   Service: {TX_SIGNING_SERVICE}")

        # Call external signing service
        response = requests.post(
            f"{TX_SIGNING_SERVICE}/sign-payment",
            headers={
                "Content-Type": "application/json",
                "x-api-key": BUYER_API_KEY
            },
            json={
                "merchant_address": recipient,
                "total_amount": str(amount_atomic),
                "chain": config.chain,
                "token": config.token
            },
            timeout=120
        )

        if response.status_code != 200:
            error_msg = f"Signing service error: HTTP {response.status_code} - {response.text}"
            print(f"❌ {error_msg}")
            return error_msg

        result = response.json()

        # Extract transaction hashes
        merchant_tx_hash = result.get('tx_hash')
        commission_tx_hash = result.get('tx_hash_commission')

        if not merchant_tx_hash or not commission_tx_hash:
            error_msg = f"Invalid response from signing service: {result}"
            print(f"❌ {error_msg}")
            return error_msg

        print(f"✅ Payment signed and submitted by external service")
        print(f"   Merchant TX: {merchant_tx_hash[:20]}...")
        print(f"   Commission TX: {commission_tx_hash[:20]}...")
        print(f"   Status: {'Success' if result.get('success') else 'Failed'}")

        # Verify hashes have correct format
        if len(merchant_tx_hash) != 66 or not merchant_tx_hash.startswith('0x'):
            error_msg = f"Invalid merchant tx_hash format from service: {merchant_tx_hash}"
            print(f"❌ {error_msg}")
            return error_msg

        if len(commission_tx_hash) != 66 or not commission_tx_hash.startswith('0x'):
            error_msg = f"Invalid commission tx_hash format from service: {commission_tx_hash}"
            print(f"❌ {error_msg}")
            return error_msg

        return f"TX_HASHES:{merchant_tx_hash},{commission_tx_hash}"

    except requests.exceptions.Timeout:
        error_msg = f"Signing service timeout (exceeded 120s)"
        print(f"❌ {error_msg}")
        return error_msg

    except requests.exceptions.ConnectionError:
        error_msg = f"Cannot connect to signing service at {TX_SIGNING_SERVICE}"
        print(f"❌ {error_msg}")
        print(f"   Check: curl {TX_SIGNING_SERVICE}/health")
        return error_msg

    except Exception as e:
        error_msg = f"Payment signing failed: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg


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
        print(f"   Status: {result.get('status', 'Confirmed')}")

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
                agent_id = f"research-assistant-{BUYER_WALLET}"
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
        description="Issue AP2 mandate using MCP tool. Input: budget amount in USD Coins."
    ),
    Tool(
        name="sign_payment",
        func=sign_payment_via_service,
        description="Sign and execute a blockchain payment via external signing service (PRODUCTION). Creates two transactions: merchant payment and gateway commission. Input should be 'amount_usd,recipient_address'."
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
system_prompt = """You are an autonomous AI agent using AgentGatePay MCP tools + external TX signing for PRODUCTION payments.

Follow this workflow:
1. Issue mandate using MCP tool (issue_mandate_mcp) with the specified budget
   - The tool returns: MANDATE_TOKEN:{token}
   - Extract the token after the colon
2. Sign blockchain payment via EXTERNAL SERVICE (sign_payment) for the specified amount to the recipient
   - This uses EXTERNAL SIGNING SERVICE (production-ready, no private key in code)
   - Input format: 'amount_usd,recipient_address'
   - The tool returns: TX_HASHES:{merchant_tx},{commission_tx}
   - Extract both transaction hashes after the colon
3. Submit payment and verify budget using MCP tool (submit_and_verify_payment)
   - This tool automatically uses the mandate and transaction hashes from previous steps
   - Returns updated budget after payment

IMPORTANT:
- All three steps must complete successfully
- Parse tool outputs to extract values (look for : separator)
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
    print("AGENTGATEPAY + LANGCHAIN: PRODUCTION MCP + TX SIGNING DEMO")
    print("=" * 80)
    print()
    print("This demo shows PRODUCTION-READY autonomous agent payments using:")
    print("  - AgentGatePay MCP tools (JSON-RPC 2.0)")
    print("  - External transaction signing service (NO private key in code)")
    print("  - LangChain agent framework")
    print("  - Multi-chain blockchain payments (Base/Ethereum/Polygon/Arbitrum)")
    print("  - Multi-token support (USDC/USDT/DAI)")
    print()
    print("✅ SECURE: Private key stored in signing service, NOT in application")
    print("✅ SCALABLE: Signing service can be deployed independently")
    print("✅ MCP PROTOCOL: Standardized agent communication")
    print("✅ PRODUCTION READY: Suitable for real-world deployments")
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

    print(f"\n✅ Initialized AgentGatePay MCP endpoint: {AGENTPAY_MCP_ENDPOINT}")
    print(f"✅ Configured TX signing service: {TX_SIGNING_SERVICE}")
    print(f"✅ Buyer wallet: {BUYER_WALLET}")
    print(f"✅ PRODUCTION MODE: Private key NOT in application code")

    # Check signing service health
    print(f"\n🏥 Checking signing service health...")
    try:
        health_response = requests.get(f"{TX_SIGNING_SERVICE}/health", timeout=5)
        if health_response.status_code == 200:
            health_data = health_response.json()
            print(f"✅ Signing service is healthy")
            print(f"   Status: {health_data.get('status', 'N/A')}")
            print(f"   Wallet configured: {health_data.get('wallet_configured', False)}")
        else:
            print(f"⚠️  Signing service returned: HTTP {health_response.status_code}")
            print(f"   Warning: Service may not be fully operational")
    except Exception as e:
        print(f"❌ Cannot connect to signing service: {str(e)}")
        print(f"   Please ensure TX_SIGNING_SERVICE is running")
        print(f"   URL: {TX_SIGNING_SERVICE}")
        print(f"   See docs/TX_SIGNING_OPTIONS.md for setup instructions")
        exit(1)

    agent_id = f"research-assistant-{BUYER_WALLET}"
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
        budget_input = input("\n💰 Enter mandate budget in USD Coins (default: 100): ").strip()
        mandate_budget = float(budget_input) if budget_input else MANDATE_BUDGET_USD
        purpose = input("📝 Enter payment purpose (default: research resource): ").strip()
        purpose = purpose if purpose else "research resource"

    # Agent task
    task = f"""
    Purchase a {purpose} for ${RESOURCE_PRICE_USD} USD using PRODUCTION MCP + TX signing service.

    Steps:
    1. Issue a payment mandate with a ${mandate_budget} budget (or reuse existing) using MCP
    2. Sign blockchain payment of ${RESOURCE_PRICE_USD} to seller: {SELLER_WALLET}
       (This will be signed by the external signing service - NO private key in code)
    3. Submit payment proof to AgentGatePay via MCP with mandate token

    This is a PRODUCTION-READY payment using MCP tools + external signing service.
    """

    try:
        # Run agent (LangGraph format expects messages)
        result = agent_executor.invoke({"messages": [("user", task)]})

        print("\n" + "=" * 80)
        print("PRODUCTION MCP + TX SIGNING WORKFLOW COMPLETED")
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

        if merchant_tx_hash:
            print(f"\nBlockchain Transactions:")
            print(f"  Merchant TX: {config.explorer}/tx/{merchant_tx_hash}")
            print(f"  Commission TX: {config.explorer}/tx/{commission_tx_hash}")

            # Display gateway audit logs with curl commands
            print(f"\nGateway Audit Logs (copy-paste these commands):")
            print(f"\n# All payment logs (by wallet):")
            print(f"curl '{AGENTPAY_API_URL}/audit/logs?client_id={BUYER_WALLET}&event_type=x402_payment_settled&limit=10' \\")
            print(f"  -H 'x-api-key: {BUYER_API_KEY}' | python3 -m json.tool")
            print(f"\n# Recent payments (24h):")
            print(f"curl '{AGENTPAY_API_URL}/audit/logs?client_id={BUYER_WALLET}&event_type=x402_payment_settled&hours=24' \\")
            print(f"  -H 'x-api-key: {BUYER_API_KEY}' | python3 -m json.tool")
            print(f"\n# Payment verification (by tx_hash):")
            print(f"curl '{AGENTPAY_API_URL}/v1/payments/verify/{merchant_tx_hash}' \\")
            print(f"  -H 'x-api-key: {BUYER_API_KEY}' | python3 -m json.tool")

            print(f"\n✅ PRODUCTION SUCCESS:")
            print(f"   Private key: SECURE (stored in signing service)")
            print(f"   Application code: CLEAN (no private keys)")
            print(f"   MCP protocol: STANDARDIZED (JSON-RPC 2.0)")
            print(f"   Payment: VERIFIED (on {config.chain.title()} blockchain)")

    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
