# AgentGatePay + LangChain Integration

**Autonomous AI agent payments using blockchain and LangChain framework**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![AgentGatePay SDK](https://img.shields.io/badge/agentgatepay--sdk-1.1.0-green.svg)](https://pypi.org/project/agentgatepay-sdk/)
[![LangChain](https://img.shields.io/badge/langchain-0.1.0-orange.svg)](https://www.langchain.com/)

## Overview

This repository contains **6 complete examples** demonstrating how to integrate AgentGatePay with LangChain for autonomous agent payments. Each example is available in **TWO versions**:

- **REST API version** - Uses published AgentGatePay SDK (v1.1.0) from PyPI
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
cd /home/maxmedov/agentgatepay-examples/python/langchain-payment-agent

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

# Example 2: Buyer/seller interaction (REST API)
python examples/2_api_buyer_seller.py

# Example 3: Payment with audit logs (REST API)
python examples/3_api_with_audit.py

# Example 4: Basic payment (MCP tools)
python examples/4_mcp_basic_payment.py

# More examples in examples/ directory
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
- AgentGatePay SDK (agentgatepay-sdk==1.1.0)
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

### Example 2: Buyer/Seller Interaction (REST API) ⭐

**File:** `examples/2_api_buyer_seller.py`

**Complete marketplace interaction** (matches n8n workflow pattern):

**BUYER AGENT:**
- Issues mandate with budget
- Discovers resource from seller
- Signs blockchain payment
- Claims resource after payment

**SELLER AGENT:**
- Provides resource catalog
- Returns 402 Payment Required
- Verifies payment via AgentGatePay API
- Delivers resource (200 OK)

**Flow:**
```
[BUYER] Issue mandate → [BUYER] Discover resource → [SELLER] 402 Payment Required
   ↓
[BUYER] Sign blockchain TX → [BUYER] Submit payment proof → [SELLER] Verify payment
   ↓
[SELLER] Deliver resource → [BUYER] Access granted → [BOTH] Audit logs
```

**Features:**
- HTTP 402 Payment Required protocol
- Two-transaction commission model
- Real Flask API for seller
- Comprehensive error handling

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

### Example 4-6: MCP Tools Versions

**Files:**
- `examples/4_mcp_basic_payment.py` - Basic payment using MCP tools
- `examples/5_mcp_buyer_seller.py` - Buyer/seller using MCP tools
- `examples/6_mcp_with_audit.py` - Audit logging using MCP tools

**MCP Advantages:**
- Native tool discovery (frameworks auto-list all 15 tools)
- Standardized JSON-RPC 2.0 protocol
- Future-proof (Anthropic-backed)
- Cleaner tool abstraction

**MCP Tools Used:**
- `agentpay_issue_mandate` - Issue payment mandate
- `agentpay_submit_payment` - Submit payment proof
- `agentpay_verify_mandate` - Verify mandate status
- `agentpay_list_audit_logs` - Retrieve audit logs
- ... and 11 more (see docs/MCP_INTEGRATION.md)

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
