# Docker Local Setup - AgentGatePay TX Signing Service

**Run production-ready transaction signing service on your local machine using Docker**

**Note:** This guide demonstrates Docker deployment as an example. You can deploy the TX signing service using any method you prefer (AWS, GCP, Azure, Railway, DigitalOcean, your own infrastructure, etc.).

## Overview

This guide shows you how to run the AgentGatePay TX signing service locally using Docker. This is perfect for:

- ✅ **Development & Testing** - Test production patterns locally before deploying
- ✅ **Learning** - Understand how external signing works without cloud deployment
- ✅ **Production (Self-Hosted)** - Run on your own infrastructure
- ✅ **Cost-Effective** - Free (no cloud hosting costs)

**Security**: Private key stays in Docker container, NOT in your application code.

---

## Prerequisites

1. **Docker Desktop** installed
   - Mac: [Download Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)
   - Windows: [Download Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
   - Linux: [Install Docker Engine](https://docs.docker.com/engine/install/)

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

## Quick Start (5 Minutes)

### Step 1: Pull Docker Image

```bash
# Pull the latest image from Docker Hub
docker pull agentgatepay/tx-signing-service:latest
```

**Image details:**
- Size: ~50MB (Alpine Linux)
- Platforms: linux/amd64, linux/arm64
- Registry: Docker Hub @ `agentgatepay/tx-signing-service`

### Step 2: Create Environment File

Create a file named `.env.signing-service` with your credentials:

```bash
# Create the file
cat > .env.signing-service << 'EOF'
# Required: Your wallet private key (KEEP THIS SECURE!)
WALLET_PRIVATE_KEY=0xYOUR_64_CHARACTER_PRIVATE_KEY_HERE

# Required: Your AgentGatePay API key
AGENTGATEPAY_API_KEY=pk_live_YOUR_API_KEY_HERE

# Optional: Custom RPC endpoints (defaults work fine for most users)
BASE_RPC_URL=https://mainnet.base.org
ETHEREUM_RPC_URL=https://cloudflare-eth.com
POLYGON_RPC_URL=https://polygon-rpc.com
ARBITRUM_RPC_URL=https://arb1.arbitrum.io/rpc

# Optional: Service port (default: 3000)
PORT=3000
EOF
```

**⚠️ IMPORTANT**: Replace `YOUR_64_CHARACTER_PRIVATE_KEY_HERE` and `YOUR_API_KEY_HERE` with your actual credentials!

### Step 3: Run Container

```bash
# Run the container
docker run -d \
  --name agentpay-tx-signer \
  --env-file .env.signing-service \
  -p 3000:3000 \
  --restart unless-stopped \
  agentgatepay/tx-signing-service:latest
```

**What this does:**
- `-d`: Run in background (detached mode)
- `--name`: Give container a friendly name
- `--env-file`: Load environment variables from file
- `-p 3000:3000`: Map container port 3000 to host port 3000
- `--restart unless-stopped`: Auto-restart container if it crashes
- `latest`: Use latest version of image

### Step 4: Verify Service is Running

```bash
# Check container status
docker ps | grep agentpay-tx-signer

# Expected output:
# CONTAINER ID   IMAGE                                    STATUS         PORTS
# abc123def456   agentgatepay/tx-signing-service:latest   Up 5 seconds   0.0.0.0:3000->3000/tcp

# Test health endpoint
curl http://localhost:3000/health

# Expected response:
# {"status":"healthy","version":"4.0.0","mode":"secure_server_fetched_config","owner_protection":"enabled","commission_config":"fetched_from_agentgatepay","wallet_configured":true}
```

✅ **If you see `"status":"healthy"` - you're ready to go!**

### Step 5: Configure Python Scripts

Update your `.env` file in the examples directory:

```bash
# In /python/langchain-payment-agent/.env
TX_SIGNING_SERVICE=http://localhost:3000
```

### Step 6: Run Example Script

```bash
# Navigate to examples directory
cd /path/to/agentgatepay-examples/python/langchain-payment-agent

# Run the external TX signing example
python examples/5_api_with_tx_service.py
```

**Expected output:**
```
✅ Signing service is healthy
✅ Wallet configured: true

🔐 Issuing mandate with $100 budget...
✅ Mandate issued successfully

💳 Requesting payment signature from external service...
✅ Payment signed and submitted by external service
   Merchant TX: 0xabc123...
   Commission TX: 0xdef456...

✅ PRODUCTION SUCCESS:
   Private key: SECURE (stored in signing service)
   Application code: CLEAN (no private keys)
   Payment: VERIFIED (on Base blockchain)
```

---

## Docker Compose (Recommended Method)

Docker Compose simplifies container management with a single configuration file.

### Step 1: Create docker-compose.yml

```bash
# Create docker-compose.yml in your project root
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  tx-signing-service:
    image: agentgatepay/tx-signing-service:latest
    container_name: agentpay-tx-signer
    ports:
      - "3000:3000"
    environment:
      - WALLET_PRIVATE_KEY=${WALLET_PRIVATE_KEY}
      - AGENTGATEPAY_API_KEY=${AGENTGATEPAY_API_KEY}
      - BASE_RPC_URL=https://mainnet.base.org
      - ETHEREUM_RPC_URL=https://cloudflare-eth.com
      - POLYGON_RPC_URL=https://polygon-rpc.com
      - ARBITRUM_RPC_URL=https://arb1.arbitrum.io/rpc
      - PORT=3000
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    networks:
      - agentpay

networks:
  agentpay:
    driver: bridge
EOF
```

### Step 2: Create .env File

```bash
# Create .env file with your credentials
cat > .env << 'EOF'
WALLET_PRIVATE_KEY=0xYOUR_PRIVATE_KEY
AGENTGATEPAY_API_KEY=pk_live_YOUR_API_KEY
EOF
```

### Step 3: Start Service

```bash
# Start the service
docker-compose up -d

# Expected output:
# Creating network "agentpay" with the default driver
# Creating agentpay-tx-signer ... done
```

### Step 4: Manage Service

```bash
# View logs
docker-compose logs -f

# Stop service
docker-compose down

# Restart service
docker-compose restart

# Check status
docker-compose ps
```

---

## Container Management

### View Logs

```bash
# View all logs
docker logs agentpay-tx-signer

# Follow logs in real-time
docker logs -f agentpay-tx-signer

# View last 100 lines
docker logs --tail 100 agentpay-tx-signer
```

### Stop Container

```bash
# Stop container (graceful shutdown)
docker stop agentpay-tx-signer

# Force stop (if unresponsive)
docker kill agentpay-tx-signer
```

### Start Container

```bash
# Start stopped container
docker start agentpay-tx-signer
```

### Restart Container

```bash
# Restart container
docker restart agentpay-tx-signer
```

### Remove Container

```bash
# Stop and remove container
docker stop agentpay-tx-signer
docker rm agentpay-tx-signer
```

### Check Container Stats

```bash
# View resource usage (CPU, memory, network)
docker stats agentpay-tx-signer

# Expected output:
# CONTAINER ID   NAME                  CPU %   MEM USAGE / LIMIT   NET I/O
# abc123def456   agentpay-tx-signer    0.05%   45MiB / 1.95GiB     1.2kB / 850B
```

### Execute Commands Inside Container

```bash
# Open shell inside container
docker exec -it agentpay-tx-signer sh

# Check environment variables
docker exec agentpay-tx-signer env | grep AGENTPAY

# View Node.js version
docker exec agentpay-tx-signer node --version
```

---

## Testing the Service

### Test Health Endpoint

```bash
curl http://localhost:3000/health

# Expected response:
{
  "status": "healthy",
  "version": "4.0.0",
  "mode": "secure_server_fetched_config",
  "owner_protection": "enabled",
  "commission_config": "fetched_from_agentgatepay",
  "wallet_configured": true
}
```

### Test Payment Signing (Manual)

```bash
curl -X POST http://localhost:3000/sign-payment \
  -H "Content-Type: application/json" \
  -H "x-api-key: pk_live_YOUR_API_KEY" \
  -d '{
    "merchant_address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
    "amount_usd": "0.01",
    "chain": "base",
    "token": "USDC"
  }'

# Expected response:
{
  "success": true,
  "tx_hash": "0xabc123...",
  "tx_hash_commission": "0xdef456...",
  "commission_address": "0x...",
  "merchant_amount": "9950",
  "commission_amount": "50",
  "commission_rate": 0.005
}
```

### Test with Wrong API Key (Should Fail)

```bash
curl -X POST http://localhost:3000/sign-payment \
  -H "Content-Type: application/json" \
  -H "x-api-key: pk_live_WRONG_KEY" \
  -d '{
    "merchant_address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
    "amount_usd": "0.01",
    "chain": "base",
    "token": "USDC"
  }'

# Expected response:
# HTTP 403 Forbidden
{
  "error": "Unauthorized: Invalid API key"
}
```

---

## Troubleshooting

### Container Won't Start

**Check logs:**
```bash
docker logs agentpay-tx-signer
```

**Common issues:**

1. **Missing environment variables**
   ```
   Error: WALLET_PRIVATE_KEY is required
   ```
   **Fix**: Check your `.env.signing-service` file has correct values

2. **Invalid private key format**
   ```
   Error: Invalid private key format
   ```
   **Fix**: Private key must be `0x` + 64 hex characters (66 total)

3. **Port 3000 already in use**
   ```
   Error: bind: address already in use
   ```
   **Fix**: Either stop other service using port 3000, or change port:
   ```bash
   docker run -d --name agentpay-tx-signer -p 3001:3000 ...
   ```
   Then update `.env`: `TX_SIGNING_SERVICE=http://localhost:3001`

### Health Check Failing

```bash
# Check if service is responding
curl http://localhost:3000/health

# If no response, check container logs
docker logs agentpay-tx-signer

# Restart container
docker restart agentpay-tx-signer
```

### Cannot Connect from Python Script

**Error:**
```
Cannot connect to signing service at http://localhost:3000
```

**Fixes:**

1. **Check container is running:**
   ```bash
   docker ps | grep agentpay-tx-signer
   ```

2. **Check port mapping:**
   ```bash
   docker port agentpay-tx-signer
   # Should show: 3000/tcp -> 0.0.0.0:3000
   ```

3. **Test from command line:**
   ```bash
   curl http://localhost:3000/health
   ```

4. **Check firewall:** Some systems block localhost connections
   ```bash
   # Linux: Check iptables
   sudo iptables -L

   # Mac: Check System Preferences → Security & Privacy → Firewall
   ```

### Payment Signing Fails

**Error:**
```
Signing service error: HTTP 500 - Internal Server Error
```

**Common causes:**

1. **Insufficient funds:**
   ```bash
   # Check wallet balance on BaseScan
   open https://basescan.org/address/YOUR_WALLET_ADDRESS
   ```
   **Fix**: Add USDC and ETH to wallet

2. **Wrong chain/token:**
   - USDT is NOT available on Base network
   - Use USDC on Base (recommended)

3. **RPC issues:**
   ```bash
   # Check RPC endpoint
   curl https://mainnet.base.org \
     -X POST \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
   ```

### Container Using Too Much Memory

```bash
# Check memory usage
docker stats agentpay-tx-signer

# If using > 100MB, restart container
docker restart agentpay-tx-signer
```

### Update to Latest Version

```bash
# Pull latest image
docker pull agentgatepay/tx-signing-service:latest

# Stop old container
docker stop agentpay-tx-signer
docker rm agentpay-tx-signer

# Start new container (same command as before)
docker run -d --name agentpay-tx-signer --env-file .env.signing-service -p 3000:3000 agentgatepay/tx-signing-service:latest
```

---

## Security Best Practices

### 1. Protect Your Environment File

```bash
# Set restrictive permissions on .env.signing-service
chmod 600 .env.signing-service

# Verify permissions
ls -la .env.signing-service
# Should show: -rw------- (owner read/write only)
```

### 2. Use Separate Testing Wallet

- ✅ **DO**: Use dedicated wallet with small amounts ($10-50)
- ❌ **DON'T**: Use your main wallet with large funds
- ✅ **DO**: Monitor wallet activity regularly
- ❌ **DON'T**: Share private key or commit it to git

### 3. Limit Container Resources

```bash
# Run container with resource limits
docker run -d \
  --name agentpay-tx-signer \
  --env-file .env.signing-service \
  -p 3000:3000 \
  --memory="256m" \
  --cpus="0.5" \
  agentgatepay/tx-signing-service:latest
```

### 4. Don't Expose Container Publicly

- ✅ **DO**: Keep container on localhost (`127.0.0.1`)
- ❌ **DON'T**: Expose to `0.0.0.0` or public internet
- ✅ **DO**: Use reverse proxy (nginx) if external access needed
- ❌ **DON'T**: Disable API key authentication

### 5. Rotate Keys Regularly

- Rotate private keys every 3-6 months
- Rotate immediately if key may be compromised
- Use different keys for different environments (dev, staging, prod)

---

## Production Deployment

### Option 1: Local Docker (Development)

**Best for:**
- Development and testing
- Single-user scripts
- Low-volume payments (<100/day)

**Cost:** Free

### Option 2: Docker on VPS

**Best for:**
- Multi-user teams
- Medium-volume payments (100-1000/day)
- When you need always-on service

**Setup:**
```bash
# SSH to your VPS
ssh root@your-server

# Install Docker
curl -fsSL https://get.docker.com | sh

# Clone config
git clone https://github.com/yourorg/config
cd config

# Start service
docker-compose up -d
```

**Providers:**
- DigitalOcean Droplets: $5-10/month
- Linode: $5-10/month
- Vultr: $5-10/month

### Option 3: Cloud Container Services

**Best for:**
- Auto-scaling
- High availability
- Enterprise deployments

**Providers:**
- AWS ECS/Fargate: ~$30-50/month
- Google Cloud Run: ~$20-40/month
- Azure Container Instances: ~$30-50/month

---

## Comparison: Docker Local vs Render

| Feature | Docker Local | Render Cloud |
|---------|-------------|--------------|
| **Setup Time** | 5 minutes | 3 minutes |
| **Cost** | Free | $0-7/month |
| **Always-On** | Yes (if computer on) | Yes (24/7) |
| **Accessible From** | Localhost only | Anywhere (HTTPS URL) |
| **Security** | Container isolated | Encrypted secrets |
| **Maintenance** | Manual updates | Automatic updates |
| **Best For** | Development, testing | Production, always-on |
| **Cold Starts** | No | Yes (free tier) |
| **Monitoring** | Manual (docker logs) | Built-in dashboard |
| **Scaling** | Single container | Auto-scaling available |

**Recommendation:**
- Start with **Docker Local** for learning and development
- Move to **Render** when deploying to production or need 24/7 availability

---

## Next Steps

1. **Test with small amount** ($0.01) first
2. **Monitor transactions** on BaseScan
3. **Run example scripts** (5_api_with_tx_service.py)
4. **Read Render guide** if you need always-on service (RENDER_DEPLOYMENT_GUIDE.md)
5. **Scale up** when comfortable

---

## See Also

- [RENDER_DEPLOYMENT_GUIDE.md](RENDER_DEPLOYMENT_GUIDE.md) - Deploy to Render cloud (always-on)
- [TX_SIGNING_OPTIONS.md](TX_SIGNING_OPTIONS.md) - Compare all signing methods
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions
- [Docker Documentation](https://docs.docker.com) - Official Docker docs

---

## Support

- **GitHub Issues**: https://github.com/AgentGatePay/agentgatepay-examples/issues
- **Docker Hub**: https://hub.docker.com/r/agentgatepay/tx-signing-service
- **Email**: support@agentgatepay.com

---

**Built with ❤️ by AgentGatePay**

*Secure, production-ready transaction signing for autonomous AI agents*
