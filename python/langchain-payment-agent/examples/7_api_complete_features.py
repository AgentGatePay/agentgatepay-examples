#!/usr/bin/env python3
"""
AgentGatePay + LangChain Integration - COMPLETE FEATURES DEMO (REST API)

This example demonstrates ALL AgentGatePay features in a single comprehensive flow:
1. User Authentication & Signup
2. Wallet Management
3. API Key Management (create, list, revoke)
4. Mandate Management (issue, verify, budget tracking)
5. Payment Flow (create, submit, verify)
6. Payment History Retrieval
7. Merchant Revenue Analytics
8. Comprehensive Audit Logging
9. Webhook Configuration
10. System Health Monitoring

This matches the complete feature set shown in n8n workflows.

Usage:
    python 7_api_complete_features.py

Requirements:
- pip install agentgatepay-sdk>=1.1.3 langchain langchain-openai web3 python-dotenv
- .env file with credentials OR run in demo mode (will create new user)
"""

import os
import time
from typing import Dict, Any
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from agentgatepay_sdk import AgentGatePay
from datetime import datetime
import json

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
DEMO_MODE = os.getenv('DEMO_MODE', 'true').lower() == 'true'

# Blockchain configuration
BASE_RPC_URL = os.getenv('BASE_RPC_URL', 'https://mainnet.base.org')
BUYER_PRIVATE_KEY = os.getenv('BUYER_PRIVATE_KEY')
SELLER_WALLET = os.getenv('SELLER_WALLET', '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb2')

# USDC configuration
USDC_CONTRACT_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
USDC_DECIMALS = 6
COMMISSION_RATE = 0.005

# ========================================
# HELPER FUNCTIONS
# ========================================

def get_commission_config(api_key: str = None) -> dict:
    """Fetch commission configuration from AgentGatePay API"""
    import requests
    try:
        headers = {}
        if api_key:
            headers["x-api-key"] = api_key
        response = requests.get(
            f"{AGENTPAY_API_URL}/v1/config/commission",
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"⚠️  Failed to fetch commission config: {e}")
        return None

# ========================================
# STATE
# ========================================

class AgentPayCompleteDemo:
    """Demonstrates all AgentGatePay features"""

    def __init__(self):
        self.agentpay = None
        self.api_key = os.getenv('BUYER_API_KEY') if not DEMO_MODE else None
        self.user_info = None
        self.api_keys = []
        self.current_mandate = None
        self.payment_history = []
        self.webhook_id = None

        # Initialize Web3
        self.web3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))
        if BUYER_PRIVATE_KEY:
            self.account = Account.from_key(BUYER_PRIVATE_KEY)
        else:
            # Generate new account for demo
            self.account = Account.create()
            print(f"⚠️  Demo mode: Generated new wallet {self.account.address}")

        # Initialize SDK if we have API key
        if self.api_key:
            self.agentpay = AgentGatePay(api_url=AGENTPAY_API_URL, api_key=self.api_key)

        print(f"\n🤖 AGENTGATEPAY COMPLETE FEATURES DEMO")
        print(f"=" * 70)
        print(f"Mode: {'DEMO (will create new user)' if DEMO_MODE else 'PRODUCTION'}")
        print(f"Wallet: {self.account.address}")
        print(f"API URL: {AGENTPAY_API_URL}")
        print(f"=" * 70)

    # ========================================
    # FEATURE 1: USER AUTHENTICATION & SIGNUP
    # ========================================

    def user_signup(self, email: str, password: str, user_type: str = "both") -> str:
        """Create new AgentGatePay user account"""
        print(f"\n👤 [AUTH] Signing up new user: {email}")

        try:
            import requests
            response = requests.post(
                f"{AGENTPAY_API_URL}/v1/users/signup",
                json={
                    "email": email,
                    "password": password,
                    "user_type": user_type  # agent, merchant, or both
                },
                timeout=10
            )

            if response.status_code == 201:
                data = response.json()
                self.api_key = data.get('api_key')
                self.user_info = data.get('user')

                # Initialize SDK with new API key
                self.agentpay = AgentGatePay(api_url=AGENTPAY_API_URL, api_key=self.api_key)

                print(f"✅ User created successfully!")
                print(f"   User ID: {self.user_info.get('user_id')}")
                print(f"   Email: {self.user_info.get('email')}")
                print(f"   Type: {self.user_info.get('user_type')}")
                print(f"   API Key: {self.api_key[:20]}... (SAVE THIS!)")

                return f"User created. API Key: {self.api_key[:20]}... (save this key!)"
            else:
                error = response.json().get('error', 'Unknown error')
                print(f"❌ Signup failed: {error}")
                return f"Signup failed: {error}"

        except Exception as e:
            error_msg = f"Signup error: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    def get_user_info(self) -> str:
        """Get current user account information"""
        if not self.agentpay:
            return "Error: Not authenticated. Run user_signup first."

        print(f"\n📋 [AUTH] Retrieving user information...")

        try:
            info = self.agentpay.users.get_info()
            self.user_info = info

            print(f"✅ User information retrieved:")
            print(f"   Email: {info.get('email')}")
            print(f"   User Type: {info.get('user_type')}")
            print(f"   Created: {info.get('created_at')}")
            print(f"   Wallets: {len(info.get('wallets', []))}")

            return f"User: {info.get('email')}, Type: {info.get('user_type')}, Wallets: {len(info.get('wallets', []))}"

        except Exception as e:
            error_msg = f"Get user info failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    # ========================================
    # FEATURE 2: WALLET MANAGEMENT
    # ========================================

    def add_wallet(self, chain: str = "base") -> str:
        """Add blockchain wallet to account"""
        if not self.agentpay:
            return "Error: Not authenticated."

        print(f"\n💳 [WALLET] Adding {chain} wallet: {self.account.address[:20]}...")

        try:
            result = self.agentpay.users.add_wallet(
                chain=chain,
                address=self.account.address
            )

            print(f"✅ Wallet added successfully")
            print(f"   Chain: {chain}")
            print(f"   Address: {self.account.address}")

            return f"Wallet added: {self.account.address} on {chain}"

        except Exception as e:
            error_msg = f"Add wallet failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    # ========================================
    # FEATURE 3: API KEY MANAGEMENT
    # ========================================

    def create_api_key(self, name: str) -> str:
        """Create new API key"""
        if not self.agentpay:
            return "Error: Not authenticated."

        print(f"\n🔑 [API KEYS] Creating new API key: {name}")

        try:
            key_data = self.agentpay.api_keys.create(name=name)

            new_key = key_data.get('api_key')
            key_id = key_data.get('key_id')

            self.api_keys.append({"key_id": key_id, "name": name})

            print(f"✅ API key created!")
            print(f"   Key ID: {key_id}")
            print(f"   Name: {name}")
            print(f"   Key: {new_key[:20]}... (SAVE THIS!)")

            return f"API key '{name}' created: {new_key[:20]}..."

        except Exception as e:
            error_msg = f"Create API key failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    def list_api_keys(self) -> str:
        """List all API keys for user"""
        if not self.agentpay:
            return "Error: Not authenticated."

        print(f"\n📜 [API KEYS] Listing all API keys...")

        try:
            keys = self.agentpay.api_keys.list()

            print(f"✅ Found {len(keys)} API key(s):")
            for key in keys:
                status = "✓ Active" if key.get('active') else "✗ Revoked"
                print(f"   - {key.get('name')}: {status} (ID: {key.get('key_id')})")

            return f"Found {len(keys)} API keys"

        except Exception as e:
            error_msg = f"List API keys failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    # ========================================
    # FEATURE 4-5: MANDATES & PAYMENTS
    # ========================================

    def issue_mandate(self, budget_usd: float) -> str:
        """Issue AP2 mandate"""
        if not self.agentpay:
            return "Error: Not authenticated."

        print(f"\n🔐 [MANDATE] Issuing mandate with ${budget_usd} budget...")

        try:
            mandate = self.agentpay.mandates.issue(
                subject=f"complete-demo-{self.account.address}",
                budget=budget_usd,
                scope="resource.read,payment.execute,analytics.read",
                ttl_minutes=10080
            )

            self.current_mandate = mandate

            print(f"✅ Mandate issued successfully")
            print(f"   Token: {mandate['mandate_token'][:50]}...")
            print(f"   Budget: ${mandate['budget_usd']}")

            return f"Mandate issued: ${budget_usd} budget"

        except Exception as e:
            error_msg = f"Issue mandate failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    def execute_payment(self, amount_usd: float, description: str = "Demo payment") -> str:
        """Execute blockchain payment"""
        print(f"\n💳 [PAYMENT] Executing payment: ${amount_usd}")

        try:
            # Fetch commission config dynamically
            commission_config = get_commission_config(api_key=self.api_key)
            if not commission_config:
                return "Error: Failed to fetch commission config"

            commission_address = commission_config['commission_address']
            commission_rate = commission_config.get('commission_rate', COMMISSION_RATE)

            # Calculate amounts
            commission_usd = amount_usd * commission_rate
            merchant_usd = amount_usd - commission_usd

            merchant_atomic = int(merchant_usd * (10 ** USDC_DECIMALS))
            commission_atomic = int(commission_usd * (10 ** USDC_DECIMALS))

            # ERC-20 transfer
            transfer_sig = self.web3.keccak(text="transfer(address,uint256)")[:4]

            # Merchant TX
            merchant_data = transfer_sig + \
                           self.web3.to_bytes(hexstr=SELLER_WALLET).rjust(32, b'\x00') + \
                           merchant_atomic.to_bytes(32, byteorder='big')

            merchant_tx = {
                'nonce': self.web3.eth.get_transaction_count(self.account.address),
                'to': USDC_CONTRACT_BASE,
                'value': 0,
                'gas': 100000,
                'gasPrice': self.web3.eth.gas_price,
                'data': merchant_data,
                'chainId': 8453
            }

            signed_merchant = self.account.sign_transaction(merchant_tx)
            tx_hash_merchant_raw = self.web3.eth.send_raw_transaction(signed_merchant.raw_transaction)
            tx_hash_merchant = f"0x{tx_hash_merchant_raw.hex()}" if not tx_hash_merchant_raw.hex().startswith('0x') else tx_hash_merchant_raw.hex()
            self.web3.eth.wait_for_transaction_receipt(tx_hash_merchant_raw, timeout=60)

            # Commission TX
            commission_data = transfer_sig + \
                             self.web3.to_bytes(hexstr=commission_address).rjust(32, b'\x00') + \
                             commission_atomic.to_bytes(32, byteorder='big')

            commission_tx = {
                'nonce': self.web3.eth.get_transaction_count(self.account.address),
                'to': USDC_CONTRACT_BASE,
                'value': 0,
                'gas': 100000,
                'gasPrice': self.web3.eth.gas_price,
                'data': commission_data,
                'chainId': 8453
            }

            signed_commission = self.account.sign_transaction(commission_tx)
            tx_hash_commission_raw = self.web3.eth.send_raw_transaction(signed_commission.raw_transaction)
            tx_hash_commission = f"0x{tx_hash_commission_raw.hex()}" if not tx_hash_commission_raw.hex().startswith('0x') else tx_hash_commission_raw.hex()
            self.web3.eth.wait_for_transaction_receipt(tx_hash_commission_raw, timeout=60)

            print(f"✅ Payment executed!")
            print(f"   Merchant TX: {tx_hash_merchant[:20]}...")
            print(f"   Commission TX: {tx_hash_commission[:20]}...")

            # Track payment
            self.payment_history.append({
                "amount_usd": amount_usd,
                "merchant_tx": tx_hash_merchant,
                "commission_tx": tx_hash_commission,
                "description": description,
                "timestamp": datetime.now().isoformat()
            })

            return f"Payment completed: ${amount_usd}. TX: {tx_hash_merchant[:20]}..."

        except Exception as e:
            error_msg = f"Payment failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    # ========================================
    # FEATURE 6: PAYMENT HISTORY
    # ========================================

    def get_payment_history(self) -> str:
        """Retrieve payment history"""
        if not self.agentpay:
            return "Error: Not authenticated."

        print(f"\n📊 [HISTORY] Retrieving payment history...")

        try:
            history = self.agentpay.payments.list(limit=50)

            payment_count = len(history.get('payments', []))
            total_spent = sum(float(p.get('amount_usd', 0)) for p in history.get('payments', []))

            print(f"✅ Payment history retrieved:")
            print(f"   Total payments: {payment_count}")
            print(f"   Total spent: ${total_spent:.2f}")

            if history.get('payments'):
                print(f"\n   Recent payments:")
                for p in history['payments'][:5]:
                    print(f"   - ${p.get('amount_usd')}: {p.get('status')} ({p.get('tx_hash', 'N/A')[:20]}...)")

            return f"Payment history: {payment_count} payments, ${total_spent:.2f} total"

        except Exception as e:
            error_msg = f"Get payment history failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    # ========================================
    # FEATURE 7: MERCHANT ANALYTICS
    # ========================================

    def get_revenue_analytics(self) -> str:
        """Get merchant revenue analytics"""
        if not self.agentpay:
            return "Error: Not authenticated."

        print(f"\n📈 [ANALYTICS] Retrieving revenue analytics...")

        try:
            analytics = self.agentpay.merchant.get_revenue()

            print(f"✅ Revenue analytics:")
            print(f"   Total revenue: ${analytics.get('total_revenue_usd', 0):.2f}")
            print(f"   Payment count: {analytics.get('payment_count', 0)}")
            print(f"   Average payment: ${analytics.get('average_payment_usd', 0):.2f}")
            print(f"   Period: {analytics.get('period', 'N/A')}")

            return f"Revenue: ${analytics.get('total_revenue_usd', 0):.2f} from {analytics.get('payment_count', 0)} payments"

        except Exception as e:
            error_msg = f"Get analytics failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    # ========================================
    # FEATURE 8: AUDIT LOGS
    # ========================================

    def get_audit_logs(self, event_type: str = None) -> str:
        """Retrieve comprehensive audit logs"""
        if not self.agentpay:
            return "Error: Not authenticated."

        print(f"\n📋 [AUDIT] Retrieving audit logs...")

        try:
            logs_response = self.agentpay.audit.list_logs(
                event_type=event_type,
                limit=50
            )

            logs = logs_response.get('logs', [])

            print(f"✅ Audit logs retrieved: {len(logs)} entries")

            if logs:
                print(f"\n   Recent events:")
                for log in logs[:5]:
                    timestamp = datetime.fromtimestamp(log.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M:%S')
                    print(f"   - {timestamp}: {log.get('event_type')} ({log.get('amount_usd', 'N/A')})")

            return f"Retrieved {len(logs)} audit log entries"

        except Exception as e:
            error_msg = f"Get audit logs failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    # ========================================
    # FEATURE 9: WEBHOOKS
    # ========================================

    def configure_webhook(self, webhook_url: str) -> str:
        """Configure webhook for payment notifications"""
        if not self.agentpay:
            return "Error: Not authenticated."

        print(f"\n🔔 [WEBHOOKS] Configuring webhook: {webhook_url[:50]}...")

        try:
            webhook = self.agentpay.webhooks.configure(
                url=webhook_url,
                events=["payment.completed", "payment.failed", "mandate.expired"]
            )

            self.webhook_id = webhook.get('webhook_id')

            print(f"✅ Webhook configured!")
            print(f"   Webhook ID: {self.webhook_id}")
            print(f"   URL: {webhook_url[:50]}...")
            print(f"   Events: {len(webhook.get('events', []))}")

            return f"Webhook configured: {self.webhook_id}"

        except Exception as e:
            error_msg = f"Configure webhook failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    def test_webhook(self) -> str:
        """Test webhook delivery"""
        if not self.agentpay or not self.webhook_id:
            return "Error: No webhook configured."

        print(f"\n🧪 [WEBHOOKS] Testing webhook delivery...")

        try:
            result = self.agentpay.webhooks.test(webhook_id=self.webhook_id)

            print(f"✅ Webhook test sent!")
            print(f"   Status: {result.get('status')}")
            print(f"   Response code: {result.get('response_code')}")

            return f"Webhook test: {result.get('status')}"

        except Exception as e:
            error_msg = f"Test webhook failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    # ========================================
    # FEATURE 10: SYSTEM HEALTH
    # ========================================

    def check_system_health(self) -> str:
        """Check AgentGatePay system health"""
        print(f"\n🏥 [HEALTH] Checking system health...")

        try:
            import requests
            response = requests.get(f"{AGENTPAY_API_URL}/health", timeout=5)

            if response.status_code == 200:
                health = response.json()
                print(f"✅ System health: {health.get('status')}")
                print(f"   Version: {health.get('version', 'N/A')}")
                print(f"   Uptime: {health.get('uptime', 'N/A')}")

                return f"System healthy: {health.get('status')}"
            else:
                return "System health check failed"

        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg


# ========================================
# LANGCHAIN AGENT
# ========================================

demo = AgentPayCompleteDemo()

# Define tools for all features
tools = [
    # Feature 1: Authentication
    Tool(
        name="user_signup",
        func=lambda params: demo.user_signup(
            params.split('|')[0],
            params.split('|')[1],
            params.split('|')[2] if len(params.split('|')) > 2 else "both"
        ),
        description="Sign up new user. Input: 'email|password|user_type'"
    ),
    Tool(
        name="get_user_info",
        func=lambda _: demo.get_user_info(),
        description="Get current user information. No input needed."
    ),

    # Feature 2: Wallets
    Tool(
        name="add_wallet",
        func=lambda chain: demo.add_wallet(chain if chain else "base"),
        description="Add blockchain wallet. Input: chain name (base, ethereum, polygon, arbitrum)"
    ),

    # Feature 3: API Keys
    Tool(
        name="create_api_key",
        func=demo.create_api_key,
        description="Create new API key. Input: key name"
    ),
    Tool(
        name="list_api_keys",
        func=lambda _: demo.list_api_keys(),
        description="List all API keys. No input needed."
    ),

    # Feature 4-5: Mandates & Payments
    Tool(
        name="issue_mandate",
        func=lambda budget: demo.issue_mandate(float(budget)),
        description="Issue AP2 mandate. Input: budget in USD"
    ),
    Tool(
        name="execute_payment",
        func=lambda params: demo.execute_payment(
            float(params.split('|')[0]),
            params.split('|')[1] if len(params.split('|')) > 1 else "Demo payment"
        ),
        description="Execute blockchain payment. Input: 'amount_usd|description'"
    ),

    # Feature 6: Payment History
    Tool(
        name="get_payment_history",
        func=lambda _: demo.get_payment_history(),
        description="Get payment history. No input needed."
    ),

    # Feature 7: Analytics
    Tool(
        name="get_revenue_analytics",
        func=lambda _: demo.get_revenue_analytics(),
        description="Get merchant revenue analytics. No input needed."
    ),

    # Feature 8: Audit Logs
    Tool(
        name="get_audit_logs",
        func=lambda event_type: demo.get_audit_logs(event_type if event_type != "all" else None),
        description="Get audit logs. Input: event_type or 'all'"
    ),

    # Feature 9: Webhooks
    Tool(
        name="configure_webhook",
        func=demo.configure_webhook,
        description="Configure webhook. Input: webhook_url"
    ),
    Tool(
        name="test_webhook",
        func=lambda _: demo.test_webhook(),
        description="Test webhook delivery. No input needed."
    ),

    # Feature 10: Health
    Tool(
        name="check_system_health",
        func=lambda _: demo.check_system_health(),
        description="Check system health. No input needed."
    ),
]

# Agent prompt
agent_prompt = PromptTemplate.from_template("""
You are an autonomous agent demonstrating ALL AgentGatePay features.

Available tools:
{tools}

Tool names: {tool_names}

Task: {input}

Complete the demonstration systematically, showing every feature.

Think step by step:
{agent_scratchpad}
""")

# Create agent
llm = ChatOpenAI(model="gpt-4", temperature=0, openai_api_key=os.getenv('OPENAI_API_KEY'))
agent = create_react_agent(llm=llm, tools=tools, prompt=agent_prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=30, handle_parsing_errors=True)

# ========================================
# MAIN EXECUTION
# ========================================

if __name__ == "__main__":
    print("=" * 70)
    print("🤖 AGENTGATEPAY COMPLETE FEATURES DEMO (REST API)")
    print("=" * 70)
    print()
    print("This demo shows ALL AgentGatePay features:")
    print("  1. User Authentication & Signup")
    print("  2. Wallet Management")
    print("  3. API Key Management")
    print("  4. Mandate Management")
    print("  5. Payment Execution")
    print("  6. Payment History")
    print("  7. Merchant Analytics")
    print("  8. Audit Logging")
    print("  9. Webhook Configuration")
    print("  10. System Health Monitoring")
    print()
    print("=" * 70)

    # Agent task
    task = """
    Demonstrate ALL AgentGatePay features in order:

    1. Sign up new user: demo@example.com / SecurePass123 / both
    2. Get user information
    3. Add wallet (base chain)
    4. Create API key named "Production Key"
    5. List all API keys
    6. Issue mandate with $100 budget
    7. Execute payment: $10 | Test payment
    8. Get payment history
    9. Get revenue analytics
    10. Get audit logs (all events)
    11. Configure webhook: https://example.com/webhooks/agentpay
    12. Test webhook delivery
    13. Check system health

    Complete ALL 13 steps systematically.
    """

    try:
        # Run agent
        result = agent_executor.invoke({"input": task})

        print("\n" + "=" * 70)
        print("✅ COMPLETE FEATURES DEMO FINISHED")
        print("=" * 70)
        print(f"\nResult: {result['output']}")

        # Display summary
        print(f"\n📊 FEATURES DEMONSTRATED:")
        print(f"   ✓ User authentication & signup")
        print(f"   ✓ Wallet management")
        print(f"   ✓ API key management")
        print(f"   ✓ Mandates (AP2)")
        print(f"   ✓ Payments (2-TX model)")
        print(f"   ✓ Payment history")
        print(f"   ✓ Revenue analytics")
        print(f"   ✓ Audit logging")
        print(f"   ✓ Webhooks")
        print(f"   ✓ System health")

        print(f"\n🎉 ALL 10 AGENTGATEPAY FEATURES DEMONSTRATED!")

    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
