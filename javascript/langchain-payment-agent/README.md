# AgentGatePay + LangChain.js Integration

**Autonomous AI agent payments using blockchain and LangChain.js framework**

**Version:** 1.0 BETA
**Last Updated:** December 2025
**Node.js:** 18.0+
**LangChain.js:** 0.3.0+

> **⚠️ BETA VERSION**: These examples are currently in beta. We're actively adding features and improvements based on user feedback. Expect updates for enhanced functionality, additional framework integrations, improved error handling, and expanded multi-chain support.

[![Node.js 18+](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)
[![AgentGatePay SDK](https://img.shields.io/badge/agentgatepay--sdk-1.1.4+-blue.svg)](https://www.npmjs.com/package/agentgatepay-sdk)
[![LangChain.js](https://img.shields.io/badge/langchain-0.3.0+-orange.svg)](https://js.langchain.com/)

## Overview

This repository contains **10 complete TypeScript examples** demonstrating how to integrate AgentGatePay with LangChain.js for autonomous agent payments.

**🔄 Python vs JavaScript:** These examples are **1:1 ports** of the Python examples. Choose based on your tech stack:
- **JavaScript/TypeScript** - This repo (npm, Node.js, ethers.js)
- **Python** - See `/python/langchain-payment-agent` (pip, web3.py)

Both versions have **identical functionality** - same flows, same features, same logic.

### Examples Included

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
- **REST API version** - Uses published AgentGatePay SDK (v1.1.4+) from npm
- **MCP version** - Uses AgentGatePay's 15 MCP tools (Model Context Protocol)

**Multi-Chain/Token Support** - All examples support **4 chains** (Base, Ethereum, Polygon, Arbitrum) and **3 tokens** (USDC, USDT, DAI) with configuration via .env file.

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

### LangChain.js Integration

- **Agent framework**: ReAct agents with payment tools
- **Tool abstraction**: Clean separation of payment logic
- **Error handling**: Automatic retry and graceful degradation
- **State management**: Mandate and payment tracking

## 🚀 Quick Start (60 Seconds)

```bash
# 1. Clone and install
git clone https://github.com/AgentGatePay/agentgatepay-examples.git
cd agentgatepay-examples/javascript/langchain-payment-agent
npm install

# 2. Configure (copy .env.example and edit)
cp .env.example .env
nano .env  # Add your API keys and wallet addresses

# 3. Run first example
npm run example:1a
```

**Need API keys?** Create 2 accounts (buyer + seller):
```bash
# Buyer account
curl -X POST https://api.agentgatepay.com/v1/users/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"buyer@example.com","password":"YourPass123!","user_type":"agent"}'

# Seller account
curl -X POST https://api.agentgatepay.com/v1/users/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"seller@example.com","password":"YourPass123!","user_type":"merchant"}'
```
**Save the API keys** from responses (shown only once): `pk_live_...`

---

## Complete Setup Guide

### Prerequisites

1. **Node.js 18+**
2. **AgentGatePay accounts** (see Quick Start section above for signup commands)

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

   Examples use **OpenAI** by default, but any LangChain.js-supported LLM works (Anthropic Claude, Google Gemini, local models, etc.). Configure your preferred LLM provider's API key in `.env` as `OPENAI_API_KEY` (or rename variable and update model initialization in scripts for other providers).

### Installation

```bash
# Clone repository
git clone https://github.com/AgentGatePay/agentgatepay-examples.git
cd agentgatepay-examples/javascript/langchain-payment-agent

# Verify Node.js version (must be 18.0 or higher)
node --version  # Should show v18.0.0 or higher

# If you need to upgrade Node.js, use nvm (Node Version Manager):
# curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
# nvm install 18
# nvm use 18

# Install dependencies (includes TypeScript, tsx, ethers.js, LangChain.js)
npm install

# Optional: Build TypeScript to JavaScript (not required for running examples)
npm run build
```

**Note:** Examples use **tsx** to run TypeScript directly without pre-compilation. The `npm run build` command is optional - all examples work with `npm run example:*` commands.

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
npm run example:1a
```

**Note:** Examples use **$0.01 USDC** for testing. Private key in `.env` is suitable for development and testing with small amounts only.

---

**Examples 1b, 3b: External Signing Service (Production)**

Deploy a separate signing service to isolate private keys from application code.

**Option A: Docker (Local)**

```bash
docker pull agentgatepay/tx-signing-service:latest
docker run -d -p 3000:3000 --env-file .env.signing-service agentgatepay/tx-signing-service:latest
```

Add to `.env`: `TX_SIGNING_SERVICE=http://localhost:3000`

**Option B: Render (Cloud)**

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/AgentGatePay/TX)

Add to `.env`: `TX_SIGNING_SERVICE=https://your-service.onrender.com`

### Run Examples

```bash
# Example 1a: REST API + Local signing (basic)
npm run example:1a

# Example 1b: REST API + External TX signing (production)
npm run example:1b

# Example 2: Buyer/seller marketplace (REST API) - TWO TERMINALS
# Terminal 1: Start seller first
npm run example:2b

# Terminal 2: Then run buyer
npm run example:2a

# Example 3a: MCP + Local signing (basic)
npm run example:3a

# Example 3b: MCP + External TX signing (production)
npm run example:3b

# Example 4: Buyer/seller marketplace (MCP tools) - TWO TERMINALS
# Terminal 1: Start seller first
npm run example:4b

# Terminal 2: Then run buyer
npm run example:4a

# Example 5a: Buyer monitoring dashboard (SPENDING & BUDGETS)
npm run example:5a

# Example 5b: Seller monitoring dashboard (REVENUE & WEBHOOKS)
npm run example:5b
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
\*\* Ethereum speed depends on RPC provider quality. Premium RPCs (Alchemy/Infura) provide significantly faster verification.

**Important Notes:**
- USDT is NOT available on Base
- DAI uses 18 decimals (USDC/USDT use 6 decimals)
- Base recommended for lowest fees and fastest transactions

**To switch chains:** Just edit `.env` and restart the script:
```bash
# Change from Base to Ethereum with USDT
nano .env  # Edit PAYMENT_CHAIN=ethereum and PAYMENT_TOKEN=USDT
npm run example:1a
```

## Examples Overview

### Example 1a: Basic Payment Flow (REST API + Local Signing)

**File:** `examples/1a_api_basic_payment.ts`

Simple autonomous payment flow demonstrating the complete 3-step process:
1. **Issue Mandate**: Create AP2 mandate with $100 budget and budget tracking
2. **Sign Transactions**: Sign two blockchain transactions (merchant + commission)
3. **Submit to Gateway**: Submit payment proof to AgentGatePay for verification

**Uses:**
- AgentGatePay SDK (agentgatepay-sdk@^1.1.4) from npm
- ethers.js for blockchain signing
- LangChain.js agent framework

**Key Features:**
- Dynamic commission fetching from API
- Live budget tracking via mandate verification
- Complete end-to-end payment flow
- Base network for fast, low-cost transactions

---

### Example 2: Buyer/Seller Marketplace (REST API) ⭐ **SEPARATE SCRIPTS**

**Files:**
- `examples/2a_api_buyer_agent.ts` - Autonomous buyer agent
- `examples/2b_api_seller_agent.ts` - Resource seller API

**Complete marketplace interaction** (matches n8n workflow pattern):

**BUYER AGENT** (`2a_api_buyer_agent.ts`):
- **Autonomous** resource discovery from ANY seller
- Issues mandate with budget control
- Signs blockchain payment (2 TX: merchant + commission)
- Claims resource after payment

**SELLER AGENT** (`2b_api_seller_agent.ts`):
- **Independent** Express API service
- Provides resource catalog
- Returns 402 Payment Required
- Verifies payment via AgentGatePay API
- Delivers resource (200 OK)

**Flow:**
```
[SELLER] Start Express API (localhost:8000) → [SELLER] Wait for buyers
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
```

---

### Example 3a: Basic Payment Flow (MCP + Local Signing)

**File:** `examples/3a_mcp_basic_payment.ts`

MCP version of Example 1a, demonstrating the same payment flow using AgentGatePay's MCP tools instead of REST API.

**Flow:**
1. Issue mandate via `agentpay_issue_mandate` tool
2. Sign blockchain transactions (ethers.js - merchant + commission)
3. Submit payment and verify budget via `agentpay_submit_payment` + `agentpay_verify_mandate` (combined)

**MCP Advantages:**
- Native tool discovery (frameworks auto-list all 15 tools)
- Standardized JSON-RPC 2.0 protocol
- Future-proof (Anthropic-backed)
- Cleaner tool abstraction

---

### Example 4: Buyer/Seller Marketplace (MCP Tools) ⭐ **SEPARATE SCRIPTS**

**Files:**
- `examples/4a_mcp_buyer_agent.ts` - Autonomous buyer agent (MCP)
- `examples/4b_mcp_seller_agent.ts` - Resource seller API (MCP)

Same marketplace pattern as Example 2, but using MCP tools for mandate and payment operations.

---

### Examples 5a/5b: Buyer & Seller Monitoring Dashboards

**Files:**
- `examples/5a_monitoring_buyer.ts` - Buyer monitoring (spending, budgets, mandates)
- `examples/5b_monitoring_seller.ts` - Seller monitoring (revenue, webhooks, top buyers)

Standalone monitoring tools for tracking AgentGatePay payments - similar to n8n monitoring workflows but as TypeScript CLI tools.

---

## Architecture

### Payment Flow (Buyer/Seller Pattern)

```
┌─────────────────────────────────────────────────────────────┐
│ BUYER AGENT (LangChain.js)                                  │
│  - Issue mandate ($100 budget, 7 days TTL)                  │
│  - Discover resource from seller                            │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ SELLER AGENT (Express API)                                  │
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

## REST API vs MCP Comparison

### When to Use REST API

✅ **Advantages:**
- Universal compatibility (all frameworks)
- Published SDK with TypeScript types (npm install agentgatepay-sdk)
- Custom error handling
- ethers.js helpers built-in
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

---

## Troubleshooting

### JavaScript/TypeScript-Specific Issues

**Error: "Cannot find module 'agentgatepay-sdk'"**
```bash
# Solution: Install dependencies
npm install
```

**Error: "SyntaxError: Cannot use import statement outside a module"**
```bash
# Solution: Verify package.json has "type": "module"
grep '"type"' package.json  # Should show: "type": "module"

# If missing, the examples won't work. Re-clone the repository.
```

**Error: "TypeError: Class constructor ChatOpenAI cannot be invoked without 'new'"**
```bash
# Solution: Check Node.js version (must be 18+)
node --version  # Must show v18.0.0 or higher

# Upgrade if needed:
nvm install 18 && nvm use 18
```

**Error: "Module not found: Error: Can't resolve 'ethers'"**
```bash
# Solution: Install all dependencies
rm -rf node_modules package-lock.json
npm install
```

**TypeScript compilation errors with `npm run build`**
```bash
# Solution: TypeScript compilation is OPTIONAL - you don't need it!
# All examples run with tsx (TypeScript executor) via npm scripts:
npm run example:1a  # Works without building

# If you still want to compile TypeScript:
npx tsc --noEmit  # Check for errors without outputting files
```

**Error: "Warning: To load an ES module, set 'type': 'module'"**
- Solution: This is normal. The examples already use ES modules (`package.json` has `"type": "module"`).

**tsx vs ts-node**
- These examples use **tsx** (faster, ESM-native)
- If you prefer ts-node: `npx ts-node --esm examples/1a_api_basic_payment.ts`
- tsx is recommended for better performance and ESM compatibility

### Payment-Related Issues

**Error: "Mandate not found or expired" or "Invalid or expired mandate"**
- Solution: Mandate TTL is 7 days. Issue a new mandate or delete `.agentgatepay_mandates.json`.
- If error persists after creating a fresh mandate, delete `.agentgatepay_mandates.json` and restart the script to force a new mandate issuance.
```bash
# Delete cached mandate file
rm .agentgatepay_mandates.json
# Run example again (will create fresh mandate)
npm run example:1a
```

**Error: "Payment verification failed"**
- Solution: Wait 10-15 seconds for Base network confirmation, then retry.
- Check wallet has sufficient USDC balance: `ethers.utils.formatUnits(balance, 6)` for USDC.

**Error: "Insufficient gas for transaction"**
- Solution: Ensure buyer wallet has native token for gas:
  - Base: ETH (~$0.001 per TX)
  - Ethereum: ETH (~$3-10 per TX)
  - Polygon: MATIC (~$0.01 per TX)
  - Arbitrum: ETH (~$0.10 per TX)

**Error: "OpenAI API key not found"**
```bash
# Solution: Set OPENAI_API_KEY in .env file
echo 'OPENAI_API_KEY=sk-YOUR_KEY_HERE' >> .env
```

**Error: "Network connection timeout"**
- Solution: Check RPC URL in .env file. Try premium RPC (Alchemy/Infura) for Ethereum:
```bash
# In .env:
ETHEREUM_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY
```

### Debugging Tips

**Enable verbose logging**
```typescript
// Add to any example file:
console.log('Debug info:', JSON.stringify(data, null, 2));
```

**Check mandate storage**
```bash
# View saved mandates
cat .agentgatepay_mandates.json | jq .

# Clear all mandates
rm .agentgatepay_mandates.json
```

**Test API connectivity**
```bash
# Test AgentGatePay API
curl https://api.agentgatepay.com/health

# Test MCP endpoint
curl https://mcp.agentgatepay.com/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

---

## Testing

```bash
# Run examples (no build required - uses tsx)
npm run example:1a
npm run example:2a
npm run example:3a

# Test with different chains (override .env)
PAYMENT_CHAIN=polygon npm run example:1a
PAYMENT_TOKEN=USDT PAYMENT_CHAIN=ethereum npm run example:1a

# Test TypeScript compilation (optional)
npm run build  # Outputs to dist/ folder
```

---

## Project Structure

```
javascript/langchain-payment-agent/
├── examples/               # 10 TypeScript examples
│   ├── 1a_api_basic_payment.ts
│   ├── 1b_api_with_tx_service.ts
│   ├── 2a_api_buyer_agent.ts
│   ├── 2b_api_seller_agent.ts
│   ├── 3a_mcp_basic_payment.ts
│   ├── 3b_mcp_with_tx_service.ts
│   ├── 4a_mcp_buyer_agent.ts
│   ├── 4b_mcp_seller_agent.ts
│   ├── 5a_monitoring_buyer.ts
│   └── 5b_monitoring_seller.ts
├── utils/                  # Utility modules
│   ├── mandateStorage.ts   # Persistent mandate storage
│   └── index.ts            # Exports
├── chain_config.ts         # Multi-chain/token configuration
├── package.json            # Dependencies & npm scripts
├── tsconfig.json           # TypeScript configuration
├── .env.example            # Environment variable template
└── README.md               # This file
```

### Key Configuration Files

**package.json - npm Scripts**
```json
{
  "type": "module",  // Enable ES modules
  "scripts": {
    "build": "tsc",                    // Compile TypeScript (optional)
    "example:1a": "tsx examples/1a_api_basic_payment.ts",  // Run with tsx
    "example:2a": "tsx examples/2a_api_buyer_agent.ts",
    "example:5a": "tsx examples/5a_monitoring_buyer.ts"
  },
  "engines": {
    "node": ">=18.0.0"  // Minimum Node.js version
  }
}
```

**tsconfig.json - TypeScript Configuration**
```json
{
  "compilerOptions": {
    "target": "ES2022",           // Modern JavaScript features
    "module": "ES2022",           // ES modules (import/export)
    "moduleResolution": "node",   // Node.js module resolution
    "strict": true,               // Enable strict type checking
    "esModuleInterop": true,      // Better CommonJS compatibility
    "skipLibCheck": true,         // Faster compilation
    "outDir": "./dist"            // Output directory for build
  }
}
```

**Why ES Modules?**
- Modern import/export syntax (`import { ethers } from 'ethers'`)
- Better tree-shaking for smaller bundles
- Native Node.js support (18+)
- Required by LangChain.js and ethers.js v6

**Why TypeScript?**
- Type safety for blockchain operations (prevents $1M → $1B bugs)
- Better IDE autocomplete (ethers.js, AgentGatePay SDK)
- Catches errors at compile time
- Industry standard for crypto development

---

## Next Steps

1. **Try all examples** - Understand both API and MCP approaches, plus external signing and monitoring
2. **Modify examples** - Adapt to your use case
3. **Build your agent** - Create custom payment workflows

---

## Resources

- **AgentGatePay API**: https://api.agentgatepay.com
- **SDK Documentation**: https://github.com/AgentGatePay/agentgatepay-sdks
- **LangChain.js Docs**: https://js.langchain.com/
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

*Last updated: December 2025*
