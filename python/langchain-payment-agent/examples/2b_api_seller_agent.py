#!/usr/bin/env python3
"""
AgentGatePay + LangChain Integration - SELLER AGENT (REST API)

This is the SELLER side of the marketplace interaction.
Run this FIRST, then run the buyer agent (2a_api_buyer_agent.py).

The seller agent:
- Provides a resource catalog (research papers, API access, etc.)
- Enforces HTTP 402 Payment Required protocol
- Verifies payments via AgentGatePay API
- Delivers resources after payment confirmation

Usage:
    python 2b_api_seller_agent.py

    This starts a Flask API on http://localhost:8000/resource
    The buyer agent will discover and purchase resources from this API.

Requirements:
- pip install agentgatepay-sdk>=1.1.3 flask python-dotenv
- .env file with SELLER_API_KEY and SELLER_WALLET
"""

import os
import time
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from agentgatepay_sdk import AgentGatePay

# Load environment variables
load_dotenv()

# ========================================
# CONFIGURATION
# ========================================

AGENTPAY_API_URL = os.getenv('AGENTPAY_API_URL', 'https://api.agentgatepay.com')
SELLER_API_KEY = os.getenv('SELLER_API_KEY')
SELLER_WALLET = os.getenv('SELLER_WALLET')
COMMISSION_RATE = 0.005  # 0.5%

SELLER_API_PORT = int(os.getenv('SELLER_API_PORT', 8000))

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
# SELLER AGENT CLASS
# ========================================

class SellerAgent:
    """
    Autonomous seller agent that monetizes resources via blockchain payments.

    Features:
    - Resource catalog with dynamic pricing
    - HTTP 402 Payment Required protocol
    - AgentGatePay API payment verification
    - Automatic resource delivery after payment
    """

    def __init__(self):
        # Initialize AgentGatePay client
        self.agentpay = AgentGatePay(
            api_url=AGENTPAY_API_URL,
            api_key=SELLER_API_KEY
        )

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

        print(f"\n💲 SELLER AGENT INITIALIZED")
        print(f"=" * 60)
        print(f"Wallet: {SELLER_WALLET}")
        print(f"API URL: {AGENTPAY_API_URL}")
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
                "chains_supported": ["ethereum", "base", "polygon", "arbitrum"],
                "tokens_supported": ["USDC", "USDT", "DAI"],
                "commission_rate": COMMISSION_RATE
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
                        "chain": "base",
                        "token": "USDC",
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

        # Payment provided → Verify
        print(f"\n🔍 [SELLER] Verifying payment for: {resource['name']}")

        try:
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

            # Verify merchant payment via AgentGatePay API
            print(f"   📡 Calling AgentGatePay API for verification...")
            verification = self.agentpay.payments.verify(tx_hash_merchant)

            if not verification.get('verified'):
                error_msg = verification.get('error', 'Unknown verification error')
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
                        "blockchain_explorer": f"https://basescan.org/tx/{tx_hash_merchant}"
                    },
                    "delivery_info": {
                        "resource_id": resource['id'],
                        "resource_name": resource['name'],
                        "delivered_at": verification.get('timestamp')
                    }
                }
            }

        except Exception as e:
            print(f"   ❌ Verification error: {str(e)}")
            return {
                "status": 500,
                "body": {
                    "error": "Internal server error during payment verification",
                    "message": str(e)
                }
            }


# ========================================
# FLASK API
# ========================================

app = Flask(__name__)
seller = SellerAgent()


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
    print("🏪 SELLER AGENT - RESOURCE MARKETPLACE API")
    print("=" * 60)
    print()
    print("This agent provides resources for sale to buyer agents.")
    print("Buyers can discover resources and purchase with blockchain payments.")
    print()
    print(f"📋 Endpoints:")
    print(f"   GET /catalog           - List all resources")
    print(f"   GET /resource?resource_id=<id>  - Purchase resource")
    print(f"   GET /health            - Health check")
    print()
    print("=" * 60)
    print()
    print("💡 Next step: Run the buyer agent (2a_api_buyer_agent.py)")
    print()

    # Start Flask API
    app.run(
        host='0.0.0.0',
        port=SELLER_API_PORT,
        debug=False  # Set to True for development
    )
