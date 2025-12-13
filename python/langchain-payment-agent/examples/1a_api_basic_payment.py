#!/usr/bin/env python3
"""
AgentGatePay + LangChain Integration - Example 1a: REST API + Local Signing

This example demonstrates a simple autonomous payment flow using:
- AgentGatePay REST API (via published SDK v1.1.5)
- LangChain agent with payment tools
- Local transaction signing (private key in .env)
- Multi-chain blockchain payments (Base, Ethereum, Polygon, Arbitrum)
- Multi-token support (USDC, USDT, DAI)

Flow:
1. Configure chain and token (from .env file)
2. Issue AP2 mandate ($100 budget)
3. Sign blockchain transactions locally (Web3.py)
4. Submit payment proof to AgentGatePay
5. Verify payment completion and view audit logs

Requirements:
- pip install agentgatepay-sdk>=1.1.5 langchain langchain-openai web3 python-dotenv
- .env file with configuration (see .env.example)

Multi-Chain Configuration:
- Edit .env file: PAYMENT_CHAIN=base (options: base, ethereum, polygon, arbitrum)
- Edit .env file: PAYMENT_TOKEN=USDC (options: USDC, USDT, DAI)
- Note: USDT not available on Base, DAI uses 18 decimals
- See README.md for complete chain/token compatibility matrix

For Production: See Example 1b (external TX signing service)
"""

import os
import sys
import time
import json
import base64
from typing import Dict, Any
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from agentgatepay_sdk import AgentGatePay
import requests

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
# See Example 1b (examples/1b_api_with_tx_service.py) for external signing usage.
#
# ========================================

# ========================================
# CONFIGURATION
# ========================================

AGENTPAY_API_URL = os.getenv('AGENTPAY_API_URL', 'https://api.agentgatepay.com')
BUYER_API_KEY = os.getenv('BUYER_API_KEY')
BUYER_EMAIL = os.getenv('BUYER_EMAIL')
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
# Note: USDT not available on Base. DAI uses 18 decimals. See README.md
config = None  # Will be set via get_or_create_config() in main()

# ========================================
# INITIALIZE CLIENTS
# ========================================
# Note: Clients initialized in main() after chain/token configuration

agentpay = None
web3 = None
buyer_account = None

# ========================================
# AGENT TOOLS
# ========================================

# Global mandate storage
current_mandate = None

def get_commission_config() -> dict:
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

def issue_payment_mandate(budget_usd: float) -> str:
    global current_mandate

    try:
        agent_id = f"research-assistant-{buyer_account.address}"
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
            'budget_remaining': budget_usd  # Initially, remaining = total
        }

        current_mandate = mandate_with_budget
        save_mandate(agent_id, mandate_with_budget)

        print(f"✅ Mandate created (Budget: ${budget_usd})")

        return f"MANDATE_TOKEN:{token}"

    except Exception as e:
        print(f"❌ Mandate failed: {str(e)}")
        return f"Failed: {str(e)}"


def sign_blockchain_payment(payment_input: str) -> str:
    try:
        parts = payment_input.split(',')
        if len(parts) != 2:
            return f"Error: Invalid format"

        amount_usd = float(parts[0].strip())
        recipient = parts[1].strip()

        commission_config = get_commission_config()
        if not commission_config:
            return "Error: Failed to fetch commission config"

        commission_address = commission_config['commission_address']
        commission_rate = commission_config['commission_rate']

        print(f"\n💳 Signing payment (${amount_usd} {config.token})...")
        print(f"   Chain: {config.chain.title()} (ID: {config.chain_id})")
        print(f"   Token: {config.token} ({config.decimals} decimals)")

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

        global merchant_tx_hash, commission_tx_hash, signed_amount_usd
        merchant_tx_hash = tx_hash_merchant
        commission_tx_hash = tx_hash_commission
        signed_amount_usd = amount_usd

        return f"TX_HASHES:{tx_hash_merchant},{tx_hash_commission}"

    except Exception as e:
        print(f"❌ Payment failed: {str(e)}")
        raise Exception(f"Payment failed: {str(e)}")


def submit_and_verify_payment(payment_data: str) -> str:
    global current_mandate

    try:
        parts = payment_data.split(',')
        if len(parts) != 4:
            return f"Error: Invalid format"

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
                    agent_id = f"research-assistant-{buyer_account.address}"
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
        func=sign_blockchain_payment,
        description="Sign and execute a blockchain payment on the configured network and token. Creates two transactions: merchant payment and gateway commission. Input should be 'amount_usd,recipient_address'."
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

# Create LangChain agent
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
    print("AGENTGATEPAY + LANGCHAIN: BASIC PAYMENT DEMO (REST API)")
    print("=" * 80)
    print()
    print("This demo shows an autonomous agent making a blockchain payment using:")
    print("  - AgentGatePay REST API (latest SDK)")
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
    agentpay = AgentGatePay(
        api_url=AGENTPAY_API_URL,
        api_key=BUYER_API_KEY
    )
    web3 = Web3(Web3.HTTPProvider(config.rpc_url))
    buyer_account = Account.from_key(BUYER_PRIVATE_KEY)

    print(f"\nInitialized AgentGatePay client: {AGENTPAY_API_URL}")
    print(f"Initialized Web3 client: {config.chain.title()} network")
    print(f"Buyer wallet: {buyer_account.address}\n")

    agent_id = f"research-assistant-{buyer_account.address}"
    existing_mandate = get_mandate(agent_id)

    if existing_mandate:
        token = existing_mandate.get('mandate_token')

        # Get LIVE budget from gateway (not JWT which is static)
        verify_response = requests.post(
            f"{AGENTPAY_API_URL}/mandates/verify",
            headers={"x-api-key": BUYER_API_KEY, "Content-Type": "application/json"},
            json={"mandate_token": token}
        )

        if verify_response.status_code == 200:
            verify_data = verify_response.json()
            budget_remaining = verify_data.get('budget_remaining', 'Unknown')
        else:
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
