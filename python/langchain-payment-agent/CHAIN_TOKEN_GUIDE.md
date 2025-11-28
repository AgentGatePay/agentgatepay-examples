# AgentGatePay Multi-Chain & Multi-Token Guide

## Overview

AgentGatePay supports 4 blockchains and 3 stablecoins, giving you flexibility in choosing the optimal network for your payment needs.

This guide explains how to switch between chains and tokens across all AgentGatePay examples.

## Supported Chains & Tokens

### Supported Chains

| Chain | Chain ID | RPC URL (Default) | Gas Price | Speed | Best For |
|-------|----------|-------------------|-----------|-------|----------|
| **Base** (Recommended) | 8453 | `https://mainnet.base.org` | ~1 gwei | Very Fast | Low fees, fast transactions |
| **Ethereum** | 1 | `https://eth-mainnet.public.blastapi.io` | ~30 gwei | Slow | High security, USDT support |
| **Polygon** | 137 | `https://polygon-rpc.com` | ~50 gwei | Very Fast | Low fees, USDT support |
| **Arbitrum** | 42161 | `https://arb1.arbitrum.io/rpc` | ~1 gwei | Very Fast | Low fees, USDT support |

### Supported Tokens

| Token | Decimals | Chains Available | Notes |
|-------|----------|------------------|-------|
| **USDC** (Recommended) | 6 | All 4 chains | Most widely used |
| **USDT** | 6 | Ethereum, Polygon, Arbitrum | Not available on Base |
| **DAI** | 18 | All 4 chains | Decentralized stablecoin, uses 18 decimals |

## Quick Start: Interactive Selection

### Option 1: First-Time Setup (Recommended)

All updated examples now support **interactive chain/token selection** on first run:

```bash
python examples/2a_api_buyer_agent.py
```

**You'll see:**
```
🔧 CHAIN & TOKEN CONFIGURATION
==============================================================

Supported Chains:
  1. Base (USDC, DAI) - Fast, low fees ⭐ RECOMMENDED
  2. Ethereum (USDC, USDT, DAI) - Most secure, higher fees
  3. Polygon (USDC, USDT, DAI) - Fast, low fees
  4. Arbitrum (USDC, USDT, DAI) - Fast, low fees

Select chain (1-4, default: 1 for Base):
```

Your choice is saved to `~/.agentgatepay_config.json` and reused across all examples.

### Option 2: Reset Configuration

To choose a different chain/token:

```bash
rm ~/.agentgatepay_config.json
python examples/2a_api_buyer_agent.py
```

### Option 3: Environment Variables

Set custom RPC URLs via environment variables:

```bash
# .env file
BASE_RPC_URL=https://mainnet.base.org
ETHEREUM_RPC_URL=https://eth-mainnet.public.blastapi.io
POLYGON_RPC_URL=https://polygon-rpc.com
ARBITRUM_RPC_URL=https://arb1.arbitrum.io/rpc
```

---

## Updated Examples with Multi-Chain Support

### ✅ Scripts with Full Multi-Chain/Token Support

| Script | Chain Selection | Monitoring | Features |
|--------|----------------|------------|----------|
| **1_api_basic_payment.py** | Manual config | ❌ | Basic payment flow |
| **2a_api_buyer_agent.py** | ✅ Interactive | ✅ | Buyer agent with optimizations |
| **2b_api_seller_agent.py** | ✅ Interactive | ✅ Revenue | Seller agent with analytics |
| **3_api_with_audit.py** | ✅ Interactive | ✅ Budget | Audit logging + budget tracking |
| **7_api_complete_features.py** | ✅ Interactive | ✅ Full | All 11 features + optimizations |
| **10_monitoring_dashboard.py** | ✅ Interactive | ✅ Standalone | Monitoring tool (n8n equivalent) |

### 🔄 MCP Scripts (4, 5, 6, 8)

MCP examples will be updated in the next release with the same multi-chain pattern.

---

## How It Works: Configuration System

### File Structure

```
python/langchain-payment-agent/
├── monitoring/
│   ├── __init__.py          # Module exports
│   ├── config.py            # 🆕 Chain/token configuration
│   ├── alerts.py            # 🆕 Smart alerts
│   ├── dashboard.py         # 🆕 MonitoringDashboard class
│   └── exports.py           # 🆕 CSV/JSON exports
├── examples/
│   ├── 1_api_basic_payment.py
│   ├── 2a_api_buyer_agent.py     # ✅ Updated
│   ├── 2b_api_seller_agent.py    # ✅ Updated
│   ├── 3_api_with_audit.py       # ✅ Updated
│   ├── 7_api_complete_features.py # ✅ Updated
│   └── 10_monitoring_dashboard.py # 🆕 NEW
└── ~/.agentgatepay_config.json   # Config storage
```

### Configuration File Format

`~/.agentgatepay_config.json`:

```json
{
  "chain": "base",
  "token": "USDC",
  "chain_id": 8453,
  "rpc_url": "https://mainnet.base.org",
  "token_contract": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
  "decimals": 6,
  "explorer": "https://basescan.org",
  "gas_price_gwei": 1,
  "last_updated": "2025-11-28T12:00:00"
}
```

---

## Token Contract Addresses

### USDC (6 decimals)

```python
USDC_CONTRACTS = {
    "ethereum": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "base": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "polygon": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
    "arbitrum": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
}
```

### USDT (6 decimals)

```python
USDT_CONTRACTS = {
    "ethereum": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    "polygon": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
    "arbitrum": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
    "base": None  # ⚠️ USDT not supported on Base
}
```

### DAI (18 decimals!)

```python
DAI_CONTRACTS = {
    "ethereum": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
    "polygon": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",
    "arbitrum": "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
    "base": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb"
}
```

**⚠️ Important:** DAI uses **18 decimals** (like ETH), not 6! The monitoring module handles this automatically.

---

## Decimal Handling

### Why Decimals Matter

Blockchain tokens use **atomic units** (smallest indivisible unit):

- **USDC/USDT**: 1 USDC = 1,000,000 atomic units (6 decimals)
- **DAI**: 1 DAI = 1,000,000,000,000,000,000 atomic units (18 decimals)

### Automatic Conversion

The monitoring module handles decimal conversion automatically:

```python
# Example: $10.50 payment in USDC (6 decimals)
amount_usd = 10.50
atomic_units = int(amount_usd * (10 ** 6))  # 10,500,000

# Example: $10.50 payment in DAI (18 decimals)
amount_usd = 10.50
atomic_units = int(amount_usd * (10 ** 18))  # 10,500,000,000,000,000,000
```

When using `self.config.decimals`, the correct decimal places are applied automatically.

---

## Chain Selection Criteria

### When to Use Each Chain

| Use Case | Recommended Chain | Reason |
|----------|-------------------|---------|
| **Most users** | Base | Fast, cheap, USDC native |
| **USDT required** | Polygon or Arbitrum | Base doesn't support USDT |
| **High security** | Ethereum | Most decentralized, highest TVL |
| **Lowest fees** | Base or Arbitrum | ~$0.01 per transaction |
| **Fastest finality** | Base or Polygon | 2-5 second blocks |
| **Testing** | Base | Faucets available, low cost |

---

## Migration Guide: Updating Existing Scripts

### Before (Hard-coded Base + USDC)

```python
BASE_RPC_URL = 'https://mainnet.base.org'
USDC_CONTRACT_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
USDC_DECIMALS = 6

web3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))
amount_atomic = int(amount_usd * (10 ** USDC_DECIMALS))
```

### After (Multi-chain with monitoring module)

```python
from monitoring import get_or_create_config

# Interactive selection on first run
config = get_or_create_config()

# Use config throughout
web3 = Web3(Web3.HTTPProvider(config.rpc_url))
amount_atomic = int(amount_usd * (10 ** config.decimals))

tx = {
    'to': config.token_contract,
    'chainId': config.chain_id,
    # ...
}
```

---

## Troubleshooting

### Issue: "Invalid chain/token combination"

**Solution:** Check token availability matrix above. USDT is not available on Base.

### Issue: "Configuration not found"

**Solution:** Run script again - it will prompt for chain/token selection automatically.

### Issue: "RPC connection failed"

**Solution:** Check RPC URL in `~/.agentgatepay_config.json`. You can set custom RPCs via environment variables:

```bash
export BASE_RPC_URL="https://your-custom-rpc.com"
```

### Issue: "Transaction amount mismatch"

**Solution:** Verify you're using the correct decimals. DAI uses 18 decimals, not 6!

---

## Advanced: Programmatic Configuration

### Load Existing Config

```python
from monitoring import load_config

config = load_config()  # Returns None if not found
if config:
    print(f"Using {config.chain} with {config.token}")
```

### Save New Config

```python
from monitoring import save_config

config = save_config(chain="polygon", token="USDT")
print(f"Saved: {config.chain} / {config.token}")
```

### Validate Chain/Token Combo

```python
from monitoring.config import validate_chain_token_combo

is_valid = validate_chain_token_combo("base", "USDT")  # False - not supported
is_valid = validate_chain_token_combo("base", "USDC")  # True
```

---

## Explorer Links

Transaction explorers for each chain:

| Chain | Explorer | Example TX Link |
|-------|----------|----------------|
| Base | https://basescan.org | `https://basescan.org/tx/0x...` |
| Ethereum | https://etherscan.io | `https://etherscan.io/tx/0x...` |
| Polygon | https://polygonscan.com | `https://polygonscan.com/tx/0x...` |
| Arbitrum | https://arbiscan.io | `https://arbiscan.io/tx/0x...` |

All updated examples automatically use `config.explorer` for correct links.

---

## Summary

✅ **4 chains supported**: Base (recommended), Ethereum, Polygon, Arbitrum
✅ **3 tokens supported**: USDC (recommended), USDT, DAI
✅ **Interactive selection**: First run prompts for chain/token
✅ **Persistent config**: Saved to `~/.agentgatepay_config.json`
✅ **Automatic decimal handling**: 6 decimals (USDC/USDT) or 18 decimals (DAI)
✅ **Dynamic explorer links**: Correct blockchain explorer for each chain

For questions or issues, see: https://github.com/AgentGatePay/agentgatepay-examples
