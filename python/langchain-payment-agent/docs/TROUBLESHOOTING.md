# Troubleshooting Guide - AgentGatePay + LangChain

Common issues and solutions when integrating AgentGatePay with LangChain.

---

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Configuration Issues](#configuration-issues)
3. [Mandate Issues](#mandate-issues)
4. [Payment Issues](#payment-issues)
5. [Blockchain Issues](#blockchain-issues)
6. [MCP Integration Issues](#mcp-integration-issues)
7. [LangChain Agent Issues](#langchain-agent-issues)
8. [Network & API Issues](#network--api-issues)

---

## Installation Issues

### Error: "Python version 3.12 or higher required"

**Symptom:**
```bash
ERROR: Python 3.12+ required, found 3.10.5
```

**Solution:**
```bash
# Install Python 3.12
# Ubuntu/Debian:
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.12

# macOS (Homebrew):
brew install python@3.12

# Verify installation:
python3.12 --version
```

---

### Error: "agentgatepay-sdk not found"

**Symptom:**
```python
ModuleNotFoundError: No module named 'agentgatepay_sdk'
```

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install/upgrade SDK
pip install --upgrade agentgatepay-sdk>=1.1.3

# Verify installation
python -c "import agentgatepay_sdk; print(agentgatepay_sdk.__version__)"
```

---

### Error: "SDK version too old"

**Symptom:**
```
SDK version 1.1.0 is too old (requires >= 1.1.3)
```

**Solution:**
```bash
pip install --upgrade agentgatepay-sdk>=1.1.3
```

---

## Configuration Issues

### Error: "BUYER_API_KEY not found"

**Symptom:**
```python
KeyError: 'BUYER_API_KEY'
```

**Solution:**
1. Verify `.env` file exists in project root
2. Check `.env` contains `BUYER_API_KEY=pk_live_...`
3. Ensure you're loading environment variables:
```python
from dotenv import load_dotenv
load_dotenv()  # Add this at the top of your script
```

---

### Error: "Invalid API key format"

**Symptom:**
```
Error: API key must start with 'pk_live_' or 'pk_test_'
```

**Solution:**
Check API key format:
```bash
# Correct format:
BUYER_API_KEY=pk_live_abc123def456...

# Wrong format (missing prefix):
BUYER_API_KEY=abc123def456...
```

---

### Error: "Private key invalid"

**Symptom:**
```
ValueError: Private key must be 32 bytes (64 hex characters)
```

**Solution:**
1. Private key must start with `0x` followed by 64 hex characters
2. Check `.env` file:
```bash
# Correct:
BUYER_PRIVATE_KEY=0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890

# Wrong (no 0x prefix):
BUYER_PRIVATE_KEY=abcdef1234567890...

# Wrong (too short):
BUYER_PRIVATE_KEY=0xabc123
```

---

## Mandate Issues

### Error: "Mandate not found or expired"

**Symptom:**
```
MandateExpiredError: Mandate not found or has expired
```

**Solution:**
Mandates have a TTL (default 7 days). Issue a new mandate:
```python
mandate = agentpay.mandates.issue(
    subject="agent-1",
    budget=100,
    scope="resource.read,payment.execute",
    ttl_minutes=10080  # 7 days (168 hours * 60)
)
```

---

### Error: "Insufficient mandate budget"

**Symptom:**
```
Error: Mandate budget ($5.00) insufficient for payment ($10.00)
```

**Solution:**
1. Issue a new mandate with higher budget
2. Or reduce payment amount
3. Check budget before payment:
```python
verification = agentpay.mandates.verify(mandate_token)
budget_remaining = verification['budget_remaining']
print(f"Budget remaining: ${budget_remaining}")
```

---

### Error: "Mandate verification failed"

**Symptom:**
```
AuthenticationError: Mandate verification failed
```

**Solution:**
1. Check API key is correct
2. Verify mandate token hasn't expired
3. Ensure subject matches the issuer
4. Check mandate scope includes required permissions:
```python
scope="resource.read,payment.execute"  # Required for payments
```

---

## Payment Issues

### Error: "Payment verification failed"

**Symptom:**
```
PaymentVerificationError: Payment not found on blockchain
```

**Solution:**
1. **Wait for blockchain confirmation** (10-15 seconds on Base)
```python
import time
time.sleep(15)  # Wait before verifying
```

2. **Check transaction exists:**
Visit BaseScan: `https://basescan.org/tx/{tx_hash}`

3. **Verify correct chain:**
```python
# Ensure you're checking the right network
result = agentpay.payments.verify(tx_hash, chain="base")
```

---

### Error: "Transaction not found on blockchain"

**Symptom:**
```
Error: Transaction 0xabc123... not found
```

**Solution:**
1. Wait longer (Base confirmations take 2-5 seconds typically)
2. Check RPC endpoint is working:
```python
from web3 import Web3
w3 = Web3(Web3.HTTPProvider("https://mainnet.base.org"))
print(w3.is_connected())  # Should be True
```

3. Verify transaction was actually sent:
```python
try:
    tx_receipt = web3.eth.get_transaction_receipt(tx_hash)
    print(f"TX found in block: {tx_receipt['blockNumber']}")
except Exception as e:
    print(f"TX not found: {e}")
```

---

### Error: "Transaction not found after 120 seconds" (Ethereum/Slow RPC)

**Symptom:**
```
⚠️ Verification failed: Transaction HexBytes('0x...') is not in the chain after 120 seconds
```

**Root Cause**: Free public RPCs (like BlastAPI) can take 60-120+ seconds to return transaction receipts for Ethereum, even though the transaction is confirmed on-chain in 12-30 seconds.

**Solution 1: Use Premium RPC (Recommended - 10-20x faster)**

Free premium RPCs with fast response times:

1. **Alchemy** (Recommended):
   ```bash
   # Sign up: https://www.alchemy.com/ (free tier: 300M compute units/month)
   # Get your API key and update .env:
   ETHEREUM_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_API_KEY
   ```
   **Result**: 60-120s → 5-10s ⚡

2. **Infura**:
   ```bash
   # Sign up: https://www.infura.io/ (free tier: 100K requests/day)
   ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/YOUR_PROJECT_ID
   ```

**Solution 2: Use Faster Chain (if compatible)**

If your use case allows, switch to faster chains with free RPCs:
```bash
# In .env file:
PAYMENT_CHAIN=base          # 5-15 sec (free RPC works great)
# Or
PAYMENT_CHAIN=polygon       # 5-15 sec (free RPC works great)
# Or
PAYMENT_CHAIN=arbitrum      # 5-15 sec (free RPC works great)
```

**Verification**:
```bash
# Check transaction on blockchain explorer (confirms it's on-chain)
# Ethereum: https://etherscan.io/tx/YOUR_TX_HASH
# If transaction shows 50+ confirmations but script times out = RPC issue
```

**See**: [RPC_CONFIGURATION.md](RPC_CONFIGURATION.md) for complete setup guide.

**Note**: Gateway uses fast RPCs (Cloudflare), so payments succeed quickly. Your local script's timeout is from YOUR configured RPC, not the gateway.

---

### Error: "Insufficient USDC balance"

**Symptom:**
```
Error: Insufficient funds for transfer
```

**Solution:**
Check wallet USDC balance:
```python
from web3 import Web3

# USDC contract on Base
USDC_CONTRACT = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

# Check balance
usdc_contract = web3.eth.contract(
    address=USDC_CONTRACT,
    abi=[{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]
)

balance = usdc_contract.functions.balanceOf(buyer_wallet).call()
balance_usdc = balance / (10 ** 6)  # USDC has 6 decimals
print(f"USDC Balance: ${balance_usdc}")
```

**Solutions:**
- Add USDC to wallet via https://app.uniswap.org (Base network)
- Bridge USDC from Ethereum via https://bridge.base.org

---

## Blockchain Issues

### Error: "Insufficient gas for transaction"

**Symptom:**
```
Error: Insufficient funds for gas * price + value
```

**Solution:**
Add ETH to wallet for gas fees:
- Base network: ~$0.001-0.01 per transaction
- Get ETH via:
  - Bridge: https://bridge.base.org
  - Buy on Coinbase, send to Base network

---

### Error: "Transaction underpriced"

**Symptom:**
```
Error: replacement transaction underpriced
```

**Solution:**
Increase gas price:
```python
# Get current gas price and add buffer
gas_price = web3.eth.gas_price
buffered_gas_price = int(gas_price * 1.2)  # 20% buffer

tx = {
    'gasPrice': buffered_gas_price,
    # ... other fields
}
```

---

### Error: "Nonce too low"

**Symptom:**
```
Error: nonce too low
```

**Solution:**
Get fresh nonce:
```python
nonce = web3.eth.get_transaction_count(account.address, 'pending')

tx = {
    'nonce': nonce,
    # ... other fields
}
```

---

## MCP Integration Issues

### Error: "MCP endpoint not found"

**Symptom:**
```
Error: POST /mcp/tools/call returned 404
```

**Solution:**
1. Verify MCP endpoint URL:
```python
MCP_ENDPOINT = "https://api.agentgatepay.com/mcp/tools/call"
```

2. Check API is accessible:
```bash
curl https://api.agentgatepay.com/health
```

---

### Error: "MCP tool not found"

**Symptom:**
```
Error: Tool 'agentpay_issue_mandates' not found
```

**Solution:**
Use exact tool name (check for typos):
```python
# Correct:
call_mcp_tool("agentpay_issue_mandate", {...})

# Wrong (plural):
call_mcp_tool("agentpay_issue_mandates", {...})
```

List available tools:
```python
response = requests.post(
    "https://api.agentgatepay.com/mcp/tools/list",
    json={"jsonrpc": "2.0", "method": "tools/list", "id": 1}
)
tools = response.json()['result']['tools']
for tool in tools:
    print(tool['name'])
```

---

### Error: "MCP JSON-RPC error"

**Symptom:**
```
Error: Invalid JSON-RPC 2.0 request
```

**Solution:**
Ensure correct payload format:
```python
payload = {
    "jsonrpc": "2.0",  # Required
    "method": "tools/call",  # Required
    "params": {  # Required
        "name": "agentpay_issue_mandate",
        "arguments": {"subject": "...", "budget_usd": 100}
    },
    "id": 1  # Required
}
```

---

## LangChain Agent Issues

### Error: "Agent execution timed out"

**Symptom:**
```
TimeoutError: Agent exceeded max_iterations
```

**Solution:**
Increase max iterations:
```python
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    max_iterations=30,  # Increase from default 15
    handle_parsing_errors=True
)
```

---

### Error: "OpenAI API key not found"

**Symptom:**
```
Error: OPENAI_API_KEY environment variable not set
```

**Solution:**
1. Add to `.env` file:
```bash
OPENAI_API_KEY=sk-YOUR_KEY_HERE
```

2. Or set in script:
```python
os.environ['OPENAI_API_KEY'] = 'sk-YOUR_KEY_HERE'
```

---

### Error: "Agent parsing error"

**Symptom:**
```
OutputParserException: Could not parse LLM output
```

**Solution:**
Enable error handling:
```python
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    handle_parsing_errors=True,  # Add this
    verbose=True
)
```

---

## Network & API Issues

### Error: "Connection timeout"

**Symptom:**
```
requests.exceptions.ConnectionError: Connection timed out
```

**Solution:**
1. Check internet connection
2. Increase timeout:
```python
response = requests.post(url, json=data, timeout=30)  # 30 seconds
```

3. Verify API is up:
```bash
curl https://api.agentgatepay.com/health
```

---

### Error: "Rate limit exceeded"

**Symptom:**
```
RateLimitError: Rate limit exceeded (100 requests/minute)
```

**Solution:**
1. Wait 60 seconds
2. If you have an API key, rate limit is higher (100/min vs 20/min)
3. Add retry logic:
```python
import time
from agentgatepay_sdk.exceptions import RateLimitError

try:
    result = agentpay.mandates.issue(...)
except RateLimitError:
    print("Rate limited, waiting 60 seconds...")
    time.sleep(60)
    result = agentpay.mandates.issue(...)  # Retry
```

---

### Error: "SSL certificate verification failed"

**Symptom:**
```
SSLError: [SSL: CERTIFICATE_VERIFY_FAILED]
```

**Solution:**
1. Update certificates:
```bash
# macOS:
/Applications/Python\ 3.12/Install\ Certificates.command

# Ubuntu/Debian:
sudo apt-get install ca-certificates
sudo update-ca-certificates
```

2. Or temporarily disable (NOT recommended for production):
```python
import requests
requests.post(url, json=data, verify=False)
```

---

## Still Having Issues?

### Check Logs

Enable verbose logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Run Tests

Validate your setup:
```bash
# Run integration tests
./test_integration.sh

# Run specific test
pytest tests/test_imports.py -v
```

### Get Help

- **GitHub Issues:** https://github.com/AgentGatePay/agentgatepay-examples/issues
- **Email Support:** support@agentgatepay.com
- **Documentation:** https://docs.agentgatepay.com

**When reporting issues, include:**
1. Python version (`python --version`)
2. SDK version (`pip show agentgatepay-sdk`)
3. Example you're running
4. Full error message
5. Relevant code snippet

---

## Useful Debug Commands

```bash
# Check Python version
python3 --version

# Check installed packages
pip list | grep agentgatepay

# Check environment variables
cat .env

# Check wallet balance (Base network)
# Visit: https://basescan.org/address/YOUR_WALLET_ADDRESS

# Check transaction status
# Visit: https://basescan.org/tx/YOUR_TX_HASH

# Test API connectivity
curl https://api.agentgatepay.com/health

# Test MCP endpoint
curl -X POST https://api.agentgatepay.com/mcp/tools/list \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

---

**📚 See Also:**
- [QUICK_START.md](QUICK_START.md) - Setup guide
- [API_INTEGRATION.md](API_INTEGRATION.md) - REST API details
- [MCP_INTEGRATION.md](MCP_INTEGRATION.md) - MCP tools details
- [README.md](../README.md) - Examples overview
