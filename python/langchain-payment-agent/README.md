# AgentGatePay + LangChain Integration

**Autonomous AI agent payments using blockchain and LangChain framework**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![AgentGatePay SDK](https://img.shields.io/badge/agentgatepay--sdk-1.1.4+-green.svg)](https://pypi.org/project/agentgatepay-sdk/)
[![LangChain](https://img.shields.io/badge/langchain-1.0.0+-orange.svg)](https://www.langchain.com/)

## Overview

This repository contains **9 complete examples** demonstrating how to integrate AgentGatePay with LangChain for autonomous agent payments:

- **Examples 1-2:** REST API basics (payment, buyer/seller marketplace)
- **Examples 3-5:** MCP tools basics (same features as 1-2 using MCP)
- **Example 6:** REST API complete (ALL 11 AgentGatePay features with optimizations)
- **Example 7:** MCP complete (ALL 15 MCP tools - 100% coverage)
- **Example 8:** External TX service (production-ready signing)
- **Example 9:** Standalone Monitoring Dashboard (analytics & audit logs)

**Integration Approaches:**
- **REST API version** - Uses published AgentGatePay SDK (v1.1.3+) from PyPI
- **MCP version** - Uses AgentGatePay's 15 MCP tools (Model Context Protocol)

**Multi-Chain/Token Support** - All examples support **4 chains** (Base, Ethereum, Polygon, Arbitrum) and **3 tokens** (USDC, USDT, DAI) with interactive selection on first run.

## What You'll Learn

- ✅ How to create autonomous agents that make blockchain payments
- ✅ Buyer/seller marketplace interactions (like n8n workflows)
- ✅ Mandate budget management and verification
- ✅ Two-transaction commission model (merchant + gateway)
- ✅ Comparison of REST API vs MCP tools approaches
- ✅ Complete audit logging and analytics (via monitoring dashboard)

## Features

### AgentGatePay Capabilities

- **Multi-chain payments**: Ethereum, Base, Polygon, Arbitrum
- **Multi-token support**: USDC, USDT, DAI
- **AP2 mandate system**: Budget-controlled payment authorization
- **Two-transaction model**: Merchant payment + gateway commission (0.5%)
- **Comprehensive audit logs**: Track all payment events
- **MCP integration**: 15 tools with 100% REST API parity

### LangChain Integration

- **Agent framework**: ReAct agents with payment tools
- **Tool abstraction**: Clean separation of payment logic
- **Error handling**: Automatic retry and graceful degradation
- **State management**: Mandate and payment tracking

## Quick Start

### Prerequisites

1. **Python 3.12+**
2. **AgentGatePay accounts** (2 accounts for buyer/seller demos)

   **Create accounts via API:**
   ```bash
   # Create buyer/agent account
   curl -X POST https://api.agentgatepay.com/v1/users/signup \
     -H "Content-Type: application/json" \
     -d '{"email": "buyer@example.com", "password": "YourPass123!", "user_type": "agent"}'

   # Create seller/merchant account
   curl -X POST https://api.agentgatepay.com/v1/users/signup \
     -H "Content-Type: application/json" \
     -d '{"email": "seller@example.com", "password": "YourPass123!", "user_type": "merchant"}'
   ```

   **Save the API keys** from the response (shown only once): `pk_live_...`

3. **Wallet setup**

   **Supported Networks:** Ethereum, Base, Polygon, Arbitrum
   **Supported Tokens:** USDC, USDT, DAI

   **Recommended:** Base network with USDC (lowest gas fees ~$0.001, fastest ~2-5 sec)

   You need:
   - Buyer wallet with stablecoins (any supported token on any supported chain)
   - Seller wallet address (for receiving payments)
   - Private key for buyer wallet (for signing transactions)
   - Small amount of native token for gas (ETH/MATIC - ~$0.01 worth)

4. **LLM API key** (for LangChain agent intelligence)

   Examples use **OpenAI** by default, but any LangChain-supported LLM works (Anthropic Claude, Google Gemini, local models, etc.). Configure your preferred LLM provider's API key in `.env` as `OPENAI_API_KEY` (or rename variable and update model initialization in scripts for other providers).

### Installation

```bash
# Clone repository
git clone https://github.com/AgentGatePay/agentgatepay-examples.git
cd agentgatepay-examples/python/langchain-payment-agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

**IMPORTANT:** Replace placeholder values with your actual credentials:
- `BUYER_PRIVATE_KEY=0xYOUR_PRIVATE_KEY` → Your actual 64-character private key
- `BUYER_WALLET` → Your wallet address
- `OPENAI_API_KEY` → Your OpenAI API key

Required variables:
```bash
# AgentGatePay API Configuration
AGENTPAY_API_URL=https://api.agentgatepay.com
MCP_API_URL=https://mcp.agentgatepay.com
BUYER_API_KEY=pk_live_YOUR_BUYER_KEY
BUYER_EMAIL=your-buyer-email@example.com
SELLER_API_KEY=pk_live_YOUR_SELLER_KEY
SELLER_EMAIL=your-seller-email@example.com

# Multi-Chain Payment Configuration
PAYMENT_CHAIN=base          # Options: base, ethereum, polygon, arbitrum
PAYMENT_TOKEN=USDC          # Options: USDC, USDT, DAI

# Blockchain RPC Endpoints (free RPCs work, premium RPCs are faster)
# See docs/RPC_CONFIGURATION.md for Alchemy/Infura setup (10-20x faster for Ethereum)
BASE_RPC_URL=https://mainnet.base.org
ETHEREUM_RPC_URL=https://eth-mainnet.public.blastapi.io
POLYGON_RPC_URL=https://polygon-rpc.com
ARBITRUM_RPC_URL=https://arb1.arbitrum.io/rpc

# Wallet Configuration
BUYER_PRIVATE_KEY=0xYOUR_PRIVATE_KEY
BUYER_WALLET=0xYOUR_BUYER_WALLET
SELLER_WALLET=0xYOUR_SELLER_WALLET

# LLM API Key (OpenAI example - swap for other providers)
OPENAI_API_KEY=sk-YOUR_OPENAI_KEY

# Optional: External TX Signing Service (recommended for production)
TX_SIGNING_SERVICE=https://your-service.onrender.com
```

### Transaction Signing

**Examples 1-8: Local Signing**

These examples sign transactions using your private key from `.env` file:

```bash
# In your .env file:
BUYER_PRIVATE_KEY=0xYOUR_PRIVATE_KEY_HERE
BUYER_WALLET=0xYOUR_WALLET_ADDRESS_HERE

# Run example:
python examples/1_api_basic_payment.py
```

**Test Amounts:** Examples use **$0.01 USDC** for testing (safe small amount).

**Note:** Private key in `.env` is for testing only. Do not use with large amounts or on mainnet with significant funds.

---

**Example 9: External Signing Service**

This example uses a separate signing service:

1. Deploy signing service (choose one):
   - Docker: `docker run -p 3000:3000 agentgatepay/tx-signing-service`
   - Render: [One-click deploy](https://render.com/deploy?repo=https://github.com/AgentGatePay/TX)

2. Add service URL to `.env`:
   ```bash
   TX_SIGNING_SERVICE=https://your-service.onrender.com
   ```

3. Run example:
   ```bash
   python examples/9_api_with_tx_service.py
   ```

---

**Other Options**

For production deployments with wallet services, HSM, or custom implementations, see [TX_SIGNING_OPTIONS.md](docs/TX_SIGNING_OPTIONS.md).

### Run Examples

```bash
# Example 1: Basic payment (REST API)
python examples/1_api_basic_payment.py

# Example 2: Buyer/seller marketplace (REST API) - TWO SCRIPTS
# Terminal 1: Start seller first
python examples/2b_api_seller_agent.py

# Terminal 2: Then run buyer
python examples/2a_api_buyer_agent.py

# Example 3: Basic payment (MCP tools)
python examples/3_mcp_basic_payment.py

# Example 4: Buyer/seller marketplace (MCP tools)
python examples/4_mcp_buyer_seller.py

# Example 5: Audit logging (MCP tools)
python examples/5_mcp_with_audit.py

# Example 6: Complete features demo (REST API) - ALL 11 FEATURES + OPTIMIZATIONS
python examples/6_api_complete_features.py

# Example 7: Complete features demo (MCP tools) - ALL 15 MCP TOOLS
python examples/7_mcp_complete_features.py

# Example 8: Production TX signing (external service) - PRODUCTION READY 🚀
python examples/8_api_with_tx_service.py

# Example 9: Monitoring dashboard (STANDALONE TOOL) - ANALYTICS & AUDIT LOGS
python examples/9_monitoring_dashboard.py

# Run with exports
python examples/9_monitoring_dashboard.py --export-csv --export-json
```

### Multi-Chain/Token Configuration

All examples support **4 chains** and **3 tokens**. Simply edit your `.env` file:

```bash
# In .env file:
PAYMENT_CHAIN=base          # Options: base, ethereum, polygon, arbitrum
PAYMENT_TOKEN=USDC          # Options: USDC, USDT, DAI
```

**Chain/Token Compatibility Matrix:**

| Chain | USDC | USDT | DAI | Gas Cost | Payment Speed* |
|-------|------|------|-----|----------|----------------|
| Base (recommended) | ✅ | ❌ | ✅ | Very Low | Quick |
| Ethereum | ✅ | ✅ | ✅ | High | Variable** |
| Polygon | ✅ | ✅ | ✅ | Low | Quick |
| Arbitrum | ✅ | ✅ | ✅ | Low | Quick |

\* Payment speed includes gateway verification. **Optimistic mode** for USDT ETH <$1 provides faster settlement.
\*\* Ethereum speed depends on RPC provider quality. Premium RPCs (Alchemy/Infura) provide significantly faster verification. See [RPC_CONFIGURATION.md](docs/RPC_CONFIGURATION.md) for optimization guide.

**Important Notes:**
- USDT is NOT available on Base
- DAI uses 18 decimals (USDC/USDT use 6 decimals)
- Base recommended for lowest fees and fastest transactions

**To switch chains:** Just edit `.env` and restart the script:
```bash
# Change from Base to Ethereum with USDT
nano .env  # Edit PAYMENT_CHAIN=ethereum and PAYMENT_TOKEN=USDT
python examples/1_api_basic_payment.py
```

## Examples Overview

### Example 1: Basic Payment Flow (REST API)

**File:** `examples/1_api_basic_payment.py`

Simple autonomous payment flow demonstrating the complete 3-step process:
1. **Issue Mandate**: Create AP2 mandate with $100 budget and budget tracking
2. **Sign Transactions**: Sign two blockchain transactions (merchant + commission)
3. **Submit to Gateway**: Submit payment proof to AgentGatePay for verification

**Uses:**
- AgentGatePay SDK (agentgatepay-sdk>=1.1.3) from PyPI
- Web3.py for blockchain signing
- LangChain 1.x agent with LangGraph backend

**Key Features:**
- Dynamic commission fetching from API
- Live budget tracking via mandate verification
- Complete end-to-end payment flow
- Base network for fast, low-cost transactions

**Output:**
```
✅ Initialized AgentGatePay client
✅ Buyer wallet: 0x9752717...

🔐 Creating mandate ($100)...
✅ Mandate created (Budget: $100.0)

💳 Signing payment ($0.01)...
   ✅ TX 1/2 confirmed (block 23485610)
   ✅ TX 2/2 confirmed (block 23485611)

📤 Submitting to gateway...
✅ Payment recorded
   ✅ Budget updated: $99.99

✅ PAYMENT WORKFLOW COMPLETED
   Budget remaining: $99.99
```

---

### Example 2: Buyer/Seller Marketplace (REST API) ⭐ **SEPARATE SCRIPTS**

**Files:**
- `examples/2a_api_buyer_agent.py` - Autonomous buyer agent
- `examples/2b_api_seller_agent.py` - Resource seller API

**Complete marketplace interaction** (matches n8n workflow pattern):

**BUYER AGENT** (`2a_api_buyer_agent.py`):
- **Autonomous** resource discovery from ANY seller
- Issues mandate with budget control
- Signs blockchain payment (2 TX: merchant + commission)
- Claims resource after payment
- Can discover from multiple sellers

**SELLER AGENT** (`2b_api_seller_agent.py`):
- **Independent** Flask API service
- Provides resource catalog
- Returns 402 Payment Required
- Verifies payment via AgentGatePay API
- **Production webhooks** for automatic delivery (optional)
- Delivers resource (200 OK)
- Serves ANY buyer agent

**Flow:**
```
[SELLER] Start Flask API (localhost:8000) → [SELLER] Wait for buyers
   ↓
[BUYER] Issue mandate → [BUYER] Discover catalog → [SELLER] Return catalog
   ↓
[BUYER] Request resource → [SELLER] 402 Payment Required
   ↓
[BUYER] Sign blockchain TX (2 transactions: merchant + commission)
   ↓
[BUYER] Submit payment to AgentGatePay gateway → [GATEWAY] Verify on-chain
   ↓
[BUYER] Claim resource with payment proof → [SELLER] Verify via AgentGatePay API
   ↓
[SELLER] Deliver resource (200 OK) → [BUYER] Access granted
   ↓
[BOTH] View audit logs
```

**Why Separate Scripts:**
- ✅ **Realistic** - Buyer and seller are separate entities
- ✅ **Flexible** - Buyer can buy from multiple sellers
- ✅ **Scalable** - Seller can serve multiple buyers
- ✅ **Production-ready** - Matches real-world architecture

**Features:**
- HTTP 402 Payment Required protocol
- Two-transaction commission model
- Real Flask API for seller (production-ready)
- **Webhook support** for automatic resource delivery (production deployments)
- Comprehensive error handling
- Multi-seller support

**Webhooks (Optional - Production Only):**

For production deployments, the seller can configure webhooks to receive automatic payment notifications:

```bash
# During seller startup, when prompted:
Configure webhooks now? (y/n, default: n): y
Enter public webhook URL: https://your-seller.com/webhooks/payment
```

**Benefits:**
- ✅ Automatic resource delivery when payments confirm
- ✅ No buyer waiting for seller verification
- ✅ Scales better for high-volume sellers
- ✅ Industry-standard async pattern

**For local testing:** Press 'n' to skip webhooks - manual verification works perfectly on localhost.

---

### Example 3: Basic Payment Flow (MCP Tools)

**File:** `examples/3_mcp_basic_payment.py`

MCP version of Example 1, demonstrating the same payment flow using AgentGatePay's MCP tools instead of REST API.

**Flow:**
1. Issue mandate via `agentpay_issue_mandate` tool
2. Sign blockchain transactions (Web3.py - merchant + commission)
3. Submit payment proof via `agentpay_submit_payment` tool
4. Gateway verifies on-chain and updates budget automatically

**MCP Advantages:**
- Native tool discovery (frameworks auto-list all 15 tools)
- Standardized JSON-RPC 2.0 protocol
- Future-proof (Anthropic-backed)
- Cleaner tool abstraction

**Output:**
```
✅ Mandate issued via MCP
💳 Payment sent: $10 to 0x742d35...
✅ Payment verified via MCP
📊 MCP Tools Used: 3
```

---

### Example 4: Buyer/Seller Marketplace (MCP Tools)

**File:** `examples/4_mcp_buyer_seller.py`

MCP version of Example 2, demonstrating marketplace interactions using MCP tools for all AgentGatePay operations.

**Features:**
- Mandate issuance via MCP (`agentpay_issue_mandate`)
- Payment submission via MCP (`agentpay_submit_payment`)
- Payment verification via MCP (`agentpay_verify_payment`)
- Simulated catalog discovery and resource delivery
- Two-transaction commission model (blockchain)

**Flow:**
1. Issue mandate (MCP)
2. Discover catalog (simulated)
3. Request resource (simulated 402)
4. Sign blockchain payment (Web3.py)
5. Submit payment proof (MCP)
6. Verify payment (MCP)
7. Claim resource (simulated)

**Why Simulated Seller:**
- Focus is on demonstrating MCP tool integration
- Real seller API shown in Example 2b (REST API version)
- Production sellers would use same MCP tools for verification

**MCP Tools Used:**
- `agentpay_issue_mandate` - Issue payment mandate
- `agentpay_submit_payment` - Submit payment proof
- `agentpay_verify_payment` - Verify payment status

---

### Example 5: Payment with Audit Logs (MCP Tools)

**File:** `examples/5_mcp_with_audit.py`

Demonstrates comprehensive audit logging using MCP tools for payment tracking and analytics.

**Features:**
- Mandate issuance via MCP
- Multiple payments with blockchain signing
- Payment submission via MCP
- Audit log retrieval via MCP (`agentpay_list_audit_logs`)
- Spending pattern analysis via MCP
- Budget monitoring via MCP (`agentpay_verify_mandate`)

**Analytics:**
```
📊 Spending Analysis (via MCP):
   Total payments: 5
   Total spent: $47.50
   Average payment: $9.50
   Budget utilization: 47.5%
```

**MCP Tools Used:**
- `agentpay_issue_mandate` - Issue mandate
- `agentpay_submit_payment` - Submit payments
- `agentpay_verify_mandate` - Check budget
- `agentpay_list_audit_logs` - Retrieve logs

**Demonstrates:**
- Complete audit trail via MCP
- Payment tracking across multiple transactions
- Budget utilization monitoring
- Spending pattern analysis

---

### Example 6: Complete Features Demo (REST API)

**File:** `examples/6_api_complete_features.py`

Comprehensive demonstration of all 11 AgentGatePay features matching n8n workflow capabilities with production optimizations.

**Features Demonstrated:**
1. User Authentication & Signup
2. Wallet Management
3. API Key Management (create, list, revoke)
4. Mandate Management (issue, verify, budget tracking)
5. Payment Execution (2-TX model with nonce optimization)
6. Payment History Retrieval
7. Merchant Revenue Analytics
8. Comprehensive Audit Logging
9. Webhook Configuration & Testing
10. System Health Monitoring
11. Monitoring Dashboard (analytics with smart alerts)

**Key Capabilities:**
- **Multi-chain support**: Interactive chain selection (Base/Ethereum/Polygon/Arbitrum)
- **Multi-token support**: USDC, USDT, or DAI selection
- **Nonce optimization**: Single nonce fetch for parallel TX submission
- **Monitoring dashboard**: Real-time analytics with alert system

**Why This Example Matters:**
- Shows complete platform capabilities
- Matches n8n buyer + seller + monitoring workflows combined
- Production-ready feature coverage with optimizations
- Demonstrates full agent economy ecosystem

**Output:**
```
Features Demonstrated: 11/11
   User authentication & signup
   Wallet management
   API key management
   Mandates (AP2)
   Payments (2-TX model with nonce optimization)
   Payment history
   Revenue analytics
   Audit logging
   Webhooks
   System health
   Monitoring dashboard (analytics + alerts)
ALL 11 AGENTGATEPAY FEATURES DEMONSTRATED
```

---

### Example 7: Complete Features Demo (MCP Tools) ⭐ **ALL 15 MCP TOOLS**

**File:** `examples/7_mcp_complete_features.py`

**Comprehensive demonstration of ALL 15 AgentGatePay MCP tools** - 100% coverage.

**MCP Tools Demonstrated:**
1. ✅ `agentpay_signup` - User signup
2. ✅ `agentpay_get_user_info` - Get user info
3. ✅ `agentpay_add_wallet` - Add wallet
4. ✅ `agentpay_create_api_key` - Create API key
5. ✅ `agentpay_list_api_keys` - List API keys
6. ✅ `agentpay_revoke_api_key` - Revoke API key
7. ✅ `agentpay_issue_mandate` - Issue mandate
8. ✅ `agentpay_verify_mandate` - Verify mandate
9. ✅ `agentpay_create_payment` - Create payment
10. ✅ `agentpay_submit_payment` - Submit payment
11. ✅ `agentpay_verify_payment` - Verify payment
12. ✅ `agentpay_get_payment_history` - Payment history
13. ✅ `agentpay_get_analytics` - Analytics
14. ✅ `agentpay_list_audit_logs` - Audit logs
15. ✅ `agentpay_get_system_health` - System health

**Why This Example Matters:**
- 100% MCP tool coverage (15/15)
- Proves MCP = REST API feature parity
- Shows standardized JSON-RPC 2.0 protocol
- Matches complete n8n workflow feature set
- Future-proof integration approach

**Output:**
```
📊 MCP TOOLS USED: 15/15
   1. agentpay_signup
   2. agentpay_get_user_info
   ... (all 15 tools listed)
   15. agentpay_get_system_health

🎉 ALL 15 MCP TOOLS DEMONSTRATED!
   100% feature parity with REST API
   Matches n8n workflow capabilities
```

---

### Example 8: Production TX Signing (External Service) ⭐ **PRODUCTION READY**

**File:** `examples/8_api_with_tx_service.py`

**PRODUCTION-READY payment flow using external transaction signing service:**
- ✅ NO private key in application code
- ✅ Signing handled by external service (Render/Docker/Railway)
- ✅ Secure private key storage
- ✅ Scalable architecture

**Flow:**
1. Issue mandate via SDK
2. Request signature from external TX service
3. Service signs both transactions (merchant + commission)
4. Submit payment proof to AgentGatePay
5. Verify payment completion

**External Service Call:**
```python
response = requests.post(
    f"{TX_SIGNING_SERVICE}/sign-payment",
    headers={"x-api-key": BUYER_API_KEY},
    json={
        "merchant_address": recipient,
        "amount_usd": str(amount_usd),
        "chain": "base",
        "token": "USDC"
    },
    timeout=120
)
# Returns: {tx_hash, tx_hash_commission, status}
```

**Security Benefits:**
- ✅ Private key stored in signing service, NOT in code
- ✅ Application cannot access private keys
- ✅ Signing service can be audited independently
- ✅ Scalable deployment (Render/Docker/Railway/self-hosted)

**Setup:**
1. Deploy TX signing service ([Render one-click](https://render.com/deploy?repo=https://github.com/AgentGatePay/TX) or Docker)
2. Add `TX_SIGNING_SERVICE=https://your-service.onrender.com` to `.env`
3. Run `python examples/8_api_with_tx_service.py`

**Output:**
```
🏥 Signing service is healthy
✅ Wallet configured: true

🔐 Issuing mandate with $100 budget...
✅ Mandate issued successfully

💳 Requesting payment signature from external service...
✅ Payment signed and submitted by external service
   Merchant TX: 0xabc123...
   Commission TX: 0xdef456...

🔍 Verifying payment: 0xabc123...
✅ Payment verified successfully

✅ PRODUCTION SUCCESS:
   Private key: SECURE (stored in signing service)
   Application code: CLEAN (no private keys)
   Payment: VERIFIED (on Base blockchain)
```

**Why This Matters:**
- Separates payment logic from key management
- Allows secure production deployments
- Keys can be rotated without code changes
- Service can be scaled independently

**See:** [TX_SIGNING_OPTIONS.md](docs/TX_SIGNING_OPTIONS.md) for complete deployment guide

---

### Example 9: Monitoring Dashboard

**File:** `examples/9_monitoring_dashboard.py`

Standalone monitoring tool for tracking AgentGatePay payments - similar to n8n monitoring workflows but as a Python CLI tool.

**Features:**
- **Multi-chain/token support**: Ethereum, Base, Polygon, Arbitrum with USDC/USDT/DAI
- **Spending analytics**: Total spent, payment count, average payment, 24h activity
- **Budget tracking**: Mandate budgets, utilization percentage, remaining budget
- **Smart alerts**: Budget warnings (critical/high/medium), mandate expiration, failed payments, spending anomalies
- **Payment history**: Last 100 payments with merchant vs commission breakdown
- **CSV/JSON exports**: Export reports for offline analysis
- **curl commands**: Ready-to-use API exploration commands

**Usage:**
```bash
# Standalone mode (prompts for credentials)
python examples/9_monitoring_dashboard.py

# With arguments
python examples/9_monitoring_dashboard.py --api-key pk_live_... --wallet 0xABC...

# Export reports
python examples/9_monitoring_dashboard.py --export-csv --export-json

# Disable alerts
python examples/9_monitoring_dashboard.py --no-alerts
```

**Interactive Chain/Token Selection:**
On first run, you'll be prompted to select:
1. **Chain**: Base (recommended), Ethereum, Polygon, or Arbitrum
2. **Token**: USDC (recommended), USDT, or DAI

Your choice is saved to `~/.agentgatepay_config.json` and reused in future runs.

**Output:**
```
AGENTGATEPAY MONITORING DASHBOARD
==============================================================
Generated: 2025-11-28T12:00:00
Chain: BASE (ID: 8453)
Token: USDC (6 decimals)
Wallet: 0x9752717...A3b844Bc

SPENDING SUMMARY
Total Spent: $47.50 USD
Payment Count: 12
Average Payment: $3.96 USD
Last 24h: 5 payments ($18.75 USD)
Spending Trend: increasing

BUDGET STATUS
Total Allocated: $100.00 USD
Remaining: $52.50 USD
Utilization: 47.5%
Active Mandates: 2

ALERTS (3)
Critical: 0 | High: 1 | Medium: 2 | Low: 0

1. [HIGH] BUDGET WARNING: Only $52.50 remaining (47.5% used)
   Action: Issue new mandate or reduce spending

2. [MEDIUM] High Spending: $18.75 spent in 24h (10x average)
   Action: Verify spending is intentional

3. [MEDIUM] Budget Notice: $52.50 remaining (47.5% used)
   Action: Monitor spending

RECENT PAYMENTS (Last 10)
1. $5.00 to 0x742d35Cc... | confirmed | 0xabc123def456...
2. $3.50 to 0x742d35Cc... | confirmed | 0xdef456abc123...

EXPLORE YOUR DATA (CURL COMMANDS)
# Last 24 hours of activity
curl 'https://api.agentgatepay.com/audit/logs?client_id=0x...&hours=24' \
  -H 'x-api-key: pk_live_...'

EXPORT OPTIONS
Run with --export-csv or --export-json to export reports
```

**Why This Matters:**
- Equivalent to n8n monitoring workflow but as standalone Python tool
- No n8n required - just Python + pip install
- Can be run anytime to check payment status
- Useful for debugging, auditing, and budget tracking
- CSV/JSON exports for integration with other tools

**See:** [CHAIN_TOKEN_GUIDE.md](CHAIN_TOKEN_GUIDE.md) for multi-chain configuration details

---

## Architecture

### Payment Flow (Buyer/Seller Pattern)

```
┌─────────────────────────────────────────────────────────────┐
│ BUYER AGENT (LangChain)                                     │
│  - Issue mandate ($100 budget, 7 days TTL)                  │
│  - Discover resource from seller                            │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ SELLER AGENT (Flask API)                                    │
│  - Return 402 Payment Required                              │
│  - Include: price, wallet, chain, token                     │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ BLOCKCHAIN (Base Network)                                   │
│  TX1: Merchant payment ($9.95 USDC → seller)                │
│  TX2: Commission ($0.05 USDC → AgentGatePay)               │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ AGENTGATEPAY API                                            │
│  - Verify payment on-chain                                  │
│  - Record in audit logs                                     │
│  - Update mandate budget                                    │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ SELLER AGENT                                                 │
│  - Verify payment via API                                   │
│  - Deliver resource (200 OK)                                │
└─────────────────────────────────────────────────────────────┘
```

### Component Coverage

All examples demonstrate:

| Component | Used | Description |
|-----------|------|-------------|
| **Mandates** | ✅ | AP2 protocol budget management |
| **Payments** | ✅ | Multi-chain blockchain transactions |
| **Audit Logs** | ✅ | Comprehensive event tracking |
| **Commission Model** | ✅ | Two-transaction (merchant + gateway) |
| **Rate Limiting** | ✅ | 100 req/min with API key |
| **Analytics** | ✅ | Spending patterns and budget tracking |
| **MCP Tools** | ✅ | 15 tools with native framework integration |

---

## REST API vs MCP Comparison

### When to Use REST API

✅ **Advantages:**
- Universal compatibility (all frameworks)
- Published SDK with types (pip install agentgatepay-sdk)
- Custom error handling
- Web3 helpers built-in
- Simpler for developers familiar with REST

❌ **Disadvantages:**
- More boilerplate code
- Manual tool definition
- Less future-proof

### When to Use MCP Tools

✅ **Advantages:**
- Native tool discovery (frameworks auto-list tools)
- Standardized JSON-RPC protocol
- Future-proof (Anthropic backing)
- Unique competitive advantage
- Cleaner separation of concerns

❌ **Disadvantages:**
- Newer protocol (less familiar)
- Framework support still growing
- Requires MCP endpoint setup

### Code Comparison

**REST API version:**
```python
from agentgatepay_sdk import AgentGatePay

agentpay = AgentGatePay(api_url="...", api_key="...")
mandate = agentpay.mandates.issue("subject", 100)
```

**MCP version:**
```python
def call_mcp_tool(tool_name, arguments):
    response = requests.post(MCP_ENDPOINT, json={
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments}
    })
    return response.json()

mandate = call_mcp_tool("agentpay_issue_mandate", {"subject": "...", "budget_usd": 100})
```

**Result:** Same functionality, different approaches. Choose based on your stack and preferences.

---

## Documentation

### Core Guides
- **[CHAIN_TOKEN_GUIDE.md](CHAIN_TOKEN_GUIDE.md)** - 🆕 Multi-chain/token configuration guide
- **[API_INTEGRATION.md](docs/API_INTEGRATION.md)** - Complete REST API guide
- **[MCP_INTEGRATION.md](docs/MCP_INTEGRATION.md)** - Complete MCP tools guide
- **[API_VS_MCP.md](docs/API_VS_MCP.md)** - Detailed comparison
- **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** - Common issues and solutions

---

## Troubleshooting

### Common Issues

**Error: "Mandate not found or expired"**
- Solution: Mandate TTL is 7 days. Issue a new mandate.

**Error: "Payment verification failed"**
- Solution: Wait 10-15 seconds for Base network confirmation, then retry.
- Check wallet has sufficient USDC balance.

**Error: "Insufficient gas for transaction"**
- Solution: Ensure buyer wallet has ETH for gas (~$0.001-0.01 per TX on Base).

**Error: "OpenAI API key not found"**
- Solution: Set `OPENAI_API_KEY` in .env file.

**See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for more.**

---

## Testing

```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_api_integration.py

# Test with different chains
PAYMENT_CHAIN=polygon python examples/1_api_basic_payment.py
```

---

## Next Steps

1. **Try all 6 examples** - Understand both API and MCP approaches
2. **Modify examples** - Adapt to your use case
3. **Read comparison docs** - Choose API vs MCP for your stack
4. **Build your agent** - Create custom payment workflows

---

## Resources

- **AgentGatePay API**: https://api.agentgatepay.com
- **SDK Documentation**: https://github.com/AgentGatePay/agentgatepay-sdks
- **LangChain Docs**: https://python.langchain.com/
- **Base Network**: https://base.org
- **MCP Specification**: https://modelcontextprotocol.io

---

## Support

- **Email**: support@agentgatepay.com
- **GitHub Issues**: https://github.com/AgentGatePay/agentgatepay-sdks/issues
- **Discord**: https://discord.gg/agentgatepay (coming soon)

---

## License

MIT License - See LICENSE file for details

---

## Contributing

Contributions welcome! Please see [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

---

**Built with ❤️ by the AgentGatePay team**

*Last updated: November 2025*
