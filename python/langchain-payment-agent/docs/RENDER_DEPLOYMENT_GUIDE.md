# Render Deployment Guide - AgentGatePay TX Signing Service

**Deploy production-ready transaction signing service to Render cloud in 3 minutes**

**Note:** This guide demonstrates Render deployment as an example. You can deploy the TX signing service using any method you prefer (AWS, GCP, Azure, Railway, Docker, DigitalOcean, your own infrastructure, etc.).

## Overview

This guide shows you how to deploy the AgentGatePay TX signing service to Render cloud. This is perfect for:

- ✅ **Production Deployments** - Always-on, globally accessible HTTPS endpoint
- ✅ **Zero DevOps** - No server management, automatic updates, built-in monitoring
- ✅ **Quick Setup** - One-click deploy from GitHub, 3 minutes to production
- ✅ **Cost-Effective** - Free tier available, $7/month for always-on

**Security**: Private key encrypted at rest, HTTPS only, owner-protected API

---

## Prerequisites

1. **GitHub account** (for Render authentication)
   - Sign up at https://github.com if you don't have one

2. **AgentGatePay account** with API key
   ```bash
   curl -X POST https://api.agentgatepay.com/v1/users/signup \
     -H "Content-Type: application/json" \
     -d '{"email": "your@email.com", "password": "YourPass123!", "user_type": "agent"}'
   ```
   **Save the API key** from response: `pk_live_...`

3. **Wallet with funds**
   - Wallet private key (format: `0x` + 64 hex characters)
   - Small amount of USDC on Base network (for testing)
   - Small amount of ETH on Base network (for gas fees, ~$0.01)

---

## Quick Start (3 Minutes)

### Step 1: One-Click Deploy

Click the button below to deploy to Render:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/AgentGatePay/TX)

**What happens:**
1. Render opens and asks you to sign in with GitHub
2. Render clones the TX repository
3. Render shows a form for environment variables
4. You fill in your credentials
5. Render builds and deploys the service (~2 minutes)

### Step 2: Configure Environment Variables

When prompted by Render, enter these values:

| Variable | Value | Example |
|----------|-------|---------|
| **WALLET_PRIVATE_KEY** | Your wallet private key | `0xabc123def456...` (66 chars) |
| **AGENTGATEPAY_API_KEY** | Your AgentGatePay API key | `pk_live_abc123def456...` |

**Optional variables** (leave as defaults):
- `BASE_RPC_URL` - Base network RPC endpoint (default: `https://mainnet.base.org`)
- `PORT` - Service port (default: `3000`)

⚠️ **IMPORTANT**: Keep these values secure! Don't share them or post screenshots.

### Step 3: Wait for Deployment

Render will:
1. Create a new web service
2. Clone the code from GitHub
3. Install dependencies
4. Build Docker image
5. Deploy to production (~2 minutes)

**Watch the deployment logs** to see progress.

### Step 4: Get Your Service URL

After deployment completes:

1. Copy your service URL from Render dashboard
   - Format: `https://your-service-name.onrender.com`
   - Example: `https://agentpay-tx-signer-abc123.onrender.com`

2. Test the health endpoint:
   ```bash
   curl https://your-service-name.onrender.com/health
   ```

   **Expected response:**
   ```json
   {
     "status": "healthy",
     "version": "4.0.0",
     "mode": "secure_server_fetched_config",
     "owner_protection": "enabled",
     "commission_config": "fetched_from_agentgatepay",
     "wallet_configured": true
   }
   ```

✅ **If you see `"status":"healthy"` - you're ready to go!**

### Step 5: Configure Python Scripts

Update your `.env` file in the examples directory:

```bash
# In /python/langchain-payment-agent/.env
TX_SIGNING_SERVICE=https://your-service-name.onrender.com
```

**Replace `your-service-name` with your actual Render service URL!**

### Step 6: Run Example Script

```bash
# Navigate to examples directory
cd /path/to/agentgatepay-examples/python/langchain-payment-agent

# Run the external TX signing example
python examples/5_api_with_tx_service.py
```

**Expected output:**
```
✅ Signing service is healthy (Render cloud)
✅ Wallet configured: true

🔐 Issuing mandate with $100 budget...
✅ Mandate issued successfully

💳 Requesting payment signature from Render service...
✅ Payment signed and submitted by Render service
   Merchant TX: 0xabc123...
   Commission TX: 0xdef456...

✅ PRODUCTION SUCCESS:
   Private key: SECURE (stored in Render service)
   Application code: CLEAN (no private keys)
   Payment: VERIFIED (on Base blockchain)
   Deployment: CLOUD (24/7 availability)
```

---

## Detailed Setup Instructions

### Option 1: One-Click Deploy (Recommended)

**Already covered above** - Click button, enter credentials, deploy!

### Option 2: Manual Deploy from Render Dashboard

If the one-click button doesn't work, deploy manually:

**Step 1: Create Render Account**

1. Go to https://render.com
2. Click "Get Started" or "Sign Up"
3. Sign in with GitHub

**Step 2: Create New Web Service**

1. Click "New +" button in dashboard
2. Select "Web Service"
3. Click "Build and deploy from a Git repository"

**Step 3: Connect Repository**

1. Click "Connect account" for GitHub
2. Authorize Render to access your GitHub
3. Search for "AgentGatePay/TX"
4. Click "Connect" next to the repository

**Step 4: Configure Service**

**Basic Settings:**
- **Name**: `agentpay-tx-signer` (or any name you like)
- **Region**: Choose closest to you (e.g., `Oregon (US West)`)
- **Branch**: `main`
- **Root Directory**: Leave empty
- **Environment**: `Docker`
- **Dockerfile Path**: `docker/Dockerfile`

**Instance Type:**
- **Free**: $0/month (cold starts after 15 min inactivity)
- **Starter**: $7/month (always-on, no cold starts)

**Advanced Settings:**
- **Health Check Path**: `/health`
- **Auto-Deploy**: Yes (recommended)

**Step 5: Add Environment Variables**

Click "Environment" tab and add:

```
WALLET_PRIVATE_KEY=0xYOUR_PRIVATE_KEY_HERE
AGENTGATEPAY_API_KEY=pk_live_YOUR_API_KEY_HERE
BASE_RPC_URL=https://mainnet.base.org
PORT=3000
```

**Step 6: Deploy**

1. Click "Create Web Service"
2. Wait for deployment (~2 minutes)
3. Check logs for "Service listening on port 3000"

---

## Upgrading Security with Secret Files

**Default security** (environment variables) is secure for most users:
- ✅ Encrypted at rest
- ✅ Redacted in logs
- ✅ Secure for 99% of use cases

**For maximum security**, move secrets to Secret Files:

### Step 1: Add Secret Files

1. Go to Render Dashboard → Your Service
2. Click **"Secret Files"** in left sidebar
3. Click **"Add Secret File"**

**First Secret File:**
- **Filename**: `wallet-private-key`
- **Contents**: Your wallet private key (e.g., `0xabcd1234...`)
- Click **"Save"**

**Second Secret File:**
- Click **"Add Secret File"** again
- **Filename**: `agentgatepay-api-key`
- **Contents**: Your AgentGatePay API key (e.g., `pk_live_abc123...`)
- Click **"Save"**

### Step 2: Remove Environment Variables

1. Go to **"Environment"** tab
2. Click delete (X) next to `WALLET_PRIVATE_KEY`
3. Click delete (X) next to `AGENTGATEPAY_API_KEY`
4. Click **"Save Changes"**

Render will automatically redeploy with secrets from files.

### Step 3: Verify

Check logs for:
```
✅ Wallet private key loaded from Secret File
✅ AgentGatePay API key loaded from Secret File
```

✅ **Done!** Your secrets are now stored as files (maximum security).

---

## Managing Your Service

### View Logs

**Real-time logs:**
1. Go to Render Dashboard → Your Service
2. Click "Logs" tab
3. See live log stream

**Download logs:**
- Click "Download" button in logs tab
- Gets last 10,000 lines

### Restart Service

**Soft restart** (graceful shutdown):
1. Go to "Manual Deploy" tab
2. Click "Clear build cache & deploy"

**Force restart** (immediate):
1. Go to "Settings" tab
2. Scroll to "Advanced"
3. Click "Suspend Service" then "Resume Service"

### Update Service

**Automatic updates** (recommended):
- Service auto-deploys when TX repo updates
- Check "Auto-Deploy" is enabled in Settings

**Manual updates:**
1. Go to "Manual Deploy" tab
2. Click "Deploy latest commit"

### View Metrics

1. Go to "Metrics" tab
2. See:
   - CPU usage
   - Memory usage
   - HTTP requests
   - Response times

### Scale Service

**Upgrade plan:**
1. Go to "Settings" tab
2. Scroll to "Instance Type"
3. Select tier:
   - **Free**: $0/month (cold starts)
   - **Starter**: $7/month (always-on)
   - **Standard**: $25/month (2GB RAM, advanced metrics)
4. Click "Update"

### Configure Custom Domain (Optional)

Want `https://payments.yourdomain.com` instead of `*.onrender.com`?

1. Go to "Settings" tab
2. Scroll to "Custom Domain"
3. Click "Add Custom Domain"
4. Enter your domain: `payments.yourdomain.com`
5. Follow DNS instructions
6. Wait for SSL certificate (automatic, ~10 minutes)

---

## Monitoring & Alerts

### Health Checks

Render automatically monitors your service:

**Health check endpoint:** `/health`
**Interval:** 30 seconds
**Timeout:** 10 seconds

If 3 consecutive health checks fail, Render sends alert.

### Email Alerts

Configure email alerts:

1. Go to "Notifications" in Settings
2. Add email addresses
3. Choose alert types:
   - ✅ Deploy succeeded
   - ✅ Deploy failed
   - ✅ Service crashed
   - ✅ Health check failing

### Integration with External Monitoring

**Datadog:**
```bash
# Add to environment variables
DD_API_KEY=your_datadog_key
DD_SITE=datadoghq.com
```

**Sentry (Error Tracking):**
```bash
# Add to environment variables
SENTRY_DSN=https://your-sentry-dsn
```

---

## Testing Your Deployment

### Test 1: Health Check

```bash
curl https://your-service-name.onrender.com/health

# Expected response:
{
  "status": "healthy",
  "version": "4.0.0",
  "wallet_configured": true
}
```

### Test 2: Owner Protection

**Test with WRONG API key** (should fail):

```bash
curl -X POST https://your-service-name.onrender.com/sign-payment \
  -H "Content-Type: application/json" \
  -H "x-api-key: pk_live_WRONG_KEY" \
  -d '{
    "merchant_address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
    "amount_usd": "0.01",
    "chain": "base",
    "token": "USDC"
  }'

# Expected: HTTP 403 Forbidden
{
  "error": "Unauthorized: Invalid API key"
}
```

### Test 3: Payment Signing

**Test with CORRECT API key** (should succeed):

```bash
curl -X POST https://your-service-name.onrender.com/sign-payment \
  -H "Content-Type: application/json" \
  -H "x-api-key: pk_live_YOUR_REAL_KEY" \
  -d '{
    "merchant_address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
    "amount_usd": "0.01",
    "chain": "base",
    "token": "USDC"
  }'

# Expected: HTTP 200 OK
{
  "success": true,
  "tx_hash": "0xabc123...",
  "tx_hash_commission": "0xdef456...",
  "commission_amount": "50",
  "merchant_amount": "9950"
}
```

### Test 4: Verify on Blockchain

```bash
# Open merchant transaction
open https://basescan.org/tx/TX_HASH

# Verify:
# - Amount: $0.01 × 0.995 = $0.00995 USDC
# - Recipient: 0x742d35... (merchant address)

# Open commission transaction
open https://basescan.org/tx/TX_HASH_COMMISSION

# Verify:
# - Amount: $0.01 × 0.005 = $0.00005 USDC
# - Recipient: AgentGatePay commission address
```

---

## Troubleshooting

### Service Won't Start

**Check logs:**
1. Go to Render Dashboard → Your Service → Logs
2. Look for error messages

**Common issues:**

**Missing environment variables:**
```
Error: WALLET_PRIVATE_KEY is required
```
**Fix**: Go to Environment tab, add missing variable, save

**Invalid private key:**
```
Error: Invalid private key format
```
**Fix**: Private key must be `0x` + 64 hex characters (66 total)

**Build failed:**
```
Error: Failed to build Docker image
```
**Fix**: Check you selected "Docker" as environment type

### Cold Starts (Free Tier)

**Symptom:** First request takes 5-10 seconds

**Why:** Free tier sleeps after 15 minutes of inactivity

**Solutions:**

**Option 1: Keep-alive ping** (free)
```bash
# Cron job to ping every 14 minutes
*/14 * * * * curl https://your-service-name.onrender.com/health
```

**Option 2: Upgrade to Starter** ($7/month)
- Always-on (no cold starts)
- Better for production

### Health Check Failing

**Symptom:** Service shows "Unhealthy" in dashboard

**Checks:**

1. **Test health endpoint manually:**
   ```bash
   curl https://your-service-name.onrender.com/health
   ```

2. **Check logs** for errors

3. **Verify wallet** has sufficient funds

4. **Restart service** (Manual Deploy → Clear build cache & deploy)

### Cannot Connect from Python

**Error:**
```
Cannot connect to signing service at https://your-service-name.onrender.com
```

**Fixes:**

1. **Verify URL is correct:**
   ```bash
   echo $TX_SIGNING_SERVICE
   # Should match your Render URL exactly
   ```

2. **Test from command line:**
   ```bash
   curl https://your-service-name.onrender.com/health
   ```

3. **Check service status** in Render dashboard
   - Should show green "Live" indicator

4. **Check for cold start** (free tier)
   - First request may timeout
   - Wait 10 seconds and retry

### Payment Signing Fails

**Error:**
```
HTTP 500 - Internal Server Error
```

**Common causes:**

1. **Insufficient funds:**
   - Check wallet on BaseScan: https://basescan.org/address/YOUR_WALLET
   - Add USDC and ETH for gas

2. **Wrong chain/token combo:**
   - USDT not available on Base
   - Use USDC on Base (recommended)

3. **RPC endpoint issues:**
   - Check Render logs for RPC errors
   - Consider using premium RPC (Alchemy/Infura)

4. **High gas prices:**
   - Base gas is usually cheap (<$0.01)
   - Check gas prices: https://basescan.org/gastracker

### Service Crashed

**Symptom:** Service shows "Crashed" in dashboard

**Automatic recovery:** Render auto-restarts crashed services

**Manual recovery:**
1. Check logs for crash reason
2. Fix underlying issue
3. Manual deploy if needed

**Common crash causes:**
- Out of memory (upgrade to larger instance)
- Uncaught exception (check logs)
- RPC endpoint unreachable

---

## Cost Management

### Free Tier Limits

- **Price**: $0/month
- **Compute**: 750 hours/month
- **Cold starts**: After 15 min inactivity
- **RAM**: 512MB
- **Best for**: Development, testing, low-volume

### Starter Tier

- **Price**: $7/month
- **Compute**: Unlimited
- **Cold starts**: None (always-on)
- **RAM**: 512MB
- **Best for**: Production, always-on service

### Standard Tier

- **Price**: $25/month
- **Compute**: Unlimited
- **Cold starts**: None
- **RAM**: 2GB
- **Best for**: High-volume, enterprise

### Cost Optimization Tips

1. **Use free tier** for development
2. **Upgrade to Starter** when deploying to production
3. **Monitor usage** in Metrics tab
4. **Use cron ping** to avoid cold starts on free tier
5. **Consider Docker local** if you only need it occasionally

### Total Cost Comparison

| Scenario | Render Cost | Gas Cost* | Total |
|----------|------------|-----------|-------|
| **Development (free tier)** | $0 | ~$3/month | **$3/month** |
| **Production (Starter)** | $7 | ~$3/month | **$10/month** |
| **High-volume (Standard)** | $25 | ~$30/month | **$55/month** |

\* Gas cost assumes Base network (~$0.001 per TX)

---

## Security Best Practices

### 1. Use Secret Files for Private Keys

- ✅ **DO**: Move secrets to Secret Files after deployment
- ❌ **DON'T**: Keep secrets in environment variables long-term
- ✅ **DO**: Follow the "Upgrading Security" section above

### 2. Enable HTTPS Only

- ✅ Render enforces HTTPS by default
- ❌ Never make HTTP requests to service
- ✅ Verify SSL certificate in browser

### 3. Protect Your API Key

- ✅ **DO**: Keep API key secure
- ❌ **DON'T**: Share service URL publicly without authentication
- ✅ **DO**: Rotate API keys quarterly
- ❌ **DON'T**: Commit API keys to git

### 4. Monitor Service Logs

- ✅ **DO**: Check logs regularly for unusual activity
- ❌ **DON'T**: Ignore failed authentication attempts
- ✅ **DO**: Set up email alerts

### 5. Use Separate Wallets

- ✅ **DO**: Use dedicated wallet for payments
- ❌ **DON'T**: Use your main wallet with large funds
- ✅ **DO**: Keep only necessary funds in wallet
- ❌ **DON'T**: Store large amounts long-term

---

## Comparison: Render vs Docker Local

| Feature | Render Cloud | Docker Local |
|---------|-------------|--------------|
| **Setup Time** | 3 minutes | 5 minutes |
| **Cost** | $0-7/month | Free |
| **Always-On** | Yes (24/7) | Only when computer on |
| **Accessible From** | Anywhere (HTTPS URL) | Localhost only |
| **Security** | Encrypted secrets | Container isolated |
| **Maintenance** | Automatic updates | Manual updates |
| **Cold Starts** | Yes (free tier) | No |
| **Monitoring** | Built-in dashboard | Manual (docker logs) |
| **Scaling** | Auto-scaling available | Single container |
| **Best For** | Production, always-on | Development, testing |

**Recommendation:**
- Start with **Docker Local** for learning and development
- Move to **Render** when deploying to production or need 24/7 availability
- Use **Render Starter** ($7/month) for production to avoid cold starts

---

## Next Steps

1. **Test with small amount** ($0.01) first
2. **Monitor transactions** on BaseScan
3. **Run example scripts** (5_api_with_tx_service.py)
4. **Set up alerts** for service health
5. **Upgrade to Starter** when ready for production
6. **Scale up** when comfortable

---

## See Also

- [DOCKER_LOCAL_SETUP.md](DOCKER_LOCAL_SETUP.md) - Run signing service locally with Docker
- [TX_SIGNING_OPTIONS.md](TX_SIGNING_OPTIONS.md) - Compare all signing methods
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions
- [Render Documentation](https://render.com/docs) - Official Render docs

---

## Support

- **GitHub Issues**: https://github.com/AgentGatePay/agentgatepay-examples/issues
- **Render Status**: https://status.render.com
- **Email**: support@agentgatepay.com

---

**Built with ❤️ by AgentGatePay**

*Secure, production-ready transaction signing for autonomous AI agents*
