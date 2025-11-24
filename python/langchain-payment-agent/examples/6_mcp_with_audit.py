#!/usr/bin/env python3
"""
AgentGatePay + LangChain Integration - Payment with Audit Logs (MCP Tools)

This demonstrates comprehensive payment tracking using AgentGatePay's MCP tools:
- agentpay_issue_mandate (mandate with budget)
- agentpay_submit_payment (payment submission)
- agentpay_list_audit_logs (retrieve logs)
- agentpay_get_audit_stats (statistics)

MCP advantages over REST API:
- Native tool discovery
- Standardized JSON-RPC 2.0 protocol
- Future-proof (Anthropic-backed)

Features demonstrated:
1. Issue mandate with budget tracking
2. Execute blockchain payments
3. Submit payments via MCP
4. Retrieve audit logs via MCP
5. Analyze spending patterns via MCP
6. Monitor budget utilization

Requirements:
- pip install langchain langchain-openai web3 python-dotenv requests
- .env file with buyer credentials
- AgentGatePay MCP endpoint running
"""

import os
import json
import requests
from typing import Dict, Any, List
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
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

# MCP endpoint
MCP_ENDPOINT = f"{AGENTPAY_API_URL}/mcp/tools/call"

# USDC configuration
USDC_CONTRACT_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
USDC_DECIMALS = 6
COMMISSION_RATE = 0.005

# ========================================
# MCP HELPER FUNCTIONS
# ========================================

def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call AgentGatePay MCP tool via JSON-RPC 2.0.

    Args:
        tool_name: MCP tool name (e.g., 'agentpay_list_audit_logs')
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
# INITIALIZE CLIENTS
# ========================================

web3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))
buyer_account = Account.from_key(BUYER_PRIVATE_KEY)

# State
current_mandate = None
payment_history = []

print(f"✅ Initialized MCP client with buyer wallet: {buyer_account.address}\n")

# ========================================
# AGENT TOOLS WITH MCP
# ========================================

def mcp_issue_mandate(budget_usd: float) -> str:
    """Issue mandate via MCP tool"""
    global current_mandate

    print(f"\n🔐 [MCP] Issuing mandate with ${budget_usd} budget...")

    try:
        mandate = call_mcp_tool("agentpay_issue_mandate", {
            "subject": f"audited-buyer-{buyer_account.address}",
            "budget_usd": budget_usd,
            "scope": "resource.read,payment.execute",
            "ttl_hours": 168
        })

        current_mandate = mandate

        print(f"✅ Mandate issued via MCP")
        print(f"   Token: {mandate['mandateToken'][:50]}...")
        print(f"   Budget: ${mandate['budgetUsd']}")
        print(f"   ID: {mandate.get('id', 'N/A')}")

        return f"Mandate issued via MCP. Budget: ${budget_usd}, ID: {mandate.get('id', 'N/A')}"

    except Exception as e:
        error_msg = f"MCP mandate issue failed: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg


def execute_blockchain_payment(amount_usd: float, recipient: str, description: str = "Payment") -> str:
    """Execute blockchain payment (2 transactions)"""
    global payment_history

    print(f"\n💳 [BLOCKCHAIN] Executing payment: ${amount_usd} to {recipient[:10]}...")
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

        return f"Payment completed: ${amount_usd}. Merchant TX: {tx_hash_merchant.hex()}, Commission TX: {tx_hash_commission.hex()}"

    except Exception as e:
        error_msg = f"Payment failed: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg


def mcp_submit_payment(merchant_tx: str, commission_tx: str) -> str:
    """Submit payment proof via MCP tool"""
    print(f"\n📤 [MCP] Submitting payment proof...")

    try:
        if not current_mandate:
            return "Error: No active mandate. Issue mandate first."

        result = call_mcp_tool("agentpay_submit_payment", {
            "mandate_token": current_mandate['mandateToken'],
            "tx_hash_merchant": merchant_tx,
            "tx_hash_commission": commission_tx,
            "chain": "base",
            "token": "USDC"
        })

        print(f"✅ Payment submitted via MCP")
        print(f"   Charge ID: {result.get('chargeId', 'N/A')}")
        print(f"   Status: {result.get('status', 'N/A')}")

        return f"Payment proof submitted via MCP. Charge ID: {result.get('chargeId')}"

    except Exception as e:
        error_msg = f"MCP payment submission failed: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg


def mcp_get_audit_logs(event_type: str = None) -> str:
    """Retrieve audit logs via MCP tool"""
    print(f"\n📊 [MCP] Retrieving audit logs...")

    try:
        args = {"limit": 50}
        if event_type:
            args["event_type"] = event_type

        logs_response = call_mcp_tool("agentpay_list_audit_logs", args)

        logs = logs_response.get('logs', [])
        total_logs = len(logs)

        print(f"✅ Retrieved {total_logs} audit logs via MCP")

        if event_type:
            print(f"   Filter: {event_type}")

        # Display recent logs
        if logs:
            print(f"\n📝 Recent Events:")
            for log in logs[:5]:
                timestamp = datetime.fromtimestamp(log.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M:%S')
                amount = log.get('amount_usd', 'N/A')
                event = log.get('event_type', 'unknown')
                print(f"   - {timestamp}: ${amount} ({event})")

        return f"Retrieved {total_logs} audit log entries via MCP" + (f" (filtered by: {event_type})" if event_type else "")

    except Exception as e:
        error_msg = f"MCP audit log retrieval failed: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg


def mcp_get_transaction_logs(tx_hash: str) -> str:
    """Retrieve audit logs for specific transaction via MCP"""
    print(f"\n🔍 [MCP] Retrieving logs for transaction: {tx_hash[:20]}...")

    try:
        logs_response = call_mcp_tool("agentpay_list_audit_logs", {
            "tx_hash": tx_hash,
            "limit": 10
        })

        logs = logs_response.get('logs', [])
        log_count = len(logs)

        print(f"✅ Retrieved {log_count} log entries via MCP")

        if logs:
            for log in logs:
                print(f"\n📝 Log Entry:")
                print(f"   Event: {log.get('event_type', 'N/A')}")
                print(f"   Amount: ${log.get('amount_usd', 'N/A')}")
                print(f"   Timestamp: {datetime.fromtimestamp(log.get('timestamp', 0)).isoformat()}")

        return f"Found {log_count} log entries via MCP for transaction {tx_hash[:20]}..."

    except Exception as e:
        error_msg = f"MCP transaction log lookup failed: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg


def mcp_analyze_spending() -> str:
    """Analyze spending patterns via MCP"""
    print(f"\n📈 [MCP] Analyzing spending patterns...")

    try:
        # Get payment completion logs
        logs_response = call_mcp_tool("agentpay_list_audit_logs", {
            "event_type": "payment_completed",
            "limit": 100
        })

        logs = logs_response.get('logs', [])

        if not logs:
            return "No payment history found via MCP"

        # Calculate analytics
        total_spent = sum(float(log.get('amount_usd', 0)) for log in logs)
        avg_payment = total_spent / len(logs) if logs else 0
        payment_count = len(logs)

        # Find largest payment
        largest_payment = max(logs, key=lambda x: float(x.get('amount_usd', 0)))
        largest_amount = float(largest_payment.get('amount_usd', 0))

        print(f"✅ Spending Analysis (via MCP):")
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

        return f"Analyzed {payment_count} payments via MCP. Total spent: ${total_spent:.2f}, Average: ${avg_payment:.2f}"

    except Exception as e:
        error_msg = f"MCP spending analysis failed: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg


def mcp_check_budget() -> str:
    """Check mandate budget via MCP"""
    if not current_mandate:
        return "No active mandate"

    try:
        print(f"\n💰 [MCP] Checking budget status...")

        # Verify mandate via MCP
        verification = call_mcp_tool("agentpay_verify_mandate", {
            "mandate_token": current_mandate['mandateToken']
        })

        if verification.get('valid'):
            budget_remaining = float(verification.get('budget_remaining', 0))
            budget_total = float(current_mandate.get('budgetUsd', 0))
            budget_used = budget_total - budget_remaining
            utilization = (budget_used / budget_total * 100) if budget_total > 0 else 0

            print(f"✅ Budget Status (via MCP):")
            print(f"   Total: ${budget_total:.2f}")
            print(f"   Used: ${budget_used:.2f}")
            print(f"   Remaining: ${budget_remaining:.2f}")
            print(f"   Utilization: {utilization:.1f}%")

            # Warning if low balance
            if budget_remaining < budget_total * 0.2:
                print(f"   ⚠️  WARNING: Less than 20% budget remaining!")

            return f"Budget via MCP: ${budget_remaining:.2f} of ${budget_total:.2f} remaining ({utilization:.1f}% used)"
        else:
            return "Mandate is no longer valid (expired or depleted)"

    except Exception as e:
        error_msg = f"MCP budget check failed: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg


# Define LangChain tools
tools = [
    Tool(
        name="mcp_issue_mandate",
        func=lambda budget: mcp_issue_mandate(float(budget)),
        description="Issue AP2 mandate via MCP tool. Input: budget amount in USD."
    ),
    Tool(
        name="execute_payment",
        func=lambda params: execute_blockchain_payment(
            float(params.split('|')[0]),
            params.split('|')[1],
            params.split('|')[2] if len(params.split('|')) > 2 else "Payment"
        ),
        description="Execute blockchain payment. Input: 'amount_usd|recipient_address|description'"
    ),
    Tool(
        name="mcp_submit_payment",
        func=lambda tx_hashes: mcp_submit_payment(
            tx_hashes.split(',')[0],
            tx_hashes.split(',')[1]
        ),
        description="Submit payment proof via MCP. Input: 'merchant_tx_hash,commission_tx_hash'"
    ),
    Tool(
        name="mcp_get_audit_logs",
        func=lambda event_type: mcp_get_audit_logs(event_type if event_type != "all" else None),
        description="Retrieve audit logs via MCP. Input: event_type (e.g., 'payment_completed') or 'all'"
    ),
    Tool(
        name="mcp_get_transaction_logs",
        func=mcp_get_transaction_logs,
        description="Get audit logs for specific transaction via MCP. Input: transaction hash."
    ),
    Tool(
        name="mcp_analyze_spending",
        func=lambda _: mcp_analyze_spending(),
        description="Analyze spending patterns via MCP. No input needed."
    ),
    Tool(
        name="mcp_check_budget",
        func=lambda _: mcp_check_budget(),
        description="Check mandate budget via MCP. No input needed."
    ),
]

# Agent prompt
agent_prompt = PromptTemplate.from_template("""
You are an autonomous agent managing payments with MCP tools for audit logging.

Available tools:
{tools}

Tool names: {tool_names}

Task: {input}

Best practices:
- Always issue mandate first (MCP)
- Execute blockchain payments
- Submit payment proofs (MCP)
- Retrieve audit logs (MCP)
- Analyze spending (MCP)
- Check budget (MCP)

Think step by step:
{agent_scratchpad}
""")

# Create agent
llm = ChatOpenAI(model="gpt-4", temperature=0, openai_api_key=os.getenv('OPENAI_API_KEY'))
agent = create_react_agent(llm=llm, tools=tools, prompt=agent_prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=25, handle_parsing_errors=True)

# ========================================
# MAIN EXECUTION
# ========================================

if __name__ == "__main__":
    print("=" * 80)
    print("🤖 AGENTGATEPAY + LANGCHAIN: AUDIT LOGGING DEMO (MCP TOOLS)")
    print("=" * 80)
    print()
    print("This demo shows comprehensive payment tracking using MCP tools:")
    print("  - Mandate management (MCP)")
    print("  - Payment submission (MCP)")
    print("  - Audit log retrieval (MCP)")
    print("  - Spending analytics (MCP)")
    print()
    print("=" * 80)

    # Agent task: Make payments and track with MCP
    task = f"""
    Execute a series of payments with MCP-based tracking:

    1. Issue a mandate with $100 budget (MCP)
    2. Execute payment #1: $10 to {SELLER_WALLET} (blockchain)
    3. Submit payment #1 proof (MCP)
    4. Execute payment #2: $5 to {SELLER_WALLET} (blockchain)
    5. Submit payment #2 proof (MCP)
    6. Check current budget status (MCP)
    7. Retrieve all audit logs (MCP)
    8. Analyze spending patterns (MCP)
    9. Get logs for the first payment transaction (MCP)

    Use MCP tools for all AgentGatePay interactions.
    Provide a final spending summary.
    """

    try:
        # Run agent
        result = agent_executor.invoke({"input": task})

        print("\n" + "=" * 80)
        print("✅ AUDIT LOGGING DEMO COMPLETED (MCP)")
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

        print(f"\n💡 MCP Tools Used:")
        print("   - agentpay_issue_mandate")
        print("   - agentpay_submit_payment")
        print("   - agentpay_verify_mandate")
        print("   - agentpay_list_audit_logs")

        print(f"\n🔗 View transactions on BaseScan:")
        for payment in payment_history:
            print(f"   https://basescan.org/tx/{payment['merchant_tx']}")

    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
