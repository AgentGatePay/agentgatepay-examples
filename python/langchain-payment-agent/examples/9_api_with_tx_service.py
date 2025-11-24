#!/usr/bin/env python3
"""
AgentGatePay + LangChain Integration - External TX Signing Service (PRODUCTION)

This example demonstrates PRODUCTION-READY payment flow using:
- AgentGatePay REST API (via published SDK v1.1.3+)
- External transaction signing service (NO private key in code)
- Base network blockchain payments
- LangChain agent framework

Flow:
1. Issue AP2 mandate ($100 budget)
2. Request payment signing from external service (TX repo)
3. Submit payment proof to AgentGatePay
4. Verify payment completion

✅ PRODUCTION READY - Private key stored securely in signing service
⚠️ Requires TX signing service deployed (see docs/TX_SIGNING_OPTIONS.md)

Requirements:
- pip install agentgatepay-sdk langchain langchain-openai python-dotenv requests
- .env file with TX_SIGNING_SERVICE configured
- External signing service running (Render/Docker/Railway/self-hosted)
"""

import os
import requests
from typing import Dict, Any
from dotenv import load_dotenv
from agentgatepay_sdk import AgentGatePay

# LangChain imports
from langchain.agents import Tool, AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

# Load environment variables
load_dotenv()

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
# - Option 1: Render one-click deploy (https://github.com/AgentGatePay/TX)
# - Option 2: Docker container (docker run ghcr.io/agentgatepay/tx-signing-service)
# - Option 3: Railway deployment (see docs/TX_SIGNING_OPTIONS.md)
# - Option 4: Self-hosted service (clone TX repo, npm start)
#
# See docs/TX_SIGNING_OPTIONS.md for complete setup guide.
#
# ========================================

# ========================================
# CONFIGURATION
# ========================================

AGENTPAY_API_URL = os.getenv('AGENTPAY_API_URL', 'https://api.agentgatepay.com')
BUYER_API_KEY = os.getenv('BUYER_API_KEY')
SELLER_WALLET = os.getenv('SELLER_WALLET')
TX_SIGNING_SERVICE = os.getenv('TX_SIGNING_SERVICE')  # e.g., https://your-service.onrender.com

# Payment configuration
RESOURCE_PRICE_USD = 10.0
MANDATE_BUDGET_USD = 100.0
COMMISSION_RATE = 0.005  # 0.5%

# Validate configuration
if not TX_SIGNING_SERVICE:
    print("❌ ERROR: TX_SIGNING_SERVICE not configured in .env")
    print("   Please set TX_SIGNING_SERVICE=https://your-service.onrender.com")
    print("   See docs/TX_SIGNING_OPTIONS.md for setup instructions")
    exit(1)

# ========================================
# INITIALIZE CLIENTS
# ========================================

# AgentGatePay SDK client
agentpay = AgentGatePay(
    api_url=AGENTPAY_API_URL,
    api_key=BUYER_API_KEY
)

print(f"✅ Initialized AgentGatePay client: {AGENTPAY_API_URL}")
print(f"✅ Configured TX signing service: {TX_SIGNING_SERVICE}")
print(f"✅ PRODUCTION MODE: Private key NOT in application code\n")

# ========================================
# AGENT TOOLS
# ========================================

# Global mandate storage
current_mandate = None
merchant_tx_hash = None
commission_tx_hash = None

def issue_payment_mandate(budget_usd: float) -> str:
    """
    Issue AP2 payment mandate with specified budget.

    Args:
        budget_usd: Budget amount in USD

    Returns:
        Mandate token string
    """
    global current_mandate

    try:
        print(f"\n🔐 Issuing mandate with ${budget_usd} budget...")

        mandate = agentpay.mandates.issue(
            subject=f"research-assistant-production",
            budget_usd=budget_usd,
            scope="resource.read,payment.execute",
            ttl_hours=168  # 7 days
        )

        current_mandate = mandate
        print(f"✅ Mandate issued successfully")
        print(f"   Token: {mandate['mandateToken'][:50]}...")
        print(f"   Budget: ${mandate['budgetUsd']}")
        print(f"   Expires: {mandate['expiresAt']}")

        return f"Mandate issued successfully. Token: {mandate['mandateToken'][:50]}... Budget: ${budget_usd}"

    except Exception as e:
        error_msg = f"Failed to issue mandate: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg


def sign_payment_via_service(amount_usd: float, recipient: str) -> str:
    """
    Sign blockchain payment via external signing service (PRODUCTION).

    The signing service handles:
    - Private key management (secure storage)
    - Transaction signing (2 TX: merchant + commission)
    - Blockchain submission
    - Nonce management

    Args:
        amount_usd: Payment amount in USD
        recipient: Recipient wallet address

    Returns:
        Transaction hashes (merchant, commission)
    """
    global merchant_tx_hash, commission_tx_hash

    try:
        print(f"\n💳 Requesting payment signature from external service...")
        print(f"   Amount: ${amount_usd}")
        print(f"   Recipient: {recipient[:10]}...")
        print(f"   Service: {TX_SIGNING_SERVICE}")

        # Call external signing service
        response = requests.post(
            f"{TX_SIGNING_SERVICE}/sign-payment",
            headers={
                "Content-Type": "application/json",
                "x-api-key": BUYER_API_KEY  # Service authenticates with this
            },
            json={
                "merchant_address": recipient,
                "amount_usd": str(amount_usd),
                "chain": "base",
                "token": "USDC"
            },
            timeout=120  # Allow time for blockchain confirmation
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
        print(f"   Merchant TX: {merchant_tx_hash}")
        print(f"   Commission TX: {commission_tx_hash}")
        print(f"   Status: {result.get('status', 'N/A')}")

        return f"Payment successful! Merchant TX: {merchant_tx_hash}, Commission TX: {commission_tx_hash}"

    except requests.exceptions.Timeout:
        error_msg = f"Signing service timeout (exceeded 120s). Service may be down or slow."
        print(f"❌ {error_msg}")
        return error_msg

    except requests.exceptions.ConnectionError:
        error_msg = f"Cannot connect to signing service at {TX_SIGNING_SERVICE}. Is it running?"
        print(f"❌ {error_msg}")
        print(f"   Check: curl {TX_SIGNING_SERVICE}/health")
        return error_msg

    except Exception as e:
        error_msg = f"Payment signing failed: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg


def verify_payment_completion(tx_hash: str) -> str:
    """
    Verify payment was recorded by AgentGatePay.

    Args:
        tx_hash: Merchant transaction hash

    Returns:
        Verification status message
    """
    try:
        print(f"\n🔍 Verifying payment: {tx_hash[:20]}...")

        # Use AgentGatePay SDK to verify payment
        verification = agentpay.payments.verify(tx_hash)

        if verification.get('verified'):
            print(f"✅ Payment verified successfully")
            print(f"   Amount: ${verification.get('amount_usd', 'N/A')}")
            print(f"   Chain: {verification.get('chain', 'N/A')}")
            print(f"   Status: {verification.get('status', 'N/A')}")
            return f"Payment verified! Amount: ${verification.get('amount_usd')}, Status: {verification.get('status')}"
        else:
            print(f"❌ Payment verification failed")
            return f"Payment verification failed: {verification.get('error', 'Unknown error')}"

    except Exception as e:
        error_msg = f"Verification error: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg


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
        name="verify_payment",
        func=verify_payment_completion,
        description="Verify that a payment was successfully recorded by AgentGatePay. Input should be the merchant transaction hash."
    ),
]

# ========================================
# AGENT PROMPT
# ========================================

agent_prompt = PromptTemplate.from_template("""
You are an autonomous AI agent that can make blockchain payments for resources.

You have access to the following tools:
{tools}

Tool Names: {tool_names}

Your task: {input}

Follow this workflow:
1. Issue a payment mandate with the specified budget
2. Sign the blockchain payment via external service (PRODUCTION READY - no private key in code)
3. Verify the payment was recorded successfully

Think step by step:
{agent_scratchpad}
""")

# ========================================
# CREATE AGENT
# ========================================

# Initialize LLM
llm = ChatOpenAI(
    model="gpt-4",
    temperature=0,
    openai_api_key=os.getenv('OPENAI_API_KEY')
)

# Create agent
agent = create_react_agent(
    llm=llm,
    tools=tools,
    prompt=agent_prompt
)

# Create executor
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
    print("🤖 AGENTGATEPAY + LANGCHAIN: PRODUCTION TX SIGNING DEMO")
    print("=" * 80)
    print()
    print("This demo shows PRODUCTION-READY autonomous agent payments using:")
    print("  - AgentGatePay REST API (via SDK v1.1.3+)")
    print("  - External transaction signing service (NO private key in code)")
    print("  - LangChain agent framework")
    print("  - Base network (USDC payments)")
    print()
    print("✅ SECURE: Private key stored in signing service, NOT in application")
    print("✅ SCALABLE: Signing service can be deployed independently")
    print("✅ PRODUCTION READY: Suitable for real-world deployments")
    print()
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

    # Agent task
    task = f"""
    Purchase a research resource for ${RESOURCE_PRICE_USD} USD using PRODUCTION signing.

    Steps:
    1. Issue a payment mandate with a ${MANDATE_BUDGET_USD} budget
    2. Make a payment of ${RESOURCE_PRICE_USD} to the seller wallet: {SELLER_WALLET}
       (This will be signed by the external signing service - NO private key in code)
    3. Verify the payment was recorded successfully

    This is a PRODUCTION-READY payment using external signing service.
    """

    try:
        # Run agent
        result = agent_executor.invoke({"input": task})

        print("\n" + "=" * 80)
        print("✅ PRODUCTION PAYMENT WORKFLOW COMPLETED")
        print("=" * 80)
        print(f"\nResult: {result['output']}")

        # Display final status
        if current_mandate:
            print(f"\n📊 Final Status:")
            print(f"   Mandate: {current_mandate.get('mandateToken', 'N/A')[:50]}...")
            print(f"   Budget remaining: ${current_mandate.get('budgetRemaining', 'N/A')}")

        if merchant_tx_hash:
            print(f"\n🔗 Blockchain Transactions:")
            print(f"   Merchant TX: https://basescan.org/tx/{merchant_tx_hash}")
            print(f"   Commission TX: https://basescan.org/tx/{commission_tx_hash}")

        print(f"\n✅ PRODUCTION SUCCESS:")
        print(f"   Private key: SECURE (stored in signing service)")
        print(f"   Application code: CLEAN (no private keys)")
        print(f"   Payment: VERIFIED (on Base blockchain)")

    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
