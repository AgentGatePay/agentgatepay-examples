# N8N Implementation Guide
## AgentGatePay Autonomous Payment Workflows

**Version:** 2.1 BETA
**Last Updated:** November 21, 2025
**Status:** Production (Verified against codebase)

> **⚠️ BETA VERSION**: These templates and AgentGatePay platform are currently in beta. We're actively adding features and improvements based on user feedback. Expect updates for:
> - Additional blockchain networks and payment tokens
> - Enhanced analytics and monitoring capabilities
> - Improved transaction speed and reliability
> - New agent framework integrations
> - Advanced security features

---

## Overview

This guide covers the implementation of autonomous AI agent payment workflows using N8N and AgentGatePay. The system enables buyer agents to autonomously discover, pay for, and receive resources from seller APIs using **multiple payment tokens (USDC, USDT, DAI) across 4 blockchains (Ethereum, Base, Polygon, Arbitrum)**.

**Architecture:**
- Buyer Agent (N8N workflow) - Pays for resources
- Seller Resource API (N8N workflow) - Sells resources
- AgentGatePay Gateway - Verifies payments and manages mandates
- Transaction Signing Service - Signs blockchain transactions (Render/Railway)

**Payment Protocol:**
- HTTP 402 (Payment Required) - x402 protocol
- AP2 Mandates - Pre-authorized spending authority
- Two-transaction commission model - Separate merchant and gateway payments

---

## What is AgentGatePay?

**AgentGatePay** is a **payment gateway router** specifically designed for the agent economy. It acts as a third-party gateway between client agents (buyers) and merchant/provider agents (sellers), enabling autonomous AI agents to make and receive payments without human intervention.

### Core Value Proposition

**Problem:** AI agents cannot make payments autonomously because they lack:
- Payment authorization mechanisms
- Budget management systems
- Security against malicious agents
- Transaction verification infrastructure
- Audit trails for compliance

**Solution:** AgentGatePay provides:
- **AP2 Mandates** - Pre-authorized spending with budget limits
- **x402 Protocol** - HTTP 402 Payment Required for agent payments
- **AIF Security** - Agent Interaction Firewall for protection
- **Multi-chain Support** - USDC/USDT/DAI on Ethereum, Base, Polygon, Arbitrum
- **Audit Logging** - Complete transaction history and compliance tracking
- **Commission Model** - Sustainable 0.5% gateway fee

### Key Benefits

1. **Autonomous Payments**
   - Agents can pay for resources without human approval
   - Budget limits prevent overspending
   - Time-limited mandates expire automatically

2. **Security First**
   - Rate limiting prevents abuse (100 req/min with API key)
   - Replay protection prevents double-spending
   - Agent reputation system blocks bad actors
   - Transaction verification on blockchain

3. **Developer Friendly**
   - Python and JavaScript SDKs
   - N8N workflow templates (no code required)
   - MCP protocol support (15 tools)
   - REST API for custom integrations

4. **Production Ready**
   - CloudFront CDN + WAF security
   - Multi-chain blockchain support
   - Webhook notifications
   - Analytics dashboard

### How AgentGatePay Works

**Step 1: Issue Mandate (AP2 Protocol)**
- Agent issues mandate with budget (e.g., $100) and time limit (e.g., 7 days)
- AgentGatePay Gateway signs mandate using Ed25519 cryptography
- Mandate token returned in JWT-like format
- Token stored for reuse until budget exhausted or expired

**Step 2: Request Resource (x402 Protocol)**
- Agent requests resource from seller
- If no payment provided, seller returns HTTP 402 Payment Required
- 402 response includes payment details (wallet, amount, token, chain)

**Step 3: Execute Payment**
- Agent signs transaction to blockchain (USDC transfer)
- TWO transactions created: Merchant payment (99.5%) + Commission (0.5%)
- Transaction hashes returned as payment proof

**Step 4: Verify and Deliver**
- Agent resubmits request with payment proof (tx_hash)
- Seller verifies transaction with AgentGatePay API
- Gateway confirms transaction on blockchain
- Seller delivers resource if payment valid

**Step 5: Track and Monitor**
- All transactions logged to audit trail
- Mandate budget deducted automatically
- Analytics dashboard tracks spending/revenue
- Webhooks notify on payment completion

### AP2 Mandate System

**AP2 (Agent Payment Protocol v2)** is AgentGatePay's mandate system that enables delegated spending authority.

**Key Features:**
- **Budget Control:** Set maximum spending in USD
- **Time Limits:** Mandates expire after TTL (1 hour to 90 days)
- **Scope Restrictions:** Define allowed actions (e.g., "resource.read payment.execute")
- **Ed25519 Signing:** Cryptographic signatures prevent tampering
- **JWT Format:** Standard token format for easy integration
- **Atomic Updates:** Budget tracking prevents race conditions

**Mandate Lifecycle:**
```
Issue → Verify → Use (deduct budget) → Renew (manual) or Expire (automatic)
```

**Mandate Token Format:**
```
header.payload.signature

Header:
{
  "alg": "EdDSA",
  "typ": "AP2-VDC"
}

Payload:
{
  "sub": "agent-worker-1",
  "budget_usd": "100.0",
  "budget_remaining": "99.99",
  "scope": "resource.read,payment.execute",
  "iat": 1705881600,
  "exp": 1706486400,
  "nonce": "abc123..."
}

Signature:
Ed25519 signature over header + payload
```

### AIF (Agent Interaction Firewall)

**AIF** is the first security firewall built specifically for AI agents. It protects agents from malicious agents and prevents abuse.

**Security Features:**

1. **Distributed Rate Limiting**
   - 100 requests/minute for authenticated users (with API key)
   - 20 requests/minute for anonymous users
   - DynamoDB atomic counters across all Lambda containers
   - Standard RFC 6585 headers (X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset)

2. **Replay Protection**
   - Transaction hashes used as nonces (cryptographically unique)
   - 24-hour TTL on nonces prevents old transactions
   - Same tx_hash cannot be submitted twice
   - Prevents double-spending at API level

3. **Agent Reputation System**
   - Score range: 0-200 (new agents start at 100)
   - Blocking thresholds: 0-30 blocked, 31-60 warning, 61-200 allowed
   - Tracks suspicious behavior (high budgets, failed payments, rapid requests)
   - Fail-open design (errors never break payment flows)
   - Manual override available for false positives

4. **Pattern Detection**
   - Detects unusually high mandate budgets
   - Flags broad scope requests
   - Monitors payment failure rates
   - Analyzes request timing patterns

**AIF Architecture:**
```
Request → AIF Check → Rate Limit → Nonce Validation → Reputation Check → Handler
```

### Audit System

**Complete audit trail** for compliance, debugging, and monitoring.

**What Gets Logged:**
- Mandate issuance and verification
- Payment requests and settlements
- Transaction verification results
- API key creation and revocation
- User account activities
- Audit log access (meta-audit)

**Audit Log Format:**
```json
{
  "id": "audit_abc123",
  "timestamp": 1705881600,
  "event_type": "payment_completed",
  "client_id": "user@example.com",
  "details": {
    "tx_hash": "0xabc...",
    "amount_usd": "0.01",
    "token": "USDC",
    "chain": "base",
    "mandate_id": "mandate_xyz"
  },
  "ip_address": "203.0.113.1",
  "user_agent": "AgentGatePay-SDK/1.0"
}
```

**Security:**
- Authentication required for all audit log access
- Users can only see their own logs
- Admin users can see all logs
- Meta-audit logs track who accessed audit logs

**Use Cases:**
- Compliance reporting (SOC 2, PCI DSS)
- Debugging payment failures
- Monitoring agent behavior
- Detecting security incidents
- Analytics and business intelligence

---

## Prerequisites

### Required Accounts

1. **N8N Account**
   - N8N Cloud (https://n8n.io) OR self-hosted instance
   - Two separate N8N workspaces recommended (buyer/seller isolation)

2. **AgentGatePay Accounts** (create TWO separate users)

   **Buyer Account:**
   ```bash
   curl -X POST https://api.agentgatepay.com/v1/users/signup \
     -H "Content-Type: application/json" \
     -d '{
       "email": "buyer-agent@yourcompany.com",
       "password": "SecurePassword123",
       "user_type": "agent"
     }'
   ```
   Save the returned `apiKey` for buyer configuration.

   **Seller Account:**
   ```bash
   curl -X POST https://api.agentgatepay.com/v1/users/signup \
     -H "Content-Type: application/json" \
     -d '{
       "email": "seller-merchant@yourcompany.com",
       "password": "SecurePassword456",
       "user_type": "merchant"
     }'
   ```
   Save the returned `apiKey` for seller configuration.

3. **Blockchain Wallet**
   - Ethereum-compatible wallet (e.g., MetaMask, Coinbase Wallet)
   - Funded with USDC (payments) and ETH (gas fees) on Base network

4. **Transaction Signing Service**
   - Option 1: Use AgentGatePay SDK with local signing (ethers.js or web3.py)
   - Option 2: Deploy to Render or Railway (instructions below)
   - Option 3: Use Coinbase Wallet API
   - Option 4: Implement custom signing service

---

## Transaction Signing Service Setup

The transaction signing service is required for autonomous blockchain transactions. It stores your private key securely and signs USDC transactions to the blockchain.

### Why Transaction Signing is Needed

**The Problem:**
- N8N workflows cannot directly sign blockchain transactions
- Private keys must be stored securely (not in workflow JSON)
- Two transactions needed per payment (merchant + commission)
- Transaction signing requires Web3 libraries (ethers.js)

**The Solution:**
- Deploy a signing service that handles transaction signing
- Service stores private key as encrypted secret
- N8N calls service API to request signed transactions
- Service returns transaction hashes for both merchant and commission

### Option 0: SDK with Local Signing

Use the AgentGatePay SDK (JavaScript or Python) directly in your N8N workflow to sign transactions locally without deploying external services. This approach executes the same transaction signing logic that would run in Render/Railway, but directly within N8N.

**How It Works:**
Replace the HTTP Request node that calls Render/Railway with a Code node that uses ethers.js (JavaScript) or web3.py (Python) to sign USDC transfer transactions.

**Basic Implementation Concept:**
```javascript
// In N8N Code node (JavaScript)
const { ethers } = require('ethers');

// Initialize wallet and provider
const provider = new ethers.JsonRpcProvider('https://mainnet.base.org');
const wallet = new ethers.Wallet(privateKey, provider);

// USDC contract on Base
const usdcContract = new ethers.Contract(
  '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
  ['function transfer(address,uint256)'],
  wallet
);

// Calculate commission (0.5%)
const commission = BigInt(totalAmount) * BigInt(5) / BigInt(1000);
const merchantAmount = BigInt(totalAmount) - commission;

// Execute two transactions
const tx1 = await usdcContract.transfer(commissionAddress, commission);
await tx1.wait();

const tx2 = await usdcContract.transfer(merchantAddress, merchantAmount);
await tx2.wait();

// Return both transaction hashes
return {
  tx_hash: tx2.hash,
  tx_hash_commission: tx1.hash
};
```

**Pros:**
- No external service deployment needed
- Lower latency (no HTTP round-trip to external service)
- Full control over signing process
- Simpler architecture (fewer moving parts)

**Cons:**
- Requires SDK and Web3 library installation in N8N environment
- Private key stored in N8N credentials (must be secured properly)
- More complex N8N workflow code than HTTP request
- Depends on N8N environment supporting npm packages (ethers.js/web3.js)

**When to Use:**
- Self-hosted N8N with full control over environment
- Need lowest possible latency
- Want to avoid external dependencies
- Comfortable managing secrets in N8N

**Note:** This approach provides the same security and functionality as Render/Railway options but executes the signing code directly in N8N instead of calling an external service. For most users, Render/Railway deployment (Option 1 below) is simpler and requires less N8N configuration.

---

### Option 1: Render One-Click Deploy

**🚀 One-Click Deploy - 3 minutes to production**

This is the EASIEST and FASTEST way to deploy. No blockchain knowledge required.

**Step 1: Get Your API Key**

```bash
curl -X POST https://api.agentgatepay.com/v1/users/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your@email.com",
    "password": "SecurePass123",
    "user_type": "agent"
  }'
```

Save your API key: `pk_live_abc123...`

**Step 2: One-Click Deploy**

Click this button: [![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/AgentGatePay/AgentGatePay)

**When prompted, enter:**
1. **AGENTGATEPAY_API_KEY:** Paste your API key (`pk_live_...`)
2. **WALLET_PRIVATE_KEY:** Paste your wallet private key (`0x...`)

**That's it!** ✅ Service deploys in ~2 minutes.

**Step 3: Save Service URL**

After deployment completes:
- Copy URL: `https://your-service-name.onrender.com`
- Test: `curl https://your-service-name.onrender.com/health`
- Use this URL in N8N buyer workflow configuration (Node 1, `render.service_url`)

**What Happens Under the Hood:**

1. **One-Click Button** triggers Render's automatic deployment
2. **Render creates Web Service** from AgentGatePay GitHub repository
3. **Environment variables set** for your API key and private key (encrypted at rest)
4. **Service deploys** with Node.js and starts listening on port (auto-detected by Render)
5. **Commission config fetched** from AgentGatePay API on every payment request
6. **Two transactions signed** automatically when /sign-payment endpoint called
7. **Transaction hashes returned** to N8N workflow for payment proof

**Security Features:**

- ✅ **Owner Protection:** Only YOUR API key can access the service (401 Unauthorized for others)
- ✅ **Server-Fetched Config:** Commission address and rate fetched from AgentGatePay (you cannot modify)
- ✅ **Encrypted Secrets:** Private key encrypted at rest by Render
- ✅ **HTTPS Only:** All requests over TLS 1.3
- ✅ **No Commission Bypass:** Commission is MANDATORY (enforced server-side)

**Upgrade to Secret Files (Optional - Maximum Security):**

After deployment, you can optionally move secrets to Secret Files for extra security:

1. Go to Render Dashboard → Your Service → Secret Files
2. Add Secret File:
   - Filename: `wallet-private-key`
   - Contents: Your private key (`0x...`)
3. Add Secret File:
   - Filename: `agentgatepay-api-key`
   - Contents: Your API key (`pk_live_...`)
4. Go to Environment tab, delete `WALLET_PRIVATE_KEY` and `AGENTGATEPAY_API_KEY`
5. Save changes (automatic redeploy)

**Result:** Secrets stored as files (not environment variables) - maximum security.

**Cost:**
- Free tier: Unlimited (service spins down after 15 min inactivity, cold start ~5 sec)
- Paid tier: $7/month (always-on, no cold starts)

---

### Option 2: Railway Deployment

**Similar to Render but with different platform:**

**Deploy:**
1. Visit Railway dashboard (https://railway.app)
2. Create new project → Deploy from GitHub
3. Connect repository: `https://github.com/AgentGatePay/AgentGatePay`
4. Wait ~2 minutes for deployment

**Configure:**
1. Add environment variables in Railway dashboard:
   ```
   AGENTGATEPAY_API_KEY=pk_live_abc123...
   WALLET_PRIVATE_KEY=0x...
   BASE_RPC=https://mainnet.base.org
   ```
2. Copy service URL: `https://your-app.railway.app`
3. Use this URL in buyer workflow

**Pros:**
- Same security features as Render
- Faster cold starts (~2 seconds)
- Better developer UX

**Cons:**
- No one-click deploy button (manual setup)
- Paid tier required after 500 hours/month

**Cost:**
- Free tier: 500 hours/month (then $5/month)
- Paid tier: $5/month minimum

---

### Option 3: Coinbase x402 API (Alternative for KYC-compliant users)

**Use Coinbase's managed signing service instead of self-hosting.**

**Setup:**
1. Create Coinbase Developer account: https://www.coinbase.com/cloud
2. Complete KYC verification (required)
3. Generate API credentials (API key + secret)
4. Get Coinbase x402 endpoint: `https://api.coinbase.com/x402/sign`

**Configure N8N Buyer Workflow:**

In Node 10 "Sign Payment (Render)", replace Render API call with Coinbase API:

**Before (Render):**
```javascript
POST {{$node["Load Config"].json["render"]["service_url"]}}/sign-payment
Headers:
  x-api-key: {{$node["Load Config"].json["buyer"]["api_key"]}}
Body:
{
  "merchant_address": "{{$json["payTo"]}}",
  "total_amount": "{{$json["amount"]}}",
  "token": "USDC",
  "chain": "base"
}
```

**After (Coinbase):**
```javascript
POST https://api.coinbase.com/x402/sign
Headers:
  CB-ACCESS-KEY: YOUR_COINBASE_API_KEY
  CB-ACCESS-SIGN: HMAC_SIGNATURE
  CB-ACCESS-TIMESTAMP: UNIX_TIMESTAMP
Body:
{
  "recipient": "{{$json["payTo"]}}",
  "amount": "{{$json["amount"]}}",
  "currency": "USDC",
  "network": "base"
}
```

**Pros:**
- No deployment needed (managed by Coinbase)
- 0% transaction fees (Coinbase covers gas)
- Enterprise-grade security
- Regulatory compliance built-in

**Cons:**
- Requires KYC verification (ID, proof of address)
- Regional restrictions (not available in all countries)
- Coinbase API dependency (downtime affects your service)
- Less customization (cannot modify commission logic)

**Cost:**
- Free tier: 1,000 requests/month
- Paid tier: $0.01 per request after free tier

**Documentation:** https://docs.coinbase.com/x402-api

---

### Option 4: Self-Hosted Custom Implementation

**Build and host your own signing service on your existing infrastructure.**

**Use Cases:**
- You already have a Python/Node.js server
- You want full control over the code
- You have specific compliance requirements
- You want to avoid external dependencies

**Architecture:**

```
Your Server (Python/Node.js/Go/etc.)
  ↓
ethers.js or web3.py library
  ↓
Sign USDC transaction
  ↓
Broadcast to blockchain (Base RPC)
  ↓
Return tx_hash to N8N
```

**Implementation (Node.js + ethers.js):**

```javascript
// server.js
const express = require('express');
const { ethers } = require('ethers');
const app = express();
app.use(express.json());

// Load private key from environment variable
const PRIVATE_KEY = process.env.WALLET_PRIVATE_KEY;
const BASE_RPC = 'https://mainnet.base.org';
const USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'; // Base USDC

// Initialize provider and wallet
const provider = new ethers.JsonRpcProvider(BASE_RPC);
const wallet = new ethers.Wallet(PRIVATE_KEY, provider);
const usdc = new ethers.Contract(USDC_ADDRESS, ['function transfer(address,uint256)'], wallet);

app.post('/sign-payment', async (req, res) => {
  try {
    const { merchant_address, total_amount, token, chain } = req.body;

    // Calculate commission (0.5%)
    const commission = BigInt(total_amount) * BigInt(5) / BigInt(1000);
    const merchant_amount = BigInt(total_amount) - commission;

    // Fetch commission address from AgentGatePay
    const commissionRes = await fetch('https://api.agentgatepay.com/v1/config/commission');
    const { commission_address } = await commissionRes.json();

    // Transaction 1: Commission
    const tx1 = await usdc.transfer(commission_address, commission);
    await tx1.wait();

    // Transaction 2: Merchant
    const tx2 = await usdc.transfer(merchant_address, merchant_amount);
    await tx2.wait();

    // Return both transaction hashes
    res.json({
      success: true,
      tx_hash: tx2.hash,
      tx_hash_commission: tx1.hash,
      commission_address,
      commission_amount: commission.toString(),
      merchant_amount: merchant_amount.toString()
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.listen(3000, () => console.log('Signing service running on port 3000'));
```

**Deployment Options:**
- AWS Lambda (serverless)
- Docker container on AWS ECS/Fargate
- Kubernetes cluster
- Traditional VPS (DigitalOcean, Linode, AWS EC2)
- Same server as your existing agent infrastructure

**Security Considerations:**
- Store private key in AWS Secrets Manager, HashiCorp Vault, or similar
- Use HTTPS only (TLS 1.3)
- Implement API key authentication
- Rate limit requests (prevent abuse)
- Monitor for unusual activity
- Rotate private keys periodically

**Pros:**
- Full control over code and infrastructure
- No external dependencies (except blockchain RPC)
- Can customize commission logic (if needed)
- Can integrate with existing monitoring/logging
- No cold starts (if using dedicated server)

**Cons:**
- Requires development work (50-200 lines of code)
- Must handle private key security yourself
- Responsibility for uptime and monitoring
- Need to maintain and update code

**Cost:**
- AWS Lambda: ~$0.20 per 1 million requests
- VPS: $5-50/month depending on specs

---

### Option 5: External Wallet Services (Future)

**Use third-party wallet infrastructure providers.**

**Providers:**
- Fireblocks (enterprise)
- BitGo (institutional)
- Turnkey (developer-friendly)
- Magic (consumer-friendly)

**Status:** Not yet integrated with AgentGatePay. Coming in Q2 2025.

**Pros:**
- Professional-grade security
- Insurance coverage for funds
- Multi-signature support
- Compliance built-in

**Cons:**
- Higher cost ($100+/month)
- KYC requirements
- Slower integration (custom API work needed)

---

### Recommended Choice by User Type

**No-Code Users (N8N only):**
→ **Render One-Click Deploy** (3 minutes, no coding)

**Developers (Python/JS agents):**
→ **Self-Hosted** (integrate with existing infrastructure)

**Enterprises (compliance required):**
→ **Coinbase x402** (KYC compliant, managed service)

**High-Volume Users (>10K payments/month):**
→ **Self-Hosted** (avoid external dependencies, optimize costs)

---

## Buyer Agent Workflow

### Template File
**Location:** `/n8n-demo-mcp/New/🤖 Buyer Agent - CLIENT TEMPLATE.json`
**Nodes:** 22 nodes total (including README v3.2 sticky note with documentation)

### Workflow Architecture

```
START
  └─> Load Config (Node 1)
      └─> Get Mandate Token (Node 2) [Data Table]
          └─> Has Token? (Node 3) [IF condition]
              ├─> YES: Verify Existing Token (Node 4)
              │   └─> Check Verification (Node 4B)
              │       └─> Merge Paths (Node 8)
              │
              └─> NO: Create New Mandate (Node 5) [MCP API]
                  └─> Parse New Mandate (Node 5B)
                      └─> Verify New Mandate (Node 6) [MCP API]
                          └─> Check New Mandate (Node 6B)
                              └─> Insert Token (Node 7) [Data Table]
                                  └─> Restore Data (Node 7B)
                                      └─> Merge Paths (Node 8)

From Node 8:
  └─> Request Resource (Node 9) [Seller API]
      └─> Parse 402 Response (Node 9B)
          └─> Sign Payment (Node 10) [Render/Railway]
              └─> Extract TX Hashes (Node 11)
                  └─> Submit Payment (Node 12) [MCP API]
                      └─> Receive Resource (Node 13) [Seller API]
                          └─> Complete Task (Node 14)
```

### Detailed Node-by-Node Breakdown

**Understanding what each node does and why it's needed:**

**Node 1: Load Config**
- **Type:** Function node (JavaScript)
- **Purpose:** Centralized configuration for all workflow parameters
- **What it does:** Defines CONFIG object with buyer info, seller API, Render URL, blockchain settings
- **Why needed:** Single source of truth - change config once, affects all downstream nodes
- **Customization:** Edit buyer email, API key, budget, TTL, seller URL, Render URL

**Node 2: Get Mandate Token**
- **Type:** Data Table node (SELECT)
- **Purpose:** Check if mandate already exists in storage
- **What it does:** Queries `AgentPay_Mandates` table for existing mandate token
- **Why needed:** Avoid creating new mandate on every execution (saves 2-3 seconds)
- **Customization:** Change table name if using different Data Table

**Node 3: Has Token?**
- **Type:** IF node (conditional)
- **Purpose:** Route workflow based on mandate existence
- **What it does:** Checks if Node 2 returned any rows (`{{$json["mandate_token"]}} !== undefined`)
- **Why needed:** Different paths for first execution (no mandate) vs subsequent executions (mandate exists)
- **Customization:** None (logic is standard)

**Node 4: Verify Existing Token** (YES path from Node 3)
- **Type:** HTTP Request node (POST to MCP API)
- **Purpose:** Verify stored mandate is still valid
- **What it does:** Calls AgentGatePay MCP `agentpay_verify_mandate` tool
- **Why needed:** Mandate may have expired or budget exhausted since last execution
- **Customization:** None (uses standard MCP protocol)

**Node 4B: Check Verification**
- **Type:** IF node (conditional)
- **Purpose:** Ensure mandate is valid before proceeding
- **What it does:** Checks verification response (`{{$json["result"]["valid"] === true}}`)
- **Why needed:** Throw error if mandate invalid (user must renew)
- **Customization:** Can add auto-renewal logic instead of throwing error

**Node 5: Create New Mandate** (NO path from Node 3)
- **Type:** HTTP Request node (POST to MCP API)
- **Purpose:** Issue new AP2 mandate if none exists
- **What it does:** Calls AgentGatePay MCP `agentpay_issue_mandate` tool with budget and TTL from config
- **Why needed:** First execution or after manual mandate deletion
- **Customization:** Can adjust budget/TTL dynamically based on external factors

**Node 5B: Parse New Mandate**
- **Type:** Function node (JavaScript)
- **Purpose:** Extract mandate token from MCP response
- **What it does:** Parses `result.mandate_token` from MCP JSON-RPC response
- **Why needed:** MCP wraps response in JSON-RPC envelope, need to extract data
- **Customization:** None (standard JSON parsing)

**Node 6: Verify New Mandate**
- **Type:** HTTP Request node (POST to MCP API)
- **Purpose:** Confirm newly issued mandate is valid
- **What it does:** Calls `agentpay_verify_mandate` immediately after issuance
- **Why needed:** Ensure mandate was created correctly before storing
- **Customization:** Can skip verification if trusting gateway (saves 1 API call)

**Node 6B: Check New Mandate**
- **Type:** IF node (conditional)
- **Purpose:** Validate new mandate before storage
- **What it does:** Checks `{{$json["result"]["valid"] === true}}`
- **Why needed:** Throw error if mandate creation failed
- **Customization:** Can add retry logic (issue mandate again on failure)

**Node 7: Insert Token**
- **Type:** Data Table node (INSERT)
- **Purpose:** Store mandate token for future executions
- **What it does:** Inserts mandate token into `AgentPay_Mandates` table
- **Why needed:** Persistence - reuse mandate across workflow executions
- **Customization:** Can add expiration timestamp column for automatic cleanup

**Node 7B: Restore Data**
- **Type:** Function node (JavaScript)
- **Purpose:** Pass mandate token to next node
- **What it does:** Extracts mandate token from insert response
- **Why needed:** Data Table INSERT returns different format, need to normalize
- **Customization:** None (standard data transformation)

**Node 8: Merge Paths**
- **Type:** Merge node
- **Purpose:** Combine YES path (existing mandate) and NO path (new mandate)
- **What it does:** Waits for either path to complete, passes data forward
- **Why needed:** Both paths lead to same payment flow (DRY principle)
- **Customization:** None (standard merge pattern)

**Node 9: Request Resource**
- **Type:** HTTP Request node (GET to Seller API)
- **Purpose:** Request resource from seller WITHOUT payment
- **What it does:** Sends GET request to seller API with mandate header
- **Why needed:** Seller returns 402 Payment Required with payment details
- **Customization:** Change HTTP method (POST/GET), add query parameters, headers

**Node 9B: Parse 402 Response**
- **Type:** Function node (JavaScript)
- **Purpose:** Extract payment details from 402 response
- **What it does:** Parses `payTo`, `amount`, `token`, `chain` from JSON
- **Why needed:** These values needed for transaction signing
- **Customization:** Handle different 402 formats if seller uses custom schema

**Node 10: Sign Payment (Render)**
- **Type:** HTTP Request node (POST to Render service)
- **Purpose:** Request transaction signing from Render service
- **What it does:** Sends payment details to Render `/sign-payment` endpoint with API key
- **Why needed:** N8N cannot sign blockchain transactions directly
- **Customization:** Switch to Coinbase API, Railway, or self-hosted service

**Node 11: Extract TX Hashes**
- **Type:** Function node (JavaScript)
- **Purpose:** Extract both transaction hashes from Render response
- **What it does:** Parses `tx_hash` and `tx_hash_commission` from response
- **Why needed:** Both hashes required for AgentGatePay payment verification
- **Customization:** None (standard JSON parsing)

**Node 12: Submit Payment**
- **Type:** HTTP Request node (POST to MCP API)
- **Purpose:** Submit payment proof to AgentGatePay for verification
- **What it does:** Calls `agentpay_submit_payment` MCP tool with both tx_hashes
- **Why needed:** Gateway verifies transactions on blockchain, deducts from mandate budget
- **Customization:** Can add retry logic if blockchain verification fails

**Node 13: Receive Resource**
- **Type:** HTTP Request node (GET to Seller API)
- **Purpose:** Re-request resource WITH payment proof
- **What it does:** Sends same request as Node 9 but with `x-payment` header containing tx_hashes
- **Why needed:** Seller verifies payment with AgentGatePay, then delivers resource
- **Customization:** Parse resource data, save to file, forward to another agent

**Node 14: Complete Task**
- **Type:** Function node (JavaScript) OR Output node
- **Purpose:** Process received resource
- **What it does:** Logs success, extracts resource data, returns to user
- **Why needed:** Final step - do something with purchased resource
- **Customization:** Send to email, save to database, trigger another workflow, feed to LLM

---

### Installation

1. **Import Template**
   - Open N8N workflow editor
   - Import JSON file: `🤖 Buyer Agent - CLIENT TEMPLATE.json`
   - Workflow imports with all nodes configured

2. **Create Data Table**
   - Navigate to: Data → Data Tables
   - Create new table: `AgentPay_Mandates`
   - Add column: `mandate_token` (type: String)
   - Save table

3. **Link Data Table to Workflow**
   - Click Node 2 "Get Mandate Token"
   - Select Data table dropdown
   - Choose: `AgentPay_Mandates`
   - Save node
   - Click Node 7 "Insert Token"
   - Select Data table dropdown
   - Choose: `AgentPay_Mandates`
   - Save node

### Configuration

**Edit Node 1 "Load Config":**

```javascript
const CONFIG = {
  buyer: {
    name: "Research Assistant AI",           // Agent name (optional)
    company: "Your Company",                  // Company name (optional)
    email: "buyer-agent@yourcompany.com",    // REQUIRED: Buyer agent identifier
    api_key: "pk_live_abc123...",            // REQUIRED: AgentGatePay API key (buyer account)
    budget_usd: 100,                         // Mandate budget in USD
    mandate_ttl_days: 7,                     // Mandate validity period (days)
    mandate_scope: "resource.read payment.execute"
  },
  seller: {
    name: "DataBot Pro",                     // Seller name (optional)
    company: "MarketInsights AI Ltd.",       // Seller company (optional)
    email: "seller@marketinsights.ai",       // Seller identifier (optional)
    service: "Premium Market Research Reports", // Service description (optional)
    api_url: "https://your-n8n.app.n8n.cloud/webhook/seller-api",  // REQUIRED: Seller webhook URL
    selected_resource_id: "saas-competitors-2025"  // Resource ID to purchase
  },
  render: {
    service_url: "https://your-app.railway.app"  // REQUIRED: Transaction signing service URL
  },
  blockchain: {
    chain: "base",                           // Blockchain network
    token: "USDC",                           // Payment token
    rpc_url: "https://mainnet.base.org"     // RPC endpoint
  },
  agentgatepay: {
    api_url: "https://api.agentgatepay.com",
    mcp_endpoint: "https://mcp.agentgatepay.com"
  }
};
```

**Required Configuration Values:**
- `buyer.email` - Unique identifier for this buyer agent
- `buyer.api_key` - API key from buyer AgentGatePay account signup
- `seller.api_url` - Webhook URL from seller workflow (configure seller first)
- `render.service_url` - URL of your deployed transaction signing service

### Execution Flow

**First Execution (No Mandate):**
1. Workflow checks Data Table for existing mandate
2. Table empty - creates new mandate via AgentGatePay MCP API
3. Gateway returns mandate token (JWT format, ~150+ characters)
4. Token saved to Data Table
5. Workflow continues with payment flow
6. Total duration: ~10-15 seconds

**Subsequent Executions (Existing Mandate):**
1. Workflow retrieves mandate token from Data Table
2. Verifies token with AgentGatePay Gateway
3. If valid: continues with existing token
4. If invalid/expired: throws error with renewal instructions
5. Total duration: ~5-8 seconds

**Payment Flow (All Executions):**
1. Request resource from seller (Node 9)
2. Receive 402 Payment Required response
3. Extract payment details (wallet address, amount, token, chain)
4. Call transaction signing service (Node 10)
5. Signing service creates TWO transactions:
   - Merchant payment (99.5% of amount)
   - Gateway commission (0.5% of amount)
6. Signing service broadcasts both transactions to blockchain
7. Returns both transaction hashes
8. Submit payment proof to AgentGatePay (Node 12)
9. Gateway verifies both transactions on-chain
10. Retry resource request with payment proof (Node 13)
11. Seller verifies payment and delivers resource

**Mandate Renewal:**
When mandate expires or budget exhausted:
1. Navigate to: Data → AgentPay_Mandates
2. Delete the existing row
3. (Optional) Update budget/TTL in Node 1 configuration
4. Execute workflow - creates new mandate automatically

### Two-Transaction Commission Model

AgentGatePay uses a two-transaction architecture to collect platform commission:

**Transaction 1: Merchant Payment**
- Amount: 99.5% of resource price
- Recipient: Seller's wallet address
- Token: USDC (or configured token)
- Chain: Base (or configured chain)

**Transaction 2: Gateway Commission**
- Amount: 0.5% of resource price
- Recipient: AgentGatePay commission wallet
- Token: Same as transaction 1
- Chain: Same as transaction 1

**Verification:**
- AgentGatePay Gateway verifies BOTH transactions on blockchain
- Checks sender, recipient, amount, token contract, transaction status
- Payment rejected if either transaction missing or invalid
- Seller only delivers resource after both transactions confirmed

**Example:**
- Resource price: $1.00 (1,000,000 USDC atomic units)
- Merchant receives: $0.995 (995,000 USDC atomic units)
- Gateway receives: $0.005 (5,000 USDC atomic units)
- Gas cost: ~$0.01 ETH (paid separately by buyer)

---

## Seller Resource API Workflow

### Template File
**Location:** `/n8n-demo-mcp/New/💲Seller Resource API - CLIENT TEMPLATE.json`
**Nodes:** 12 nodes total (including README v3.2 sticky note with documentation)

### Workflow Architecture

```
Webhook Trigger (GET /resource/{resourceId})
  └─> Parse Request (Node 1)
      └─> Has Payment? (Node 2) [IF condition]
          ├─> NO: Generate 402 (Node 3)
          │   └─> Send 402 (Node 4)
          │
          └─> YES: Verify Payment (Node 5) [AgentGatePay API]
              └─> Validate Payment (Node 6)
                  └─> Route: Valid? (Node 6B) [IF condition]
                      ├─> YES: Deliver Resource (Node 7)
                      │   └─> Send 200 OK (Node 8)
                      │
                      └─> NO: Send Error (Node 9)
```

### Detailed Node-by-Node Breakdown (Seller)

**Understanding what each seller node does:**

**Node 1: Parse Request**
- **Type:** Function node (JavaScript)
- **Purpose:** Centralized seller configuration and request parsing
- **What it does:** Defines SELLER_CONFIG with wallet, API key, catalog; extracts resource_id from URL
- **Why needed:** Single configuration source + request validation
- **Customization:** Edit wallet address, API key, add/remove resources from catalog

**Node 2: Has Payment?**
- **Type:** IF node (conditional)
- **Purpose:** Route based on payment presence
- **What it does:** Checks if `x-payment` header exists in request
- **Why needed:** First request has no payment (return 402), second request has payment (verify and deliver)
- **Customization:** None (standard x402 protocol flow)

**Node 3: Generate 402** (NO payment path)
- **Type:** Function node (JavaScript)
- **Purpose:** Create HTTP 402 Payment Required response
- **What it does:** Builds JSON response with payment details (payTo, amount, token, chain, resource info)
- **Why needed:** Tell buyer how to pay (wallet address, amount, blockchain)
- **Customization:** Add custom fields (merchant name, payment deadline, discount codes)

**Node 4: Send 402**
- **Type:** Respond to Webhook node
- **Purpose:** Return 402 response to buyer
- **What it does:** Sends HTTP 402 status code with payment requirements JSON
- **Why needed:** Standard HTTP response to N8N webhook
- **Customization:** Change status code for testing (use 200 with special field)

**Node 5: Verify Payment** (YES payment path)
- **Type:** HTTP Request node (GET to AgentGatePay API)
- **Purpose:** Verify blockchain transaction with AgentGatePay
- **What it does:** Calls `/v1/payments/verify/{tx_hash}` with seller API key
- **Why needed:** Confirm payment is real, correct amount, correct recipient
- **Customization:** Add custom verification logic (check buyer reputation, payment history)

**Node 6: Validate Payment**
- **Type:** Function node (JavaScript)
- **Purpose:** Check verification result details
- **What it does:** Validates `verified === true`, checks amount matches price, checks recipient is seller wallet
- **Why needed:** Extra validation beyond AgentGatePay verification
- **Customization:** Add business logic (minimum amount, allowed tokens, buyer whitelist)

**Node 6B: Route: Valid?**
- **Type:** IF node (conditional)
- **Purpose:** Route to delivery or error based on validation
- **What it does:** Checks validation result from Node 6
- **Why needed:** Separate paths for valid payments (deliver) vs invalid (error)
- **Customization:** None (standard routing pattern)

**Node 7: Deliver Resource** (YES valid payment)
- **Type:** Function node (JavaScript)
- **Purpose:** Prepare resource data for delivery
- **What it does:** Retrieves resource from catalog by ID, formats response
- **Why needed:** Return actual resource data to buyer
- **Customization:** Load from database, generate dynamic content, call external API

**Node 8: Send 200 OK**
- **Type:** Respond to Webhook node
- **Purpose:** Return success response with resource
- **What it does:** Sends HTTP 200 status code with resource data JSON
- **Why needed:** Standard successful HTTP response
- **Customization:** Add headers (content-type, cache-control), format data (JSON/XML/CSV)

**Node 9: Send Error** (NO invalid payment)
- **Type:** Respond to Webhook node
- **Purpose:** Return error response
- **What it does:** Sends HTTP 400/403 status code with error message
- **Why needed:** Inform buyer why payment was rejected
- **Customization:** Add detailed error codes, suggest resolution steps

---

### Installation

1. **Import Template**
   - Open N8N workflow editor
   - Import JSON file: `💲Seller Resource API - CLIENT TEMPLATE.json`
   - Workflow imports with webhook configured

2. **Activate Workflow**
   - Toggle "Active" switch in top-right
   - Workflow begins listening for requests

3. **Copy Webhook URL**
   - Click Node "📡 GET /resource/{id}"
   - Copy Production URL
   - Format: `https://your-n8n.app.n8n.cloud/webhook/{path}/resource/{resourceId}`
   - Provide this URL to buyer agents

### Configuration

**Edit Node 1 "Parse Request":**

```javascript
const SELLER_CONFIG = {
  merchant: {
    name: "DataBot Pro",
    company: "MarketInsights AI Ltd.",
    email: "seller-merchant@yourcompany.com",  // Seller identifier

    wallet_address: "0x742d35...",            // REQUIRED: Your Base wallet address
    api_key: "pk_live_def456..."              // REQUIRED: AgentGatePay API key (seller account)
  },

  payment: {
    token: "USDC",                            // Accepted payment token
    chain: "base"                              // Accepted blockchain
  },

  catalog: {
    "saas-competitors-2025": {
      id: "saas-competitors-2025",
      title: "Top 5 SaaS Competitors Analysis 2025",
      price_usd: 0.01,                        // Resource price in USD
      preview: "Salesforce (19.8%), HubSpot (8.5%)..."
    }
    // Add more resources here
  }
};
```

**Required Configuration Values:**
- `merchant.wallet_address` - Your Base network wallet (where you receive payments)
- `merchant.api_key` - API key from seller AgentGatePay account signup

**Optional: Add More Resources**

```javascript
catalog: {
  "resource-1": {
    id: "resource-1",
    title: "First Resource",
    price_usd: 0.05,
    preview: "Preview text..."
  },
  "resource-2": {
    id: "resource-2",
    title: "Second Resource",
    price_usd: 0.10,
    preview: "Preview text..."
  }
}
```

**Edit Node 7 "Deliver Resource"** to customize resource data returned to buyer.

### Execution Flow

**Request 1: No Payment (Returns 402)**
1. Buyer requests resource without payment header
2. Workflow generates 402 Payment Required response
3. Response includes:
   - Seller wallet address (`payTo`)
   - Payment amount in atomic units (`amount`)
   - Token symbol (`token`)
   - Blockchain network (`chain`)
   - Resource details (id, title, preview)
4. Buyer receives payment requirements

**Request 2: With Payment (Verifies and Delivers)**
1. Buyer requests resource with payment header (`x-payment: {tx_hash}`)
2. Workflow extracts transaction hash
3. Calls AgentGatePay verification API
4. Gateway verifies transaction on blockchain:
   - Transaction exists and succeeded
   - Correct recipient (seller wallet)
   - Correct amount (resource price)
   - Correct token contract
5. If valid: Deliver resource data
6. If invalid: Return error with details

### 402 Payment Required Response Format

```json
{
  "statusCode": 402,
  "message": "Payment Required",
  "protocol": "x402",
  "payTo": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEbB",
  "amount": "10000",
  "token": "USDC",
  "chain": "base",
  "priceUsd": "0.01",
  "nonce": "nonce_1234567890_abc123",
  "resource": {
    "id": "saas-competitors-2025",
    "title": "Top 5 SaaS Competitors Analysis 2025",
    "preview": "Salesforce (19.8%)..."
  },
  "merchant": {
    "name": "DataBot Pro",
    "email": "seller@example.com"
  },
  "instructions": [
    "1. Send 10000 USDC to 0x742d35...",
    "2. Wait for confirmation",
    "3. Retry with header: x-payment: {tx_hash}"
  ]
}
```

---

## Monitoring Workflows

### Buyer Monitoring Dashboard

**Template File:** `/n8n-demo-mcp/New/📊 Buyer Monitoring - MANUAL RUN.json`

**Purpose:** Track buyer agent spending, mandate budget, and transaction history.

**Features:**
- Mandate budget status (remaining, spent, utilization percentage)
- Transaction list with details (timestamp, amount, recipient, tx_hash)
- Spending analytics (total, count, average)
- Budget alerts (when remaining < threshold)

**Configuration:**
- Edit Node 1: Set buyer wallet address and AgentGatePay API key
- Execute manually or schedule (e.g., daily at 9am)
- View results in Node output or send to Slack/email

**Technical Note (Nov 19, 2025):**
Buyer monitoring is powered by the **PayerIndex Global Secondary Index** on the Charges DynamoDB table. This index enables efficient querying of all payments made by a specific buyer wallet address, sorted by timestamp. Prior to November 19, 2025, only seller monitoring was supported (via ReceiverIndex). The addition of PayerIndex completed the bidirectional monitoring capability.

### Seller Monitoring Dashboard

**Template File:** `/n8n-demo-mcp/New/💲 Seller Monitoring - MANUAL RUN.json`

**Purpose:** Track seller revenue, payments received, and customer analytics.

**Features:**
- Revenue summary (total, count, average per payment)
- Revenue by time period (today, week, month)
- Top payers list (by total amount)
- Revenue by chain/token distribution
- Recent transactions list

**Configuration:**
- Edit Node 1: Set seller wallet address and AgentGatePay API key
- Execute manually or schedule
- View results or send reports

---

## Testing

### Test Seller API

**Test 1: Verify 402 Response**

```bash
curl -i https://your-n8n.app.n8n.cloud/webhook/seller-api/resource/saas-competitors-2025
```

Expected: HTTP 402 with payment details in JSON body

**Test 2: Test Payment Verification**

```bash
curl -i -H "x-payment: 0xabc123..." \
  https://your-n8n.app.n8n.cloud/webhook/seller-api/resource/saas-competitors-2025
```

Expected: HTTP 200 with resource data (if tx_hash valid) or HTTP 400 (if invalid)

### Test Buyer Agent

**Execution Steps:**
1. Ensure seller workflow is active
2. Configure buyer workflow with seller webhook URL
3. Execute buyer workflow (click "Execute Workflow")
4. Monitor execution:
   - Node 2: Should retrieve or create mandate
   - Node 9: Should receive 402 from seller
   - Node 10: Should sign payment via Render/Railway
   - Node 12: Should submit payment to AgentGatePay
   - Node 13: Should receive resource from seller
5. Check Data Table: Should contain exactly 1 row with mandate token

**Verify on Blockchain:**
- Copy tx_hash from Node 11 output
- Visit: https://basescan.org/tx/{tx_hash}
- Verify:
  - Status: Success
  - From: Buyer wallet
  - To: USDC contract
  - Function: transfer(address,uint256)
  - Recipient: Seller wallet
  - Amount: Correct USDC atomic units

---

## Troubleshooting

### Buyer Workflow Issues

**Error: "Data table not found"**
- Cause: Data Table not created or not linked to nodes
- Fix: Create `AgentPay_Mandates` table, re-select in Node 2 and Node 7

**Error: "Configuration Required"**
- Cause: Placeholder values not replaced in Node 1
- Fix: Edit Node 1, replace all fields marked "REQUIRED"

**Error: "Cannot connect to seller"**
- Cause: Seller workflow not active or wrong URL
- Fix: Activate seller workflow, copy correct webhook URL

**Error: "Render signing failed"**
- Cause: Transaction signing service down or misconfigured
- Fix: Check Railway/Render deployment status, verify environment variables

**Error: "Mandate expired"**
- Cause: Mandate TTL exceeded or budget exhausted
- Fix: Delete mandate row from Data Table, execute workflow to create new mandate

### Seller Workflow Issues

**Error: "Seller configuration incomplete"**
- Cause: Node 1 configuration incomplete
- Fix: Replace wallet_address and api_key in Node 1

**Error: "Payment verification failed"**
- Cause: Invalid transaction or wrong recipient
- Fix: Check tx_hash on block explorer, verify wallet address configuration

**Error: "Wrong amount"**
- Cause: Payment amount doesn't match resource price
- Fix: Verify resource price in Node 1 catalog matches buyer expectation

### General Issues

**Workflow not receiving requests**
- Check workflow is Active (toggle in top-right)
- Verify webhook URL is accessible (test with curl)

**Blockchain transaction not confirming**
- Network congestion (wait 30-60 seconds)
- Insufficient gas (buyer needs ETH for gas)
- Wrong network (verify chain configuration matches wallet)

---

## Production Deployment

### Pre-Production Checklist

- [ ] Both buyer and seller AgentGatePay accounts created
- [ ] Transaction signing service deployed and tested
- [ ] Buyer workflow configured and tested on testnet
- [ ] Seller workflow configured and tested
- [ ] Data Table created and linked
- [ ] Webhook URLs accessible from internet
- [ ] Wallets funded (USDC + ETH for gas)
- [ ] Monitoring workflows configured
- [ ] Error handling tested (invalid payments, network failures)

### Mainnet Configuration

**Switch from Testnet to Mainnet:**
1. Update RPC URLs in configurations (if using custom RPCs)
2. Verify wallet addresses are mainnet addresses
3. Fund wallets with mainnet USDC and ETH
4. Test with small amount first (e.g., $0.01)

**Security Recommendations:**
- Use separate wallets for agents (not your main wallet)
- Set reasonable mandate budgets ($100-$1000)
- Monitor spending daily
- Enable webhook authentication (add API key validation in seller workflow)
- Store private keys securely (use hardware wallet for high-value transactions)

### Scaling Considerations

**N8N Execution Limits:**
- N8N Cloud Free: 5,000 executions/month
- N8N Cloud Starter: 100,000 executions/month
- Self-hosted: Unlimited executions

**Blockchain Limits:**
- Base network: ~50 TPS, no practical limit for agent payments
- Transaction confirmation: ~2 seconds on Base
- Gas costs: ~$0.01 per transaction on Base

**AgentGatePay Rate Limits:**
- With API key: 100 requests/minute
- MCP endpoint: Same limits apply

**For High Volume (>1000 payments/day):**
- Use multiple buyer agents (distribute load)
- Implement queue system for payment requests
- Monitor blockchain gas prices (adjust retry logic)
- Consider multiple seller instances (load balancing)

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                         BUYER AGENT                          │
│                      (N8N Workflow)                          │
│                                                              │
│  1. Load Config                                             │
│  2. Get/Create Mandate (Data Table + MCP API)              │
│  3. Request Resource (Seller API) ────────┐                │
│  4. Sign Payment (Render/Railway) ────────┼────┐           │
│  5. Submit Proof (MCP API)                │    │           │
│  6. Receive Resource (Seller API) ────────┼────┼───┐       │
│                                           │    │   │       │
└───────────────────────────────────────────┼────┼───┼───────┘
                                           │    │   │
                ┌──────────────────────────┘    │   │
                ▼                               │   │
┌──────────────────────────────────────────────┼───┼───────────┐
│                     SELLER API                │   │           │
│                  (N8N Workflow)               │   │           │
│                                               │   │           │
│  Webhook: GET /resource/{id}                 │   │           │
│  1. Parse request ◀──────────────────────────┘   │           │
│  2. If no payment: Return 402                    │           │
│  3. If payment: Verify (AgentGatePay API)        │           │
│  4. Deliver resource ◀───────────────────────────┘           │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                                               │
                                               │ Verify payment
                                               ▼
┌──────────────────────────────────────────────────────────────┐
│                   AGENTGATEPAY GATEWAY                       │
│                  (Lambda + DynamoDB)                         │
│                                                              │
│  - Issue/verify mandates (AP2 protocol)                     │
│  - Verify blockchain transactions                           │
│  - Track mandate budgets                                    │
│  - Audit logging                                            │
│  - Rate limiting                                            │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                                               │
                ┌──────────────────────────────┤
                │                              │
                ▼                              ▼
┌────────────────────────────┐   ┌────────────────────────────┐
│  TRANSACTION SIGNING       │   │      BLOCKCHAIN            │
│  (Render/Railway)          │   │      (Base Network)        │
│                            │   │                            │
│  - Stores buyer private    │   │  - USDC contract           │
│    key (encrypted)         │   │  - Transaction records     │
│  - Signs transactions      │   │  - Immutable verification  │
│  - Broadcasts to chain     │───▶│                            │
│  - Returns tx_hash         │   │                            │
└────────────────────────────┘   └────────────────────────────┘
```

---

## Complete API Reference

### MCP Protocol Overview

**MCP (Model Context Protocol)** is a standard protocol that enables AI agents to call external tools. AgentGatePay exposes **15 MCP tools** that provide 100% feature parity with the REST API.

**Base URL:** `https://mcp.agentgatepay.com` (or `https://api.agentgatepay.com/mcp`)

**Protocol:** JSON-RPC 2.0

**Authentication:** Include `x-api-key` header for authenticated endpoints

---

### MCP Tools Reference (All 15 Tools)

#### Category 1: Core Payment Flow (4 tools)

**1. agentpay_issue_mandate**
Issue an AP2 mandate for delegated spending authority.

**Request:**
```json
POST https://mcp.agentgatepay.com
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "agentpay_issue_mandate",
    "arguments": {
      "subject": "agent-worker-1",
      "budget_usd": 100.0,
      "scope": "resource.read,payment.execute",
      "ttl_minutes": 10080
    }
  }
}
Headers: x-api-key: YOUR_API_KEY
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "mandate_id": "mandate_abc123",
    "mandate_token": "eyJhbGciOiJFZERTQSIsInR5cCI6IkFQMi1WREMifQ...",
    "issued_at": 1705881600,
    "expires_at": 1706486400,
    "budget_usd": "100.0",
    "scope": "resource.read,payment.execute"
  }
}
```

---

**2. agentpay_verify_mandate**
Verify an AP2 mandate token is valid.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "agentpay_verify_mandate",
    "arguments": {
      "mandate_token": "eyJhbGciOiJFZERTQSIsInR5cCI6IkFQMi1WREMifQ..."
    }
  }
}
Headers: x-api-key: YOUR_API_KEY
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "valid": true,
    "payload": {
      "sub": "agent-worker-1",
      "budget_usd": "100.0",
      "budget_remaining": "99.99",
      "scope": "resource.read,payment.execute",
      "exp": 1706486400
    }
  }
}
```

---

**3. agentpay_create_payment**
Create an x402 payment requirement (for sellers).

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "agentpay_create_payment",
    "arguments": {
      "amount_usd": "0.01",
      "resource_path": "/api/premium-content"
    }
  }
}
Headers: x-api-key: YOUR_API_KEY
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "x402_version": 1,
    "accepts": [{
      "network": "base",
      "max_amount_required": "10000",
      "pay_to": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
      "nonce": "abc123..."
    }]
  }
}
```

---

**4. agentpay_submit_payment**
Submit x402 payment proof and access protected resource.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "tools/call",
  "params": {
    "name": "agentpay_submit_payment",
    "arguments": {
      "tx_hash": "0xABC123...",
      "tx_hash_commission": "0xDEF456...",
      "mandate_token": "eyJhbGciOiJFZERTQSIsInR5cCI6IkFQMi1WREMifQ...",
      "chain": "base",
      "token": "USDC",
      "price_usd": "0.01"
    }
  }
}
Headers: x-api-key: YOUR_API_KEY
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "result": {
    "success": true,
    "charge_id": "charge_xyz789",
    "verified": true,
    "amount_usd": "0.01",
    "mandate_budget_remaining": "99.99"
  }
}
```

---

#### Category 2: Payment History & Analytics (2 tools)

**5. agentpay_get_payment_history**
Get payment history for authenticated user.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "method": "tools/call",
  "params": {
    "name": "agentpay_get_payment_history",
    "arguments": {
      "limit": 50,
      "start_time": 1705881600,
      "end_time": 1706486400
    }
  }
}
Headers: x-api-key: YOUR_API_KEY (REQUIRED)
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "result": {
    "payments": [
      {
        "id": "charge_abc",
        "tx_hash": "0x...",
        "amount_usd": "0.01",
        "token": "USDC",
        "chain": "base",
        "timestamp": 1705885200,
        "status": "completed"
      }
    ],
    "total": 10,
    "page": 1
  }
}
```

---

**6. agentpay_get_analytics**
Get spending/revenue analytics for authenticated user.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 6,
  "method": "tools/call",
  "params": {
    "name": "agentpay_get_analytics",
    "arguments": {
      "period": "30d"
    }
  }
}
Headers: x-api-key: YOUR_API_KEY (REQUIRED)
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 6,
  "result": {
    "total_volume_usd": "125.50",
    "transaction_count": 1255,
    "average_transaction_usd": "0.10",
    "unique_counterparties": 42,
    "period": "30d"
  }
}
```

---

#### Category 3: Payment Verification (1 tool)

**7. agentpay_verify_payment**
Verify a blockchain payment transaction (public, no auth required).

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "method": "tools/call",
  "params": {
    "name": "agentpay_verify_payment",
    "arguments": {
      "tx_hash": "0xABC123..."
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "result": {
    "verified": true,
    "tx_hash": "0xABC123...",
    "from_address": "0xBuyerWallet...",
    "to_address": "0xSellerWallet...",
    "amount_usd": "0.01",
    "token": "USDC",
    "chain": "base",
    "timestamp": 1705885200,
    "block_number": 12345678
  }
}
```

---

#### Category 4: User Account Management (3 tools)

**8. agentpay_signup**
Create new user account (returns auto-generated API key).

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 8,
  "method": "tools/call",
  "params": {
    "name": "agentpay_signup",
    "arguments": {
      "email": "user@example.com",
      "password": "SecurePass123!",
      "user_type": "agent"
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 8,
  "result": {
    "user_id": "user_abc123",
    "email": "user@example.com",
    "user_type": "agent",
    "api_key": "pk_live_xyz789...",
    "created_at": 1705881600,
    "message": "Save API key now - shown only once!"
  }
}
```

---

**9. agentpay_get_user_info**
Get current user account information.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 9,
  "method": "tools/call",
  "params": {
    "name": "agentpay_get_user_info",
    "arguments": {}
  }
}
Headers: x-api-key: YOUR_API_KEY (REQUIRED)
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 9,
  "result": {
    "user_id": "user_abc123",
    "email": "user@example.com",
    "user_type": "agent",
    "wallets": [
      {
        "chain": "base",
        "address": "0x742d35..."
      }
    ],
    "created_at": 1705881600
  }
}
```

---

**10. agentpay_add_wallet**
Add blockchain wallet address to account.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 10,
  "method": "tools/call",
  "params": {
    "name": "agentpay_add_wallet",
    "arguments": {
      "chain": "base",
      "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
    }
  }
}
Headers: x-api-key: YOUR_API_KEY (REQUIRED)
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 10,
  "result": {
    "success": true,
    "wallet": {
      "chain": "base",
      "address": "0x742d35...",
      "added_at": 1705881600
    }
  }
}
```

---

#### Category 5: API Key Management (3 tools)

**11. agentpay_create_api_key**
Create new API key for programmatic access.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 11,
  "method": "tools/call",
  "params": {
    "name": "agentpay_create_api_key",
    "arguments": {
      "name": "Production Server"
    }
  }
}
Headers: x-api-key: YOUR_EXISTING_API_KEY (REQUIRED)
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 11,
  "result": {
    "key_id": "key_abc123",
    "api_key": "pk_live_newkey789...",
    "name": "Production Server",
    "created_at": 1705881600,
    "message": "Save API key now - shown only once!"
  }
}
```

**Note:** Limit of 10 API keys per day per user.

---

**12. agentpay_list_api_keys**
List all API keys for current user.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 12,
  "method": "tools/call",
  "params": {
    "name": "agentpay_list_api_keys",
    "arguments": {}
  }
}
Headers: x-api-key: YOUR_API_KEY (REQUIRED)
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 12,
  "result": {
    "api_keys": [
      {
        "key_id": "key_abc123",
        "name": "Production Server",
        "key_preview": "pk_live_xyz789...",
        "created_at": 1705881600,
        "last_used": 1705968000,
        "status": "active"
      }
    ],
    "total": 3
  }
}
```

---

**13. agentpay_revoke_api_key**
Revoke an API key (soft delete).

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 13,
  "method": "tools/call",
  "params": {
    "name": "agentpay_revoke_api_key",
    "arguments": {
      "key_id": "key_abc123"
    }
  }
}
Headers: x-api-key: YOUR_API_KEY (REQUIRED)
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 13,
  "result": {
    "success": true,
    "key_id": "key_abc123",
    "revoked_at": 1705881600,
    "message": "API key revoked successfully"
  }
}
```

---

#### Category 6: Audit & Monitoring (2 tools)

**14. agentpay_get_audit_logs**
Get audit logs for current user.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 14,
  "method": "tools/call",
  "params": {
    "name": "agentpay_get_audit_logs",
    "arguments": {
      "event_type": "payment_completed",
      "limit": 50,
      "start_time": 1705881600,
      "end_time": 1706486400
    }
  }
}
Headers: x-api-key: YOUR_API_KEY (REQUIRED)
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 14,
  "result": {
    "logs": [
      {
        "id": "audit_abc123",
        "timestamp": 1705885200,
        "event_type": "payment_completed",
        "client_id": "user@example.com",
        "details": {
          "tx_hash": "0x...",
          "amount_usd": "0.01"
        }
      }
    ],
    "total": 125,
    "page": 1
  }
}
```

---

**15. agentpay_get_system_health**
Get system health and status information (public, no auth).

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 15,
  "method": "tools/call",
  "params": {
    "name": "agentpay_get_system_health",
    "arguments": {}
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 15,
  "result": {
    "status": "healthy",
    "version": "1.0.0",
    "uptime_seconds": 3600,
    "components": {
      "ap2": "operational",
      "x402": "operational",
      "aif": "operational",
      "audit": "operational",
      "blockchain_rpc": "operational"
    }
  }
}
```

---

### REST API Endpoints Reference

**Base URL:** `https://api.agentgatepay.com`

**Authentication:** Include `x-api-key` header (except public endpoints)

---

#### User Management Endpoints

**POST /v1/users/signup**
Create new user account.

```bash
curl -X POST https://api.agentgatepay.com/v1/users/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "user_type": "agent"
  }'
```

**GET /v1/users/me**
Get current user information (requires API key).

```bash
curl https://api.agentgatepay.com/v1/users/me \
  -H "x-api-key: YOUR_API_KEY"
```

**POST /v1/users/wallets/add**
Add blockchain wallet (requires API key).

```bash
curl -X POST https://api.agentgatepay.com/v1/users/wallets/add \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{
    "wallet_address": "0x742d35..."
  }'
```

---

#### Mandate Endpoints

**POST /mandates/issue**
Issue AP2 mandate.

```bash
curl -X POST https://api.agentgatepay.com/mandates/issue \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{
    "subject": "agent-worker-1",
    "budget_usd": 100.0,
    "scope": "resource.read,payment.execute",
    "ttl_minutes": 10080
  }'
```

**POST /mandates/verify**
Verify mandate token.

```bash
curl -X POST https://api.agentgatepay.com/mandates/verify \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{
    "mandate_token": "eyJhbGciOiJFZERTQSIsInR5cCI6IkFQMi1WREMifQ..."
  }'
```

---

#### Payment Verification Endpoints

**GET /v1/payments/verify/{tx_hash}**
Verify blockchain payment (public, no auth required).

```bash
curl https://api.agentgatepay.com/v1/payments/verify/0xABC123...
```

**GET /v1/payments/status/{tx_hash}**
Get payment status (public, no auth required).

```bash
curl https://api.agentgatepay.com/v1/payments/status/0xABC123...
```

**GET /v1/payments/list**
List payments for merchant wallet (requires API key).

```bash
curl https://api.agentgatepay.com/v1/payments/list \
  -H "x-api-key: YOUR_API_KEY"
```

---

#### Webhook Endpoints

**POST /v1/webhooks/configure**
Configure payment notification webhook (requires API key).

```bash
curl -X POST https://api.agentgatepay.com/v1/webhooks/configure \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{
    "url": "https://your-server.com/webhook",
    "events": ["payment.completed", "payment.failed"],
    "secret": "your-webhook-secret"
  }'
```

**GET /v1/webhooks/list**
List all webhooks (requires API key).

```bash
curl https://api.agentgatepay.com/v1/webhooks/list \
  -H "x-api-key: YOUR_API_KEY"
```

**POST /v1/webhooks/test**
Test webhook delivery (requires API key).

```bash
curl -X POST https://api.agentgatepay.com/v1/webhooks/test \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{"webhook_id": "webhook_abc123"}'
```

**DELETE /v1/webhooks/{webhook_id}**
Delete webhook (requires API key).

```bash
curl -X DELETE https://api.agentgatepay.com/v1/webhooks/webhook_abc123 \
  -H "x-api-key: YOUR_API_KEY"
```

---

#### Analytics Endpoints

**GET /v1/analytics/public**
Get public aggregate analytics (no auth required, 15-min cache).

```bash
curl https://api.agentgatepay.com/v1/analytics/public
```

**GET /v1/analytics/me**
Get user-specific analytics (requires API key).

```bash
curl https://api.agentgatepay.com/v1/analytics/me \
  -H "x-api-key: YOUR_API_KEY"
```

**GET /v1/merchant/revenue**
Get merchant revenue analytics (requires API key).

```bash
curl https://api.agentgatepay.com/v1/merchant/revenue \
  -H "x-api-key: YOUR_API_KEY"
```

---

#### API Key Management Endpoints

**POST /v1/api-keys/create**
Create new API key (requires existing API key).

```bash
curl -X POST https://api.agentgatepay.com/v1/api-keys/create \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{
    "name": "Production Server"
  }'
```

**GET /v1/api-keys/list**
List all API keys (requires API key).

```bash
curl https://api.agentgatepay.com/v1/api-keys/list \
  -H "x-api-key: YOUR_API_KEY"
```

**POST /v1/api-keys/revoke**
Revoke API key (requires API key).

```bash
curl -X POST https://api.agentgatepay.com/v1/api-keys/revoke \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{
    "key_id": "key_abc123"
  }'
```

---

#### Audit Log Endpoints (All require authentication)

**GET /audit/logs**
Get audit logs for current user.

```bash
curl "https://api.agentgatepay.com/audit/logs?event_type=payment_completed&limit=50" \
  -H "x-api-key: YOUR_API_KEY"
```

**GET /audit/stats**
Get audit statistics summary.

```bash
curl https://api.agentgatepay.com/audit/stats \
  -H "x-api-key: YOUR_API_KEY"
```

**GET /audit/logs** (by transaction - use event_type filter)
Get payment logs by filtering for specific transactions.

```bash
# Query recent payments with event type filter
curl "https://api.agentgatepay.com/audit/logs?event_type=x402_payment_settled&hours=24" \
  -H "x-api-key: YOUR_API_KEY"

# Verify specific payment by tx_hash
curl "https://api.agentgatepay.com/v1/payments/verify/0xABC123..." \
  -H "x-api-key: YOUR_API_KEY"
```

---

#### System Endpoints

**GET /health**
Health check (public, no auth).

```bash
curl https://api.agentgatepay.com/health
```

**GET /dashboard**
Analytics dashboard HTML (public, no auth).

```bash
open https://api.agentgatepay.com/dashboard
```

---

### Rate Limits

| User Type | Rate Limit | Window |
|-----------|-----------|---------|
| **With API Key** | 100 requests | per minute |
| **No API Key** | 20 requests | per minute |
| **Signup** | 5 requests | per hour (per IP) |
| **API Key Creation** | 10 keys | per day |

**Headers Returned:**
- `X-RateLimit-Limit` - Maximum requests per window
- `X-RateLimit-Remaining` - Requests remaining
- `X-RateLimit-Reset` - Unix timestamp when window resets
- `Retry-After` - Seconds to wait if rate limited (429 response)

---

## API Reference

### AgentGatePay MCP Endpoints (Legacy Section - See Complete Reference Above)

**Issue Mandate:**
```
POST https://mcp.agentgatepay.com
Body: {
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "agentpay_issue_mandate",
    "arguments": {
      "subject": "buyer@example.com",
      "budget_usd": 100,
      "scope": "resource.read payment.execute",
      "ttl_minutes": 10080
    }
  }
}
Headers: x-api-key: {buyer_api_key}
```

**Verify Mandate:**
```
POST https://mcp.agentgatepay.com
Body: {
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "agentpay_verify_mandate",
    "arguments": {
      "mandate_token": "{mandate_token}"
    }
  }
}
Headers: x-api-key: {buyer_api_key}
```

**Submit Payment:**
```
POST https://mcp.agentgatepay.com
Body: {
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "agentpay_submit_payment",
    "arguments": {
      "mandate_token": "{mandate_token}",
      "tx_hash": "0x...",
      "tx_hash_commission": "0x...",
      "chain": "base",
      "token": "USDC",
      "price_usd": "0.01"
    }
  }
}
Headers: x-api-key: {buyer_api_key}
```

### AgentGatePay REST Endpoints

**Verify Payment (Seller):**
```
GET https://api.agentgatepay.com/v1/payments/verify/{tx_hash}
Headers: x-api-key: {seller_api_key}

Response: {
  "verified": true,
  "tx_hash": "0x...",
  "from_address": "0x...",
  "to_address": "0x...",
  "amount_usd": 0.01,
  "token": "USDC",
  "chain": "base",
  "timestamp": "2025-01-21T12:00:00Z"
}
```

### Transaction Signing Service Endpoints

**Sign Payment (Render/Railway):**
```
POST https://your-app.railway.app/sign-payment
Body: {
  "merchant_address": "0x...",
  "total_amount": "10000",
  "token": "USDC",
  "chain": "base"
}

Response: {
  "success": true,
  "tx_hash": "0x...",
  "tx_hash_commission": "0x...",
  "from": "0x...",
  "commission_address": "0x...",
  "total_usd": 0.01,
  "merchant_usd": 0.00995,
  "commission_usd": 0.00005
}
```

---

## Support

**Documentation:**
- AgentGatePay API: https://docs.agentgatepay.com
- N8N Documentation: https://docs.n8n.io
- Base Network: https://docs.base.org

**Technical Support:**
- GitHub Issues: https://github.com/agentgatepay/agentgatepay-sdk/issues
- Email: support@agentgatepay.com

---

**License:** MIT
**Maintained by:** AgentGatePay Team

