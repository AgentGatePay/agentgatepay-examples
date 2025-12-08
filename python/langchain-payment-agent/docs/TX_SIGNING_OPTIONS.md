# Transaction Signing Options - AgentGatePay LangChain

**Complete guide to blockchain transaction signing for autonomous agent payments.**

When making payments with AgentGatePay, your agent must sign blockchain transactions to transfer USDC/USDT/DAI. This guide covers all available signing methods, from simple local signing (for testing) to production-ready external services.

---

## Table of Contents

1. [Why Transaction Signing Matters](#why-transaction-signing-matters)
2. [Option 0: Local Signing with Web3.py](#option-0-local-signing-with-web3py)
3. [Option 1: Docker Container](#option-1-docker-container-recommended-for-production)
4. [Option 2: Render One-Click Deploy](#option-2-render-one-click-deploy)
5. [Option 3: Railway Deployment](#option-3-railway-deployment)
6. [Option 4: Self-Hosted Custom Service](#option-4-self-hosted-custom-service)
7. [Option 5: External Wallet Services](#option-5-external-wallet-services-future)
8. [Comparison Matrix](#comparison-matrix)
9. [Recommended Choice by User Type](#recommended-choice-by-user-type)
10. [Security Best Practices](#security-best-practices)

---

## Why Transaction Signing Matters

**The Problem:**

AI agents need to make autonomous payments on blockchains like Base, but signing transactions requires a **private key**. Where should this private key live?

**The Challenge:**

- **Option 1:** Store private key in application code (`.env` file)
  - ⚠️ Security risk: Anyone with code access can steal funds
  - ⚠️ Not recommended for production

- **Option 2:** Use external signing service
  - ✅ Private key isolated from application
  - ✅ Production-ready
  - ✅ Can serve multiple agents

**AgentGatePay Payment Flow:**

Every payment requires **TWO blockchain transactions:**
1. **Merchant Payment** (99.5% of amount) → Seller wallet
2. **Gateway Commission** (0.5% of amount) → AgentGatePay wallet

Both transactions must be signed with your private key and broadcast to the blockchain (Base/Ethereum/Polygon/Arbitrum).

---

## Option 0: Local Signing with Web3.py

**Current implementation in Examples 1-8**

### How It Works

```python
from web3 import Web3
from eth_account import Account
import os

# Load private key from .env file
web3 = Web3(Web3.HTTPProvider('https://mainnet.base.org'))
buyer_account = Account.from_key(os.getenv('BUYER_PRIVATE_KEY'))

# Sign transaction directly in Python
tx = {
    'nonce': web3.eth.get_transaction_count(buyer_account.address),
    'to': USDC_CONTRACT,
    'value': 0,
    'gas': 100000,
    'gasPrice': web3.eth.gas_price,
    'data': transfer_data,
    'chainId': 8453  # Base mainnet
}

signed_tx = buyer_account.sign_transaction(tx)
tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
```

### Setup

1. Install dependencies:
```bash
pip install web3 eth-account
```

2. Add private key to `.env`:
```bash
BUYER_PRIVATE_KEY=0xYOUR_64_CHAR_PRIVATE_KEY
BASE_RPC_URL=https://mainnet.base.org
```

3. Run example:
```bash
python examples/1_api_basic_payment.py
```

### Pros

- ✅ **Simple** - No external dependencies
- ✅ **Fast** - No HTTP round-trip (~2-5 seconds for Base)
- ✅ **Self-contained** - Runs anywhere Python runs
- ✅ **Educational** - See complete signing flow
- ✅ **Free** - No hosting costs

### Cons

- ⚠️ **Security Risk** - Private key in `.env` file
- ⚠️ **Not Production-Ready** - Anyone with file access can steal funds
- ⚠️ **No Key Rotation** - Must manually update everywhere
- ⚠️ **No Audit Trail** - No centralized logging of signing events
- ⚠️ **No Rate Limiting** - Can't control signing frequency

### When to Use

- ✅ Development and testing
- ✅ Learning AgentGatePay
- ✅ Proof-of-concept projects
- ✅ Single-user scripts
- ✅ Low-value transactions (<$10)

### Security Measures

**If you MUST use local signing:**

1. **Separate Wallet** - Use dedicated wallet for testing (not your main wallet)
2. **Limited Funds** - Keep only small amount needed ($10-50)
3. **Never Commit** - Add `.env` to `.gitignore`
4. **Rotate Keys** - Change private key regularly
5. **Monitor Transactions** - Check wallet on BaseScan frequently

---

## Option 1: Docker Container (Recommended for Self-Hosted Production)

**Run signing service in isolated Docker container**

**Complete Setup Guide:** [DOCKER_LOCAL_SETUP.md](DOCKER_LOCAL_SETUP.md)

### How It Works

```
Python Script
    ↓ HTTP POST /sign-payment
Docker Container (tx-signing-service)
    ↓ (private key isolated in container)
Sign 2 transactions (merchant + commission)
    ↓ broadcast to Base blockchain
Return tx_hash + tx_hash_commission
    ↓
Python Script submits proof to AgentGatePay
```

### Setup

**Step 1: Pull Docker Image**

```bash
docker pull agentgatepay/tx-signing-service:latest
```

**Step 2: Create Environment File**

```bash
# .env.signing-service
WALLET_PRIVATE_KEY=0xYOUR_PRIVATE_KEY
AGENTPAY_API_KEY=pk_live_YOUR_API_KEY
BASE_RPC_URL=https://mainnet.base.org
PORT=3000
```

**Step 3: Run Container**

```bash
docker run -d \
  --name agentpay-tx-signer \
  --env-file .env.signing-service \
  -p 3000:3000 \
  --restart unless-stopped \
  agentgatepay/tx-signing-service:latest
```

**Step 4: Test Service**

```bash
curl http://localhost:3000/health
# Should return: {"status": "ok", "service": "tx-signing-service"}
```

**Step 5: Use from Python**

```python
import requests
import os

TX_SIGNING_SERVICE = os.getenv('TX_SIGNING_SERVICE', 'http://localhost:3000')

# Request transaction signing
response = requests.post(
    f"{TX_SIGNING_SERVICE}/sign-payment",
    headers={"x-api-key": BUYER_API_KEY},
    json={
        "merchant_address": "0x742d35...",
        "total_amount": "10000",  # USDC atomic units (6 decimals)
        "token": "USDC",
        "chain": "base"
    },
    timeout=30
)

result = response.json()
tx_hash = result['tx_hash']
tx_hash_commission = result['tx_hash_commission']

# Submit to AgentGatePay
payment = agentpay.payments.submit(
    mandate_token=mandate_token,
    amount_usd=10.0,
    receiver_address="0x742d35...",
    tx_hash=tx_hash,
    chain="base"
)
```

### Docker Compose (Easier)

```yaml
# docker-compose.yml
version: '3.8'
services:
  tx-signing-service:
    image: agentgatepay/tx-signing-service:latest
    ports:
      - "3000:3000"
    environment:
      - WALLET_PRIVATE_KEY=${WALLET_PRIVATE_KEY}
      - AGENTPAY_API_KEY=${AGENTPAY_API_KEY}
      - BASE_RPC_URL=https://mainnet.base.org
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**Usage:**
```bash
# Start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Deployment Options

**Local Docker:**
- Run on your laptop/desktop
- Free
- Use for development and low-volume production

**AWS ECS/Fargate:**
- Managed container service
- Auto-scaling
- ~$10-30/month

**Google Cloud Run:**
- Serverless containers
- Pay per request
- ~$5-20/month

**Azure Container Instances:**
- Simple container hosting
- ~$10-25/month

**DigitalOcean App Platform:**
- Simple container deployment
- $5-12/month

### Pros

- ✅ **Production-Ready** - Private key isolated from application
- ✅ **Portable** - Run anywhere Docker runs
- ✅ **Secure** - Container environment isolation
- ✅ **Scalable** - Can handle multiple agents/scripts
- ✅ **Easy Updates** - `docker pull && docker restart`
- ✅ **Resource Limits** - Control CPU/memory usage
- ✅ **Health Checks** - Automatic restart on failure

### Cons

- ⚠️ **Requires Docker** - Need Docker knowledge
- ⚠️ **Infrastructure Management** - Must maintain container
- ⚠️ **Local Network Only** - Need VPN or cloud deployment for remote access

### When to Use

- ✅ Production deployments
- ✅ Multi-agent systems
- ✅ Team/enterprise use
- ✅ High-volume payments (>100/day)
- ✅ When you have Docker infrastructure

### Cost

- **Local Docker:** Free
- **Cloud Hosting:** $5-30/month depending on provider
- **Transaction Gas:** ~$0.001 per payment on Base

---

## Option 2: Render One-Click Deploy (Recommended for Cloud Production)

**Managed cloud hosting with one-click deployment**

**Complete Setup Guide:** [RENDER_DEPLOYMENT_GUIDE.md](RENDER_DEPLOYMENT_GUIDE.md)

### How It Works

1. Click deploy button → Render creates service from GitHub
2. Add environment variables (private key + API key)
3. Service deploys in ~2 minutes
4. Get HTTPS URL: `https://your-service.onrender.com`
5. Use URL from Python scripts

**No server management, no Docker knowledge required.**

### Setup

**Step 1: One-Click Deploy**

Click: [![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/AgentGatePay/TX)

**When prompted, enter:**
1. **Service Name:** `agentpay-tx-signer` (or any name)
2. **WALLET_PRIVATE_KEY:** Your private key (`0x...`)
3. **AGENTPAY_API_KEY:** Your API key (`pk_live_...`)

**Step 2: Wait for Deployment**

Render builds and deploys service (~2 minutes)

**Step 3: Get Service URL**

After deployment:
- Copy URL: `https://agentpay-tx-signer.onrender.com`
- Test: `curl https://agentpay-tx-signer.onrender.com/health`

**Step 4: Use from Python**

```python
# .env
TX_SIGNING_SERVICE=https://agentpay-tx-signer.onrender.com

# Python script
import os
TX_SIGNING_SERVICE = os.getenv('TX_SIGNING_SERVICE')

response = requests.post(
    f"{TX_SIGNING_SERVICE}/sign-payment",
    headers={"x-api-key": BUYER_API_KEY},
    json={...}
)
```

### Security Features

**Built-in Security:**
- ✅ **Owner Protection** - Only your API key can access service (401 for others)
- ✅ **Server-Fetched Config** - Commission address fetched from AgentGatePay (can't be bypassed)
- ✅ **Encrypted Secrets** - Private key encrypted at rest by Render
- ✅ **HTTPS Only** - All requests over TLS 1.3
- ✅ **Automatic Updates** - Security patches applied automatically

**Optional: Secret Files (Maximum Security)**

After deployment, move secrets to Secret Files:

1. Go to Render Dashboard → Your Service → **Secret Files**
2. Add Secret File:
   - Filename: `wallet-private-key`
   - Contents: Your private key (`0x...`)
3. Add Secret File:
   - Filename: `agentgatepay-api-key`
   - Contents: Your API key (`pk_live_...`)
4. Go to **Environment** tab, delete `WALLET_PRIVATE_KEY` and `AGENTPAY_API_KEY`
5. Save (automatic redeploy)

**Result:** Secrets stored as files (not environment variables) - maximum security.

### Pros

- ✅ **Easiest Deployment** - 3 minutes to production
- ✅ **No DevOps Required** - Render manages infrastructure
- ✅ **Automatic HTTPS** - SSL certificate included
- ✅ **Automatic Backups** - Service configuration backed up
- ✅ **Monitoring Included** - Uptime monitoring built-in
- ✅ **One-Click Updates** - Redeploy from GitHub with one click
- ✅ **Free Tier Available** - Unlimited requests (with cold starts)

### Cons

- ⚠️ **Cold Starts on Free Tier** - Service sleeps after 15 min inactivity (~5 sec startup)
- ⚠️ **External Dependency** - Relies on Render uptime (99.9% SLA)
- ⚠️ **Network Latency** - ~200-500ms overhead vs local
- ⚠️ **Limited Customization** - Can't modify service infrastructure

### When to Use

- ✅ No-code/low-code users
- ✅ Quick production deployment
- ✅ Don't want to manage infrastructure
- ✅ Low to medium volume (<1000 payments/day)
- ✅ Budget-conscious ($0-7/month)

### Cost

| Tier | Price | Features |
|------|-------|----------|
| **Free** | $0/month | Unlimited requests, 512MB RAM, cold starts after 15 min |
| **Starter** | $7/month | Always-on (no cold starts), 512MB RAM, metrics |
| **Standard** | $25/month | 2GB RAM, advanced metrics, priority support |

**Transaction Gas:** ~$0.001 per payment on Base (separate from hosting)

### Upgrade from Free to Paid

If cold starts become an issue:

1. Go to Render Dashboard → Your Service
2. Click **Upgrade**
3. Select **Starter** ($7/month)
4. Service now always-on (no cold starts)

---

## Option 3: Railway Deployment

**Alternative cloud platform with faster cold starts**

### How It Works

Similar to Render but with different trade-offs:
- Faster cold starts (~2 seconds vs ~5 seconds)
- Manual setup (no one-click button)
- Better developer UX
- Free tier: 500 hours/month (then $5/month)

### Setup

**Step 1: Create Railway Account**

Visit: https://railway.app and sign up with GitHub

**Step 2: Create New Project**

1. Click **New Project**
2. Select **Deploy from GitHub repo**
3. Connect: `https://github.com/AgentGatePay/TX`
4. Click **Deploy**

**Step 3: Add Environment Variables**

1. Go to **Variables** tab
2. Add:
   ```
   WALLET_PRIVATE_KEY=0x...
   AGENTPAY_API_KEY=pk_live_...
   BASE_RPC_URL=https://mainnet.base.org
   PORT=3000
   ```
3. Click **Redeploy**

**Step 4: Get Service URL**

1. Go to **Settings** tab
2. Click **Generate Domain**
3. Copy URL: `https://your-app.railway.app`
4. Test: `curl https://your-app.railway.app/health`

**Step 5: Use from Python**

```python
TX_SIGNING_SERVICE = "https://your-app.railway.app"
```

### Pros

- ✅ **Faster Cold Starts** - ~2 seconds (vs Render's ~5 seconds)
- ✅ **Better Developer UX** - More modern dashboard
- ✅ **Instant Logs** - Real-time log streaming
- ✅ **GitHub Integration** - Auto-deploy on push
- ✅ **Simple Pricing** - $5/month flat after free tier

### Cons

- ⚠️ **No One-Click Deploy** - Manual setup required
- ⚠️ **Free Tier Limits** - 500 hours/month (Render is unlimited)
- ⚠️ **Less Mature** - Newer platform than Render

### When to Use

- ✅ Developer-friendly users
- ✅ Need faster cold starts than Render
- ✅ Comfortable with manual setup
- ✅ Want better logging/debugging

### Cost

- **Free Tier:** 500 hours/month (~20 days of always-on)
- **Paid Tier:** $5/month minimum (unlimited hours)
- **Overage:** $0.000231/GB-hour after free tier

---

## Option 4: Self-Hosted Custom Service

**Build and deploy your own signing service**

### When to Use

- ✅ You have existing infrastructure (AWS, GCP, Azure)
- ✅ Need full control over code
- ✅ Have specific compliance requirements
- ✅ Want to avoid external dependencies
- ✅ High volume (>10K payments/day)

### Architecture

```
Your Infrastructure
    ↓
Python Flask / Node.js Express
    ↓
Web3.py / ethers.js signing logic
    ↓
Base RPC endpoint
    ↓
Blockchain transactions
```

### Python Implementation

```python
# tx_signing_service.py
from flask import Flask, request, jsonify
from web3 import Web3
from eth_account import Account
import os

app = Flask(__name__)

# Initialize Web3
web3 = Web3(Web3.HTTPProvider(os.getenv('BASE_RPC_URL')))
account = Account.from_key(os.getenv('WALLET_PRIVATE_KEY'))

USDC_CONTRACT = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
USDC_ABI = [{"constant": False, "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "type": "function"}]

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "service": "tx-signing-service"})

@app.route('/sign-payment', methods=['POST'])
def sign_payment():
    data = request.json

    # Validate API key
    api_key = request.headers.get('x-api-key')
    if api_key != os.getenv('AGENTPAY_API_KEY'):
        return jsonify({"error": "Unauthorized"}), 401

    merchant_address = data['merchant_address']
    total_amount = int(data['total_amount'])  # USDC atomic units

    # Calculate commission (0.5%)
    commission_amount = int(total_amount * 0.005)
    merchant_amount = total_amount - commission_amount

    # Fetch commission address from AgentGatePay API
    import requests
    config_response = requests.get('https://api.agentgatepay.com/v1/config/commission')
    commission_address = config_response.json()['commission_address']

    # Prepare contract
    usdc_contract = web3.eth.contract(address=USDC_CONTRACT, abi=USDC_ABI)

    # TX 1: Commission
    tx1 = usdc_contract.functions.transfer(
        commission_address,
        commission_amount
    ).build_transaction({
        'from': account.address,
        'nonce': web3.eth.get_transaction_count(account.address),
        'gas': 100000,
        'gasPrice': web3.eth.gas_price,
        'chainId': 8453
    })

    signed_tx1 = web3.eth.account.sign_transaction(tx1, account.key)
    tx_hash_commission = web3.eth.send_raw_transaction(signed_tx1.raw_transaction)

    # Wait for confirmation
    web3.eth.wait_for_transaction_receipt(tx_hash_commission, timeout=60)

    # TX 2: Merchant
    tx2 = usdc_contract.functions.transfer(
        merchant_address,
        merchant_amount
    ).build_transaction({
        'from': account.address,
        'nonce': web3.eth.get_transaction_count(account.address),
        'gas': 100000,
        'gasPrice': web3.eth.gas_price,
        'chainId': 8453
    })

    signed_tx2 = web3.eth.account.sign_transaction(tx2, account.key)
    tx_hash = web3.eth.send_raw_transaction(signed_tx2.raw_transaction)

    # Wait for confirmation
    web3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

    return jsonify({
        "success": True,
        "tx_hash": tx_hash.hex(),
        "tx_hash_commission": tx_hash_commission.hex(),
        "commission_address": commission_address,
        "merchant_amount": str(merchant_amount),
        "commission_amount": str(commission_amount)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
```

### Deployment Options

**AWS Lambda (Serverless):**
```bash
# Deploy with Serverless Framework
serverless deploy
```

**Docker on AWS ECS:**
```bash
# Build image
docker build -t tx-signing-service .

# Push to ECR
docker push your-ecr-repo/tx-signing-service

# Deploy to ECS
aws ecs update-service --service tx-signing-service --force-new-deployment
```

**Traditional VPS (DigitalOcean, Linode):**
```bash
# SSH to server
ssh root@your-server

# Clone repo
git clone https://github.com/yourorg/tx-signing-service
cd tx-signing-service

# Install dependencies
pip install -r requirements.txt

# Run with systemd
sudo systemctl start tx-signing-service
sudo systemctl enable tx-signing-service
```

### Security Considerations

**Must-Have:**
- ✅ Store private key in **AWS Secrets Manager / HashiCorp Vault**
- ✅ Use **HTTPS only** (TLS 1.3)
- ✅ Implement **API key authentication**
- ✅ Add **rate limiting** (prevent abuse)
- ✅ Enable **logging and monitoring** (CloudWatch, Datadog)
- ✅ Set up **alerts** for unusual activity
- ✅ **Rotate private keys** periodically (quarterly)
- ✅ Use **IAM roles** (not hardcoded credentials)

**Optional but Recommended:**
- IP whitelisting (only allow your application IPs)
- Request signing (HMAC signatures)
- Transaction amount limits (max $1000/transaction)
- Daily spending limits
- Multi-signature wallet (requires 2+ approvals)

### Pros

- ✅ **Full Control** - Complete customization possible
- ✅ **No External Dependencies** - Only blockchain RPC
- ✅ **Integrate with Existing Infrastructure** - Use your monitoring, logging, secrets management
- ✅ **No Cold Starts** - Always-on if using dedicated server
- ✅ **Custom Logic** - Add business rules, notifications, etc.
- ✅ **Compliance** - Meet specific regulatory requirements

### Cons

- ⚠️ **Development Work** - 100-300 lines of code
- ⚠️ **Security Responsibility** - You handle all security
- ⚠️ **Maintenance Burden** - Updates, patches, monitoring
- ⚠️ **DevOps Required** - Need infrastructure knowledge

### When to Use

- ✅ Enterprise deployments
- ✅ Existing infrastructure to leverage
- ✅ Specific compliance requirements (SOC 2, HIPAA, etc.)
- ✅ High volume (>10K payments/day)
- ✅ Need custom logic or integrations

### Cost

- **AWS Lambda:** ~$0.20 per 1M requests + $0.0000166667/GB-sec
- **AWS ECS Fargate:** ~$30-100/month for small cluster
- **VPS:** $5-50/month depending on specs
- **Secrets Manager:** $0.40/secret/month + $0.05 per 10K API calls

---

## Option 5: External Wallet Services (Future)

**Third-party wallet infrastructure providers**

### Status

🚧 **Not yet integrated with AgentGatePay. Coming Q2 2025.**

### Providers Being Evaluated

**Fireblocks (Enterprise):**
- Multi-party computation (MPC) wallets
- Insurance coverage up to $30M
- SOC 2 Type II certified
- $200+/month

**BitGo (Institutional):**
- Multi-signature wallets
- Custodial services
- Regulatory compliance built-in
- $100+/month

**Turnkey (Developer-Friendly):**
- API-first wallet infrastructure
- Non-custodial MPC
- Simple integration
- $50+/month

**Magic (Consumer-Friendly):**
- Passwordless authentication
- Social login integration
- Web3 onboarding
- Free tier + paid

**Coinbase x402 API:**
- Managed signing service
- 0% transaction fees (Coinbase covers gas)
- KYC required
- Free tier: 1,000 requests/month

### Pros

- ✅ **Professional Security** - Enterprise-grade key management
- ✅ **Insurance Coverage** - Funds protected up to $30M+
- ✅ **Compliance Built-In** - Meet regulatory requirements
- ✅ **Multi-Signature** - Require multiple approvals
- ✅ **Key Recovery** - Can recover if keys lost
- ✅ **Audit Trails** - Complete transaction logging

### Cons

- ⚠️ **Higher Cost** - $50-$200+/month
- ⚠️ **KYC Requirements** - Identity verification needed
- ⚠️ **Integration Work** - Custom API integration
- ⚠️ **Slower Transactions** - Multi-sig adds latency
- ⚠️ **Not Available Yet** - Coming Q2 2025

### When to Use

- ✅ Enterprise with >$100K/month volume
- ✅ Need insurance coverage
- ✅ Regulatory compliance required (SOC 2, PCI DSS)
- ✅ Multi-signature requirements
- ✅ Budget for premium service

---

## Comparison Matrix

### Feature Comparison

| Feature | Local | Docker | Render | Railway | Self-Hosted | Coinbase (Future) |
|---------|-------|--------|--------|---------|-------------|-------------------|
| **Setup Time** | 1 min | 5 min | 3 min | 5 min | 30+ min | 10 min |
| **Deployment** | None | Manual | One-click | Manual | Custom | API signup |
| **Security** | ⚠️ Medium | ✅ High | ✅ High | ✅ High | ✅ High | ✅ Very High |
| **Private Key Storage** | .env file | Container | Encrypted | Encrypted | Your vault | Coinbase KMS |
| **Maintenance** | None | Low | None | None | High | None |
| **Production Ready** | ❌ NO | ✅ YES | ✅ YES | ✅ YES | ✅ YES | ✅ YES |
| **Cold Starts** | N/A | No | Yes (free) | Yes (free) | No | No |
| **Customization** | Full | Full | Limited | Limited | Full | Limited |
| **Monitoring** | None | Manual | Built-in | Built-in | Custom | Built-in |
| **Free Tier** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No | ✅ Yes |

### Cost Comparison

| Method | Setup Cost | Monthly Cost | Transaction Cost | Total (100 payments/day) |
|--------|-----------|--------------|------------------|--------------------------|
| **Local** | Free | Free | Gas only (~$0.001) | ~$3/month |
| **Docker (Local)** | Free | Free | Gas only | ~$3/month |
| **Docker (VPS)** | Free | $5-10 | Gas only | ~$8-13/month |
| **Render Free** | Free | Free | Gas + cold starts | ~$3/month |
| **Render Paid** | Free | $7 | Gas only | ~$10/month |
| **Railway** | Free | $5 | Gas only | ~$8/month |
| **AWS Lambda** | Free | $5-20 | Gas only | ~$8-23/month |
| **Coinbase (Future)** | Free | Free (1K/mo) | $0 (Coinbase pays) | Free |

**Note:** Gas cost on Base: ~$0.001 per payment = ~$3/month for 100 payments/day

### Security Comparison

| Method | Private Key Location | Encryption | Access Control | Audit Logs | Production Grade |
|--------|---------------------|------------|----------------|------------|------------------|
| **Local** | .env file | ❌ No | ❌ No | ❌ No | ⚠️ Testing Only |
| **Docker** | Container env vars | ✅ At rest | ✅ API key | ⚠️ Manual | ✅ Yes |
| **Render** | Encrypted secrets | ✅ At rest + transit | ✅ API key | ✅ Built-in | ✅ Yes |
| **Railway** | Encrypted secrets | ✅ At rest + transit | ✅ API key | ✅ Built-in | ✅ Yes |
| **Self-Hosted** | Your vault (AWS SM) | ✅ At rest + transit | ✅ IAM + API key | ✅ CloudWatch | ✅ Yes |
| **Coinbase** | Coinbase KMS | ✅ Enterprise-grade | ✅ OAuth 2.0 | ✅ Built-in | ✅ Yes |

---

## Recommended Choice by User Type

### Beginner / Learning AgentGatePay

**Recommendation:** Option 0 (Local Signing)

**Why:**
- Simplest to understand
- No deployment needed
- See complete flow in code
- Fast iteration

**Start Here:**
```bash
python examples/1_api_basic_payment.py
```

---

### Developer / Testing

**Recommendation:** Option 0 (Local Signing) OR Option 1 (Docker)

**Why:**
- Local: Fast iteration, no infrastructure
- Docker: Production-like environment, test isolation

**Migration Path:**
1. Start with local signing (examples 1-8)
2. Move to Docker when ready for production testing
3. Deploy Docker to cloud when deploying

---

### Production / Single User

**Recommendation:** Option 2 (Render) OR Option 1 (Docker on VPS)

**Why:**
- Render: Easiest deployment (3 minutes)
- Docker on VPS: More control, no cold starts

**Quick Start:**
```bash
# Render: Click button, add secrets, done
# Docker: docker-compose up -d
```

---

### Production / Team

**Recommendation:** Option 4 (Self-Hosted) OR Option 1 (Docker on AWS/GCP)

**Why:**
- Leverage existing infrastructure
- Centralized secrets management
- Team-wide monitoring
- Custom integrations

**Setup:**
```bash
# Deploy to AWS ECS, GCP Cloud Run, or Azure Container Instances
terraform apply
```

---

### Enterprise / High-Volume

**Recommendation:** Option 4 (Self-Hosted) OR Option 5 (Coinbase/Fireblocks)

**Why:**
- Full control and customization
- Meet compliance requirements
- Insurance coverage (Option 5)
- Dedicated resources

**Requirements:**
- >10K payments/day
- SOC 2 / HIPAA compliance
- Multi-signature wallets
- Insurance coverage

---

### No-Code / No-DevOps

**Recommendation:** Option 2 (Render One-Click)

**Why:**
- Zero infrastructure knowledge needed
- One button to deploy
- Managed updates
- Built-in monitoring

**Setup:**
1. Click deploy button
2. Add 2 environment variables
3. Wait 2 minutes
4. Done ✅

---

## Security Best Practices

### General Guidelines

**1. Never Store Private Keys in Code**
```python
# ❌ NEVER DO THIS
PRIVATE_KEY = "0xabc123..."

# ✅ ALWAYS USE ENVIRONMENT VARIABLES
PRIVATE_KEY = os.getenv('BUYER_PRIVATE_KEY')
```

**2. Use Separate Wallets for Testing and Production**
- Testing wallet: $10-50 max
- Production wallet: Only needed funds (refill weekly)
- Cold storage wallet: Long-term holdings (hardware wallet)

**3. Monitor Wallet Activity**
- Set up BaseScan alerts for your wallet
- Check transactions daily
- Investigate any unexpected activity immediately

**4. Rotate Private Keys Regularly**
- Quarterly rotation recommended
- After any security incident
- When team members leave

**5. Limit Permissions**
- Use API keys with minimal required permissions
- Different keys for different environments
- Revoke unused keys immediately

### Specific to Each Option

**Local Signing:**
- ✅ Add `.env` to `.gitignore`
- ✅ Use separate testing wallet
- ✅ Keep max $50 in wallet
- ✅ Monitor transactions daily
- ❌ Never commit .env file
- ❌ Never use production wallet for testing

**Docker Container:**
- ✅ Use Docker secrets (not environment variables)
- ✅ Enable health checks
- ✅ Limit container network access
- ✅ Use read-only filesystem
- ✅ Set resource limits (CPU/memory)
- ❌ Never expose port 3000 publicly (use reverse proxy)

**Render/Railway:**
- ✅ Use Secret Files for private keys
- ✅ Enable automatic security updates
- ✅ Use custom domain with SSL
- ✅ Monitor service logs
- ❌ Never share environment variable screenshots

**Self-Hosted:**
- ✅ Use AWS Secrets Manager / HashiCorp Vault
- ✅ Enable CloudWatch alarms
- ✅ Implement IP whitelisting
- ✅ Use IAM roles (not access keys)
- ✅ Enable audit logging
- ✅ Regular security audits
- ❌ Never store secrets in code/config files

---

## Migration Guide

### From Local to Docker

**Step 1: Start Docker service**
```bash
docker-compose up -d
```

**Step 2: Update Python code**
```python
# Before (local)
from web3 import Web3
tx_hash = sign_locally(...)

# After (Docker)
import requests
response = requests.post('http://localhost:3000/sign-payment', ...)
tx_hash = response.json()['tx_hash']
```

**Step 3: Test**
```bash
python examples/9_api_with_tx_service.py
```

**Step 4: Remove local signing code**
```bash
# No longer needed
# from web3 import Web3
# from eth_account import Account
```

---

### From Docker to Render

**Step 1: Deploy to Render**
- Click deploy button
- Add same environment variables as Docker

**Step 2: Update Python code**
```python
# Before (local Docker)
TX_SIGNING_SERVICE = "http://localhost:3000"

# After (Render)
TX_SIGNING_SERVICE = "https://your-service.onrender.com"
```

**Step 3: Test**
```bash
# Same code works, just different URL
python examples/9_api_with_tx_service.py
```

**Step 4: Stop Docker container (optional)**
```bash
docker-compose down
```

---

## Troubleshooting

### Local Signing Issues

**Error: "Invalid private key"**
```bash
# Check format (must start with 0x)
echo $BUYER_PRIVATE_KEY
# Should be: 0xabc123...def (64 hex chars)
```

**Error: "Insufficient funds for gas"**
```bash
# Add ETH to wallet for gas
# Base network: ~$0.01 ETH covers ~1000 transactions
```

### Docker Issues

**Error: "Cannot connect to Docker daemon"**
```bash
# Start Docker Desktop (Mac/Windows)
# Or start Docker service (Linux)
sudo systemctl start docker
```

**Error: "Port 3000 already in use"**
```bash
# Change port in docker-compose.yml
ports:
  - "3001:3000"  # Host port 3001
```

**Error: "Container exited with code 1"**
```bash
# Check logs
docker logs agentpay-tx-signer

# Common cause: Missing environment variables
docker exec agentpay-tx-signer env | grep WALLET
```

### Render Issues

**Error: "Service failed to start"**
- Check environment variables are set correctly
- Verify private key format (starts with 0x)
- Check Render service logs

**Error: "Cold start timeout"**
- Free tier cold starts can take 5-10 seconds
- Upgrade to paid tier ($7/month) for always-on

### API Call Issues

**Error: "Connection refused"**
```bash
# Check service is running
curl http://localhost:3000/health

# If using Render, check URL is correct
curl https://your-service.onrender.com/health
```

**Error: "401 Unauthorized"**
```bash
# Verify API key is correct
curl -H "x-api-key: pk_live_..." http://localhost:3000/health
```

---

## Support

**Documentation:**
- AgentGatePay API: https://docs.agentgatepay.com
- Transaction signing: https://docs.agentgatepay.com/tx-signing
- Docker: https://docs.docker.com
- Render: https://render.com/docs
- Railway: https://docs.railway.app

**Technical Support:**
- GitHub Issues: https://github.com/AgentGatePay/agentgatepay-examples/issues
- Email: support@agentgatepay.com

---

**Next Steps:**

1. **Choose your signing method** based on use case
2. **Follow setup guide** for chosen option
3. **Test with small amount** ($0.01) first
4. **Monitor transactions** on BaseScan
5. **Scale up** when comfortable

**See Also:**
- [QUICK_START.md](QUICK_START.md) - Get started in 5 minutes
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues
- [API_INTEGRATION.md](API_INTEGRATION.md) - REST API guide
- [README.md](../README.md) - Examples overview
