# AgentGatePay + LangChain Integration

**Autonomous AI agent payments using blockchain and LangChain framework**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![AgentGatePay SDK](https://img.shields.io/badge/agentgatepay--sdk-1.1.3+-green.svg)](https://pypi.org/project/agentgatepay-sdk/)
[![LangChain](https://img.shields.io/badge/langchain-0.1.0-orange.svg)](https://www.langchain.com/)

## Overview

This repository contains **8 complete examples** demonstrating how to integrate AgentGatePay with LangChain for autonomous agent payments:

- **Examples 1-3:** REST API basics (payment, buyer/seller, audit logs)
- **Examples 4-6:** MCP tools basics (same features as 1-3 using MCP)
- **Example 7:** REST API complete (ALL 10 AgentGatePay features)
- **Example 8:** MCP complete (ALL 15 MCP tools - 100% coverage)

**Integration Approaches:**
- **REST API version** - Uses published AgentGatePay SDK (v1.1.3+) from PyPI
- **MCP version** - Uses AgentGatePay's 15 MCP tools (Model Context Protocol)

## What You'll Learn

- ✅ How to create autonomous agents that make blockchain payments
- ✅ Buyer/seller marketplace interactions (like n8n workflows)
- ✅ Complete audit logging and payment tracking
- ✅ Mandate budget management and verification
- ✅ Two-transaction commission model (merchant + gateway)
- ✅ Comparison of REST API vs MCP tools approaches

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
   - Buyer account: `user_type="agent"`
   - Seller account: `user_type="merchant"`
   - Get API keys from: https://api.agentgatepay.com/v1/users/signup

3. **Wallet setup**
   - Buyer wallet with USDC on Base network
   - Seller wallet address for receiving payments
   - Private key for buyer wallet (for signing transactions)

4. **OpenAI API key** (for LangChain LLM)

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

Required variables:
```bash
# AgentGatePay
AGENTPAY_API_URL=https://api.agentgatepay.com
BUYER_API_KEY=pk_live_YOUR_BUYER_KEY
SELLER_API_KEY=pk_live_YOUR_SELLER_KEY

# Blockchain
BASE_RPC_URL=https://mainnet.base.org
BUYER_PRIVATE_KEY=0xYOUR_PRIVATE_KEY
BUYER_WALLET=0xYOUR_BUYER_WALLET
SELLER_WALLET=0xYOUR_SELLER_WALLET

# OpenAI
OPENAI_API_KEY=sk-YOUR_OPENAI_KEY
```

### Run Examples

```bash
# Example 1: Basic payment (REST API)
python examples/1_api_basic_payment.py

# Example 2: Buyer/seller marketplace (REST API) - TWO SCRIPTS
# Terminal 1: Start seller first
python examples/2b_api_seller_agent.py

# Terminal 2: Then run buyer
python examples/2a_api_buyer_agent.py

# Example 3: Payment with audit logs (REST API)
python examples/3_api_with_audit.py

# Example 4: Basic payment (MCP tools)
python examples/4_mcp_basic_payment.py

# Example 5: Buyer/seller marketplace (MCP tools)
python examples/5_mcp_buyer_seller.py

# Example 6: Audit logging (MCP tools)
python examples/6_mcp_with_audit.py

# Example 7: Complete features demo (REST API) - ALL 10 FEATURES
python examples/7_api_complete_features.py

# Example 8: Complete features demo (MCP tools) - ALL 15 MCP TOOLS
python examples/8_mcp_complete_features.py
```

## Examples Overview

### Example 1: Basic Payment Flow (REST API)

**File:** `examples/1_api_basic_payment.py`

Simple autonomous payment flow:
1. Issue AP2 mandate ($100 budget)
2. Sign blockchain transaction (USDC on Base)
3. Submit payment proof
4. Verify completion

**Uses:**
- AgentGatePay SDK (agentgatepay-sdk>=1.1.3)
- Web3.py for blockchain signing
- LangChain ReAct agent

**Output:**
```
✅ Mandate issued successfully
💳 Payment sent: $10 to 0x742d35...
✅ Payment verified
📊 Budget remaining: $90
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
[BUYER] Sign blockchain TX (2 transactions) → [BUYER] Submit payment proof
   ↓
[SELLER] Verify via AgentGatePay API → [SELLER] Deliver resource (200 OK)
   ↓
[BUYER] Access granted → [BOTH] Audit logs
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
- Comprehensive error handling
- Multi-seller support

---

### Example 3: Payment with Audit Logs (REST API)

**File:** `examples/3_api_with_audit.py`

Demonstrates comprehensive payment tracking:
- Multiple payments with descriptions
- Budget utilization monitoring
- Spending pattern analysis
- Transaction history retrieval
- Audit log filtering by event type

**Analytics:**
```
📊 Spending Analysis:
   Total payments: 5
   Total spent: $47.50
   Average payment: $9.50
   Budget utilization: 47.5%
```

---

### Example 4: Basic Payment Flow (MCP Tools)

**File:** `examples/4_mcp_basic_payment.py`

MCP version of Example 1, demonstrating the same payment flow using AgentGatePay's MCP tools instead of REST API.

**Flow:**
1. Issue mandate via `agentpay_issue_mandate` tool
2. Sign blockchain transaction (Web3.py)
3. Submit payment via `agentpay_submit_payment` tool
4. Verify payment via `agentpay_verify_payment` tool

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

### Example 5: Buyer/Seller Marketplace (MCP Tools)

**File:** `examples/5_mcp_buyer_seller.py`

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

### Example 6: Payment with Audit Logs (MCP Tools)

**File:** `examples/6_mcp_with_audit.py`

MCP version of Example 3, demonstrating comprehensive audit logging using MCP tools.

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

### Example 7: Complete Features Demo (REST API) ⭐ **ALL FEATURES**

**File:** `examples/7_api_complete_features.py`

**Comprehensive demonstration of ALL 10 AgentGatePay features** matching n8n workflow capabilities.

**Features Demonstrated:**
1. ✅ User Authentication & Signup
2. ✅ Wallet Management
3. ✅ API Key Management (create, list, revoke)
4. ✅ Mandate Management (issue, verify, budget tracking)
5. ✅ Payment Execution (2-TX model)
6. ✅ Payment History Retrieval
7. ✅ Merchant Revenue Analytics
8. ✅ Comprehensive Audit Logging
9. ✅ Webhook Configuration & Testing
10. ✅ System Health Monitoring

**Why This Example Matters:**
- Shows COMPLETE platform capabilities
- Matches n8n buyer + seller + monitoring workflows combined
- Production-ready feature coverage
- Demonstrates full agent economy ecosystem

**Output:**
```
✅ Features Demonstrated: 10/10
   ✓ User authentication & signup
   ✓ Wallet management
   ✓ API key management
   ✓ Mandates (AP2)
   ✓ Payments (2-TX model)
   ✓ Payment history
   ✓ Revenue analytics
   ✓ Audit logging
   ✓ Webhooks
   ✓ System health
🎉 ALL 10 AGENTGATEPAY FEATURES DEMONSTRATED!
```

---

### Example 8: Complete Features Demo (MCP Tools) ⭐ **ALL 15 MCP TOOLS**

**File:** `examples/8_mcp_complete_features.py`

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
