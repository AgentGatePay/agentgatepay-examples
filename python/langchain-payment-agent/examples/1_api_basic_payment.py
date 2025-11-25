#!/usr/bin/env python3
"""
AgentGatePay + LangChain Integration - Basic Payment Flow (REST API)

This example demonstrates a simple autonomous payment flow using:
- AgentGatePay REST API (via published SDK v1.1.0)
- LangChain agent with payment tools
- Base network blockchain payments

Flow:
1. Issue AP2 mandate ($100 budget)
2. Sign blockchain transaction (USDC on Base)
3. Submit payment proof to AgentGatePay
4. Verify payment completion

Requirements:
- pip install agentgatepay-sdk langchain langchain-openai web3 python-dotenv
- .env file with configuration (see .env.example)
"""

import os
import time
from typing import Dict, Any
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from agentgatepay_sdk import AgentGatePay

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
BUYER_API_KEY = os.getenv('BUYER_API_KEY')
BASE_RPC_URL = os.getenv('BASE_RPC_URL', 'https://mainnet.base.org')
BUYER_PRIVATE_KEY = os.getenv('BUYER_PRIVATE_KEY')
SELLER_WALLET = os.getenv('SELLER_WALLET')
COMMISSION_ADDRESS = os.getenv('AGENTPAY_COMMISSION_ADDRESS')

# Payment configuration
RESOURCE_PRICE_USD = 0.01
MANDATE_BUDGET_USD = 100.0
COMMISSION_RATE = 0.005  # 0.5%

# USDC contract on Base
USDC_CONTRACT_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
USDC_DECIMALS = 6

# ========================================
# INITIALIZE CLIENTS
# ========================================

# AgentGatePay SDK client
agentpay = AgentGatePay(
    api_url=AGENTPAY_API_URL,
    api_key=BUYER_API_KEY
)

# Web3 client for blockchain interaction
web3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))
buyer_account = Account.from_key(BUYER_PRIVATE_KEY)

print(f"✅ Initialized AgentGatePay client: {AGENTPAY_API_URL}")
print(f"✅ Initialized Web3 client (Base network)")
print(f"✅ Buyer wallet: {buyer_account.address}\n")

# ========================================
# AGENT TOOLS
# ========================================

# Global mandate storage
current_mandate = None

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
        agent_id = f"research-assistant-{buyer_account.address}"

        # Check for existing mandate
        existing_mandate = get_mandate(agent_id)
        if existing_mandate:
            print(f"\n♻️  Reusing existing mandate...")
            print(f"   Budget remaining: ${existing_mandate.get('budget_remaining', 'N/A')}")
            current_mandate = existing_mandate
            return f"Reusing existing mandate. Budget remaining: ${existing_mandate.get('budget_remaining')}"

        print(f"\n🔐 Creating new mandate with ${budget_usd} budget...")

        mandate = agentpay.mandates.issue(
            subject=agent_id,
            budget=budget_usd,
            scope="resource.read,payment.execute",
            ttl_minutes=168 * 60  # 7 days in minutes
        )

        current_mandate = mandate
        save_mandate(agent_id, mandate)

        print(f"✅ Mandate issued successfully")
        print(f"   Token: {mandate['mandate_token'][:50]}...")
        print(f"   Budget: ${mandate['budget_usd']}")
        print(f"   Expires: {mandate['expires_at']}")

        return f"Mandate issued successfully. Token: {mandate['mandate_token'][:50]}... Budget: ${budget_usd}"

    except Exception as e:
        error_msg = f"Failed to issue mandate: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg


def sign_blockchain_payment(amount_usd: float, recipient: str) -> str:
    """
    Sign and execute blockchain payment (USDC on Base).
    Creates TWO transactions: merchant payment + commission.

    Args:
        amount_usd: Payment amount in USD
        recipient: Recipient wallet address

    Returns:
        Transaction hashes (merchant, commission)
    """
    try:
        print(f"\n💳 Signing blockchain payment: ${amount_usd} to {recipient[:10]}...")

        # Calculate amounts (merchant + commission)
        commission_amount_usd = amount_usd * COMMISSION_RATE
        merchant_amount_usd = amount_usd - commission_amount_usd

        # Convert to atomic units (USDC has 6 decimals)
        merchant_amount_atomic = int(merchant_amount_usd * (10 ** USDC_DECIMALS))
        commission_amount_atomic = int(commission_amount_usd * (10 ** USDC_DECIMALS))

        print(f"   Merchant amount: ${merchant_amount_usd:.4f} ({merchant_amount_atomic} atomic units)")
        print(f"   Commission amount: ${commission_amount_usd:.4f} ({commission_amount_atomic} atomic units)")

        # USDC ERC-20 transfer function signature
        transfer_function_signature = web3.keccak(text="transfer(address,uint256)")[:4]

        # Transaction 1: Merchant payment
        print(f"\n   📤 Signing transaction 1 (merchant)...")
        merchant_data = transfer_function_signature + \
                       web3.to_bytes(hexstr=recipient).rjust(32, b'\x00') + \
                       merchant_amount_atomic.to_bytes(32, byteorder='big')

        merchant_tx = {
            'nonce': web3.eth.get_transaction_count(buyer_account.address),
            'to': USDC_CONTRACT_BASE,
            'value': 0,
            'gas': 100000,
            'gasPrice': web3.eth.gas_price,
            'data': merchant_data,
            'chainId': 8453  # Base mainnet
        }

        signed_merchant_tx = buyer_account.sign_transaction(merchant_tx)
        tx_hash_merchant = web3.eth.send_raw_transaction(signed_merchant_tx.raw_transaction)

        print(f"   ✅ Merchant TX sent: {tx_hash_merchant.hex()}")

        # Wait for merchant transaction to be mined
        print(f"   ⏳ Waiting for merchant TX confirmation...")
        merchant_receipt = web3.eth.wait_for_transaction_receipt(tx_hash_merchant, timeout=60)
        print(f"   ✅ Merchant TX confirmed in block {merchant_receipt['blockNumber']}")

        # Get fresh nonce after first TX confirms
        time.sleep(2)

        # Transaction 2: Commission payment
        print(f"\n   📤 Signing transaction 2 (commission)...")
        commission_data = transfer_function_signature + \
                         web3.to_bytes(hexstr=COMMISSION_ADDRESS).rjust(32, b'\x00') + \
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

        signed_commission_tx = buyer_account.sign_transaction(commission_tx)
        tx_hash_commission = web3.eth.send_raw_transaction(signed_commission_tx.raw_transaction)

        print(f"   ✅ Commission TX sent: {tx_hash_commission.hex()}")

        # Wait for commission transaction
        print(f"   ⏳ Waiting for commission TX confirmation...")
        commission_receipt = web3.eth.wait_for_transaction_receipt(tx_hash_commission, timeout=60)
        print(f"   ✅ Commission TX confirmed in block {commission_receipt['blockNumber']}")

        result = f"Payment successful! Merchant TX: {tx_hash_merchant.hex()}, Commission TX: {tx_hash_commission.hex()}"

        # Store transaction hashes globally for verification
        global merchant_tx_hash, commission_tx_hash
        merchant_tx_hash = tx_hash_merchant.hex()
        commission_tx_hash = tx_hash_commission.hex()

        return result

    except Exception as e:
        error_msg = f"Payment failed: {str(e)}"
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
        func=sign_blockchain_payment,
        description="Sign and execute a blockchain payment in USDC on Base network. Creates two transactions: merchant payment and gateway commission. Input should be 'amount_usd,recipient_address'."
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
2. Sign the blockchain payment for the specified amount to the specified recipient
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
    print("🤖 AGENTGATEPAY + LANGCHAIN: BASIC PAYMENT DEMO (REST API)")
    print("=" * 80)
    print()
    print("This demo shows an autonomous agent making a blockchain payment using:")
    print("  - AgentGatePay REST API (via SDK v1.1.0)")
    print("  - LangChain agent framework")
    print("  - Base network (USDC payments)")
    print()
    print("=" * 80)

    # Get user input
    budget_input = input("\n💰 Enter mandate budget amount in USD (default: 100): ").strip()
    mandate_budget = float(budget_input) if budget_input else MANDATE_BUDGET_USD

    purpose = input("📝 Enter payment purpose (default: research resource): ").strip()
    purpose = purpose if purpose else "research resource"

    # Agent task
    task = f"""
    Purchase a {purpose} for ${RESOURCE_PRICE_USD} USD.

    Steps:
    1. Issue a payment mandate with a ${mandate_budget} budget
    2. Make a payment of ${RESOURCE_PRICE_USD} to the seller wallet: {SELLER_WALLET}
    3. Verify the payment was recorded successfully
    """

    try:
        # Run agent
        result = agent_executor.invoke({"input": task})

        print("\n" + "=" * 80)
        print("✅ PAYMENT WORKFLOW COMPLETED")
        print("=" * 80)
        print(f"\nResult: {result['output']}")

        # Display final status
        if current_mandate:
            print(f"\n📊 Final Status:")
            print(f"   Mandate: {current_mandate.get('mandate_token', 'N/A')[:50]}...")
            print(f"   Budget remaining: ${current_mandate.get('budget_remaining', 'N/A')}")

        if 'merchant_tx_hash' in globals():
            print(f"   Merchant TX: https://basescan.org/tx/{merchant_tx_hash}")
            print(f"   Commission TX: https://basescan.org/tx/{commission_tx_hash}")

    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
