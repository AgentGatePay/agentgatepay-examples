# MCP Integration Guide - AgentGatePay + LangChain

**Complete guide to using AgentGatePay's 15 MCP tools with LangChain agents.**

MCP (Model Context Protocol) provides a standardized JSON-RPC 2.0 interface for AI agents to interact with AgentGatePay. This guide covers all 15 tools with complete examples.

---

## Table of Contents

1. [What is MCP?](#what-is-mcp)
2. [MCP vs REST API](#mcp-vs-rest-api)
3. [Getting Started](#getting-started)
4. [All 15 MCP Tools](#all-15-mcp-tools)
5. [Complete Workflows](#complete-workflows)
6. [Authentication](#authentication)
7. [Error Handling](#error-handling)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## What is MCP?

**MCP (Model Context Protocol)** is a JSON-RPC 2.0 based protocol that allows AI agents to discover and use tools in a standardized way.

**Benefits:**
- **Standardized**: Works with any MCP-compatible AI framework
- **Discoverable**: Tools are self-documenting with schemas
- **Type-Safe**: JSON Schema validation for all inputs/outputs
- **Framework-Agnostic**: Same tools work with LangChain, AutoGPT, CrewAI, etc.

**AgentGatePay MCP Endpoint:**
```
https://api.agentgatepay.com/mcp/tools/call
```

---

## MCP vs REST API

Both approaches offer **100% feature parity** - use whichever fits your architecture better.

| Feature | MCP Tools | REST API (SDK) |
|---------|-----------|----------------|
| **Protocol** | JSON-RPC 2.0 | HTTP REST |
| **Discovery** | `tools/list` method | Documentation |
| **Type Safety** | JSON Schema | Python type hints |
| **Auth** | Header-based | SDK constructor |
| **Frameworks** | Universal | Python-specific |
| **Best For** | Multi-framework, AI agents | Python apps, type safety |

**When to use MCP:**
- Building framework-agnostic AI agents
- Need runtime tool discovery
- Integrating with multiple AI platforms
- Using Claude Desktop, OpenAI Agent Builder

**When to use REST API (SDK):**
- Python-only application
- Want IDE autocomplete and type checking
- Prefer object-oriented interface
- Need advanced Web3 helpers

---

## Getting Started

### 1. Installation

```bash
pip install requests>=2.31.0
```

No SDK required for MCP - just standard HTTP!

### 2. Basic MCP Call

```python
import requests
import json

MCP_ENDPOINT = "https://api.agentgatepay.com/mcp/tools/call"

def call_mcp_tool(tool_name: str, arguments: dict, api_key: str = None) -> dict:
    """Call AgentGatePay MCP tool via JSON-RPC 2.0"""

    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        },
        "id": 1
    }

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key

    response = requests.post(MCP_ENDPOINT, json=payload, headers=headers, timeout=30)
    response.raise_for_status()

    result = response.json()
    if "error" in result:
        raise Exception(f"MCP Error: {result['error']}")

    # Parse result content (MCP returns stringified JSON)
    content_text = result['result']['content'][0]['text']
    return json.loads(content_text)
```

### 3. Tool Discovery

```python
def list_mcp_tools() -> list:
    """Discover all available MCP tools"""

    payload = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": 1
    }

    response = requests.post(
        "https://api.agentgatepay.com/mcp/tools/list",
        json=payload,
        timeout=30
    )

    result = response.json()
    return result['result']['tools']

# List all tools
tools = list_mcp_tools()
for tool in tools:
    print(f"{tool['name']}: {tool['description']}")
```

---

## All 15 MCP Tools

### Category 1: User Management (3 tools)

#### 1. `agentpay_signup` - Create Account

**Description:** Register a new AgentGatePay user account and receive API key.

**Input Schema:**
```json
{
  "email": "string (required, valid email)",
  "password": "string (required, 8+ chars)",
  "user_type": "agent | merchant | both (required)"
}
```

**Example:**
```python
result = call_mcp_tool("agentpay_signup", {
    "email": "agent@example.com",
    "password": "SecurePass123!",
    "user_type": "agent"
})

api_key = result['api_key']  # Save this! Shown only once
user_id = result['user']['user_id']
print(f"Account created: {user_id}")
print(f"API Key: {api_key}")
```

**Output:**
```json
{
  "api_key": "pk_live_abc123def456...",
  "user": {
    "user_id": "user_123",
    "email": "agent@example.com",
    "user_type": "agent",
    "created_at": 1700000000
  }
}
```

---

#### 2. `agentpay_get_user_info` - Get Account Info

**Description:** Retrieve current user's account information.

**Input Schema:**
```json
{
  "api_key": "string (required)"
}
```

**Example:**
```python
result = call_mcp_tool("agentpay_get_user_info", {
    "api_key": api_key
})

print(f"User ID: {result['user_id']}")
print(f"Email: {result['email']}")
print(f"Wallets: {result['wallets']}")
```

**Output:**
```json
{
  "user_id": "user_123",
  "email": "agent@example.com",
  "user_type": "agent",
  "wallets": ["0x742d35..."],
  "created_at": 1700000000,
  "reputation_score": 100
}
```

---

#### 3. `agentpay_add_wallet` - Add Wallet Address

**Description:** Add Ethereum wallet address to your account.

**Input Schema:**
```json
{
  "api_key": "string (required)",
  "wallet_address": "string (required, 0x... format)"
}
```

**Example:**
```python
result = call_mcp_tool("agentpay_add_wallet", {
    "api_key": api_key,
    "wallet_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
})

print(f"Wallet added: {result['wallet_address']}")
print(f"Total wallets: {len(result['wallets'])}")
```

**Output:**
```json
{
  "message": "Wallet added successfully",
  "wallet_address": "0x742d35...",
  "wallets": ["0x742d35..."]
}
```

---

### Category 2: API Key Management (3 tools)

#### 4. `agentpay_create_api_key` - Generate New API Key

**Description:** Create a new API key for your account (limit: 10/day).

**Input Schema:**
```json
{
  "api_key": "string (required, existing key)",
  "name": "string (optional, key label)"
}
```

**Example:**
```python
result = call_mcp_tool("agentpay_create_api_key", {
    "api_key": api_key,
    "name": "Production Key"
})

new_key = result['api_key']  # Save this! Shown only once
print(f"New API Key: {new_key}")
print(f"Key ID: {result['key_id']}")
```

**Output:**
```json
{
  "api_key": "pk_live_xyz789abc456...",
  "key_id": "key_abc123",
  "name": "Production Key",
  "created_at": 1700000000
}
```

---

#### 5. `agentpay_list_api_keys` - List All API Keys

**Description:** List all API keys for your account.

**Input Schema:**
```json
{
  "api_key": "string (required)"
}
```

**Example:**
```python
result = call_mcp_tool("agentpay_list_api_keys", {
    "api_key": api_key
})

for key in result['keys']:
    status = "🟢 Active" if key['is_active'] else "🔴 Revoked"
    print(f"{status} {key['name']}: {key['key_id']}")
```

**Output:**
```json
{
  "keys": [
    {
      "key_id": "key_abc123",
      "name": "Production Key",
      "created_at": 1700000000,
      "is_active": true
    }
  ]
}
```

---

#### 6. `agentpay_revoke_api_key` - Revoke API Key

**Description:** Revoke an API key (soft delete, cannot be undone).

**Input Schema:**
```json
{
  "api_key": "string (required, your current key)",
  "key_id": "string (required, key to revoke)"
}
```

**Example:**
```python
result = call_mcp_tool("agentpay_revoke_api_key", {
    "api_key": api_key,
    "key_id": "key_old123"
})

print(f"Status: {result['message']}")
```

**Output:**
```json
{
  "message": "API key revoked successfully",
  "key_id": "key_old123",
  "revoked_at": 1700000100
}
```

---

### Category 3: Mandate Management (2 tools)

#### 7. `agentpay_issue_mandate` - Create Payment Mandate

**Description:** Issue AP2 mandate with budget authorization.

**Input Schema:**
```json
{
  "api_key": "string (required)",
  "subject": "string (required, agent identifier)",
  "budget_usd": "number (required, max spend)",
  "scope": "string (required, permissions)",
  "ttl_hours": "number (optional, default 168 = 7 days)"
}
```

**Example:**
```python
result = call_mcp_tool("agentpay_issue_mandate", {
    "api_key": api_key,
    "subject": "agent-12345",
    "budget_usd": 100.0,
    "scope": "resource.read,payment.execute",
    "ttl_hours": 168  # 7 days
})

mandate_token = result['mandate_token']  # Use for payments
print(f"Mandate issued: {result['mandate_id']}")
print(f"Budget: ${result['budget_usd']}")
print(f"Expires: {result['expires_at']}")
```

**Output:**
```json
{
  "mandate_id": "mandate_abc123",
  "mandate_token": "eyJhbGciOiJFZERTQSI...",
  "subject": "agent-12345",
  "budget_usd": 100.0,
  "scope": "resource.read,payment.execute",
  "issued_at": 1700000000,
  "expires_at": 1700604800
}
```

---

#### 8. `agentpay_verify_mandate` - Verify Mandate

**Description:** Verify mandate token and check remaining budget.

**Input Schema:**
```json
{
  "mandate_token": "string (required)"
}
```

**Example:**
```python
result = call_mcp_tool("agentpay_verify_mandate", {
    "mandate_token": mandate_token
})

if result['valid']:
    print(f"✅ Mandate valid")
    print(f"Budget remaining: ${result['budget_remaining']}")
else:
    print(f"❌ Mandate invalid: {result['error']}")
```

**Output:**
```json
{
  "valid": true,
  "mandate_id": "mandate_abc123",
  "subject": "agent-12345",
  "budget_usd": 100.0,
  "budget_remaining": 90.0,
  "scope": "resource.read,payment.execute",
  "expires_at": 1700604800
}
```

---

### Category 4: Payment Execution (4 tools)

#### 9. `agentpay_submit_payment` - Execute Payment

**Description:** Submit blockchain payment proof after signing 2 transactions (merchant + commission). Gateway verifies both transactions on-chain.

**Input Schema:**
```json
{
  "api_key": "string (required)",
  "mandate_token": "string (required)",
  "amount_usd": "number (required)",
  "receiver_address": "string (required, 0x...)",
  "resource_id": "string (optional)",
  "tx_hash": "string (required, merchant blockchain tx hash)",
  "chain": "base | ethereum | polygon | arbitrum (optional, default: base)"
}
```

**Complete 3-Step Payment Flow:**
```python
import requests
import json
import base64
from web3 import Web3
from eth_account import Account

# Step 1: Fetch commission configuration dynamically
commission_response = requests.get(
    "https://api.agentgatepay.com/v1/config/commission",
    headers={"x-api-key": api_key}
)
commission_config = commission_response.json()
commission_address = commission_config['commission_address']
commission_rate = commission_config.get('commission_rate', 0.005)
print(f"Commission: {commission_rate*100}% to {commission_address[:10]}...")

# Step 2: Sign TWO blockchain transactions
web3 = Web3(Web3.HTTPProvider("https://mainnet.base.org"))
account = Account.from_key(BUYER_PRIVATE_KEY)

USDC_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
USDC_ABI = [{"constant": False, "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "type": "function"}]
usdc_contract = web3.eth.contract(address=USDC_ADDRESS, abi=USDC_ABI)

amount_usd = 10.0
merchant_amount = int(amount_usd * (1 - commission_rate) * 10**6)  # 99.5%
commission_amount = int(amount_usd * commission_rate * 10**6)      # 0.5%

# TX 1: Merchant payment
tx1 = usdc_contract.functions.transfer(
    receiver_address, merchant_amount
).build_transaction({
    'from': account.address,
    'nonce': web3.eth.get_transaction_count(account.address),
    'gas': 100000,
    'gasPrice': web3.eth.gas_price
})
signed_tx1 = web3.eth.account.sign_transaction(tx1, BUYER_PRIVATE_KEY)
tx_hash1 = web3.eth.send_raw_transaction(signed_tx1.raw_transaction)
receipt1 = web3.eth.wait_for_transaction_receipt(tx_hash1)
print(f"✅ TX 1/2 confirmed: {receipt1.transactionHash.hex()}")

# TX 2: Commission payment
tx2 = usdc_contract.functions.transfer(
    commission_address, commission_amount
).build_transaction({
    'from': account.address,
    'nonce': web3.eth.get_transaction_count(account.address),
    'gas': 100000,
    'gasPrice': web3.eth.gas_price
})
signed_tx2 = web3.eth.account.sign_transaction(tx2, BUYER_PRIVATE_KEY)
tx_hash2 = web3.eth.send_raw_transaction(signed_tx2.raw_transaction)
receipt2 = web3.eth.wait_for_transaction_receipt(tx_hash2)
print(f"✅ TX 2/2 confirmed: {receipt2.transactionHash.hex()}")

# Step 3: Submit payment proof to AgentGatePay gateway
payment_payload = {
    "scheme": "eip3009",
    "tx_hash": receipt1.transactionHash.hex(),
    "tx_hash_commission": receipt2.transactionHash.hex()
}
payment_b64 = base64.b64encode(json.dumps(payment_payload).encode()).decode()

payment_response = requests.get(
    f"https://api.agentgatepay.com/x402/resource?chain=base&token=USDC&price_usd={amount_usd}",
    headers={
        "x-api-key": api_key,
        "x-mandate": mandate_token,
        "x-payment": payment_b64
    }
)
result = payment_response.json()

print(f"✅ Payment verified by gateway: {result.get('charge_id')}")
print(f"   Merchant TX: {receipt1.transactionHash.hex()}")
print(f"   Commission TX: {receipt2.transactionHash.hex()}")

# Fetch updated budget
verification = call_mcp_tool("agentpay_verify_mandate", {"mandate_token": mandate_token})
print(f"   Budget remaining: ${verification['budget_remaining']}")
```

**Output:**
```json
{
  "charge_id": "charge_abc123",
  "merchant_tx_hash": "0xabc123...",
  "commission_tx_hash": "0xdef456...",
  "amount_usd": 10.0,
  "merchant_amount": 9.95,
  "commission_amount": 0.05,
  "receiver_address": "0x742d35...",
  "budget_remaining": 90.0,
  "paid_at": 1700000000,
  "chain": "base"
}
```

---

#### 10. `agentpay_verify_payment` - Verify Payment

**Description:** Verify blockchain payment status (public, no auth required).

**Input Schema:**
```json
{
  "tx_hash": "string (required, 0x...)",
  "chain": "base | ethereum | polygon | arbitrum (optional, default: base)"
}
```

**Example:**
```python
result = call_mcp_tool("agentpay_verify_payment", {
    "tx_hash": "0xabc123def456...",
    "chain": "base"
})

if result['verified']:
    print(f"✅ Payment verified")
    print(f"Amount: ${result['amount_usd']}")
    print(f"Confirmed in block: {result['block_number']}")
else:
    print(f"❌ Payment not found: {result['reason']}")
```

**Output:**
```json
{
  "verified": true,
  "tx_hash": "0xabc123...",
  "amount_usd": 10.0,
  "from_address": "0x742d35...",
  "to_address": "0x123abc...",
  "block_number": 12345678,
  "confirmed_at": 1700000000,
  "chain": "base"
}
```

---

#### 11. `agentpay_get_payment_status` - Quick Status Check

**Description:** Fast payment status check (lighter than full verification).

**Input Schema:**
```json
{
  "tx_hash": "string (required)"
}
```

**Example:**
```python
result = call_mcp_tool("agentpay_get_payment_status", {
    "tx_hash": "0xabc123def456..."
})

print(f"Status: {result['status']}")  # pending | confirmed | failed
```

**Output:**
```json
{
  "tx_hash": "0xabc123...",
  "status": "confirmed",
  "amount_usd": 10.0,
  "confirmed_at": 1700000000
}
```

---

#### 12. `agentpay_list_payments` - Payment History

**Description:** List payment history for merchant wallet (requires API key).

**Input Schema:**
```json
{
  "api_key": "string (required)",
  "limit": "number (optional, default 50, max 200)",
  "start_time": "number (optional, Unix timestamp)",
  "end_time": "number (optional, Unix timestamp)"
}
```

**Example:**
```python
result = call_mcp_tool("agentpay_list_payments", {
    "api_key": api_key,
    "limit": 10
}, api_key=api_key)

print(f"Total payments: {result['total_count']}")
for payment in result['payments']:
    print(f"  ${payment['amount_usd']} - {payment['resource_id']} - {payment['status']}")
```

**Output:**
```json
{
  "payments": [
    {
      "charge_id": "charge_abc123",
      "amount_usd": 10.0,
      "resource_id": "research-paper-2025",
      "payer": "0x742d35...",
      "status": "completed",
      "paid_at": 1700000000
    }
  ],
  "total_count": 42,
  "limit": 10
}
```

---

### Category 5: Analytics & Reporting (2 tools)

#### 13. `agentpay_get_audit_logs` - Retrieve Audit Logs

**Description:** Get audit logs for your account (requires API key).

**Input Schema:**
```json
{
  "api_key": "string (required)",
  "event_type": "string (optional, filter by type)",
  "limit": "number (optional, default 50, max 200)",
  "start_time": "number (optional, Unix timestamp)",
  "end_time": "number (optional, Unix timestamp)"
}
```

**Example:**
```python
result = call_mcp_tool("agentpay_get_audit_logs", {
    "api_key": api_key,
    "event_type": "payment_completed",
    "limit": 20
}, api_key=api_key)

print(f"Total logs: {result['total_count']}")
for log in result['logs']:
    print(f"[{log['timestamp']}] {log['event_type']}: {log['description']}")
```

**Output:**
```json
{
  "logs": [
    {
      "id": "log_abc123",
      "timestamp": 1700000000,
      "event_type": "payment_completed",
      "client_id": "agent@example.com",
      "description": "Payment verified for $10.00",
      "metadata": {
        "charge_id": "charge_abc123",
        "amount_usd": 10.0
      }
    }
  ],
  "total_count": 156,
  "limit": 20
}
```

---

#### 14. `agentpay_get_analytics` - Get Analytics

**Description:** Retrieve spending (agents) or revenue (merchants) analytics.

**Input Schema:**
```json
{
  "api_key": "string (required)",
  "start_time": "number (optional, Unix timestamp)",
  "end_time": "number (optional, Unix timestamp)"
}
```

**Example:**
```python
# Agent spending analytics
result = call_mcp_tool("agentpay_get_analytics", {
    "api_key": api_key
}, api_key=api_key)

print(f"Total spent: ${result['total_spent_usd']}")
print(f"Transactions: {result['transaction_count']}")
print(f"Active mandates: {result['active_mandates']}")
```

**Output (Agent):**
```json
{
  "user_type": "agent",
  "total_spent_usd": 245.50,
  "transaction_count": 32,
  "active_mandates": 3,
  "budget_remaining": 154.50,
  "top_merchants": [
    {"address": "0x123...", "amount": 120.00}
  ]
}
```

**Output (Merchant):**
```json
{
  "user_type": "merchant",
  "total_revenue_usd": 1250.00,
  "net_revenue_usd": 1243.75,
  "commission_paid_usd": 6.25,
  "transaction_count": 125,
  "unique_payers": 23
}
```

---

### Category 6: System Health (1 tool)

#### 15. `agentpay_get_system_health` - System Status

**Description:** Check AgentGatePay system health (public, no auth required).

**Input Schema:** (none)

**Example:**
```python
result = call_mcp_tool("agentpay_get_system_health", {})

if result['status'] == 'ok':
    print(f"✅ System healthy")
    print(f"Uptime: {result['uptime_hours']}h")
    print(f"Supported chains: {', '.join(result['chains'])}")
else:
    print(f"⚠️ System degraded: {result['message']}")
```

**Output:**
```json
{
  "status": "ok",
  "timestamp": 1700000000,
  "chains": ["base", "ethereum", "polygon", "arbitrum"],
  "tokens": ["USDC", "USDT", "DAI"],
  "uptime_hours": 720,
  "version": "1.1.5"
}
```

---

## Complete Workflows

### Workflow 1: Buyer Agent Payment Flow

**Scenario:** Autonomous agent discovers resource, issues mandate, pays, and claims access.

```python
import requests
import json
from web3 import Web3
from eth_account import Account

MCP_ENDPOINT = "https://api.agentgatepay.com/mcp/tools/call"

def call_mcp_tool(tool_name: str, arguments: dict, api_key: str = None):
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
        "id": 1
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key

    response = requests.post(MCP_ENDPOINT, json=payload, headers=headers, timeout=30)
    return json.loads(response.json()['result']['content'][0]['text'])

# Step 1: Create account (first time only)
signup_result = call_mcp_tool("agentpay_signup", {
    "email": "buyer_agent@example.com",
    "password": "SecurePass123!",
    "user_type": "agent"
})
api_key = signup_result['api_key']
print(f"✅ Account created: {signup_result['user']['user_id']}")

# Step 2: Add wallet
wallet_result = call_mcp_tool("agentpay_add_wallet", {
    "api_key": api_key,
    "wallet_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
}, api_key=api_key)
print(f"✅ Wallet added: {wallet_result['wallet_address']}")

# Step 3: Issue mandate ($100 budget for 7 days)
mandate_result = call_mcp_tool("agentpay_issue_mandate", {
    "api_key": api_key,
    "subject": "buyer-agent-12345",
    "budget_usd": 100.0,
    "scope": "resource.read,payment.execute",
    "ttl_hours": 168
}, api_key=api_key)
mandate_token = mandate_result['mandate_token']
print(f"✅ Mandate issued: {mandate_result['mandate_id']}")
print(f"   Budget: ${mandate_result['budget_usd']}")

# Step 4: Discover resource from seller
seller_url = "http://localhost:8000"
catalog_response = requests.get(f"{seller_url}/catalog")
catalog = catalog_response.json()['catalog']
resource = catalog[0]  # First resource
print(f"✅ Discovered resource: {resource['id']} (${resource['price_usd']})")

# Step 5: Request resource (expect 402)
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

# Step 6: Sign blockchain transaction
web3 = Web3(Web3.HTTPProvider("https://mainnet.base.org"))
account = Account.from_key(BUYER_PRIVATE_KEY)

USDC_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
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

signed_tx = web3.eth.account.sign_transaction(tx, BUYER_PRIVATE_KEY)
tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
print(f"✅ Blockchain TX sent: {receipt.transactionHash.hex()}")

# Step 7: Submit payment to AgentGatePay
payment_result = call_mcp_tool("agentpay_submit_payment", {
    "api_key": api_key,
    "mandate_token": mandate_token,
    "amount_usd": payment_info['amount_usd'],
    "receiver_address": payment_info['receiver_address'],
    "resource_id": resource['id'],
    "tx_hash": receipt.transactionHash.hex(),
    "chain": "base"
}, api_key=api_key)
print(f"✅ Payment verified: {payment_result['charge_id']}")
print(f"   Budget remaining: ${payment_result['budget_remaining']}")

# Step 8: Claim resource with payment proof
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

# Step 9: Check audit logs
audit_result = call_mcp_tool("agentpay_get_audit_logs", {
    "api_key": api_key,
    "limit": 5
}, api_key=api_key)
print(f"✅ Audit logs: {audit_result['total_count']} events")
for log in audit_result['logs'][:3]:
    print(f"   [{log['event_type']}] {log['description']}")

# Step 10: Check spending analytics
analytics_result = call_mcp_tool("agentpay_get_analytics", {
    "api_key": api_key
}, api_key=api_key)
print(f"✅ Analytics:")
print(f"   Total spent: ${analytics_result['total_spent_usd']}")
print(f"   Transactions: {analytics_result['transaction_count']}")
print(f"   Budget remaining: ${analytics_result['budget_remaining']}")
```

**Expected Output:**
```
✅ Account created: user_abc123
✅ Wallet added: 0x742d35...
✅ Mandate issued: mandate_xyz789
   Budget: $100.0
✅ Discovered resource: research-paper-2025 ($10.0)
✅ 402 Payment Required: $10.0
✅ Blockchain TX sent: 0xabc123...
✅ Payment verified: charge_def456
   Budget remaining: $90.0
✅ Resource claimed: 1024 bytes
✅ Audit logs: 8 events
   [payment_completed] Payment verified for $10.00
   [mandate_issued] Mandate issued with $100.00 budget
   [user_signup] User registered successfully
✅ Analytics:
   Total spent: $10.0
   Transactions: 1
   Budget remaining: $90.0
```

---

### Workflow 2: Merchant Revenue Tracking

**Scenario:** Merchant monitors incoming payments and revenue analytics.

```python
# Step 1: Create merchant account
signup_result = call_mcp_tool("agentpay_signup", {
    "email": "merchant@example.com",
    "password": "SecurePass123!",
    "user_type": "merchant"
})
api_key = signup_result['api_key']
print(f"✅ Merchant account: {signup_result['user']['user_id']}")

# Step 2: Add receiving wallet
wallet_result = call_mcp_tool("agentpay_add_wallet", {
    "api_key": api_key,
    "wallet_address": "0x123abc456def..."
}, api_key=api_key)
print(f"✅ Receiving wallet: {wallet_result['wallet_address']}")

# Step 3: List payment history
payments_result = call_mcp_tool("agentpay_list_payments", {
    "api_key": api_key,
    "limit": 50
}, api_key=api_key)

print(f"✅ Payment history: {payments_result['total_count']} payments")
for payment in payments_result['payments'][:5]:
    print(f"   ${payment['amount_usd']} from {payment['payer'][:10]}... - {payment['status']}")

# Step 4: Get revenue analytics
analytics_result = call_mcp_tool("agentpay_get_analytics", {
    "api_key": api_key
}, api_key=api_key)

print(f"✅ Revenue Analytics:")
print(f"   Total revenue: ${analytics_result['total_revenue_usd']}")
print(f"   Net revenue: ${analytics_result['net_revenue_usd']}")
print(f"   Commission paid: ${analytics_result['commission_paid_usd']}")
print(f"   Transactions: {analytics_result['transaction_count']}")
print(f"   Unique payers: {analytics_result['unique_payers']}")

# Step 5: Check audit logs for payment events
audit_result = call_mcp_tool("agentpay_get_audit_logs", {
    "api_key": api_key,
    "event_type": "payment_completed",
    "limit": 10
}, api_key=api_key)

print(f"✅ Payment audit logs: {audit_result['total_count']} completed payments")
```

---

## Authentication

### API Key Header

All MCP tools that require authentication accept API key via header:

```python
headers = {
    "Content-Type": "application/json",
    "x-api-key": "pk_live_abc123..."
}

response = requests.post(MCP_ENDPOINT, json=payload, headers=headers)
```

### Rate Limits

- **Without API Key**: 20 requests/minute
- **With API Key**: 100 requests/minute (5x higher)

**Rate Limit Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1700000060
```

### Public Tools (No Auth Required)

These tools work without API key:
- `agentpay_signup` - Account creation
- `agentpay_verify_payment` - Payment verification
- `agentpay_get_payment_status` - Quick status check
- `agentpay_get_system_health` - System health

All other tools require valid API key.

---

## Error Handling

### MCP Tool Response Format

⚠️ **CRITICAL:** All MCP tools return `{"success": true/false, ...}`. Always check `success` before proceeding.

```python
result = call_mcp_tool("agentpay_submit_payment", {...})

# ✅ ALWAYS CHECK SUCCESS
if not result.get('success', False):
    error = result.get('error', 'Unknown error')
    print(f"❌ Payment failed: {error}")
    return  # Stop workflow

print(f"✅ Payment succeeded")
# Continue with successful result
```

**Common Gateway Errors:**
- `"Nonce already used (replay attack blocked)"` - Transaction already submitted
- `"Invalid mandate token"` - Mandate expired or not found
- `"Insufficient budget"` - Not enough budget remaining
- `"Payment verification failed"` - Transaction not found on blockchain

### JSON-RPC Error Format

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32600,
    "message": "Invalid request",
    "data": {
      "details": "Missing required field: email"
    }
  },
  "id": 1
}
```

### Common Error Codes

| Code | Meaning | Solution |
|------|---------|----------|
| `-32700` | Parse error | Check JSON syntax |
| `-32600` | Invalid request | Verify payload structure |
| `-32601` | Method not found | Check tool name spelling |
| `-32602` | Invalid params | Validate input schema |
| `-32603` | Internal error | Retry or contact support |

### HTTP Status Codes

| Status | Meaning | Common Cause |
|--------|---------|--------------|
| `200` | Success | Request completed |
| `400` | Bad request | Invalid JSON or missing fields |
| `401` | Unauthorized | Invalid or missing API key |
| `404` | Not found | Wrong endpoint URL |
| `429` | Rate limited | Too many requests (wait 60s) |
| `500` | Server error | Internal issue (retry) |

### Python Error Handling

```python
import requests
import json
import time

def call_mcp_tool_with_retry(tool_name: str, arguments: dict, api_key: str = None, max_retries: int = 3):
    """Call MCP tool with automatic retry on rate limit"""

    for attempt in range(max_retries):
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
                "id": 1
            }

            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["x-api-key"] = api_key

            response = requests.post(MCP_ENDPOINT, json=payload, headers=headers, timeout=30)

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                print(f"⚠️ Rate limited, waiting {retry_after}s...")
                time.sleep(retry_after)
                continue

            response.raise_for_status()
            result = response.json()

            # Check for JSON-RPC error
            if "error" in result:
                raise Exception(f"MCP Error [{result['error']['code']}]: {result['error']['message']}")

            # Parse result
            content_text = result['result']['content'][0]['text']
            return json.loads(content_text)

        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                print(f"⚠️ Timeout, retrying ({attempt + 1}/{max_retries})...")
                time.sleep(2)
                continue
            raise

        except requests.exceptions.RequestException as e:
            print(f"❌ HTTP Error: {e}")
            raise

        except json.JSONDecodeError as e:
            print(f"❌ JSON Parse Error: {e}")
            raise

    raise Exception(f"Failed after {max_retries} attempts")
```

---

## Best Practices

### 1. Cache API Keys Securely

```python
import os
from dotenv import load_dotenv

load_dotenv()  # Load from .env file
API_KEY = os.getenv('AGENTPAY_API_KEY')

# NEVER hardcode API keys
# ❌ BAD: api_key = "pk_live_abc123..."
# ✅ GOOD: api_key = os.getenv('AGENTPAY_API_KEY')
```

### 2. Validate Inputs Before Calling

```python
def validate_email(email: str) -> bool:
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_wallet_address(address: str) -> bool:
    from web3 import Web3
    return Web3.is_address(address)

# Validate before calling
if not validate_email(email):
    raise ValueError("Invalid email format")

result = call_mcp_tool("agentpay_signup", {"email": email, ...})
```

### 3. Handle Rate Limits Gracefully

```python
import time

def call_with_backoff(tool_name, arguments, api_key=None):
    backoff = 1
    max_backoff = 60

    while True:
        try:
            return call_mcp_tool(tool_name, arguments, api_key)
        except Exception as e:
            if "rate limit" in str(e).lower():
                print(f"Rate limited, waiting {backoff}s...")
                time.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)
            else:
                raise
```

### 4. Log MCP Calls for Debugging

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def call_mcp_tool_logged(tool_name: str, arguments: dict, api_key: str = None):
    logger.info(f"MCP Call: {tool_name} with {len(arguments)} arguments")

    try:
        result = call_mcp_tool(tool_name, arguments, api_key)
        logger.info(f"MCP Success: {tool_name}")
        return result
    except Exception as e:
        logger.error(f"MCP Error: {tool_name} - {e}")
        raise
```

### 5. Use Connection Pooling for Performance

```python
import requests

session = requests.Session()
session.headers.update({"Content-Type": "application/json"})

def call_mcp_tool_session(tool_name: str, arguments: dict, api_key: str = None):
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
        "id": 1
    }

    headers = {}
    if api_key:
        headers["x-api-key"] = api_key

    response = session.post(MCP_ENDPOINT, json=payload, headers=headers, timeout=30)
    return json.loads(response.json()['result']['content'][0]['text'])
```

### 6. Verify Mandates Before Payments

```python
def safe_payment(mandate_token, amount_usd, receiver_address, tx_hash, api_key):
    # Step 1: Verify mandate is valid
    verification = call_mcp_tool("agentpay_verify_mandate", {
        "mandate_token": mandate_token
    })

    if not verification['valid']:
        raise Exception(f"Mandate invalid: {verification.get('error')}")

    if verification['budget_remaining'] < amount_usd:
        raise Exception(f"Insufficient budget: ${verification['budget_remaining']} < ${amount_usd}")

    # Step 2: Submit payment
    return call_mcp_tool("agentpay_submit_payment", {
        "api_key": api_key,
        "mandate_token": mandate_token,
        "amount_usd": amount_usd,
        "receiver_address": receiver_address,
        "tx_hash": tx_hash,
        "chain": "base"
    }, api_key=api_key)
```

---

## Troubleshooting

### Issue: "Method not found" error

**Symptom:**
```json
{"error": {"code": -32601, "message": "Method not found: tools/cal"}}
```

**Solution:**
Check tool name for typos. Use `tools/list` to see all available tools:
```python
payload = {
    "jsonrpc": "2.0",
    "method": "tools/list",
    "params": {},
    "id": 1
}
response = requests.post("https://api.agentgatepay.com/mcp/tools/list", json=payload)
tools = response.json()['result']['tools']
print([tool['name'] for tool in tools])
```

---

### Issue: "Invalid params" error

**Symptom:**
```json
{"error": {"code": -32602, "message": "Invalid params: Missing required field 'email'"}}
```

**Solution:**
Validate all required fields match the schema. Use JSON Schema validation:
```python
import jsonschema

# Example: Validate signup arguments
signup_schema = {
    "type": "object",
    "properties": {
        "email": {"type": "string"},
        "password": {"type": "string", "minLength": 8},
        "user_type": {"type": "string", "enum": ["agent", "merchant", "both"]}
    },
    "required": ["email", "password", "user_type"]
}

arguments = {"email": "test@example.com", "password": "short"}
try:
    jsonschema.validate(arguments, signup_schema)
except jsonschema.ValidationError as e:
    print(f"Validation error: {e.message}")
```

---

### Issue: Rate limit exceeded

**Symptom:**
```
HTTP 429: Rate limit exceeded (20 requests/minute)
```

**Solution:**
1. Create an account to get 5x higher rate limit (100/min)
2. Add exponential backoff retry logic
3. Check `Retry-After` header

```python
if response.status_code == 429:
    retry_after = int(response.headers.get('Retry-After', 60))
    print(f"Rate limited, waiting {retry_after}s...")
    time.sleep(retry_after)
```

---

### Issue: JSON parse error on result

**Symptom:**
```python
json.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

**Solution:**
MCP returns stringified JSON in `result.content[0].text`. Always parse twice:
```python
# ❌ WRONG
result = response.json()['result']

# ✅ CORRECT
result = response.json()
content_text = result['result']['content'][0]['text']
parsed_result = json.loads(content_text)
```

---

### Issue: Payment verification fails

**Symptom:**
```json
{"verified": false, "reason": "Transaction not found on blockchain"}
```

**Solution:**
1. Wait 10-15 seconds for Base network confirmation
2. Verify correct chain parameter (`chain: "base"`)
3. Check transaction on BaseScan: `https://basescan.org/tx/{tx_hash}`

```python
import time

# Send blockchain transaction
tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

# Wait for confirmation
time.sleep(15)  # Base network needs 10-15 seconds

# Then verify
result = call_mcp_tool("agentpay_verify_payment", {
    "tx_hash": tx_hash.hex(),
    "chain": "base"
})
```

---

### Issue: Mandate budget tracking incorrect

**Symptom:**
Budget remaining doesn't match expected value after payments.

**Solution:**
Budget is updated AFTER successful payment verification:
```python
# Before payment
verification = call_mcp_tool("agentpay_verify_mandate", {"mandate_token": mandate_token})
print(f"Before: ${verification['budget_remaining']}")

# After payment
payment = call_mcp_tool("agentpay_submit_payment", {...})
print(f"After: ${payment['budget_remaining']}")  # Updated here

# Verify budget was deducted
assert payment['budget_remaining'] == verification['budget_remaining'] - payment['amount_usd']
```

---

## See Also

- **[QUICK_START.md](QUICK_START.md)** - 5-minute setup guide
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common errors & solutions
- **[API_INTEGRATION.md](API_INTEGRATION.md)** - REST API with SDK guide
- **[README.md](../README.md)** - Examples overview

---

**Need Help?**
- Email: support@agentgatepay.com
- GitHub: https://github.com/AgentGatePay/agentgatepay-examples/issues
- Docs: https://docs.agentgatepay.com

**MCP Resources:**
- MCP Specification: https://modelcontextprotocol.io
- Claude Desktop Integration: See `mcp-server/` directory
- OpenAI Agent Builder: Use unified endpoint `POST /mcp`
