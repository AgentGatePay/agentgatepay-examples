# AgentGatePay + LangChain Integration

**Autonomous AI agent payments using blockchain and LangChain framework**

**Version:** 1.0 BETA
**Last Updated:** November 2025
**Python:** 3.12+
**LangChain:** 1.0.0+

> **⚠️ BETA VERSION**: These examples are currently in beta. We're actively adding features and improvements based on user feedback. Expect updates for enhanced functionality, additional framework integrations, improved error handling, and expanded multi-chain support.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![AgentGatePay SDK](https://img.shields.io/badge/agentgatepay--sdk-1.1.6+-green.svg)](https://pypi.org/project/agentgatepay-sdk/)
[![LangChain](https://img.shields.io/badge/langchain-1.0.0+-orange.svg)](https://www.langchain.com/)

## Overview

This repository contains **10 complete examples** demonstrating how to integrate AgentGatePay with LangChain for autonomous agent payments:

- **Examples 1a/1b:** REST API (1a: local signing, 1b: external TX service)
- **Examples 2a/2b:** REST API marketplace (buyer/seller split)
- **Examples 3a/3b:** MCP tools (3a: local signing, 3b: external TX service)
- **Examples 4a/4b:** MCP marketplace (buyer/seller split, with webhooks)
- **Examples 5a/5b:** Monitoring dashboards (buyer spending, seller revenue)

**Logical Grouping:**
- **1a/1b**: REST API payments (local vs external signing)
- **2a/2b**: REST API marketplace (buyer vs seller)
- **3a/3b**: MCP payments (local vs external signing)
- **4a/4b**: MCP marketplace (buyer vs seller)
- **5a/5b**: Monitoring (buyer vs seller dashboards)

**Integration Approaches:**
- **REST API version** - Uses published AgentGatePay SDK (v1.1.6+) from PyPI
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

**Examples 1a, 2a/2b, 3a, 4a/4b, 5a/5b: Local Signing**

Sign transactions using your private key from `.env` file:

```bash
# In your .env file:
BUYER_PRIVATE_KEY=0xYOUR_PRIVATE_KEY_HERE
BUYER_WALLET=0xYOUR_WALLET_ADDRESS_HERE

# Run example:
python examples/1a_api_basic_payment.py
```

**Note:** Examples use **$0.01 USDC** for testing. Private key in `.env` is suitable for development and testing with small amounts only.

---

**Examples 1b, 3b: External Signing Service (Production)**

Deploy a separate signing service to isolate private keys from application code.

**Note:** Docker and Render are shown as examples, but you can deploy the signing service using any method you prefer (AWS ECS, GCP Cloud Run, Azure Container Instances, Railway, your own VPS, etc.). The example script works with any HTTP endpoint.

**Option A: Docker (Local)**

```bash
docker pull agentgatepay/tx-signing-service:latest
docker run -d -p 3000:3000 --env-file .env.signing-service agentgatepay/tx-signing-service:latest
```

Add to `.env`: `TX_SIGNING_SERVICE=http://localhost:3000`

See [DOCKER_LOCAL_SETUP.md](docs/DOCKER_LOCAL_SETUP.md) for detailed setup.

**Option B: Render (Cloud)**

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/AgentGatePay/TX)

When prompted, enter:
- **WALLET_PRIVATE_KEY**: Your wallet private key
- **AGENTGATEPAY_API_KEY**: Your API key

Add to `.env`: `TX_SIGNING_SERVICE=https://your-service.onrender.com`

See [RENDER_DEPLOYMENT_GUIDE.md](docs/RENDER_DEPLOYMENT_GUIDE.md) for detailed setup.

**Other deployment options:** See [TX_SIGNING_OPTIONS.md](docs/TX_SIGNING_OPTIONS.md) for additional methods (cloud providers, self-hosted, custom infrastructure).

### Run Examples

```bash
# Example 1a: REST API + Local signing (basic)
python examples/1a_api_basic_payment.py

# Example 1b: REST API + External TX signing (production)
python examples/1b_api_with_tx_service.py

# Example 2: Buyer/seller marketplace (REST API) - TWO SCRIPTS
# Terminal 1: Start seller first
python examples/2b_api_seller_agent.py

# Terminal 2: Then run buyer
python examples/2a_api_buyer_agent.py

# Example 3a: MCP + Local signing (basic)
python examples/3a_mcp_basic_payment.py

# Example 3b: MCP + External TX signing (production)
python examples/3b_mcp_with_tx_service.py

# Example 4: Buyer/seller marketplace (MCP tools) - TWO SCRIPTS
# Terminal 1: Start seller first
python examples/4b_mcp_seller_agent.py

# Terminal 2: Then run buyer
python examples/4a_mcp_buyer_agent.py

# Example 5a: Buyer monitoring dashboard (SPENDING & BUDGETS)
python examples/5a_monitoring_buyer.py

# Example 5b: Seller monitoring dashboard (REVENUE & WEBHOOKS)
python examples/5b_monitoring_seller.py
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
python examples/1a_api_basic_payment.py
```

## Examples Overview

### Example 1a: Basic Payment Flow (REST API + Local Signing)

**File:** `examples/1a_api_basic_payment.py`

Simple autonomous payment flow demonstrating the complete 3-step process:
1. **Issue Mandate**: Create AP2 mandate with $100 budget and budget tracking
2. **Sign Transactions**: Sign two blockchain transactions (merchant + commission)
3. **Submit to Gateway**: Submit payment proof to AgentGatePay for verification

**Uses:**
- AgentGatePay SDK (agentgatepay-sdk>=1.1.6) from PyPI
- Web3.py for blockchain signing
- LangChain agent framework

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

### Example 3a: Basic Payment Flow (MCP + Local Signing)

**File:** `examples/3a_mcp_basic_payment.py`

MCP version of Example 1a, demonstrating the same payment flow using AgentGatePay's MCP tools instead of REST API.

**Flow:**
1. Issue mandate via `agentpay_issue_mandate` tool
2. Sign blockchain transactions (Web3.py - merchant + commission)
3. Submit payment and verify budget via `agentpay_submit_payment` + `agentpay_verify_mandate` (combined)

**MCP Advantages:**
- Native tool discovery (frameworks auto-list all 15 tools)
- Standardized JSON-RPC 2.0 protocol
- Future-proof (Anthropic-backed)
- Cleaner tool abstraction

**Key Features:**
- Matches Script 1a exact flow (3 steps)
- Combined submit+verify for efficiency
- Audit log curl commands for verification
- Same output format as REST API version

**Output:**
```
✅ Mandate issued via MCP
💳 Payment executed: $0.01 to 0x742d35...
✅ Payment submitted via MCP
   ✅ Budget updated: $99.99

📋 Gateway Audit Logs (copy-paste these commands):
# All payment logs:
curl 'https://api.agentgatepay.com/audit/logs?...' | python3 -m json.tool
```

---

### Example 4: Buyer/Seller Marketplace (MCP Tools) ⭐ **SEPARATE SCRIPTS**

**Files:**
- `examples/4a_mcp_buyer_agent.py` - Autonomous buyer agent (MCP)
- `examples/4b_mcp_seller_agent.py` - Resource seller API (MCP)

**Complete marketplace interaction** using MCP tools (matches Example 2 pattern):

**BUYER AGENT** (`4a_mcp_buyer_agent.py`):
- **Autonomous** resource discovery from ANY seller
- Issues mandate via MCP (`agentpay_issue_mandate`)
- Signs blockchain payment (2 TX: merchant + commission)
- Submits payment via MCP (`agentpay_submit_payment`)
- Claims resource after payment
- Can discover from multiple sellers

**SELLER AGENT** (`4b_mcp_seller_agent.py`):
- **Independent** Flask API service
- Provides resource catalog
- Returns 402 Payment Required
- **Verifies payment via MCP** (`agentpay_verify_payment`) instead of REST API SDK
- Delivers resource (200 OK)
- Serves ANY buyer agent

**Flow:**
```
[SELLER] Start Flask API (localhost:8000) → [SELLER] Wait for buyers
   ↓
[BUYER] Issue mandate via MCP → [BUYER] Discover catalog → [SELLER] Return catalog
   ↓
[BUYER] Request resource → [SELLER] 402 Payment Required
   ↓
[BUYER] Sign blockchain TX (2 transactions: merchant + commission)
   ↓
[BUYER] Submit payment to gateway via MCP → [GATEWAY] Verify on-chain
   ↓
[BUYER] Claim resource with proof → [SELLER] Verify via MCP → [SELLER] Deliver (200 OK)
```

**Why Separate Scripts:**
- ✅ **Realistic** - Buyer and seller are separate entities
- ✅ **Flexible** - Buyer can buy from multiple sellers
- ✅ **Scalable** - Seller can serve multiple buyers
- ✅ **MCP Focus** - Shows MCP tools in production marketplace pattern

**MCP Tools Used:**
- **Buyer:** `agentpay_issue_mandate`, `agentpay_submit_payment`
- **Seller:** `agentpay_verify_payment` (instead of REST API SDK)

**Features:**
- HTTP 402 Payment Required protocol
- Two-transaction commission model
- Real Flask API for seller (production-ready)
- Adaptive retry logic for payment verification
- Comprehensive error handling
- Audit log commands at end
- **Production webhooks** for automatic resource delivery (optional)

---

### Example 1b: REST API + External TX Signing (Production)

**File:** `examples/1b_api_with_tx_service.py`

Same payment flow as Example 1a, but using external transaction signing service to isolate private keys from application code (production-ready).

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
- Private key stored in signing service, not in application code
- Application cannot access private keys
- Signing service can be audited independently
- Scalable deployment (Docker local or Render cloud)

**Setup Options:**

**Docker (Local):**
```bash
docker pull agentgatepay/tx-signing-service:latest
docker run -d -p 3000:3000 --env-file .env.signing-service agentgatepay/tx-signing-service:latest
```
Add to `.env`: `TX_SIGNING_SERVICE=http://localhost:3000`

See [DOCKER_LOCAL_SETUP.md](docs/DOCKER_LOCAL_SETUP.md) for detailed setup.

**Render (Cloud):**

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/AgentGatePay/TX)

Add to `.env`: `TX_SIGNING_SERVICE=https://your-service.onrender.com`

See [RENDER_DEPLOYMENT_GUIDE.md](docs/RENDER_DEPLOYMENT_GUIDE.md) for detailed setup.

**Run:**
```bash
python examples/1b_api_with_tx_service.py
```

**Output:**
```
Signing service is healthy
Wallet configured: true

Issuing mandate with $100 budget...
Mandate issued successfully

Requesting payment signature from external service...
Payment signed and submitted by external service
   Merchant TX: 0xabc123...
   Commission TX: 0xdef456...

Verifying payment: 0xabc123...
Payment verified successfully

PRODUCTION SUCCESS:
   Private key: SECURE (stored in signing service)
   Application code: CLEAN (no private keys)
   Payment: VERIFIED (on Base blockchain)
```

**Why This Matters:**
- Separates payment logic from key management
- Keys can be rotated without code changes
- Service can be scaled independently
- Suitable for production deployments

**See:** [TX_SIGNING_OPTIONS.md](docs/TX_SIGNING_OPTIONS.md) for additional deployment options (AWS, GCP, Azure, custom HSM).

---

### Example 3b: MCP + External TX Signing (Production)

**File:** `examples/3b_mcp_with_tx_service.py`

Same payment flow as Example 3a, but using external transaction signing service for production security.

Combines the best of both worlds:
- **MCP tools** for mandate management and payment submission (JSON-RPC 2.0 protocol)
- **External TX signing** for production security (no private key in code)

**Flow:**
1. Issue mandate via MCP (`agentpay_issue_mandate` tool)
2. Request signature from external TX service (Docker/Render/Railway)
3. Service signs both transactions (merchant + commission)
4. Submit payment proof via MCP (`agentpay_submit_payment` tool)
5. Verify budget via MCP (`agentpay_verify_mandate` tool)

**Why This Combination:**
- ✅ **MCP Protocol**: Standardized agent communication (Anthropic-backed)
- ✅ **Production Security**: Private keys isolated in signing service
- ✅ **Scalable**: Both MCP and TX service can scale independently
- ✅ **Future-proof**: MCP standard + secure key management
- ✅ **Best Practices**: Combines industry standards from both protocols

**Setup:**

Same as Example 1b - setup external TX signing service:

**Docker (Local):**
```bash
docker pull agentgatepay/tx-signing-service:latest
docker run -d -p 3000:3000 --env-file .env.signing-service agentgatepay/tx-signing-service:latest
```

**Render (Cloud):**

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/AgentGatePay/TX)

Add to `.env`: `TX_SIGNING_SERVICE=http://localhost:3000` (or your Render URL)

**Run:**
```bash
python examples/3b_mcp_with_tx_service.py
```

**Output:**
```
AGENTGATEPAY + LANGCHAIN: PRODUCTION MCP + TX SIGNING DEMO
==============================================================================

✅ SECURE: Private key stored in signing service, NOT in application
✅ SCALABLE: Signing service can be deployed independently
✅ MCP PROTOCOL: Standardized agent communication
✅ PRODUCTION READY: Suitable for real-world deployments

Signing service is healthy
Wallet configured: true

   📡 Calling MCP tool: agentpay_issue_mandate
🔐 Creating mandate ($100)...
✅ Mandate created (Budget: $100.0)

💳 Requesting payment signature from external service...
✅ Payment signed and submitted by external service
   Merchant TX: 0xad2fe7...
   Commission TX: 0x29292d...
   Status: Success

   📡 Calling MCP tool: agentpay_submit_payment
✅ Payment submitted via MCP
   Status: Confirmed

   📡 Calling MCP tool: agentpay_verify_mandate
   ✅ Budget updated: $99.99

✅ PRODUCTION SUCCESS:
   Private key: SECURE (stored in signing service)
   Application code: CLEAN (no private keys)
   MCP protocol: STANDARDIZED (JSON-RPC 2.0)
   Payment: VERIFIED (on Base blockchain)
```

**Use Cases:**
- Production agent deployments requiring secure key management
- Multi-agent systems needing standardized communication (MCP)
- Scalable payment infrastructures with independent services
- Agent frameworks with native MCP support

**Comparison to Other Examples:**
- **vs Example 1a/3a**: Adds production security (external TX signing)
- **vs Example 1b**: Uses MCP protocol instead of REST API
- **Best of both**: MCP standardization + production security

---

### Examples 5a/5b: Buyer & Seller Monitoring Dashboards

**Files:**
- `examples/5a_monitoring_buyer.py` - Buyer monitoring (spending, budgets, mandates)
- `examples/5b_monitoring_seller.py` - Seller monitoring (revenue, webhooks, top buyers)

Standalone monitoring tools for tracking AgentGatePay payments - similar to n8n monitoring workflows but as Python CLI tools. Split into **buyer** and **seller** dashboards to match real-world usage patterns.

**Why Separate Dashboards:**
- ✅ **Buyer Focus** - Track spending, budget utilization, mandate expiration
- ✅ **Seller Focus** - Track revenue, webhook delivery, top buyers
- ✅ **Realistic** - Buyers and sellers have different monitoring needs
- ✅ **Matches n8n** - Same pattern as n8n buyer/seller monitoring workflows

---

#### Example 5a: Buyer Monitoring Dashboard

**File:** `examples/5a_monitoring_buyer.py`

Monitor your SPENDING as a buyer (outgoing payments):

**Buyer-Specific Features:**
- **Spending analytics**: Total spent, payment count, average payment, 24h activity
- **Budget tracking**: Mandate budgets, utilization percentage, remaining budget
- **Smart alerts**: Budget warnings (critical/high/medium), mandate expiration, failed payments
- **Outgoing payments**: Track what you paid to merchants
- **Live CURL commands**: Generated commands with actual results

**Usage:**
```bash
# Standalone mode (prompts for credentials)
python examples/5a_monitoring_buyer.py

# With arguments
python examples/5a_monitoring_buyer.py --api-key pk_live_... --wallet 0xABC...
```

**Output:**
```
BUYER MONITORING DASHBOARD (Outgoing Payments)
==============================================================
Generated: 2025-11-28T12:00:00
Buyer Wallet: 0x9752717...A3b844Bc

SPENDING SUMMARY
Total Spent: $47.50 USD
Payment Count: 12 (outgoing payments)
Average Payment: $3.96 USD
Last 24h: 5 payments ($18.75 USD)
Spending Trend: increasing

BUDGET STATUS
Total Allocated: $100.00 USD
Remaining: $52.50 USD
Utilization: 47.5%
Active Mandates: 2

BUYER ALERTS (3)
1. [HIGH] BUDGET WARNING: Only $52.50 remaining (47.5% used)
   Action: Issue new mandate or reduce spending

OUTGOING PAYMENTS (Last 10)
(Payments YOU sent to merchants)
1. YOU PAID $5.00 → Merchant 0x742d35Cc... | confirmed | TX 0xabc123...

ACTIVE MANDATES (2)
(Budget allocations for your payments)
1. mandate_abc123... | Budget: $100.00 | Remaining: $52.50 | active
```

---

#### Example 5b: Seller Monitoring Dashboard

**File:** `examples/5b_monitoring_seller.py`

Monitor your REVENUE as a seller (incoming payments):

**Seller-Specific Features:**
- **Revenue analytics**: Total revenue, payment count, average payment, monthly trends
- **Webhook tracking**: Webhook delivery status and success rates
- **Top buyers**: Identify your best customers
- **Incoming payments**: Track what buyers paid you
- **Payment success rate**: Monitor payment failures and issues

**Usage:**
```bash
# Standalone mode (prompts for credentials)
python examples/5b_monitoring_seller.py

# With arguments
python examples/5b_monitoring_seller.py --api-key pk_live_... --wallet 0xDEF...
```

**Output:**
```
SELLER MONITORING DASHBOARD (Incoming Payments)
==============================================================
Generated: 2025-11-28T12:00:00
Seller Wallet: 0x742d35Cc...A1B2C3D4

REVENUE SUMMARY
Total Revenue: $247.50 USD
Payment Count: 23 (incoming payments)
Average Payment: $10.76 USD
This Month: $89.25 USD
Last 24h: 8 payments ($42.30 USD)

WEBHOOK STATUS
Total Webhooks: 2
Active Webhooks: 2

  1. https://seller.com/webhook... | ✅ Active
  2. https://backup.com/webhook... | ✅ Active

PAYMENT METRICS
Success Rate: 95.7%
Failed Payments: 1
Total Events (24h): 45

INCOMING PAYMENTS (Last 10)
(Payments buyers sent to YOU)
1. YOU RECEIVED $15.00 ← Buyer 0x9752717... | confirmed | TX 0xdef456...

TOP BUYERS (5)
(Buyers who paid you the most)
1. 0x9752717... | $87.50 | 8 payments
2. 0xABC1234... | $65.00 | 6 payments
```

**Why This Matters:**
- **Buyer Dashboard**: Track your spending and budget utilization
- **Seller Dashboard**: Track your revenue and webhook delivery
- Equivalent to n8n buyer/seller monitoring workflows
- No n8n required - just Python + pip install
- Can be run anytime to check payment/revenue status
- Live CURL commands for API integration and debugging

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
PAYMENT_CHAIN=polygon python examples/1a_api_basic_payment.py
```

---

## Next Steps

1. **Try all examples** - Understand both API and MCP approaches, plus external signing and monitoring
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

---

## License

MIT License - See LICENSE file for details

---

## Contributing

Contributions welcome! Please see [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

---

**Built with ❤️ by the AgentGatePay team**

*Last updated: November 2025*
