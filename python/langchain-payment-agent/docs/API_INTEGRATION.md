# REST API Integration Guide - AgentGatePay Python SDK

**Complete guide to using the AgentGatePay Python SDK for autonomous agent payments.**

This guide covers the REST API approach using the official `agentgatepay-sdk` Python package. For MCP tools approach, see [MCP_INTEGRATION.md](MCP_INTEGRATION.md).

---

## Table of Contents

1. [Why Use the SDK?](#why-use-the-sdk)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [SDK Modules](#sdk-modules)
5. [Complete Workflows](#complete-workflows)
6. [Authentication](#authentication)
7. [Error Handling](#error-handling)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Why Use the SDK?

The AgentGatePay Python SDK provides a Pythonic, type-safe interface to the REST API.

**Benefits:**
- **Type Safety**: Full type hints for IDE autocomplete
- **Object-Oriented**: Clean, intuitive API design
- **Error Handling**: Custom exceptions for better debugging
- **Web3 Helpers**: Built-in blockchain utilities
- **Automatic Retries**: Smart retry logic for transient errors
- **Production-Ready**: Tested with 95%+ coverage

**SDK vs MCP Comparison:**

| Feature | Python SDK | MCP Tools |
|---------|-----------|-----------|
| **Installation** | `pip install agentgatepay-sdk` | No dependencies |
| **API Style** | Object-oriented | JSON-RPC 2.0 |
| **Type Hints** | ✅ Full Python types | ❌ JSON only |
| **IDE Support** | ✅ Autocomplete | ⚠️ Limited |
| **Framework** | Python-specific | Universal |
| **Best For** | Python apps, type safety | Multi-framework, AI agents |

**When to use SDK:**
- Building Python-only applications
- Want IDE autocomplete and type checking
- Prefer object-oriented interfaces
- Need advanced Web3 utilities

**When to use MCP:**
- Framework-agnostic integration
- Multi-language environment
- AI agent tool discovery
- Claude Desktop, OpenAI Agent Builder

---

## Installation

### Requirements

- Python 3.12 or higher
- pip package manager

### Install SDK

```bash
pip install agentgatepay-sdk>=1.1.3
```

### Verify Installation

```python
import agentgatepay_sdk
print(f"SDK Version: {agentgatepay_sdk.__version__}")  # Should be >= 1.1.3
```

### Optional Dependencies

For blockchain integration (if not using SDK's Web3 helpers):

```bash
pip install web3>=6.0.0 eth-account>=0.9.0
```

For LangChain integration:

```bash
pip install langchain>=0.1.0 langchain-openai>=0.0.5
```

---

## Quick Start

### 1. Configure Environment

Create `.env` file:

```bash
# AgentGatePay
AGENTPAY_API_URL=https://api.agentgatepay.com
BUYER_API_KEY=pk_live_YOUR_BUYER_KEY_HERE
SELLER_API_KEY=pk_live_YOUR_SELLER_KEY_HERE

# Blockchain (Base network)
BASE_RPC_URL=https://mainnet.base.org
BUYER_PRIVATE_KEY=0xYOUR_64_CHAR_PRIVATE_KEY
BUYER_WALLET=0xYOUR_BUYER_WALLET_ADDRESS
SELLER_WALLET=0xYOUR_SELLER_WALLET_ADDRESS

# OpenAI (for LangChain examples)
OPENAI_API_KEY=sk-YOUR_OPENAI_KEY
```

### 2. Initialize SDK

```python
from agentgatepay_sdk import AgentGatePay
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize SDK
agentpay = AgentGatePay(
    api_url=os.getenv('AGENTPAY_API_URL'),
    api_key=os.getenv('BUYER_API_KEY')
)

# Test connection
health = agentpay.system.health()
print(f"✅ Connected to AgentGatePay v{health['version']}")
```

### 3. First Payment Flow

```python
from web3 import Web3
from eth_account import Account

# Step 1: Issue mandate ($100 budget for 7 days)
mandate = agentpay.mandates.issue(
    subject="buyer-agent-12345",
    budget_usd=100.0,
    scope="resource.read,payment.execute",
    ttl_hours=168  # 7 days
)
print(f"✅ Mandate issued: {mandate['mandate_id']}")
print(f"   Budget: ${mandate['budget_usd']}")

# Step 2: Verify mandate
verification = agentpay.mandates.verify(mandate['mandate_token'])
print(f"✅ Mandate valid: ${verification['budget_remaining']} remaining")

# Step 3: Sign blockchain transaction (USDC on Base)
web3 = Web3(Web3.HTTPProvider(os.getenv('BASE_RPC_URL')))
account = Account.from_key(os.getenv('BUYER_PRIVATE_KEY'))

USDC_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
USDC_ABI = [{"constant": False, "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "type": "function"}]

usdc_contract = web3.eth.contract(address=USDC_ADDRESS, abi=USDC_ABI)

# Calculate merchant amount (99.5% of $10 = $9.95)
amount_usd = 10.0
merchant_amount = int(9.95 * 10**6)  # USDC has 6 decimals

tx = usdc_contract.functions.transfer(
    os.getenv('SELLER_WALLET'),
    merchant_amount
).build_transaction({
    'from': account.address,
    'nonce': web3.eth.get_transaction_count(account.address),
    'gas': 100000,
    'gasPrice': web3.eth.gas_price
})

# Sign and send
signed_tx = web3.eth.account.sign_transaction(tx, os.getenv('BUYER_PRIVATE_KEY'))
tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
print(f"✅ Blockchain TX: {receipt.transactionHash.hex()}")

# Step 4: Submit payment to AgentGatePay
payment = agentpay.payments.submit(
    mandate_token=mandate['mandate_token'],
    amount_usd=amount_usd,
    receiver_address=os.getenv('SELLER_WALLET'),
    tx_hash=receipt.transactionHash.hex(),
    chain="base"
)
print(f"✅ Payment verified: {payment['charge_id']}")
print(f"   Merchant TX: {payment['merchant_tx_hash']}")
print(f"   Commission TX: {payment['commission_tx_hash']}")
print(f"   Budget remaining: ${payment['budget_remaining']}")
```

**Expected Output:**
```
✅ Connected to AgentGatePay v1.1.3
✅ Mandate issued: mandate_abc123
   Budget: $100.0
✅ Mandate valid: $100.0 remaining
✅ Blockchain TX: 0xabc123def456...
✅ Payment verified: charge_xyz789
   Merchant TX: 0xabc123...
   Commission TX: 0xdef456...
   Budget remaining: $90.0
```

---

## SDK Modules

The SDK is organized into 7 modules, each handling a specific domain.

### Module 1: Authentication (`auth`)

**User account management and authentication.**

```python
# Create new account
user = agentpay.auth.signup(
    email="agent@example.com",
    password="SecurePass123!",
    user_type="agent"  # or "merchant" or "both"
)
api_key = user['api_key']  # Save this! Shown only once
print(f"✅ User created: {user['user']['user_id']}")

# Get current user info
user_info = agentpay.auth.me()
print(f"Email: {user_info['email']}")
print(f"Type: {user_info['user_type']}")
print(f"Wallets: {user_info['wallets']}")

# Add wallet address
wallet = agentpay.auth.add_wallet("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0")
print(f"✅ Wallet added: {wallet['wallet_address']}")

# Create new API key
new_key = agentpay.auth.create_api_key(name="Production Key")
print(f"✅ New API key: {new_key['api_key']}")  # Save immediately!

# List all API keys
keys = agentpay.auth.list_api_keys()
for key in keys['keys']:
    status = "🟢" if key['is_active'] else "🔴"
    print(f"{status} {key['name']}: {key['key_id']}")

# Revoke API key
agentpay.auth.revoke_api_key(key_id="key_old123")
print(f"✅ API key revoked")
```

**Type Signatures:**
```python
def signup(email: str, password: str, user_type: str) -> Dict[str, Any]
def me() -> Dict[str, Any]
def add_wallet(wallet_address: str) -> Dict[str, Any]
def create_api_key(name: Optional[str] = None) -> Dict[str, Any]
def list_api_keys() -> Dict[str, List[Dict[str, Any]]]
def revoke_api_key(key_id: str) -> Dict[str, Any]
```

---

### Module 2: Mandates (`mandates`)

**AP2 mandate issuance and verification.**

```python
# Issue mandate
mandate = agentpay.mandates.issue(
    subject="agent-12345",
    budget_usd=100.0,
    scope="resource.read,payment.execute",
    ttl_hours=168  # 7 days (default)
)

mandate_token = mandate['mandate_token']  # Use for payments
print(f"✅ Mandate ID: {mandate['mandate_id']}")
print(f"   Budget: ${mandate['budget_usd']}")
print(f"   Expires: {mandate['expires_at']}")

# Verify mandate
verification = agentpay.mandates.verify(mandate_token)

if verification['valid']:
    print(f"✅ Mandate valid")
    print(f"   Budget remaining: ${verification['budget_remaining']}")
    print(f"   Scope: {verification['scope']}")
else:
    print(f"❌ Mandate invalid: {verification.get('error')}")
```

**Type Signatures:**
```python
def issue(
    subject: str,
    budget_usd: float,
    scope: str,
    ttl_hours: int = 168
) -> Dict[str, Any]

def verify(mandate_token: str) -> Dict[str, Any]
```

**Mandate Scopes:**
- `resource.read` - Read resource metadata
- `payment.execute` - Execute payments
- `resource.write` - Write resources (future)

**Common Patterns:**
```python
# Check budget before payment
verification = agentpay.mandates.verify(mandate_token)
if verification['budget_remaining'] < payment_amount:
    raise ValueError("Insufficient budget")

# Issue mandate with custom TTL
mandate = agentpay.mandates.issue(
    subject="agent-12345",
    budget_usd=50.0,
    scope="resource.read,payment.execute",
    ttl_hours=24  # 1 day only
)
```

---

### Module 3: Payments (`payments`)

**Payment submission, verification, and history.**

```python
# Submit payment (after blockchain transaction)
payment = agentpay.payments.submit(
    mandate_token=mandate_token,
    amount_usd=10.0,
    receiver_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
    tx_hash="0xabc123def456...",
    chain="base",  # or "ethereum", "polygon", "arbitrum"
    resource_id="research-paper-2025"  # optional
)

print(f"✅ Payment verified: {payment['charge_id']}")
print(f"   Merchant TX: {payment['merchant_tx_hash']}")
print(f"   Commission TX: {payment['commission_tx_hash']}")
print(f"   Budget remaining: ${payment['budget_remaining']}")

# Verify payment (public, no auth)
verification = agentpay.payments.verify(
    tx_hash="0xabc123def456...",
    chain="base"
)

if verification['verified']:
    print(f"✅ Payment verified on blockchain")
    print(f"   Amount: ${verification['amount_usd']}")
    print(f"   Block: {verification['block_number']}")
    print(f"   From: {verification['from_address']}")
    print(f"   To: {verification['to_address']}")

# Quick status check
status = agentpay.payments.status("0xabc123def456...")
print(f"Status: {status['status']}")  # pending | confirmed | failed

# List payment history (merchant view)
payments = agentpay.payments.list(
    limit=50,
    start_time=1700000000,  # Unix timestamp
    end_time=1700100000
)

print(f"Total payments: {payments['total_count']}")
for payment in payments['payments']:
    print(f"  ${payment['amount_usd']} - {payment['resource_id']} - {payment['status']}")
```

**Type Signatures:**
```python
def submit(
    mandate_token: str,
    amount_usd: float,
    receiver_address: str,
    tx_hash: str,
    chain: str = "base",
    resource_id: Optional[str] = None
) -> Dict[str, Any]

def verify(tx_hash: str, chain: str = "base") -> Dict[str, Any]

def status(tx_hash: str) -> Dict[str, Any]

def list(
    limit: int = 50,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None
) -> Dict[str, Any]
```

**Supported Chains:**
- `base` - Base (default, fastest, cheapest)
- `ethereum` - Ethereum mainnet
- `polygon` - Polygon PoS
- `arbitrum` - Arbitrum One

**Supported Tokens:**
- `USDC` - USD Coin (6 decimals)
- `USDT` - Tether USD (6 decimals)
- `DAI` - Dai Stablecoin (18 decimals)

---

### Module 4: Webhooks (`webhooks`)

**Payment notification webhooks for merchants.**

```python
# Configure webhook
webhook = agentpay.webhooks.configure(
    url="https://your-server.com/webhook",
    events=["payment.completed", "payment.failed", "mandate.expired"],
    secret="your_webhook_secret_123"  # For HMAC signature verification
)

print(f"✅ Webhook configured: {webhook['webhook_id']}")
print(f"   URL: {webhook['url']}")
print(f"   Events: {', '.join(webhook['events'])}")

# List all webhooks
webhooks = agentpay.webhooks.list()
for wh in webhooks['webhooks']:
    print(f"Webhook {wh['webhook_id']}: {wh['url']}")

# Test webhook delivery
test_result = agentpay.webhooks.test(webhook['webhook_id'])
if test_result['success']:
    print(f"✅ Webhook test successful")
else:
    print(f"❌ Webhook test failed: {test_result['error']}")

# Delete webhook
agentpay.webhooks.delete(webhook['webhook_id'])
print(f"✅ Webhook deleted")
```

**Webhook Payload Example:**
```json
{
  "event": "payment.completed",
  "timestamp": 1700000000,
  "data": {
    "charge_id": "charge_abc123",
    "amount_usd": 10.0,
    "merchant_amount": 9.95,
    "commission_amount": 0.05,
    "receiver_address": "0x742d35...",
    "payer": "0x123abc...",
    "tx_hash": "0xabc123...",
    "resource_id": "research-paper-2025",
    "paid_at": 1700000000
  },
  "signature": "sha256=abc123def456..."
}
```

**Verify Webhook Signature:**
```python
import hmac
import hashlib

def verify_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    """Verify webhook HMAC signature"""
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)

# In your webhook handler
@app.route('/webhook', methods=['POST'])
def webhook_handler():
    payload = request.get_data(as_text=True)
    signature = request.headers.get('X-Webhook-Signature')

    if not verify_webhook_signature(payload, signature, WEBHOOK_SECRET):
        return jsonify({"error": "Invalid signature"}), 401

    event = request.json
    if event['event'] == 'payment.completed':
        handle_payment_completed(event['data'])

    return jsonify({"status": "ok"}), 200
```

**Type Signatures:**
```python
def configure(
    url: str,
    events: List[str],
    secret: Optional[str] = None
) -> Dict[str, Any]

def list() -> Dict[str, List[Dict[str, Any]]]

def test(webhook_id: str) -> Dict[str, Any]

def delete(webhook_id: str) -> Dict[str, Any]
```

---

### Module 5: Analytics (`analytics`)

**Revenue and spending analytics.**

```python
# Get user analytics (agent or merchant)
analytics = agentpay.analytics.me(
    start_time=1700000000,  # Optional: Unix timestamp
    end_time=1700100000
)

if analytics['user_type'] == 'agent':
    print(f"Total spent: ${analytics['total_spent_usd']}")
    print(f"Transactions: {analytics['transaction_count']}")
    print(f"Active mandates: {analytics['active_mandates']}")
    print(f"Budget remaining: ${analytics['budget_remaining']}")

    print(f"\nTop merchants:")
    for merchant in analytics['top_merchants']:
        print(f"  {merchant['address']}: ${merchant['amount']}")

elif analytics['user_type'] == 'merchant':
    print(f"Total revenue: ${analytics['total_revenue_usd']}")
    print(f"Net revenue: ${analytics['net_revenue_usd']}")
    print(f"Commission paid: ${analytics['commission_paid_usd']}")
    print(f"Transactions: {analytics['transaction_count']}")
    print(f"Unique payers: {analytics['unique_payers']}")

# Get public platform analytics (no auth required)
public_analytics = agentpay.analytics.public()
print(f"\nPlatform Stats:")
print(f"Total volume: ${public_analytics['total_volume_usd']}")
print(f"Total transactions: {public_analytics['transaction_count']}")
print(f"Active users: {public_analytics['active_users']}")
```

**Type Signatures:**
```python
def me(
    start_time: Optional[int] = None,
    end_time: Optional[int] = None
) -> Dict[str, Any]

def public() -> Dict[str, Any]
```

---

### Module 6: Audit (`audit`)

**Comprehensive audit logging and compliance.**

```python
# Get audit logs
logs = agentpay.audit.logs(
    event_type="payment_completed",  # Optional filter
    limit=50,
    start_time=1700000000,
    end_time=1700100000
)

print(f"Total logs: {logs['total_count']}")
for log in logs['logs']:
    print(f"[{log['timestamp']}] {log['event_type']}: {log['description']}")

# Get audit statistics
stats = agentpay.audit.stats()
print(f"\nAudit Stats:")
print(f"Total events: {stats['total_events']}")
print(f"Event types: {', '.join(stats['event_types'])}")
print(f"Time range: {stats['oldest_event']} - {stats['newest_event']}")

# Get logs by transaction
tx_logs = agentpay.audit.by_transaction("0xabc123def456...")
print(f"\nTransaction logs: {len(tx_logs['logs'])} events")
for log in tx_logs['logs']:
    print(f"  {log['event_type']}: {log['description']}")
```

**Common Event Types:**
- `user_signup` - New user registration
- `mandate_issued` - Mandate created
- `mandate_verified` - Mandate validation
- `payment_initiated` - Payment started
- `payment_completed` - Payment successful
- `payment_failed` - Payment failed
- `webhook_delivered` - Webhook sent
- `api_key_created` - New API key generated
- `api_key_revoked` - API key revoked
- `audit_log_access` - Audit log viewed

**Type Signatures:**
```python
def logs(
    event_type: Optional[str] = None,
    limit: int = 50,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None
) -> Dict[str, Any]

def stats() -> Dict[str, Any]

def by_transaction(tx_hash: str) -> Dict[str, Any]
```

---

### Module 7: System (`system`)

**System health and status checks.**

```python
# Check system health
health = agentpay.system.health()

if health['status'] == 'ok':
    print(f"✅ System healthy")
    print(f"Version: {health['version']}")
    print(f"Uptime: {health['uptime_hours']} hours")
    print(f"Chains: {', '.join(health['chains'])}")
    print(f"Tokens: {', '.join(health['tokens'])}")
else:
    print(f"⚠️ System degraded: {health['message']}")
```

**Type Signature:**
```python
def health() -> Dict[str, Any]
```

---

## Complete Workflows

### Workflow 1: Autonomous Buyer Agent

**Full payment flow from account creation to resource access.**

```python
from agentgatepay_sdk import AgentGatePay
from web3 import Web3
from eth_account import Account
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Step 1: Initialize SDK (first time: no API key yet)
agentpay_anon = AgentGatePay(api_url=os.getenv('AGENTPAY_API_URL'))

# Step 2: Create buyer account
user = agentpay_anon.auth.signup(
    email="buyer_agent@example.com",
    password="SecurePass123!",
    user_type="agent"
)
api_key = user['api_key']  # SAVE THIS!
print(f"✅ Account created: {user['user']['user_id']}")

# Step 3: Re-initialize SDK with API key (5x rate limit)
agentpay = AgentGatePay(
    api_url=os.getenv('AGENTPAY_API_URL'),
    api_key=api_key
)

# Step 4: Add wallet address
wallet = agentpay.auth.add_wallet(os.getenv('BUYER_WALLET'))
print(f"✅ Wallet added: {wallet['wallet_address']}")

# Step 5: Issue mandate ($100 budget, 7 days)
mandate = agentpay.mandates.issue(
    subject="buyer-agent-12345",
    budget_usd=100.0,
    scope="resource.read,payment.execute",
    ttl_hours=168
)
mandate_token = mandate['mandate_token']
print(f"✅ Mandate issued: {mandate['mandate_id']}")

# Step 6: Verify mandate
verification = agentpay.mandates.verify(mandate_token)
print(f"✅ Budget: ${verification['budget_remaining']}")

# Step 7: Discover resources from seller
seller_url = "http://localhost:8000"
catalog_response = requests.get(f"{seller_url}/catalog")
catalog = catalog_response.json()['catalog']
resource = catalog[0]
print(f"✅ Found resource: {resource['id']} (${resource['price_usd']})")

# Step 8: Request resource (expect HTTP 402)
resource_response = requests.get(
    f"{seller_url}/resource/{resource['id']}",
    headers={
        "x-agent-id": "buyer-agent-12345",
        "x-mandate": mandate_token
    }
)
assert resource_response.status_code == 402
payment_info = resource_response.json()
print(f"✅ 402 Payment Required: ${payment_info['amount_usd']}")

# Step 9: Sign blockchain transaction
web3 = Web3(Web3.HTTPProvider(os.getenv('BASE_RPC_URL')))
account = Account.from_key(os.getenv('BUYER_PRIVATE_KEY'))

USDC_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
USDC_ABI = [{"constant": False, "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "type": "function"}]

usdc_contract = web3.eth.contract(address=USDC_ADDRESS, abi=USDC_ABI)
merchant_amount = int(payment_info['merchant_amount'] * 10**6)

tx = usdc_contract.functions.transfer(
    payment_info['receiver_address'],
    merchant_amount
).build_transaction({
    'from': account.address,
    'nonce': web3.eth.get_transaction_count(account.address),
    'gas': 100000,
    'gasPrice': web3.eth.gas_price
})

signed_tx = web3.eth.account.sign_transaction(tx, os.getenv('BUYER_PRIVATE_KEY'))
tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
print(f"✅ Blockchain TX: {receipt.transactionHash.hex()}")

# Step 10: Submit payment to AgentGatePay
payment = agentpay.payments.submit(
    mandate_token=mandate_token,
    amount_usd=payment_info['amount_usd'],
    receiver_address=payment_info['receiver_address'],
    tx_hash=receipt.transactionHash.hex(),
    chain="base",
    resource_id=resource['id']
)
print(f"✅ Payment verified: {payment['charge_id']}")
print(f"   Budget remaining: ${payment['budget_remaining']}")

# Step 11: Claim resource with payment proof
resource_response = requests.get(
    f"{seller_url}/resource/{resource['id']}",
    headers={
        "x-agent-id": "buyer-agent-12345",
        "x-mandate": mandate_token,
        "x-payment": receipt.transactionHash.hex()
    }
)
assert resource_response.status_code == 200
resource_data = resource_response.json()
print(f"✅ Resource claimed: {len(resource_data['content'])} bytes")

# Step 12: View audit trail
logs = agentpay.audit.logs(limit=10)
print(f"✅ Audit logs: {logs['total_count']} events")
for log in logs['logs'][:5]:
    print(f"   [{log['event_type']}] {log['description']}")

# Step 13: Check spending analytics
analytics = agentpay.analytics.me()
print(f"✅ Analytics:")
print(f"   Total spent: ${analytics['total_spent_usd']}")
print(f"   Transactions: {analytics['transaction_count']}")
print(f"   Budget remaining: ${analytics['budget_remaining']}")
```

---

### Workflow 2: Merchant Payment Verification

**Merchant receives payment and verifies before delivering resource.**

```python
from agentgatepay_sdk import AgentGatePay
from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Initialize SDK with merchant API key
agentpay = AgentGatePay(
    api_url=os.getenv('AGENTPAY_API_URL'),
    api_key=os.getenv('SELLER_API_KEY')
)

# In-memory resource catalog
CATALOG = {
    "research-paper-2025": {
        "id": "research-paper-2025",
        "price_usd": 10.0,
        "description": "AI Research Paper 2025",
        "content": "SECRET_RESEARCH_DATA_HERE"
    }
}

@app.route('/catalog', methods=['GET'])
def get_catalog():
    """Return public catalog (no auth required)"""
    catalog = [
        {
            "id": r['id'],
            "price_usd": r['price_usd'],
            "description": r['description']
        }
        for r in CATALOG.values()
    ]
    return jsonify({"catalog": catalog}), 200

@app.route('/resource/<resource_id>', methods=['GET'])
def get_resource(resource_id):
    """HTTP 402 payment flow"""

    # Check resource exists
    if resource_id not in CATALOG:
        return jsonify({"error": "Resource not found"}), 404

    resource = CATALOG[resource_id]

    # Check for payment header
    payment_tx = request.headers.get('x-payment')

    if not payment_tx:
        # No payment: Return HTTP 402
        return jsonify({
            "error": "Payment Required",
            "amount_usd": resource['price_usd'],
            "merchant_amount": resource['price_usd'] * 0.995,
            "commission_amount": resource['price_usd'] * 0.005,
            "receiver_address": os.getenv('SELLER_WALLET'),
            "resource_id": resource_id
        }), 402

    # Verify payment with AgentGatePay
    try:
        verification = agentpay.payments.verify(tx_hash=payment_tx, chain="base")

        if not verification['verified']:
            return jsonify({
                "error": "Payment verification failed",
                "reason": verification.get('reason', 'Unknown')
            }), 400

        # Check payment amount
        if verification['amount_usd'] < resource['price_usd']:
            return jsonify({
                "error": "Insufficient payment",
                "expected": resource['price_usd'],
                "received": verification['amount_usd']
            }), 400

        # Check receiver address
        if verification['to_address'].lower() != os.getenv('SELLER_WALLET').lower():
            return jsonify({
                "error": "Payment sent to wrong address",
                "expected": os.getenv('SELLER_WALLET'),
                "received": verification['to_address']
            }), 400

        # Payment verified: Deliver resource
        return jsonify({
            "resource_id": resource_id,
            "content": resource['content'],
            "tx_hash": payment_tx
        }), 200

    except Exception as e:
        return jsonify({"error": f"Verification error: {str(e)}"}), 500

@app.route('/webhook', methods=['POST'])
def webhook_handler():
    """Receive payment notifications"""
    import hmac
    import hashlib

    # Verify signature
    payload = request.get_data(as_text=True)
    signature = request.headers.get('X-Webhook-Signature')
    webhook_secret = os.getenv('WEBHOOK_SECRET')

    expected = hmac.new(
        webhook_secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(f"sha256={expected}", signature):
        return jsonify({"error": "Invalid signature"}), 401

    # Process webhook
    event = request.json
    if event['event'] == 'payment.completed':
        print(f"✅ Payment received: ${event['data']['amount_usd']}")

    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    # Configure webhook on startup
    try:
        webhook = agentpay.webhooks.configure(
            url="https://your-server.com/webhook",
            events=["payment.completed", "payment.failed"],
            secret=os.getenv('WEBHOOK_SECRET')
        )
        print(f"✅ Webhook configured: {webhook['webhook_id']}")
    except Exception as e:
        print(f"⚠️ Webhook configuration failed: {e}")

    # Start Flask server
    app.run(host='0.0.0.0', port=8000)
```

---

## Authentication

### API Key Management

```python
# Option 1: Constructor (recommended)
agentpay = AgentGatePay(
    api_url="https://api.agentgatepay.com",
    api_key="pk_live_abc123..."
)

# Option 2: Set after initialization
agentpay = AgentGatePay(api_url="https://api.agentgatepay.com")
agentpay.api_key = "pk_live_abc123..."

# Option 3: From environment variable
os.environ['AGENTPAY_API_KEY'] = "pk_live_abc123..."
agentpay = AgentGatePay(
    api_url="https://api.agentgatepay.com",
    api_key=os.getenv('AGENTPAY_API_KEY')
)
```

### Rate Limits

- **Without API Key**: 20 requests/minute
- **With API Key**: 100 requests/minute (5x higher)

**Check Rate Limit Headers:**
```python
# All SDK methods return response metadata
result = agentpay.mandates.issue(...)

# Access response headers via internal _last_response
if hasattr(agentpay, '_last_response'):
    headers = agentpay._last_response.headers
    print(f"Limit: {headers.get('X-RateLimit-Limit')}")
    print(f"Remaining: {headers.get('X-RateLimit-Remaining')}")
    print(f"Reset: {headers.get('X-RateLimit-Reset')}")
```

---

## Error Handling

### SDK Exceptions

The SDK raises custom exceptions for better error handling:

```python
from agentgatepay_sdk.exceptions import (
    AuthenticationError,
    MandateError,
    PaymentError,
    RateLimitError,
    ValidationError,
    APIError
)

try:
    mandate = agentpay.mandates.issue(
        subject="agent-12345",
        budget_usd=100.0,
        scope="resource.read,payment.execute"
    )
except AuthenticationError as e:
    print(f"❌ Auth failed: {e}")
    # Re-authenticate or get new API key

except MandateError as e:
    print(f"❌ Mandate error: {e}")
    # Check mandate parameters

except RateLimitError as e:
    print(f"❌ Rate limited: {e}")
    # Wait and retry (retry_after available)
    time.sleep(e.retry_after)

except ValidationError as e:
    print(f"❌ Validation error: {e}")
    # Check input parameters

except APIError as e:
    print(f"❌ API error: {e}")
    # General API error, check message

except Exception as e:
    print(f"❌ Unexpected error: {e}")
    # Unknown error, log and investigate
```

### Retry Logic

```python
import time

def call_with_retry(func, *args, max_retries=3, **kwargs):
    """Call SDK method with automatic retry"""

    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)

        except RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = e.retry_after or 60
                print(f"⚠️ Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            raise

        except APIError as e:
            if attempt < max_retries - 1 and e.status_code >= 500:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"⚠️ Server error, retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            raise

    raise Exception(f"Failed after {max_retries} attempts")

# Usage
mandate = call_with_retry(
    agentpay.mandates.issue,
    subject="agent-12345",
    budget_usd=100.0,
    scope="resource.read,payment.execute"
)
```

---

## Best Practices

### 1. Secure API Key Storage

```python
# ✅ GOOD: Environment variables
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv('AGENTPAY_API_KEY')

# ❌ BAD: Hardcoded keys
api_key = "pk_live_abc123..."  # NEVER DO THIS!
```

### 2. Validate Inputs Before SDK Calls

```python
from web3 import Web3

def validate_wallet_address(address: str) -> bool:
    """Validate Ethereum address with checksum"""
    return Web3.is_address(address)

def validate_amount(amount: float) -> bool:
    """Validate payment amount"""
    return 0 < amount <= 10000  # Max $10k per payment

# Validate before calling SDK
if not validate_wallet_address(receiver_address):
    raise ValueError("Invalid wallet address")

if not validate_amount(amount_usd):
    raise ValueError("Invalid payment amount")

payment = agentpay.payments.submit(...)
```

### 3. Check Mandate Budget Before Payment

```python
def safe_payment(mandate_token, amount_usd, receiver_address, tx_hash):
    """Execute payment with mandate budget check"""

    # Step 1: Verify mandate
    verification = agentpay.mandates.verify(mandate_token)

    if not verification['valid']:
        raise ValueError(f"Mandate invalid: {verification.get('error')}")

    # Step 2: Check budget
    if verification['budget_remaining'] < amount_usd:
        raise ValueError(
            f"Insufficient budget: "
            f"${verification['budget_remaining']} < ${amount_usd}"
        )

    # Step 3: Submit payment
    return agentpay.payments.submit(
        mandate_token=mandate_token,
        amount_usd=amount_usd,
        receiver_address=receiver_address,
        tx_hash=tx_hash,
        chain="base"
    )
```

### 4. Use Connection Pooling for Performance

```python
import requests
from agentgatepay_sdk import AgentGatePay

# Create session with connection pooling
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(
    pool_connections=10,
    pool_maxsize=20
)
session.mount('https://', adapter)

# Pass session to SDK (if supported in future versions)
# agentpay = AgentGatePay(api_url=..., api_key=..., session=session)
```

### 5. Log SDK Operations for Debugging

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def logged_mandate_issue(**kwargs):
    """Issue mandate with logging"""
    logger.info(f"Issuing mandate: {kwargs}")

    try:
        mandate = agentpay.mandates.issue(**kwargs)
        logger.info(f"Mandate issued: {mandate['mandate_id']}")
        return mandate

    except Exception as e:
        logger.error(f"Mandate issuance failed: {e}")
        raise

# Usage
mandate = logged_mandate_issue(
    subject="agent-12345",
    budget_usd=100.0,
    scope="resource.read,payment.execute"
)
```

### 6. Handle Blockchain Delays

```python
import time

def submit_payment_with_confirmation(mandate_token, amount_usd, receiver_address, web3_tx_hash):
    """Submit payment with blockchain confirmation wait"""

    # Wait for blockchain confirmation (Base: 2-5 seconds typically)
    print(f"⏳ Waiting for blockchain confirmation...")
    time.sleep(10)  # Safe wait time for Base network

    # Then submit to AgentGatePay
    return agentpay.payments.submit(
        mandate_token=mandate_token,
        amount_usd=amount_usd,
        receiver_address=receiver_address,
        tx_hash=web3_tx_hash.hex(),
        chain="base"
    )
```

---

## Troubleshooting

### Issue: SDK import fails

**Symptom:**
```python
ModuleNotFoundError: No module named 'agentgatepay_sdk'
```

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install/upgrade SDK
pip install --upgrade agentgatepay-sdk>=1.1.3

# Verify installation
python -c "import agentgatepay_sdk; print(agentgatepay_sdk.__version__)"
```

---

### Issue: Authentication fails

**Symptom:**
```python
AuthenticationError: Invalid API key
```

**Solution:**
```python
# Check API key format (must start with pk_live_ or pk_test_)
if not api_key.startswith('pk_'):
    raise ValueError("Invalid API key format")

# Check .env file
print(f"API Key: {os.getenv('AGENTPAY_API_KEY')}")  # Should not be None

# Verify key is active
keys = agentpay.auth.list_api_keys()
active_keys = [k for k in keys['keys'] if k['is_active']]
print(f"Active keys: {len(active_keys)}")
```

---

### Issue: Mandate verification fails

**Symptom:**
```python
MandateError: Mandate not found or expired
```

**Solution:**
```python
# Mandates have a TTL (default 7 days), issue a new one
mandate = agentpay.mandates.issue(
    subject="agent-12345",
    budget_usd=100.0,
    scope="resource.read,payment.execute",
    ttl_hours=168  # 7 days
)

# Save mandate token for future use
mandate_token = mandate['mandate_token']
```

---

### Issue: Payment verification fails

**Symptom:**
```python
PaymentError: Transaction not found on blockchain
```

**Solution:**
```python
import time

# 1. Wait longer for blockchain confirmation
time.sleep(15)  # Base network needs 10-15 seconds

# 2. Verify correct chain
payment = agentpay.payments.verify(
    tx_hash=tx_hash,
    chain="base"  # Must match blockchain network
)

# 3. Check transaction on BaseScan
print(f"Check TX: https://basescan.org/tx/{tx_hash}")
```

---

### Issue: Rate limit exceeded

**Symptom:**
```python
RateLimitError: Rate limit exceeded (20 requests/minute)
```

**Solution:**
```python
# 1. Create account to get 5x higher rate limit
user = agentpay.auth.signup(
    email="agent@example.com",
    password="SecurePass123!",
    user_type="agent"
)
api_key = user['api_key']

# 2. Use new API key (100 requests/minute)
agentpay = AgentGatePay(
    api_url="https://api.agentgatepay.com",
    api_key=api_key
)

# 3. Add retry logic with exponential backoff
from agentgatepay_sdk.exceptions import RateLimitError
import time

try:
    result = agentpay.mandates.issue(...)
except RateLimitError as e:
    time.sleep(e.retry_after or 60)
    result = agentpay.mandates.issue(...)  # Retry
```

---

## See Also

- **[QUICK_START.md](QUICK_START.md)** - 5-minute setup guide
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common errors & solutions
- **[MCP_INTEGRATION.md](MCP_INTEGRATION.md)** - MCP tools approach
- **[README.md](../README.md)** - Examples overview

---

**Need Help?**
- Email: support@agentgatepay.com
- GitHub: https://github.com/AgentGatePay/agentgatepay-examples/issues
- Docs: https://docs.agentgatepay.com
- SDK Source: https://github.com/AgentGatePay/agentgatepay-sdks

**Python SDK Resources:**
- PyPI: https://pypi.org/project/agentgatepay-sdk/
- API Reference: https://docs.agentgatepay.com/python-sdk
- Type Stubs: Included in package for IDE autocomplete
