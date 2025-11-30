# Quick Start Guide - AgentGatePay + LangChain

**Get your first autonomous agent payment running in 5 minutes.**

This guide assumes you have basic knowledge of Python and blockchain wallets. If you're completely new, start with Example 1 (basic payment) before trying more complex examples.

---

## Prerequisites Checklist

Before starting, gather these items:

- [ ] Python 3.12+ installed
- [ ] Git installed
- [ ] Wallet with USDC on Base network (~$1 worth)
- [ ] Wallet private key (for signing transactions)
- [ ] OpenAI API key (for LangChain LLM)

---

## Step 1: Get AgentGatePay API Keys (2 minutes)

You need **two accounts** for buyer/seller examples:

### Create Buyer Account

```bash
curl -X POST https://api.agentgatepay.com/v1/users/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "buyer@yourdomain.com",
    "password": "YourSecurePassword123!",
    "user_type": "agent"
  }'
```

**Save the API key** from the response (shown only once):
```json
{
  "api_key": "pk_live_abc123...",
  "user": {...}
}
```

### Create Seller Account

```bash
curl -X POST https://api.agentgatepay.com/v1/users/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "seller@yourdomain.com",
    "password": "YourSecurePassword123!",
    "user_type": "merchant"
  }'
```

**Save this API key too.**

---

## Step 2: Get Test USDC on Base (2 minutes)

### Option A: Use a Faucet (Testnet - Recommended for Testing)

1. Get Base Sepolia ETH: https://www.alchemy.com/faucets/base-sepolia
2. Get USDC on Base Sepolia: Use Uniswap or Aave faucets

**Note:** For testnet, change RPC URL in `.env` to Base Sepolia.

### Option B: Buy Real USDC (Mainnet - Production)

1. Buy ETH on Coinbase/Binance
2. Bridge to Base network via https://bridge.base.org
3. Swap ETH → USDC on https://app.uniswap.org (select Base network)
4. You need ~$1 USDC + ~$0.01 ETH for gas

---

## Step 3: Clone and Install (1 minute)

```bash
# Clone repository
git clone https://github.com/AgentGatePay/agentgatepay-examples.git
cd agentgatepay-examples/python/langchain-payment-agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Step 4: Choose Transaction Signing Method (Important!)

AgentGatePay requires blockchain transactions to be signed. You have 2 options:

### Option A: Local Signing (Quick Start - Development Only)

✅ **Best for:** Testing and learning
⚠️ **NOT recommended for production**

Private key stored in `.env` file. Used in examples 1-8.

**Setup:** Continue to Step 5 below (configure `.env` file)

### Option B: External Signing Service (Production Ready)

✅ **Recommended for production**
✅ **Private key NOT in application code**

**Quick Deploy (3 minutes):**

1. **Click Deploy Button:**
   [![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/AgentGatePay/TX)

2. **Add Environment Variables:**
   - `WALLET_PRIVATE_KEY`: Your private key (`0x...`)
   - `AGENTPAY_API_KEY`: Your API key (`pk_live_...`)

3. **Save Service URL:**
   Copy: `https://your-service.onrender.com`

4. **Use in Python:**
   ```python
   # Add to .env file
   TX_SIGNING_SERVICE=https://your-service.onrender.com

   # Run Example 9 (uses external signing)
   python examples/9_api_with_tx_service.py
   ```

**See:** [TX_SIGNING_OPTIONS.md](TX_SIGNING_OPTIONS.md) for all signing methods (Docker, Railway, self-hosted, etc.)

---

## Step 5: Configure Environment (1 minute)

```bash
# Copy template
cp .env.example .env

# Edit with your credentials
nano .env  # or use any text editor
```

**Fill in these values:**

```bash
# AgentGatePay
AGENTPAY_API_URL=https://api.agentgatepay.com
BUYER_API_KEY=pk_live_YOUR_BUYER_KEY_HERE
SELLER_API_KEY=pk_live_YOUR_SELLER_KEY_HERE

# Blockchain (Base Mainnet)
BASE_RPC_URL=https://mainnet.base.org
BUYER_PRIVATE_KEY=0xYOUR_64_CHAR_PRIVATE_KEY
BUYER_WALLET=0xYOUR_BUYER_WALLET_ADDRESS
SELLER_WALLET=0xYOUR_SELLER_WALLET_ADDRESS

# OpenAI
OPENAI_API_KEY=sk-YOUR_OPENAI_KEY

# Optional: For testing on Base Sepolia (testnet)
# BASE_RPC_URL=https://sepolia.base.org
```

**⚠️ Security Warning:**
- Never commit `.env` to git
- Never share your private key
- Use a separate wallet for testing (not your main wallet)
- **Local signing is for TESTING ONLY** - Use external signing service for production

**Production Users:** If you deployed a signing service in Step 4, also add:
```bash
# External Signing Service (Optional - for production)
TX_SIGNING_SERVICE=https://your-service.onrender.com
```

---

## Step 6: Run Your First Example (30 seconds)

### Example 1: Basic Payment

```bash
python examples/1_api_basic_payment.py
```

**Expected Output:**
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

**Verify on Blockchain:**
Open BaseScan and check your transaction:
```
https://basescan.org/tx/0xabc123...
```

---

## What Just Happened?

Your autonomous agent completed the **3-step payment flow**:

1. ✅ **Issue Mandate** - Created $100 budget with live tracking
2. ✅ **Sign Blockchain Transactions:**
   - Merchant payment ($0.01 USDC to seller)
   - Gateway commission (0.5% to AgentGatePay)
3. ✅ **Submit to Gateway** - Payment proof submitted and verified on-chain
   - Gateway verified transactions on Base blockchain
   - Budget automatically updated: $100.00 → $99.99

**Total cost:** $0.01 (payment + ~$0.001 gas)

---

## Next Steps

### Try More Examples

```bash
# Example 2: Buyer/Seller marketplace (run seller first)
# Terminal 1:
python examples/2b_api_seller_agent.py

# Terminal 2:
python examples/2a_api_buyer_agent.py

# Example 3: Basic payment using MCP tools
python examples/3_mcp_basic_payment.py

# Example 4: Buyer/Seller marketplace (MCP tools) - run seller first
# Terminal 1:
python examples/4b_mcp_seller_agent.py

# Terminal 2:
python examples/4a_mcp_buyer_agent.py

# Example 6: ALL 11 features (comprehensive demo)
python examples/6_api_complete_features.py

# Example 7: ALL 15 MCP tools (100% coverage)
python examples/7_mcp_complete_features.py

# Example 8: Production signing (external service) - PRODUCTION READY 🚀
python examples/8_api_with_tx_service.py

# Example 9: Monitoring dashboard (analytics & audit logs)
python examples/9_monitoring_dashboard.py
```

**Example 8 Requirements:**
- TX signing service must be deployed (see Step 4, Option B)
- `TX_SIGNING_SERVICE` must be set in `.env` file
- Uses external service for secure transaction signing (NO private key in code)

### Learn More

- **[README.md](../README.md)** - Complete examples overview
- **[TX_SIGNING_OPTIONS.md](TX_SIGNING_OPTIONS.md)** - Transaction signing guide (Docker, Render, self-hosted)
- **[API_INTEGRATION.md](API_INTEGRATION.md)** - REST API detailed guide
- **[MCP_INTEGRATION.md](MCP_INTEGRATION.md)** - MCP tools detailed guide
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues & solutions

---

## Common Issues (Quick Fixes)

### Error: "Insufficient funds for gas"
**Solution:** Add ETH to your wallet (~$0.01 worth)

### Error: "Insufficient USDC balance"
**Solution:** Add USDC to your wallet (at least $1)

### Error: "Mandate not found"
**Solution:** Check your BUYER_API_KEY is correct

### Error: "OpenAI API key not found"
**Solution:** Set OPENAI_API_KEY in `.env` file

### Error: "Transaction not found on blockchain"
**Solution:** Wait 10-15 seconds for Base network confirmation, then retry. For Ethereum, see [RPC_CONFIGURATION.md](RPC_CONFIGURATION.md) for 10-20x speedup with Alchemy/Infura.

For more troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

## Support

- **Email:** support@agentgatepay.com
- **GitHub Issues:** https://github.com/AgentGatePay/agentgatepay-examples/issues
- **Documentation:** https://docs.agentgatepay.com

---

**🎉 Congratulations!** You've successfully run your first autonomous agent payment. Now explore the other examples to see buyer/seller interactions, audit logging, and MCP tools integration.
