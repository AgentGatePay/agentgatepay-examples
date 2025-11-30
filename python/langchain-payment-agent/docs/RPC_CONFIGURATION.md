# RPC Configuration Guide

## Overview

AgentGatePay examples use blockchain RPC endpoints to interact with Ethereum, Base, Polygon, and Arbitrum networks. The RPC provider you choose **significantly impacts payment speed**.

## Performance Comparison

| RPC Provider | Ethereum Speed | Cost | Reliability | Sign Up |
|--------------|----------------|------|-------------|---------|
| **BlastAPI** (default) | 60-120s | Free | 70% | None |
| **Alchemy** (recommended) | 5-10s | Free tier | 99.9% | [alchemy.com](https://www.alchemy.com/) |
| **Infura** | 5-10s | Free tier | 99.5% | [infura.io](https://www.infura.io/) |
| **QuickNode** | 3-5s | Paid | 99.9% | [quicknode.com](https://www.quicknode.com/) |

**For Base, Polygon, Arbitrum:** Default free RPCs are fast (5-15s). Ethereum is the only chain where premium RPC makes a big difference.

## Quick Setup: Alchemy (Recommended)

**Free Tier:** 300M compute units/month (sufficient for thousands of payments)

### 1. Sign Up
- Go to https://www.alchemy.com/
- Create a free account

### 2. Create App
- Dashboard → "Create new app"
- Chain: Ethereum Mainnet
- Network: Mainnet
- Copy the HTTPS URL

### 3. Update .env
```bash
# Replace this line in your .env file:
ETHEREUM_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_API_KEY
```

### 4. Test
```bash
python3 examples/2a_api_buyer_agent.py
```

**Result:** Ethereum payments go from 60-120s → 5-10s ⚡

## Alternative: Infura

**Free Tier:** 100K requests/day

### Setup
1. Sign up at https://www.infura.io/
2. Create project → Ethereum Mainnet
3. Copy HTTPS endpoint
4. Update .env:
   ```bash
   ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/YOUR_PROJECT_ID
   ```

## Multi-Chain Configuration

Configure RPCs for all chains in `.env`:

```bash
# Ethereum (use premium RPC for best performance)
ETHEREUM_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY

# Base (default is fast enough)
BASE_RPC_URL=https://mainnet.base.org

# Polygon (default is okay, but Alchemy is faster)
POLYGON_RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/YOUR_KEY

# Arbitrum (default is fast enough)
ARBITRUM_RPC_URL=https://arb-mainnet.g.alchemy.com/v2/YOUR_KEY
```

## Why Does RPC Speed Matter?

### Payment Flow
1. **Buyer broadcasts TX** → Blockchain confirms in 12-30s
2. **Buyer verifies TX locally** → RPC must return receipt
3. **Gateway verifies TX** → Uses its own RPC

**Slow RPC = buyer waits 60-120s even though blockchain confirmed in 12s**

### Gateway vs Buyer RPC

- **Gateway**: Always uses fast RPC (Cloudflare)
- **Your buyer script**: Uses YOUR .env RPC
- Gateway accepts payments in 3-10s regardless of your RPC
- **YOU wait for YOUR RPC** to confirm locally

## Troubleshooting

### "Transaction not found after 120s"
**Problem:** Your RPC is too slow to return transaction receipt

**Solution:**
1. Use Alchemy or Infura (recommended)
2. OR increase timeout in buyer script (not recommended - just masks slow RPC)

### "Still slow with Alchemy"
**Check:**
1. Verify you updated the correct .env file
2. Restart the script after changing .env
3. Check Alchemy dashboard for rate limit errors

### "Free tier limits exceeded"
**Alchemy Free Tier:** 300M compute units/month
- Each Ethereum payment: ~50K compute units
- Supports: ~6,000 payments/month free
- If exceeded: Upgrade to growth plan ($49/month unlimited)

## Cost Analysis

### Free Tier Comparison
| Provider | Monthly Limit | Ethereum Payments | Cost After Limit |
|----------|---------------|-------------------|------------------|
| BlastAPI | Unlimited | Unlimited | Always free (but slow) |
| Alchemy | 300M CU | ~6,000 | $49/month |
| Infura | 100K requests | ~50,000 | $50/month |

### Recommendation by Use Case

**Hobbyist / Testing:**
- Use BlastAPI (default) - Free and works
- Accept 60-120s payment time

**Production / Better UX:**
- Use Alchemy free tier - 6,000 payments/month free
- 5-10s payment time
- Upgrade to paid if needed

**High Volume:**
- Alchemy Growth ($49/month unlimited)
- QuickNode ($9-299/month based on throughput)

## Advanced: RPC Fallbacks

For production, consider configuring fallback RPCs:

```python
# In your custom integration
rpcs = [
    os.getenv('ETHEREUM_RPC_PRIMARY'),
    os.getenv('ETHEREUM_RPC_FALLBACK'),
    'https://eth-mainnet.public.blastapi.io'  # Last resort
]
```

This requires custom code modification (not supported in basic examples).

## Summary

✅ **Default free RPCs work** - just slower for Ethereum
✅ **Alchemy free tier recommended** - 10-20x faster for Ethereum
✅ **Easy setup** - just change one line in .env
✅ **No code changes needed** - fully supported

**For best UX: Use Alchemy for Ethereum, keep defaults for other chains.**
