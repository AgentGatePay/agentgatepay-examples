#!/usr/bin/env python3
"""
AgentGatePay + LangChain Integration - Payment with Audit Logs (REST API)

This example demonstrates payment tracking and audit logging using:
- AgentGatePay REST API (via SDK v1.1.0)
- Comprehensive audit log retrieval
- Budget tracking and analytics
- Transaction history monitoring

Features demonstrated:
1. Issue mandate with budget tracking
2. Execute payment with automatic audit logging
3. Retrieve audit logs filtered by event type
4. Analyze spending patterns
5. Monitor budget utilization

Requirements:
- pip install agentgatepay-sdk langchain langchain-openai web3 python-dotenv
- .env file with buyer credentials
"""

import os
from typing import Dict, List, Any
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from agentgatepay_sdk import AgentGatePay
from datetime import datetime

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
BASE_RPC_URL = os.getenv('BASE_RPC_URL', 'https://mainnet.base.org')
BUYER_PRIVATE_KEY = os.getenv('BUYER_PRIVATE_KEY')
SELLER_WALLET = os.getenv('SELLER_WALLET')
COMMISSION_ADDRESS = os.getenv('AGENTPAY_COMMISSION_ADDRESS', '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEbB')

# USDC configuration
USDC_CONTRACT_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
USDC_DECIMALS = 6
COMMISSION_RATE = 0.005

# ========================================
# INITIALIZE CLIENTS
# ========================================

agentpay = AgentGatePay(api_url=AGENTPAY_API_URL, api_key=BUYER_API_KEY)
web3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))
buyer_account = Account.from_key(BUYER_PRIVATE_KEY)

# State
current_mandate = None
payment_history = []

print(f"✅ Initialized with buyer wallet: {buyer_account.address}\n")

# ========================================
# AGENT TOOLS WITH AUDIT LOGGING
# ========================================

def issue_mandate_with_tracking(budget_usd: float) -> str:
    """Issue mandate and log event"""
    global current_mandate

    print(f"\n🔐 Issuing mandate with ${budget_usd} budget...")

    mandate = agentpay.mandates.issue(
        subject=f"audited-buyer-{buyer_account.address}",
        budget_usd=budget_usd,
        scope="resource.read,payment.execute",
        ttl_hours=168
    )

    current_mandate = mandate

    print(f"✅ Mandate issued")
    print(f"   Token: {mandate['mandateToken'][:50]}...")
    print(f"   Budget: ${mandate['budgetUsd']}")
    print(f"   ID: {mandate.get('id', 'N/A')}")

    return f"Mandate issued successfully. Budget: ${budget_usd}, ID: {mandate.get('id', 'N/A')}"


def execute_tracked_payment(amount_usd: float, recipient: str, description: str = "Payment") -> str:
    """Execute payment and track in history"""
    global payment_history

    print(f"\n💳 Executing payment: ${amount_usd} to {recipient[:10]}...")
    print(f"   Description: {description}")

    try:
        # Calculate amounts
        commission_usd = amount_usd * COMMISSION_RATE
        merchant_usd = amount_usd - commission_usd

        merchant_atomic = int(merchant_usd * (10 ** USDC_DECIMALS))
        commission_atomic = int(commission_usd * (10 ** USDC_DECIMALS))

        # ERC-20 transfer
        transfer_sig = web3.keccak(text="transfer(address,uint256)")[:4]

        # Merchant transaction
        print(f"   📤 Merchant TX: ${merchant_usd:.4f}")
        merchant_data = transfer_sig + \
                       web3.to_bytes(hexstr=recipient).rjust(32, b'\x00') + \
                       merchant_atomic.to_bytes(32, byteorder='big')

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
        tx_hash_merchant = web3.eth.send_raw_transaction(signed_merchant.rawTransaction)
        merchant_receipt = web3.eth.wait_for_transaction_receipt(tx_hash_merchant, timeout=60)

        print(f"   ✅ Merchant TX confirmed: {tx_hash_merchant.hex()[:20]}...")

        # Commission transaction
        print(f"   📤 Commission TX: ${commission_usd:.4f}")
        commission_data = transfer_sig + \
                         web3.to_bytes(hexstr=COMMISSION_ADDRESS).rjust(32, b'\x00') + \
                         commission_atomic.to_bytes(32, byteorder='big')

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
        tx_hash_commission = web3.eth.send_raw_transaction(signed_commission.rawTransaction)
        commission_receipt = web3.eth.wait_for_transaction_receipt(tx_hash_commission, timeout=60)

        print(f"   ✅ Commission TX confirmed: {tx_hash_commission.hex()[:20]}...")

        # Track payment locally
        payment_record = {
            "amount_usd": amount_usd,
            "merchant_tx": tx_hash_merchant.hex(),
            "commission_tx": tx_hash_commission.hex(),
            "recipient": recipient,
            "description": description,
            "timestamp": datetime.now().isoformat()
        }
        payment_history.append(payment_record)

        return f"Payment completed: ${amount_usd}. Merchant TX: {tx_hash_merchant.hex()}"

    except Exception as e:
        error_msg = f"Payment failed: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg


def get_all_audit_logs() -> str:
    """Retrieve all audit logs for buyer"""
    print(f"\n📊 Retrieving all audit logs...")

    try:
        # Get payment completion logs
        payment_logs = agentpay.audit.list_logs(
            event_type="payment_completed",
            limit=50
        )

        # Get mandate issuance logs
        mandate_logs = agentpay.audit.list_logs(
            event_type="mandate_issued",
            limit=50
        )

        total_logs = len(payment_logs.get('logs', [])) + len(mandate_logs.get('logs', []))

        print(f"✅ Retrieved {total_logs} audit logs")
        print(f"   Payment events: {len(payment_logs.get('logs', []))}")
        print(f"   Mandate events: {len(mandate_logs.get('logs', []))}")

        # Display recent payment logs
        if payment_logs.get('logs'):
            print(f"\n📝 Recent Payment Events:")
            for log in payment_logs['logs'][:5]:
                timestamp = datetime.fromtimestamp(log.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M:%S')
                print(f"   - {timestamp}: ${log.get('amount_usd', 'N/A')} ({log.get('event_type', 'unknown')})")

        return f"Retrieved {total_logs} audit log entries (payments: {len(payment_logs.get('logs', []))}, mandates: {len(mandate_logs.get('logs', []))})"

    except Exception as e:
        error_msg = f"Audit log retrieval failed: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg


def get_payment_by_transaction(tx_hash: str) -> str:
    """Retrieve audit logs for specific transaction"""
    print(f"\n🔍 Retrieving logs for transaction: {tx_hash[:20]}...")

    try:
        logs = agentpay.audit.list_logs_by_transaction(tx_hash)

        log_count = len(logs.get('logs', []))
        print(f"✅ Retrieved {log_count} log entries for this transaction")

        if logs.get('logs'):
            for log in logs['logs']:
                print(f"\n📝 Log Entry:")
                print(f"   Event: {log.get('event_type', 'N/A')}")
                print(f"   Amount: ${log.get('amount_usd', 'N/A')}")
                print(f"   Timestamp: {datetime.fromtimestamp(log.get('timestamp', 0)).isoformat()}")

        return f"Found {log_count} log entries for transaction {tx_hash[:20]}..."

    except Exception as e:
        error_msg = f"Transaction log lookup failed: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg


def analyze_spending_pattern() -> str:
    """Analyze spending patterns from audit logs"""
    print(f"\n📈 Analyzing spending patterns...")

    try:
        # Get recent payment logs
        logs_response = agentpay.audit.list_logs(
            event_type="payment_completed",
            limit=100
        )

        logs = logs_response.get('logs', [])

        if not logs:
            return "No payment history found"

        # Calculate analytics
        total_spent = sum(float(log.get('amount_usd', 0)) for log in logs)
        avg_payment = total_spent / len(logs) if logs else 0
        payment_count = len(logs)

        # Find largest payment
        largest_payment = max(logs, key=lambda x: float(x.get('amount_usd', 0)))
        largest_amount = float(largest_payment.get('amount_usd', 0))

        print(f"✅ Spending Analysis:")
        print(f"   Total payments: {payment_count}")
        print(f"   Total spent: ${total_spent:.2f}")
        print(f"   Average payment: ${avg_payment:.2f}")
        print(f"   Largest payment: ${largest_amount:.2f}")

        # Budget utilization
        if current_mandate:
            budget_total = float(current_mandate.get('budgetUsd', 0))
            budget_remaining = float(current_mandate.get('budgetRemaining', budget_total))
            budget_used = budget_total - budget_remaining
            utilization = (budget_used / budget_total * 100) if budget_total > 0 else 0

            print(f"\n💰 Budget Status:")
            print(f"   Allocated: ${budget_total:.2f}")
            print(f"   Used: ${budget_used:.2f}")
            print(f"   Remaining: ${budget_remaining:.2f}")
            print(f"   Utilization: {utilization:.1f}%")

        return f"Analyzed {payment_count} payments. Total spent: ${total_spent:.2f}, Average: ${avg_payment:.2f}"

    except Exception as e:
        error_msg = f"Spending analysis failed: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg


def get_budget_status() -> str:
    """Check current mandate budget status"""
    if not current_mandate:
        return "No active mandate"

    try:
        # Verify mandate is still valid
        verification = agentpay.mandates.verify(current_mandate['mandateToken'])

        if verification.get('valid'):
            budget_remaining = float(verification.get('budget_remaining', 0))
            budget_total = float(current_mandate.get('budgetUsd', 0))
            budget_used = budget_total - budget_remaining
            utilization = (budget_used / budget_total * 100) if budget_total > 0 else 0

            print(f"\n💰 Current Budget Status:")
            print(f"   Total: ${budget_total:.2f}")
            print(f"   Used: ${budget_used:.2f}")
            print(f"   Remaining: ${budget_remaining:.2f}")
            print(f"   Utilization: {utilization:.1f}%")

            # Warning if low balance
            if budget_remaining < budget_total * 0.2:
                print(f"   ⚠️  WARNING: Less than 20% budget remaining!")

            return f"Budget: ${budget_remaining:.2f} of ${budget_total:.2f} remaining ({utilization:.1f}% used)"
        else:
            return "Mandate is no longer valid (expired or depleted)"

    except Exception as e:
        error_msg = f"Budget check failed: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg


# Define LangChain tools
tools = [
    Tool(
        name="issue_mandate",
        func=lambda budget: issue_mandate_with_tracking(float(budget)),
        description="Issue AP2 mandate with budget tracking. Input: budget amount in USD."
    ),
    Tool(
        name="execute_payment",
        func=lambda params: execute_tracked_payment(
            float(params.split('|')[0]),
            params.split('|')[1],
            params.split('|')[2] if len(params.split('|')) > 2 else "Payment"
        ),
        description="Execute payment with description. Input: 'amount_usd|recipient_address|description'"
    ),
    Tool(
        name="get_audit_logs",
        func=lambda _: get_all_audit_logs(),
        description="Retrieve all audit logs (payments + mandates). No input needed."
    ),
    Tool(
        name="get_transaction_logs",
        func=get_payment_by_transaction,
        description="Get audit logs for specific transaction. Input: transaction hash."
    ),
    Tool(
        name="analyze_spending",
        func=lambda _: analyze_spending_pattern(),
        description="Analyze spending patterns and budget utilization. No input needed."
    ),
    Tool(
        name="check_budget",
        func=lambda _: get_budget_status(),
        description="Check current mandate budget status. No input needed."
    ),
]

# Agent prompt
agent_prompt = PromptTemplate.from_template("""
You are an autonomous agent that manages payments with comprehensive audit logging.

Available tools:
{tools}

Tool names: {tool_names}

Task: {input}

Best practices:
- Always issue mandate first
- Track every payment with descriptive labels
- Check budget before large payments
- Retrieve audit logs after payments
- Analyze spending patterns regularly

Think step by step:
{agent_scratchpad}
""")

# Create agent
llm = ChatOpenAI(model="gpt-4", temperature=0, openai_api_key=os.getenv('OPENAI_API_KEY'))
agent = create_react_agent(llm=llm, tools=tools, prompt=agent_prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=20, handle_parsing_errors=True)

# ========================================
# MAIN EXECUTION
# ========================================

if __name__ == "__main__":
    print("=" * 80)
    print("🤖 AGENTGATEPAY + LANGCHAIN: AUDIT LOGGING DEMO (REST API)")
    print("=" * 80)
    print()
    print("This demo shows comprehensive payment tracking and audit logging:")
    print("  - Mandate budget tracking")
    print("  - Automatic payment logging")
    print("  - Audit log retrieval and analysis")
    print("  - Spending pattern analytics")
    print()
    print("=" * 80)

    # Agent task: Make multiple payments and analyze
    task = f"""
    Execute a series of payments with comprehensive tracking:

    1. Issue a mandate with $100 budget
    2. Make payment #1: $10 to {SELLER_WALLET} (description: "Research paper purchase")
    3. Make payment #2: $5 to {SELLER_WALLET} (description: "API access fee")
    4. Check current budget status
    5. Retrieve all audit logs
    6. Analyze spending patterns
    7. Get logs for the first payment transaction

    Track everything and provide a final spending summary.
    """

    try:
        # Run agent
        result = agent_executor.invoke({"input": task})

        print("\n" + "=" * 80)
        print("✅ AUDIT LOGGING DEMO COMPLETED")
        print("=" * 80)
        print(f"\nResult: {result['output']}")

        # Display final summary
        print(f"\n📊 FINAL SUMMARY:")
        print(f"   Total payments made: {len(payment_history)}")

        if payment_history:
            total_spent = sum(p['amount_usd'] for p in payment_history)
            print(f"   Total amount spent: ${total_spent:.2f}")
            print(f"\n   Payment History:")
            for i, payment in enumerate(payment_history, 1):
                print(f"      {i}. ${payment['amount_usd']:.2f} - {payment['description']}")
                print(f"         TX: {payment['merchant_tx'][:20]}...")

        if current_mandate:
            print(f"\n   Mandate Status:")
            print(f"      ID: {current_mandate.get('id', 'N/A')}")
            print(f"      Budget allocated: ${current_mandate.get('budgetUsd', 'N/A')}")

        print(f"\n🔗 View transactions on BaseScan:")
        for payment in payment_history:
            print(f"   https://basescan.org/tx/{payment['merchant_tx']}")

    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
