# AgentGatePay N8N Templates

**Version:** 1.0 BETA
**Last Updated:** November 2025
**Compatibility:** N8N v1.0+

> **⚠️ BETA VERSION**: These templates are currently in beta. We're actively adding features and improvements based on user feedback. Expect updates for enhanced functionality, additional blockchain networks, new payment tokens, improved analytics, and faster transaction processing.

## Overview

This package contains 4 production-ready N8N workflow templates for autonomous AI agent payments using AgentGatePay. These templates enable agents to buy and sell resources with automatic **multi-chain, multi-token** blockchain payments.

**Supported Payment Options:**
- **Tokens**: USDC (6 decimals), USDT (6 decimals), DAI (18 decimals)
- **Blockchains**: Ethereum, Base (recommended), Polygon, Arbitrum
- **Gas Fees**: As low as $0.001 per transaction on Base

---

## Documentation

This package includes comprehensive documentation to get you started:

### Quick Start (Recommended for New Users)
**[QUICK_START.md](QUICK_START.md)** - 2-page fast-track guide
- 10-minute setup walkthrough
- Prerequisites checklist
- First payment execution
- Essential troubleshooting

### Comprehensive Setup Guide (This File)
**README.md** - Complete reference guide (you are here)
- Detailed template descriptions
- Step-by-step configuration
- Architecture overview
- Advanced configuration options
- Security best practices
- Performance optimization

### Technical Reference
**[N8N_IMPLEMENTATION_GUIDE.md](N8N_IMPLEMENTATION_GUIDE.md)** - Deep technical documentation
- Complete node-by-node breakdown (buyer: 22 nodes, seller: 12 nodes)
- MCP protocol integration details
- AP2 mandate system deep dive
- AIF security layer explanation
- Blockchain verification internals
- All 15 MCP endpoints reference

**Choose your path:**
- **Fast track:** Start with QUICK_START.md (10 minutes)
- **Comprehensive:** Follow this README.md (30 minutes)
- **Deep dive:** Read N8N_IMPLEMENTATION_GUIDE.md (technical reference)

---

## Templates Included

### 1. Buyer Agent - CLIENT TEMPLATE
**File:** `🤖 Buyer Agent - CLIENT TEMPLATE.json`
**Use Case:** AI agent that autonomously purchases resources from sellers
**Features:**
- **Multi-chain, multi-token payments** (USDC/USDT/DAI on Ethereum/Base/Polygon/Arbitrum)
- Automatic mandate issuance and verification
- Dynamic resource discovery and purchase
- Blockchain transaction signing via Render/Railway service
- Budget tracking and low-balance alerts
- Error handling and retry logic

**When to Use:** Your agent needs to buy data, services, or API access from sellers

---

### 2. Seller Resource API - CLIENT TEMPLATE
**File:** `💲Seller Resource API - CLIENT TEMPLATE.json`
**Use Case:** Webhook API that sells resources to buyer agents
**Features:**
- **Accepts USDC, USDT, or DAI on 4 blockchains**
- HTTP 402 Payment Required enforcement
- Payment verification via AgentGatePay API
- Resource catalog with dynamic pricing
- Secure resource delivery after payment confirmation
- Two-transaction commission model (merchant + gateway)

**When to Use:** You want to monetize your data or services for agent buyers

---

### 3. Buyer Monitoring - MANUAL RUN
**File:** `📊 Buyer Monitoring - MANUAL RUN.json`
**Use Case:** Track spending and mandate budget for buyer agents
**Features:**
- Payment history by buyer wallet address
- Mandate budget tracking and visualization
- Spending analytics (total, average, count)
- Low-balance alerts
- Transaction status monitoring

**When to Use:** Monitor your agent's spending and budget usage

---

### 4. Seller Monitoring - MANUAL RUN
**File:** `💲 Seller Monitoring - MANUAL RUN.json`
**Use Case:** Track revenue and payments for sellers
**Features:**
- Payment history by seller wallet address
- Revenue analytics (total, commission, net)
- Top payers list
- Payment status tracking
- Commission breakdown

**When to Use:** Monitor revenue from agents buying your resources

---

## Prerequisites

Before importing these templates, you need:

1. **AgentGatePay Account (2 accounts for testing)**
   - Buyer account (user_type="agent")
   - Seller account (user_type="merchant")
   - Get API keys for both accounts

2. **Wallet Addresses**
   - Buyer wallet address (must have USDC, USDT, or DAI on selected blockchain)
   - Seller wallet address (receives payments)

3. **Transaction Signing Service**
   - Option 1: Use AgentGatePay SDK with local signing (ethers.js or web3.py)
   - Option 2: Deploy Render/Railway service from: https://github.com/AgentGatePay/TX
   - Option 3: Use Coinbase x402 API
   - Option 4: Implement custom signing solution

4. **N8N Environment**
   - N8N Cloud account (n8n.cloud) OR
   - Self-hosted N8N instance (v1.0+)

5. **Blockchain Setup (Flexible)**
   - **Tokens**: USDC, USDT, or DAI (choose one)
   - **Blockchain**: Base (recommended - lowest gas), Ethereum, Polygon, or Arbitrum
   - **RPC Endpoint**: Free via Alchemy, Infura, or public RPCs
   - **Recommendation**: Start with USDC on Base network (~$0.001 per transaction)

---

## Quick Start Guide

### Step 1: Create AgentGatePay Accounts

**Create Buyer Account:**
```bash
curl -X POST https://api.agentgatepay.com/v1/users/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "buyer@example.com",
    "password": "SecurePassword123!",
    "user_type": "agent"
  }'
```

**Create Seller Account:**
```bash
curl -X POST https://api.agentgatepay.com/v1/users/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "seller@example.com",
    "password": "SecurePassword123!",
    "user_type": "merchant"
  }'
```

Save the API keys returned in the response (shown only once).

---

### Step 3: Choose Transaction Signing Method

**Option 1: SDK with Local Signing (Simple, no external service)**

Use AgentGatePay SDK (JavaScript or Python) with ethers.js/web3.py for local transaction signing. This approach signs transactions directly in your N8N workflow using the SDK without requiring external services.

**Pros:**
- No external service deployment needed
- Direct control over signing process
- Works with existing infrastructure
- Full SDK feature access (mandates, payments, analytics)

**Cons:**
- Requires SDK installation in N8N environment
- Need to manage private key securely in N8N
- Slightly more code than managed service options

**Implementation:** Replace Render/Railway API calls in buyer workflow with SDK code. See N8N_IMPLEMENTATION_GUIDE.md for SDK integration examples.

---

**Option 2: Render/Railway Service (Managed, easy deployment)**

1. Fork repository: https://github.com/AgentGatePay/TX
2. Create new Web Service on Render.com or Railway.app
3. Connect your GitHub repository
4. Add environment variables
5. Deploy (takes ~2 minutes)
6. Save service URL: `https://your-app.onrender.com` or `https://your-app.railway.app`

**Pros:**
- Quick setup (2-minute deployment)
- Isolated private key management
- Free tier available
- Pre-configured N8N workflow templates provided

**Cons:**
- External dependency
- Cold start delays on free tier (~5 seconds)

**N8N Templates:** This method includes ready-to-use N8N workflow templates (included in this repository). If you need help or additional custom workflows, please contact us at support@agentgatepay.com

---

**Option 3: Coinbase x402 API (Managed, KYC required)**

1. Create Coinbase account and get API key
2. Use Coinbase x402 endpoint in templates
3. See documentation: https://docs.agentgatepay.com/transaction-signing

**Pros:**
- Managed by Coinbase
- Zero transaction fees
- No deployment needed

**Cons:**
- Requires KYC verification
- Regional restrictions may apply

---

### Step 4: Import Templates into N8N

**For N8N Cloud:**

1. Log in to your N8N account at https://app.n8n.cloud
2. Click "Workflows" in left sidebar
3. Click "Add Workflow" button (top right)
4. Click three dots menu → "Import from File"
5. Select template JSON file
6. Click "Import"
7. Repeat for all 4 templates

**For Self-Hosted N8N:**

1. Access your N8N instance
2. Navigate to Workflows section
3. Click "Add Workflow"
4. Use "Import from File" option
5. Select template JSON file
6. Confirm import

---

### Step 5: Configure Templates

#### Configure Buyer Agent Template

Open **"🤖 Buyer Agent - CLIENT TEMPLATE"** and edit **Node 1: "Set Buyer Configuration"**:

```javascript
const CONFIG = {
  buyer: {
    email: "buyer@example.com",              // Your buyer email
    api_key: "pk_live_abc123...",            // Your buyer API key
    budget_usd: 100,                          // Initial mandate budget
    mandate_ttl_days: 7                       // Mandate validity period
  },
  seller: {
    api_url: "https://YOUR_N8N.app.n8n.cloud/webhook/seller-resource-api-test"  // Your seller webhook URL
  },
  render: {
    service_url: "https://YOUR_APP.onrender.com"  // Your Render service URL
  }
};
```

**Important - Webhook URL Format:**

When you copy the webhook URL from N8N, it will show the FULL path including dynamic parameters:
```
https://your-instance.app.n8n.cloud/webhook/abc123def456/resource/:resourceId
```

**You must ONLY use the base URL** (remove `/resource/:resourceId` from the end):
```javascript
api_url: "https://your-instance.app.n8n.cloud/webhook/abc123def456"  // ✅ CORRECT - Base URL only
```

**Why?** The buyer workflow automatically appends `/resource/{resource_id}` when making requests. If you include it in the config, the URL will be doubled and requests will fail.

**Other replacements:**
- Replace `YOUR_N8N.app.n8n.cloud` with your actual N8N webhook domain
- Replace `YOUR_APP.onrender.com` with your Render/Railway service URL

---

#### Configure Seller API Template

Open **"💲Seller Resource API - CLIENT TEMPLATE"** and edit **Node 1: "Set Seller Configuration"**:

```javascript
const SELLER_CONFIG = {
  merchant: {
    wallet_address: "0xYourSellerWallet...",  // Your seller wallet
    api_key: "pk_live_xyz789..."              // Your seller API key
  },
  catalog: {
    "saas-competitors-2025": {
      id: "saas-competitors-2025",
      price_usd: 0.01,                        // Price in USD
      description: "SaaS competitor analysis for 2025"
    }
  }
};
```

**Get Webhook URL:**
1. Click the **Webhook** trigger node in your seller workflow
2. Copy the **"Production URL"** shown in the node settings
3. **IMPORTANT:** N8N shows the full URL with path parameters like:
   ```
   https://your-instance.app.n8n.cloud/webhook/abc123def456/resource/:resourceId
   ```
4. **Remove** the `/resource/:resourceId` part, use ONLY the base URL:
   ```
   https://your-instance.app.n8n.cloud/webhook/abc123def456
   ```
5. Paste this base URL into the buyer agent configuration (Node 1, `seller.api_url`)

---

#### Configure Monitoring Templates

**⚠️ NOTE:** Monitoring workflows do NOT require Data Tables (unlike the buyer agent).

**Buyer Monitoring Setup:**
1. Open **"📊 Buyer Monitoring - MANUAL RUN"**
2. Click **Node 2** "🔐 Set Credentials"
3. Edit the configuration node:
   ```javascript
   {
     "email": "buyer@example.com",        // Your buyer account email
     "api_key": "pk_live_abc123...",      // Your buyer API key
     "wallet_address": "0xYourBuyerWallet..."  // Your buyer wallet address
   }
   ```
4. Click **Save**

**Seller Monitoring Setup:**
1. Open **"💲 Seller Monitoring - MANUAL RUN"**
2. Click **Node 2** "🔐 Set Credentials"
3. Edit the configuration node:
   ```javascript
   {
     "wallet_address": "0xYourSellerWallet...",  // Your seller wallet address
     "api_key": "pk_live_xyz789..."              // Your seller API key
   }
   ```
4. Click **Save**

**What monitoring workflows do:**
- **Buyer Monitoring**: Shows spending history, mandate budget status, total spent, transaction count
- **Seller Monitoring**: Shows revenue analytics, incoming payments, top payers, commission breakdown

---

### Step 6: Enable and Test Workflows

#### Enable Seller API First

1. Open seller template
2. Click "Active" toggle (top right) to enable webhook
3. Verify webhook is listening (check execution history)

#### Test Buyer Agent

1. Open buyer agent template
2. Click "Execute Workflow" button
3. Monitor execution in real-time
4. Expected flow:
   - Load configuration
   - Get or create mandate
   - Request resource (receives 402 Payment Required)
   - Sign transaction via Render service
   - Submit payment proof
   - Receive resource (200 OK)

#### Verify on Blockchain

Check transaction on BaseScan:
- Merchant transaction: `https://basescan.org/tx/{tx_hash}`
- Commission transaction: `https://basescan.org/tx/{tx_hash_commission}`

#### Run Monitoring Workflows

1. Open buyer/seller monitoring template
2. Click "Execute Workflow"
3. Review analytics and payment history

---

## Configuration Reference

### N8N Data Table Setup (CRITICAL - Required for Buyer Agent)

⚠️ **IMPORTANT:** The buyer agent MUST have a Data Table configured. Follow these steps EXACTLY:

**Step 1: Create the Data Table**
1. In N8N, go to: **Data** → **Data Tables** → **+ Create New**
2. Name: `AgentPay_Mandates` (exact name - case sensitive!)
3. Add column: `mandate_token` (type: String)
4. Click **Save**

**Step 2: Link Table to Workflow Nodes (CRITICAL!)**
After importing the buyer workflow, you MUST re-link the table:

1. Open buyer workflow
2. Click **Node 2** "📊 Get Mandate Token"
3. Click the **"Data table"** dropdown
4. Select: `AgentPay_Mandates`
5. Click **Save**
6. Click **Node 7** "💾 Insert Token"
7. Click the **"Data table"** dropdown
8. Select: `AgentPay_Mandates`
9. Click **Save**

**Why this step is needed:** N8N imports don't preserve Data Table links. You must manually re-select the table after import, or the workflow will fail with "Data table not found."

**How it works:**
- First execution: Creates new mandate, stores token in table
- Subsequent executions: Reuses token from table (faster, saves budget)
- Token persists until mandate expires or you manually delete the row

**To renew mandate:** Delete the row from Data Table, workflow creates new mandate on next run.

---

### Transaction Signing Options

#### 1. SDK with Local Signing

Use the AgentGatePay SDK directly in your N8N workflow to sign transactions locally without external services.

**Pros:**
- No external service needed
- Direct control over signing
- Full SDK capabilities (mandates, payments, webhooks, analytics)
- Lower latency (no network calls to signing service)

**Cons:**
- Requires SDK installation in N8N environment
- Private key stored in N8N credentials
- More code than managed service options

**Setup:**
Replace the Render/Railway HTTP request node in the buyer workflow with SDK code that signs transactions using ethers.js (JavaScript) or web3.py (Python). Basic implementation involves initializing a wallet with your private key and calling the transfer function on the USDC contract.

**Note:** This approach is similar to Render/Railway but runs the signing code directly in N8N instead of calling an external service.

---

#### 2. Render/Railway Service

Deploy a managed transaction signing service to an external platform.

**Pros:**
- Quick deployment (2 minutes)
- Isolated private key storage
- Free tier available
- No N8N configuration changes needed

**Cons:**
- External dependency
- Cold start delays on free tier (~5 seconds)
- Additional service to maintain

**Setup:** See Step 3 above

---

#### 3. Coinbase x402 API

Use Coinbase managed wallet infrastructure for transaction signing.

**Pros:**
- Zero transaction fees
- Managed by Coinbase
- No deployment or maintenance
- Enterprise-grade security

**Cons:**
- KYC verification required
- Regional restrictions
- Coinbase API dependency

**Setup:**
1. Get Coinbase API key: https://www.coinbase.com/cloud
2. Replace Render service calls with Coinbase x402 API in buyer workflow
3. See documentation: https://docs.agentgatepay.com/coinbase-x402

---

#### 4. Custom Implementation

Build your own transaction signing service tailored to your infrastructure.

**Pros:**
- Full control over implementation
- Can integrate with existing systems
- No external dependencies

**Cons:**
- Development work required
- Must handle private key security
- Ongoing maintenance responsibility

**Languages Supported:**
- Python (web3.py, eth-account)
- JavaScript/TypeScript (ethers.js, web3.js)
- Go (go-ethereum)
- Any language with Web3 library support

**Reference Implementation:** See https://github.com/AgentGatePay/TX for a complete Node.js example

---

## Architecture Overview

### Payment Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. BUYER AGENT (N8N Workflow)                                  │
│    - Issue mandate (budget: $100, TTL: 7 days)                 │
│    - Store mandate token in Data Table                          │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. REQUEST RESOURCE                                             │
│    GET {seller_api_url}?resource_id=saas-competitors-2025       │
│    Headers: x-agent-id, x-mandate                               │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. SELLER API (N8N Webhook)                                     │
│    - Check payment header                                       │
│    - If no payment → Return 402 Payment Required                │
│    - Include: payment_address, price_usd, chain, token          │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. SIGN TRANSACTION (Render/Railway Service)                   │
│    POST {render_service_url}/sign-transaction                   │
│    Body: {to, value, chain, token}                              │
│    Response: {tx_hash, tx_hash_commission}                      │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. SUBMIT PAYMENT PROOF                                         │
│    GET {seller_api_url}?resource_id=saas-competitors-2025       │
│    Headers: x-payment (contains tx_hash + tx_hash_commission)   │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. SELLER VERIFIES PAYMENT                                      │
│    - Call AgentGatePay API: GET /v1/payments/verify/{tx_hash}   │
│    - Verify both transactions on blockchain                     │
│    - Check: amount, recipient, token, status                    │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. DELIVER RESOURCE                                             │
│    - Return 200 OK with resource data                           │
│    - Buyer agent receives resource                              │
└─────────────────────────────────────────────────────────────────┘
```

### Two-Transaction Commission Model

Each payment consists of TWO blockchain transactions:

**Transaction 1: Merchant Payment (99.5%)**
- From: Buyer wallet
- To: Seller wallet
- Amount: $0.00995 USDC (for $0.01 resource)
- Field: `tx_hash`

**Transaction 2: Gateway Commission (0.5%)**
- From: Buyer wallet
- To: AgentGatePay commission address
- Amount: $0.00005 USDC (for $0.01 resource)
- Field: `tx_hash_commission`

**Verification:** Both transactions must be confirmed on-chain before resource delivery.

---

## Troubleshooting

### Mandate Issues

**Error: "Mandate not found or expired"**
- **Solution:** Delete mandate token from Data Table, workflow will create new mandate on next run

**Error: "Insufficient mandate budget"**
- **Solution:** Increase budget_usd in buyer configuration or issue new mandate

**Error: "Mandate verification failed"**
- **Solution:** Check API key is correct and account is active

---

### Payment Issues

**Error: "Transaction not found on blockchain"**
- **Solution:** Wait 10-15 seconds for blockchain confirmation, then retry
- **Cause:** Base network propagation delay

**Error: "Payment verification failed"**
- **Solution:** Verify wallet has sufficient token balance (USDC/USDT/DAI)
- **Solution:** Ensure correct chain and token are configured
- **Solution:** Check RPC endpoint is accessible
- **Solution:** Verify tx_hash is correct format (0x...)

**Error: "Commission transaction missing"**
- **Solution:** Ensure transaction signing service sends BOTH transactions
- **Solution:** Verify Render/Railway service is running and accessible

---

### Webhook Issues

**Error: "Webhook not responding"**
- **Solution:** Verify seller workflow is ACTIVE (toggle must be ON)
- **Solution:** Check webhook URL in buyer configuration matches seller production URL
- **Solution:** Test webhook manually with curl

**Error: "CORS error when calling webhook"**
- **Solution:** N8N webhooks are CORS-enabled by default, check N8N version (requires v1.0+)

---

### Transaction Signing Service Issues

**Error: "Connection to Render service failed"**
- **Solution:** Check Render service is deployed and running
- **Solution:** Verify service URL includes `https://` prefix
- **Solution:** Check Render free tier hasn't spun down (cold start takes 5-10 sec)

**Error: "Private key invalid"**
- **Solution:** Verify PRIVATE_KEY environment variable in Render/Railway
- **Solution:** Check private key format: `0x` prefix followed by 64 hex characters

**Error: "Insufficient gas for transaction"**
- **Solution:** Ensure wallet has ETH for gas (on Base network, ~$0.001-0.01 per transaction)

---

### N8N Execution Errors

**Error: "Execution timed out"**
- **Solution:** Increase N8N timeout settings (Settings → Executions → Timeout)
- **Solution:** Blockchain confirmation can take 10-15 seconds, ensure adequate timeout

**Error: "Data Table not found"**
- **Solution:** Create `mandate_storage` table in N8N Settings → Data
- **Solution:** Add `mandate_token` column (type: String)

**Error: "Variable $json not defined"**
- **Solution:** Check node connections are correct
- **Solution:** Verify previous node executed successfully

---

## Advanced Configuration

### Multi-Chain and Multi-Token Support

AgentGatePay supports **3 payment tokens** on **4 blockchains** (12 combinations total).

**Supported Tokens:**
| Token | Decimals | Contract Addresses | Best Chain |
|-------|----------|-------------------|------------|
| USDC  | 6        | Available on all 4 chains | Base (lowest gas) |
| USDT  | 6        | Available on all 4 chains | Polygon |
| DAI   | 18       | Available on all 4 chains | Ethereum |

**Supported Blockchains:**
| Chain | Gas Cost per TX | Confirmation Time | Status |
|-------|----------------|-------------------|--------|
| **Base** (recommended) | ~$0.001 | 2-5 sec | ✅ Production |
| Polygon | ~$0.01 | 3-7 sec | ✅ Production |
| Arbitrum | ~$0.05 | 5-10 sec | ✅ Production |
| Ethereum | ~$5-20 | 12-20 sec | ✅ Production (expensive) |

**How to Change Chain and Token:**

1. Edit buyer configuration (Node 1):
```javascript
const CONFIG = {
  buyer: { /* ... */ },
  seller: { /* ... */ },
  render: { /* ... */ },
  payment: {
    chain: "polygon",  // ethereum, base, polygon, arbitrum
    token: "DAI"       // USDC, USDT, DAI
  }
};
```

2. Update Render service environment variables:
   - Add RPC URL for target chain (e.g., `POLYGON_RPC_URL`)
   - Ensure private key's wallet has tokens on target chain

3. Fund your wallet:
   - Send selected token to your wallet on selected chain
   - Include native token for gas (ETH for Ethereum/Arbitrum, MATIC for Polygon, ETH for Base)

**Important Notes:**
- Token decimals are handled automatically (USDC/USDT use 6 decimals, DAI uses 18 decimals)
- Seller will automatically detect chain and token from buyer's payment request
- Both merchant and commission transactions use the same token and chain

---

### Custom Resource Catalog

Edit seller configuration to add multiple resources:

```javascript
const SELLER_CONFIG = {
  merchant: {
    wallet_address: "0xYourWallet...",
    api_key: "pk_live_..."
  },
  catalog: {
    "basic-plan": {
      id: "basic-plan",
      price_usd: 0.01,
      description: "Basic API access"
    },
    "pro-plan": {
      id: "pro-plan",
      price_usd: 0.10,
      description: "Pro API access with analytics"
    },
    "enterprise-plan": {
      id: "enterprise-plan",
      price_usd: 1.00,
      description: "Enterprise API with priority support"
    }
  }
};
```

Buyer requests resource by ID: `?resource_id=pro-plan`

---

### Automated Monitoring

Set monitoring workflows to run on schedule:

1. Open monitoring workflow
2. Replace "Execute Workflow" trigger with "Schedule Trigger" node
3. Set schedule (example: every 1 hour)
4. Add notification node (Slack, email, Discord) for alerts

**Example: Low Balance Alert**
- Monitor mandate budget every hour
- If budget < $10 → Send Slack notification
- Prevents agent from running out of funds mid-operation

---

## Security Best Practices

### Private Key Management

1. **Use Separate Wallet for Agent**
   - Don't use your main wallet
   - Fund with limited amounts (~$10-100)
   - Easy to regenerate if compromised

2. **Secure Render/Railway Environment Variables**
   - Never commit private keys to Git
   - Use environment variables only
   - Rotate keys periodically

3. **Monitor Wallet Activity**
   - Set up alerts for large transactions
   - Review blockchain explorer regularly
   - Use monitoring workflows to track spending

---

### API Key Security

1. **Rotate API Keys Regularly**
   - Create new key every 30-90 days
   - Revoke old keys after rotation

2. **Store Keys Securely**
   - Use N8N credentials manager (encrypted)
   - Never hardcode in workflow JSON
   - Don't share keys in public channels

3. **Use Separate Keys for Testing**
   - Development key for testing
   - Production key for live operations
   - Revoke test keys after development

---

### Mandate Security

1. **Set Conservative Budgets**
   - Start with small budgets ($10-50)
   - Increase as you verify agent behavior
   - Monitor budget usage with monitoring workflow

2. **Use Short TTL for Testing**
   - Development: 1-7 days
   - Production: 30-90 days
   - Automatically expires to limit exposure

3. **Review Mandate Usage**
   - Check buyer monitoring workflow regularly
   - Verify purchases match expected behavior
   - Revoke mandate if suspicious activity detected

---

## Performance Optimization

### Reduce Cold Starts (Render/Railway)

**Problem:** First request after inactivity takes 5-10 seconds

**Solutions:**
1. Upgrade to paid tier (always-on instances)
2. Set up "keep-alive" pinger (cron job that calls service every 5 minutes)
3. Use Render's "auto-scale" feature (instantly scale up)

---

### Caching Mandate Tokens

**Problem:** Issuing mandate on every execution is slow (2-3 API calls)

**Solution:** Use N8N Data Table to persist mandate token

**Implementation:**
- First execution: Issue mandate, store token in Data Table
- Subsequent executions: Load token from Data Table
- If mandate expired: Automatically issue new mandate and update table

**Result:** 2x faster execution (1-2 seconds vs 3-4 seconds)

---

### Webhook Response Time

**Problem:** Blockchain verification can take 10-15 seconds

**Solutions:**
1. Use Base network (fastest confirmations)
2. Implement optimistic confirmation (respond immediately, verify async)
3. Cache verification results (same tx_hash = same result)

---

## Support and Resources

### Documentation

- **Main Documentation:** https://docs.agentgatepay.com
- **N8N Complete Guide:** https://docs.agentgatepay.com/n8n-guide
- **Transaction Signing Guide:** https://docs.agentgatepay.com/transaction-signing
- **API Reference:** https://docs.agentgatepay.com/api

### Code Examples

- **GitHub Repository:** https://github.com/agentgatepay/agentgatepay-sdk
- **Python SDK Examples:** https://github.com/agentgatepay/agentgatepay-python-sdk/tree/main/examples
- **JavaScript SDK Examples:** https://github.com/agentgatepay/agentgatepay-sdk/tree/main/examples

### Support

- **GitHub Issues:** https://github.com/agentgatepay/agentgatepay-sdk/issues
- **Email Support:** support@agentgatepay.com

---

## Changelog

### Version 1.0 (January 2025)

**Initial Release:**
- 4 production-ready N8N templates
- Multi-chain support (Ethereum, Base, Polygon, Arbitrum)
- Multi-token support (USDC, USDT, DAI)
- Two-transaction commission model
- Render/Railway transaction signing integration
- Data Table mandate persistence
- Comprehensive monitoring workflows

---

## License

These templates are provided under the MIT License.

Copyright (c) 2025 AgentGatePay

Permission is hereby granted, free of charge, to any person obtaining a copy of these templates to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the templates, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the templates.

THE TEMPLATES ARE PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

---

## Contributing

Found a bug or have a feature request?

1. **Report Issues:** https://github.com/agentgatepay/agentgatepay-sdk/issues
2. **Submit Pull Requests:** https://github.com/agentgatepay/n8n-templates
3. **Share Your Templates:** Email support@agentgatepay.com

---

**Questions?** Contact support@agentgatepay.com

**Ready to get started?** Follow Step 1 above and have your first autonomous agent payment running in under 10 minutes!

