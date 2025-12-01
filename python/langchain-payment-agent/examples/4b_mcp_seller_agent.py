#!/usr/bin/env python3
"""
AgentGatePay + LangChain Integration - SELLER AGENT (MCP TOOLS)

This is the SELLER side of the marketplace interaction using MCP tools.
Run this FIRST, then run the buyer agent (4a_mcp_buyer_agent.py).

The seller agent:
- Provides a resource catalog (research papers, API access, etc.)
- Enforces HTTP 402 Payment Required protocol
- Verifies payments via AgentGatePay MCP tools (instead of REST API)
- Delivers resources after payment confirmation

Usage:
    python 4b_mcp_seller_agent.py

    This starts a Flask API on http://localhost:8000/resource
    The buyer agent will discover and purchase resources from this API.

Requirements:
- pip install flask python-dotenv requests
- .env file with SELLER_API_KEY and SELLER_WALLET
"""

import os
import sys
import time
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from flask import Flask, request, jsonify

# Add parent directory to path for chain_config import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Load environment variables FIRST
load_dotenv()

# Chain configuration from .env
from chain_config import get_chain_config, ChainConfig

# ========================================
# CONFIGURATION
# ========================================

AGENTPAY_API_URL = os.getenv('AGENTPAY_API_URL', 'https://api.agentgatepay.com')
MCP_API_URL = os.getenv('MCP_API_URL', 'https://mcp.agentgatepay.com')
SELLER_API_KEY = os.getenv('SELLER_API_KEY')
SELLER_WALLET = os.getenv('SELLER_WALLET')
COMMISSION_RATE = 0.005  # 0.5%

SELLER_API_PORT = int(os.getenv('SELLER_API_PORT', 8000))

# Chain/token configuration - will be selected interactively on first run
CHAIN_CONFIG = None  # Set in main() from monitoring config

# Fetch commission address from API dynamically
def get_commission_address():
    """Fetch live commission address from AgentGatePay API"""
    import requests
    try:
        response = requests.get(
            f"{AGENTPAY_API_URL}/v1/config/commission",
            headers={"x-api-key": SELLER_API_KEY}
        )
        response.raise_for_status()
        config = response.json()
        return config.get('commission_address')
    except Exception as e:
        print(f"⚠️  Failed to fetch commission address: {e}")
        return "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEbB"  # Fallback

COMMISSION_ADDRESS = get_commission_address()

# ========================================
# MCP HELPER FUNCTIONS
# ========================================

def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call AgentGatePay MCP tool via JSON-RPC 2.0.

    Args:
        tool_name: MCP tool name (e.g., 'agentpay_verify_payment')
        arguments: Tool-specific arguments

    Returns:
        Tool result as dictionary
    """
    import requests

    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        },
        "id": 1
    }

    headers = {
        "Content-Type": "application/json",
        "x-api-key": SELLER_API_KEY
    }

    response = requests.post(MCP_API_URL, json=payload, headers=headers, timeout=30)

    if response.status_code != 200:
        raise Exception(f"MCP call failed: HTTP {response.status_code} - {response.text}")

    result = response.json()

    if "error" in result:
        raise Exception(f"MCP error: {result['error']}")

    # Parse result content (MCP returns text in content array)
    content = result.get('result', {}).get('content', [])
    if content and len(content) > 0:
        return json.loads(content[0]['text'])

    return {}


# ========================================
# SELLER AGENT CLASS (MCP VERSION)
# ========================================

class SellerAgentMCP:
    """
    Autonomous seller agent that monetizes resources via blockchain payments.

    Features:
    - Resource catalog with dynamic pricing
    - HTTP 402 Payment Required protocol
    - AgentGatePay MCP payment verification (instead of REST API SDK)
    - Automatic resource delivery after payment
    """

    def __init__(self, config: ChainConfig):
        # Store chain/token config
        self.config = config

        # Resource catalog - ADD YOUR RESOURCES HERE
        self.catalog = {
            "research-paper-2025": {
                "id": "research-paper-2025",
                "name": "AI Agent Payments Research Paper 2025",
                "price_usd": 0.01,
                "description": "Comprehensive research on autonomous agent payment systems",
                "category": "research",
                "data": {
                    "title": "Autonomous Agent Payment Systems: A 2025 Perspective",
                    "authors": ["Dr. AI Researcher", "Prof. Blockchain Expert"],
                    "abstract": "This paper explores the evolution of payment systems for autonomous AI agents, covering AP2 mandates, x402 protocol, and multi-chain settlements.",
                    "pages": 42,
                    "published": "2025-01",
                    "doi": "10.1234/agentpay.2025.001",
                    "pdf_url": "https://research.example.com/papers/agent-payments-2025.pdf"
                }
            },
            "market-data-api": {
                "id": "market-data-api",
                "name": "Premium Market Data API Access",
                "price_usd": 5.0,
                "description": "Real-time market data feed with 1000 req/hour limit",
                "category": "api-access",
                "data": {
                    "service": "Premium Market Data API",
                    "endpoints": [
                        "GET /v1/prices - Real-time asset prices",
                        "GET /v1/volume - Trading volumes",
                        "GET /v1/orderbook - Order book depth"
                    ],
                    "rate_limit": "1000 requests/hour",
                    "api_key": "premium_mkt_abc123xyz789",
                    "base_url": "https://api.marketdata.example.com",
                    "documentation": "https://docs.marketdata.example.com"
                }
            },
            "ai-model-training-dataset": {
                "id": "ai-model-training-dataset",
                "name": "Curated AI Training Dataset (10K samples)",
                "price_usd": 25.0,
                "description": "High-quality labeled dataset for agent training",
                "category": "dataset",
                "data": {
                    "name": "AgentBehavior-10K Dataset",
                    "samples": 10000,
                    "format": "JSONL",
                    "labels": ["intent", "action", "outcome", "reward"],
                    "quality_score": 0.97,
                    "download_url": "https://datasets.example.com/agentbehavior-10k.jsonl.gz",
                    "checksum_sha256": "abc123def456..."
                }
            }
        }

        print(f"\n💲 SELLER AGENT (MCP) INITIALIZED")
        print(f"=" * 60)
        print(f"Wallet: {SELLER_WALLET}")
        print(f"Chain: {config.chain.upper()} (ID: {config.chain_id})")
        print(f"Token: {config.token} ({config.decimals} decimals)")
        print(f"Explorer: {config.explorer}")
        print(f"MCP URL: {MCP_API_URL}")
        print(f"Catalog: {len(self.catalog)} resources available")
        print(f"Listening on: http://localhost:{SELLER_API_PORT}/resource")
        print(f"=" * 60)

    def list_catalog(self) -> Dict[str, Any]:
        """Return full resource catalog"""
        return {
            "catalog": [
                {
                    "id": res["id"],
                    "name": res["name"],
                    "price_usd": res["price_usd"],
                    "description": res["description"],
                    "category": res["category"]
                }
                for res in self.catalog.values()
            ],
            "total_resources": len(self.catalog),
            "payment_info": {
                "chain": self.config.chain,
                "token": self.config.token,
                "chains_supported": ["ethereum", "base", "polygon", "arbitrum"],
                "tokens_supported": ["USDC", "USDT", "DAI"],
                "commission_rate": COMMISSION_RATE,
                "explorer": self.config.explorer
            }
        }

    def handle_resource_request(self, resource_id: str, payment_header: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle resource request with HTTP 402 protocol.

        Args:
            resource_id: Resource identifier
            payment_header: x-payment header (format: "tx_hash,tx_hash_commission")

        Returns:
            Response dict with status code and body
        """
        # Check if resource exists
        resource = self.catalog.get(resource_id)
        if not resource:
            print(f"\n❌ [SELLER] Resource not found: {resource_id}")
            return {
                "status": 404,
                "body": {
                    "error": "Resource not found",
                    "available_resources": list(self.catalog.keys()),
                    "catalog_url": f"http://localhost:{SELLER_API_PORT}/catalog"
                }
            }

        # If no payment provided → Return 402 Payment Required
        if not payment_header:
            print(f"\n💳 [SELLER] Payment required for: {resource['name']}")
            print(f"   Price: ${resource['price_usd']}")
            print(f"   Waiting for payment proof...")

            return {
                "status": 402,
                "body": {
                    "error": "Payment Required",
                    "message": "This resource requires payment before access",
                    "resource": {
                        "id": resource['id'],
                        "name": resource['name'],
                        "description": resource['description'],
                        "price_usd": resource['price_usd'],
                        "category": resource['category']
                    },
                    "payment_info": {
                        "recipient_wallet": SELLER_WALLET,
                        "chain": self.config.chain,
                        "token": self.config.token,
                        "token_contract": self.config.token_contract,
                        "decimals": self.config.decimals,
                        "commission_address": COMMISSION_ADDRESS,
                        "commission_rate": COMMISSION_RATE,
                        "total_amount_usd": resource['price_usd'],
                        "merchant_amount_usd": resource['price_usd'] * (1 - COMMISSION_RATE),
                        "commission_amount_usd": resource['price_usd'] * COMMISSION_RATE
                    },
                    "instructions": [
                        "1. Sign two blockchain transactions (merchant + commission)",
                        "2. Submit payment proof via x-payment header",
                        "3. Format: 'merchant_tx_hash,commission_tx_hash'"
                    ]
                }
            }

        # Payment provided → Verify using MCP tool
        print(f"\n🔍 [SELLER] Verifying payment for: {resource['name']}")

        # Parse payment header
        parts = payment_header.split(',')
        if len(parts) != 2:
            print(f"   ❌ Invalid payment header format")
            return {
                "status": 400,
                "body": {
                    "error": "Invalid payment header format",
                    "expected_format": "merchant_tx_hash,commission_tx_hash",
                    "received": payment_header
                }
            }

        tx_hash_merchant = parts[0].strip()
        tx_hash_commission = parts[1].strip()

        print(f"   Merchant TX: {tx_hash_merchant[:20]}...")
        print(f"   Commission TX: {tx_hash_commission[:20]}...")

        # Verify merchant payment via MCP tool with retry logic
        print(f"   📡 Calling MCP tool: agentpay_verify_payment...")

        # Adaptive retry strategy based on payment amount
        if resource['price_usd'] < 1.0:
            max_retries = 6  # More retries for optimistic mode
            retry_delay = 10  # Longer delays
            print(f"   💨 Optimistic mode expected (payment <$1)")
            print(f"   ⏳ Will retry up to {max_retries} times over ~90 seconds")
        else:
            max_retries = 12  # Extended retries for public RPC propagation
            retry_delay = 10
            print(f"   ✅ Synchronous mode expected (payment ≥$1)")
            print(f"   ⏳ Will retry up to {max_retries} times over ~120 seconds")

        verification = None
        last_error = None

        for attempt in range(max_retries):
            try:
                verification = call_mcp_tool("agentpay_verify_payment", {
                    "tx_hash": tx_hash_merchant,
                    "chain": self.config.chain
                })

                # Check verification result
                if verification.get('verified'):
                    status = verification.get('status', 'unknown')
                    if status == 'pending':
                        print(f"   💨 Payment verified (OPTIMISTIC MODE)")
                        print(f"   ✅ Accepting payment")
                    else:
                        print(f"   ✅ Payment verified (ON-CHAIN CONFIRMED)")
                    break
                elif verification.get('status') == 'pending' and attempt < max_retries - 1:
                    print(f"   ⏳ Payment status: PENDING (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                elif verification.get('error') == 'Payment not found' and attempt < max_retries - 1:
                    print(f"   ⏳ Payment not found yet (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    last_error = verification.get('error', 'Unknown verification error')
                    break
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries - 1:
                    print(f"   ⏳ Verification error (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s...")
                    print(f"      Error: {last_error}")
                    time.sleep(retry_delay)
                else:
                    break

        if not verification or not verification.get('verified'):
            error_msg = last_error or 'Unknown verification error'
            print(f"   ❌ Payment verification failed: {error_msg}")
            return {
                "status": 403,
                "body": {
                    "error": "Payment verification failed",
                    "message": error_msg,
                    "tx_hash": tx_hash_merchant
                }
            }

        # Verify amount matches resource price (allow $0.01 tolerance)
        paid_amount = float(verification.get('amount_usd', 0))
        expected_merchant_amount = resource['price_usd'] * (1 - COMMISSION_RATE)

        if abs(paid_amount - expected_merchant_amount) > 0.01:
            print(f"   ❌ Amount mismatch: expected ${expected_merchant_amount:.2f}, got ${paid_amount:.2f}")
            return {
                "status": 403,
                "body": {
                    "error": "Payment amount mismatch",
                    "expected_usd": expected_merchant_amount,
                    "received_usd": paid_amount,
                    "tolerance": 0.01
                }
            }

        # Payment verified → Deliver resource
        print(f"   ✅ Payment verified successfully!")
        print(f"   💰 Amount: ${paid_amount:.2f}")
        print(f"   📦 Delivering resource to buyer...")

        return {
            "status": 200,
            "body": {
                "message": "Payment verified. Resource access granted.",
                "resource": resource['data'],
                "payment_confirmation": {
                    "merchant_tx": tx_hash_merchant,
                    "commission_tx": tx_hash_commission,
                    "amount_verified_usd": paid_amount,
                    "verification_time": verification.get('timestamp'),
                    "blockchain_explorer": f"{self.config.explorer}/tx/{tx_hash_merchant}"
                },
                "delivery_info": {
                    "resource_id": resource['id'],
                    "resource_name": resource['name'],
                    "delivered_at": verification.get('timestamp')
                }
            }
        }


# ========================================
# FLASK API
# ========================================

app = Flask(__name__)
seller = None  # Will be initialized in main() after config selection


@app.route('/resource', methods=['GET'])
def resource_endpoint():
    """Main resource endpoint - handles discovery and purchase"""
    resource_id = request.args.get('resource_id')
    payment_header = request.headers.get('x-payment')

    if not resource_id:
        return jsonify({
            "error": "Missing resource_id parameter",
            "usage": "GET /resource?resource_id=<id>",
            "catalog_endpoint": "/catalog"
        }), 400

    response = seller.handle_resource_request(resource_id, payment_header)
    return jsonify(response['body']), response['status']


@app.route('/catalog', methods=['GET'])
def catalog_endpoint():
    """List all available resources"""
    return jsonify(seller.list_catalog()), 200


@app.route('/health', methods=['GET'])
def health_endpoint():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "seller_wallet": SELLER_WALLET,
        "resources_available": len(seller.catalog)
    }), 200


# ========================================
# MAIN
# ========================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🏪 SELLER AGENT - RESOURCE MARKETPLACE API (MCP)")
    print("=" * 60)
    print()
    print("This agent provides resources for sale to buyer agents.")
    print("Buyers can discover resources and purchase with blockchain payments.")
    print()
    print("Payment verification uses MCP tools instead of REST API SDK.")
    print()

    # ========================================
    # STEP 0: LOAD CHAIN AND TOKEN FROM .ENV
    # ========================================

    print("\n🔧 CHAIN & TOKEN CONFIGURATION")
    print("=" * 60)
    config = get_chain_config()

    print(f"\nUsing configuration from .env:")
    print(f"  Chain: {config.chain.title()} (ID: {config.chain_id})")
    print(f"  Token: {config.token} ({config.decimals} decimals)")
    print(f"  To change: Edit PAYMENT_CHAIN and PAYMENT_TOKEN in .env file")
    print("=" * 60)

    # Initialize seller agent with selected config
    seller = SellerAgentMCP(config)

    # Ask user to set resource prices
    print(f"\n💵 Set resource prices (press Enter for default $0.01):")
    for res_id, res in seller.catalog.items():
        price_input = input(f"   {res['name']}: $").strip()
        if price_input:
            try:
                new_price = float(price_input)
                if new_price > 0:
                    seller.catalog[res_id]['price_usd'] = new_price
                    print(f"      ✅ Set to ${new_price}")
                else:
                    print(f"      ⚠️  Invalid price, using default $0.01")
                    seller.catalog[res_id]['price_usd'] = 0.01
            except ValueError:
                print(f"      ⚠️  Invalid input, using default $0.01")
                seller.catalog[res_id]['price_usd'] = 0.01
        else:
            # User pressed Enter without typing - default to $0.01
            seller.catalog[res_id]['price_usd'] = 0.01
            print(f"      ✅ Set to default: $0.01")

    print(f"\n✅ Final prices:")
    for res_id, res in seller.catalog.items():
        print(f"   - {res['name']}: ${res['price_usd']}")

    print()
    print(f"📋 Endpoints:")
    print(f"   GET /catalog                - List all resources")
    print(f"   GET /resource?resource_id=<id>  - Purchase resource")
    print(f"   GET /health                 - Health check")
    print()
    print(f"💡 MCP Tools Used:")
    print(f"   - agentpay_verify_payment (payment verification)")
    print()
    print("=" * 60)
    print()
    print("💡 Next step: Run the buyer agent (4a_mcp_buyer_agent.py)")
    print()

    # Start Flask API
    app.run(
        host='0.0.0.0',
        port=SELLER_API_PORT,
        debug=False  # Set to True for development
    )
