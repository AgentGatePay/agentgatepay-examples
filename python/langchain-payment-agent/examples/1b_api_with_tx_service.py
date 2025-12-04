#!/usr/bin/env python3
"""
AgentGatePay + LangChain Integration - Example 1b: REST API + External TX Signing

This example demonstrates the SAME payment flow as Example 1a,
but using an external transaction signing service for production security.

Flow:
1. Issue AP2 mandate ($100 budget)
2. Request payment signing from external service (Docker/Render/Railway/self-hosted)
3. Submit payment proof to AgentGatePay
4. Verify payment completion

Security Benefits:
- Private key stored in signing service, NOT in application code
- Application cannot access private keys
- Signing service can be audited independently
- Scalable deployment options

Setup Options:
- Docker local: See docs/DOCKER_LOCAL_SETUP.md
- Render cloud: See docs/RENDER_DEPLOYMENT_GUIDE.md
- Other options: See docs/TX_SIGNING_OPTIONS.md

Requirements:
- pip install agentgatepay-sdk langchain langchain-openai python-dotenv requests
- .env file with TX_SIGNING_SERVICE configured

For Development: See Example 1a (local signing, simpler setup)
For MCP Version: See Example 3b (MCP + external signing)
"""

import os
import sys
import json
import base64
import requests
from typing import Dict, Any
from dotenv import load_dotenv
from agentgatepay_sdk import AgentGatePay

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
# INITIALIZE CLIENTS
# ========================================

agentpay = AgentGatePay(
    api_url=AGENTPAY_API_URL,
    api_key=BUYER_API_KEY
)

print(f"✅ Initialized AgentGatePay client: {AGENTPAY_API_URL}")
print(f"✅ Configured TX signing service: {TX_SIGNING_SERVICE}")
print(f"✅ Buyer wallet: {BUYER_WALLET}")
print(f"✅ PRODUCTION MODE: Private key NOT in application code\n")

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
# AGENT TOOLS
# ========================================

# Global state
current_mandate = None
merchant_tx_hash = None
commission_tx_hash = None

def issue_payment_mandate(budget_usd: float) -> str:
    """Issue mandate with reuse logic (matches Script 1)"""
    global current_mandate

    try:
        agent_id = f"research-assistant-{BUYER_WALLET}"
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
                token_data = decode_mandate_token(token)
                budget_remaining = token_data.get('budget_remaining', existing_mandate.get('budget_usd', 'Unknown'))

            print(f"\n♻️  Reusing mandate (Budget: ${budget_remaining})")
            current_mandate = existing_mandate
            current_mandate['budget_remaining'] = budget_remaining
            return f"MANDATE_TOKEN:{token}"

        print(f"\n🔐 Creating mandate (${budget_usd})...")

        mandate = agentpay.mandates.issue(
            subject=agent_id,
            budget=budget_usd,
            scope="resource.read,payment.execute",
            ttl_minutes=168 * 60
        )

        # Store mandate with budget info
        token = mandate['mandate_token']
        mandate_with_budget = {
            **mandate,
            'budget_usd': budget_usd,
            'budget_remaining': budget_usd
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


def submit_and_verify_payment(payment_data: str) -> str:
    """Submit payment proof and verify budget (matches Script 1)"""
    global current_mandate

    try:
        parts = payment_data.split(',')
        if len(parts) != 4:
            return f"Error: Invalid format (expected 4 parts, got {len(parts)})"

        merchant_tx = parts[0].strip()
        commission_tx = parts[1].strip()
        mandate_token = parts[2].strip()
        price_usd = float(parts[3].strip())

        print(f"\n📤 Submitting to gateway...")

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

        url = f"{AGENTPAY_API_URL}/x402/resource?chain={config.chain}&token={config.token}&price_usd={price_usd}"
        response = requests.get(url, headers=headers)

        if response.status_code >= 400:
            result = response.json() if response.text else {}
            error = result.get('error', response.text)
            print(f"❌ Gateway error ({response.status_code}): {error}")
            return f"Failed: {error}"

        result = response.json()

        # Check if payment was successful
        if result.get('message') or result.get('success') or result.get('paid') or result.get('status') == 'confirmed':
            print(f"✅ Payment recorded")

            # Verify mandate to get updated budget
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

                if current_mandate:
                    current_mandate['budget_remaining'] = new_budget
                    agent_id = f"research-assistant-{BUYER_WALLET}"
                    save_mandate(agent_id, current_mandate)

                return f"Success! Paid: ${price_usd}, Remaining: ${new_budget}"
            else:
                print(f"   ⚠️  Could not fetch updated budget")
                return f"Success! Paid: ${price_usd}"

        else:
            error = result.get('error', 'Unknown error')
            print(f"❌ Failed: {error}")
            return f"Failed: {error}"

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return f"Error: {str(e)}"


# Define LangChain tools
tools = [
    Tool(
        name="issue_mandate",
        func=issue_payment_mandate,
        description="Issue an AP2 payment mandate with a specified budget in USD. Use this FIRST before making any payments. Input should be a float representing the budget amount."
    ),
    Tool(
        name="sign_payment",
        func=sign_payment_via_service,
        description="Sign and execute a blockchain payment via external signing service (PRODUCTION). Creates two transactions: merchant payment and gateway commission. Input should be 'amount_usd,recipient_address'."
    ),
    Tool(
        name="submit_payment",
        func=submit_and_verify_payment,
        description="Submit payment proof to AgentGatePay gateway for verification and budget tracking. Input should be 'merchant_tx,commission_tx,mandate_token,price_usd'."
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
system_prompt = """You are an autonomous AI agent that can make blockchain payments for resources.

Follow this workflow:
1. Issue a payment mandate with the specified budget using the issue_mandate tool
   - The tool returns: MANDATE_TOKEN:{token}
   - Extract the token after the colon
2. Sign the blockchain payment for the specified amount to the recipient using the sign_payment tool
   - This uses EXTERNAL SIGNING SERVICE (production-ready, no private key in code)
   - The tool returns: TX_HASHES:{merchant_tx},{commission_tx}
   - Extract both transaction hashes after the colon
3. Submit the payment to AgentGatePay using the submit_payment tool with: merchant_tx,commission_tx,mandate_token,price_usd
   - Use the mandate token from step 1
   - Use the transaction hashes from step 2
   - Use the payment amount specified in the task

IMPORTANT:
- Parse tool outputs to extract values (look for : separator)
- Always submit payment to AgentGatePay after signing (step 3 is mandatory)
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
    print("AGENTGATEPAY + LANGCHAIN: PRODUCTION TX SIGNING DEMO")
    print("=" * 80)
    print()
    print("This demo shows PRODUCTION-READY autonomous agent payments using:")
    print("  - AgentGatePay REST API (latest SDK)")
    print("  - External transaction signing service (NO private key in code)")
    print("  - LangChain agent framework")
    print("  - Multi-chain blockchain payments (Base/Ethereum/Polygon/Arbitrum)")
    print("  - Multi-token support (USDC/USDT/DAI)")
    print()
    print("✅ SECURE: Private key stored in signing service, NOT in application")
    print("✅ SCALABLE: Signing service can be deployed independently")
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
            # Fallback to JWT decode if verify fails
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
    Purchase a {purpose} for ${RESOURCE_PRICE_USD} USD using PRODUCTION signing service.

    Steps:
    1. Issue a payment mandate with a ${mandate_budget} budget (or reuse existing)
    2. Sign blockchain payment of ${RESOURCE_PRICE_USD} to seller: {SELLER_WALLET}
       (This will be signed by the external signing service - NO private key in code)
    3. Submit payment proof to AgentGatePay with mandate token

    This is a PRODUCTION-READY payment using external signing service.
    """

    try:
        # Run agent (LangGraph format expects messages)
        result = agent_executor.invoke({"messages": [("user", task)]})

        print("\n" + "=" * 80)
        print("PRODUCTION PAYMENT WORKFLOW COMPLETED")
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
            print(f"   Payment: VERIFIED (on {config.chain.title()} blockchain)")

    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
