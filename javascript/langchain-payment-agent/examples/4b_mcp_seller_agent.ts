/**
 * AgentGatePay + LangChain Integration - SELLER AGENT (MCP TOOLS)
 *
 * This is the SELLER side of the marketplace interaction using MCP tools.
 * Run this FIRST, then run the buyer agent (4a_mcp_buyer_agent.ts).
 *
 * The seller agent:
 * - Provides a resource catalog (research papers, API access, etc.)
 * - Enforces HTTP 402 Payment Required protocol
 * - Verifies payments via AgentGatePay MCP tools (instead of REST API)
 * - Delivers resources after payment confirmation
 *
 * Usage:
 *     npm run example:4b
 *
 *     This starts an Express API on http://localhost:8000/resource
 *     The buyer agent will discover and purchase resources from this API.
 *
 * Requirements:
 * - npm install
 * - .env file with SELLER_API_KEY and SELLER_WALLET
 */

import 'dotenv/config';
import express, { Request, Response } from 'express';
import axios from 'axios';
import crypto from 'crypto';
import { getChainConfig, ChainConfig } from '../chain_config.js';

// ========================================
// CONFIGURATION
// ========================================

const AGENTPAY_API_URL = process.env.AGENTPAY_API_URL || 'https://api.agentgatepay.com';
const MCP_API_URL = process.env.MCP_API_URL || 'https://mcp.agentgatepay.com';
const SELLER_API_KEY = process.env.SELLER_API_KEY;
const SELLER_WALLET = process.env.SELLER_WALLET;
const COMMISSION_RATE = 0.005; // 0.5%

const SELLER_API_PORT = parseInt(process.env.SELLER_API_PORT || '8000', 10);

// Fetch commission address from API dynamically
async function getCommissionAddress(): Promise<string> {
  try {
    const response = await axios.get(
      `${AGENTPAY_API_URL}/v1/config/commission`,
      { headers: { 'x-api-key': SELLER_API_KEY || '' } }
    );
    return response.data.commission_address;
  } catch (error) {
    console.error(`⚠️  Failed to fetch commission address: ${error}`);
    return '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEbB'; // Fallback
  }
}

let COMMISSION_ADDRESS = '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEbB';

// ========================================
// MCP HELPER FUNCTIONS
// ========================================

async function callMcpTool(toolName: string, args: any): Promise<any> {
  const payload = {
    jsonrpc: '2.0',
    method: 'tools/call',
    params: {
      name: toolName,
      arguments: args
    },
    id: 1
  };

  const response = await axios.post(MCP_API_URL, payload, {
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': SELLER_API_KEY || ''
    },
    timeout: 30000
  });

  if (response.status !== 200) {
    throw new Error(`MCP call failed: HTTP ${response.status} - ${response.data}`);
  }

  if (response.data.error) {
    throw new Error(`MCP error: ${JSON.stringify(response.data.error)}`);
  }

  // Parse result content (MCP returns text in content array)
  const content = response.data.result?.content;
  if (content && content.length > 0) {
    return JSON.parse(content[0].text);
  }

  return {};
}

// ========================================
// SELLER AGENT CLASS (MCP VERSION)
// ========================================

interface Resource {
  id: string;
  name: string;
  price_usd: number;
  description: string;
  category: string;
  data: any;
}

interface Catalog {
  [key: string]: Resource;
}

class SellerAgentMCP {
  private config: ChainConfig;
  private pendingDeliveries: { [txHash: string]: string } = {};
  private webhookSecret: string | null = null;
  public catalog: Catalog;

  constructor(config: ChainConfig) {
    this.config = config;

    // Resource catalog - ADD YOUR RESOURCES HERE
    this.catalog = {
      'research-paper-2025': {
        id: 'research-paper-2025',
        name: 'AI Agent Payments Research Paper 2025',
        price_usd: 0.01,
        description: 'Comprehensive research on autonomous agent payment systems',
        category: 'research',
        data: {
          title: 'Autonomous Agent Payment Systems: A 2025 Perspective',
          authors: ['Dr. AI Researcher', 'Prof. Blockchain Expert'],
          abstract: 'This paper explores the evolution of payment systems for autonomous AI agents, covering AP2 mandates, x402 protocol, and multi-chain settlements.',
          pages: 42,
          published: '2025-01',
          doi: '10.1234/agentpay.2025.001',
          pdf_url: 'https://research.example.com/papers/agent-payments-2025.pdf'
        }
      },
      'market-data-api': {
        id: 'market-data-api',
        name: 'Premium Market Data API Access',
        price_usd: 5.0,
        description: 'Real-time market data feed with 1000 req/hour limit',
        category: 'api-access',
        data: {
          service: 'Premium Market Data API',
          endpoints: [
            'GET /v1/prices - Real-time asset prices',
            'GET /v1/volume - Trading volumes',
            'GET /v1/orderbook - Order book depth'
          ],
          rate_limit: '1000 requests/hour',
          api_key: 'premium_mkt_abc123xyz789',
          base_url: 'https://api.marketdata.example.com',
          documentation: 'https://docs.marketdata.example.com'
        }
      },
      'ai-model-training-dataset': {
        id: 'ai-model-training-dataset',
        name: 'Curated AI Training Dataset (10K samples)',
        price_usd: 25.0,
        description: 'High-quality labeled dataset for agent training',
        category: 'dataset',
        data: {
          name: 'AgentBehavior-10K Dataset',
          samples: 10000,
          format: 'JSONL',
          labels: ['intent', 'action', 'outcome', 'reward'],
          quality_score: 0.97,
          download_url: 'https://datasets.example.com/agentbehavior-10k.jsonl.gz',
          checksum_sha256: 'abc123def456...'
        }
      }
    };

    console.log(`\n💲 SELLER AGENT (MCP) INITIALIZED`);
    console.log('='.repeat(60));
    console.log(`Wallet: ${SELLER_WALLET}`);
    console.log(`Chain: ${config.chain.toUpperCase()} (ID: ${config.chainId})`);
    console.log(`Token: ${config.token} (${config.decimals} decimals)`);
    console.log(`Explorer: ${config.explorer}`);
    console.log(`MCP URL: ${MCP_API_URL}`);
    console.log(`Catalog: ${Object.keys(this.catalog).length} resources available`);
    console.log(`Listening on: http://localhost:${SELLER_API_PORT}/resource`);
    console.log('='.repeat(60));
  }

  async configureWebhook(webhookUrl: string): Promise<any> {
    console.log(`\n🔔 Configuring webhook for payment notifications...`);
    console.log(`   Webhook URL: ${webhookUrl}`);

    try {
      const response = await axios.post(
        `${AGENTPAY_API_URL}/v1/webhooks/configure`,
        {
          merchant_wallet: SELLER_WALLET,
          webhook_url: webhookUrl,
          events: ['payment.confirmed']
        },
        {
          headers: {
            'x-api-key': SELLER_API_KEY || '',
            'Content-Type': 'application/json'
          }
        }
      );

      if (response.status === 200) {
        const result = response.data;
        this.webhookSecret = result.webhook_secret;
        console.log(`   ✅ Webhook configured successfully`);
        console.log(`   Webhook ID: ${result.webhook_id}`);
        console.log(`   Secret: ${this.webhookSecret?.substring(0, 20)}... (for HMAC verification)`);
        return result;
      } else {
        const error = response.data.error || 'Unknown error';
        console.log(`   ⚠️  Webhook configuration failed: ${error}`);
        return { error };
      }
    } catch (error: any) {
      console.log(`   ⚠️  Webhook configuration error: ${error.message}`);
      return { error: error.message };
    }
  }

  verifyWebhookSignature(payload: Buffer, signature: string): boolean {
    if (!this.webhookSecret) return false;

    const expectedSig = crypto
      .createHmac('sha256', this.webhookSecret)
      .update(payload)
      .digest('hex');

    return crypto.timingSafeEqual(
      Buffer.from(expectedSig),
      Buffer.from(signature)
    );
  }

  handleWebhook(payload: any, signature: string): any {
    console.log(`\n🔔 [WEBHOOK] Received payment notification`);

    const event = payload.event;
    const txHash = payload.tx_hash;
    const amountUsd = payload.amount_usd;
    const merchantWallet = payload.merchant_wallet;

    console.log(`   Event: ${event}`);
    console.log(`   TX Hash: ${txHash?.substring(0, 20)}...`);
    console.log(`   Amount: $${amountUsd}`);
    console.log(`   Merchant: ${merchantWallet?.substring(0, 10)}...`);

    // Check if we have a pending delivery for this payment
    if (txHash in this.pendingDeliveries) {
      const resourceId = this.pendingDeliveries[txHash];
      const resource = this.catalog[resourceId];

      if (resource) {
        console.log(`   📦 Auto-delivering resource: ${resource.name}`);

        const deliveryInfo = {
          resource_id: resourceId,
          resource_name: resource.name,
          tx_hash: txHash,
          amount: amountUsd,
          delivered_at: Date.now() / 1000
        };

        console.log(`   ✅ Resource delivered successfully!`);

        // Remove from pending
        delete this.pendingDeliveries[txHash];

        return {
          status: 'delivered',
          delivery: deliveryInfo
        };
      }
    }

    console.log(`   ⚠️  No pending delivery found for this payment`);
    return { status: 'received', message: 'Payment confirmed but no pending delivery' };
  }

  listCatalog(): any {
    return {
      catalog: Object.values(this.catalog).map(res => ({
        id: res.id,
        name: res.name,
        price_usd: res.price_usd,
        description: res.description,
        category: res.category
      })),
      total_resources: Object.keys(this.catalog).length,
      payment_info: {
        chain: this.config.chain,
        token: this.config.token,
        chains_supported: ['ethereum', 'base', 'polygon', 'arbitrum'],
        tokens_supported: ['USDC', 'USDT', 'DAI'],
        commission_rate: COMMISSION_RATE,
        explorer: this.config.explorer
      }
    };
  }

  async handleResourceRequest(resourceId: string, paymentHeader?: string): Promise<{ status: number; body: any }> {
    // Check if resource exists
    const resource = this.catalog[resourceId];
    if (!resource) {
      console.log(`\n❌ [SELLER] Resource not found: ${resourceId}`);
      return {
        status: 404,
        body: {
          error: 'Resource not found',
          available_resources: Object.keys(this.catalog),
          catalog_url: `http://localhost:${SELLER_API_PORT}/catalog`
        }
      };
    }

    // If no payment provided → Return 402 Payment Required
    if (!paymentHeader) {
      console.log(`\n💳 [SELLER] Payment required for: ${resource.name}`);
      console.log(`   Price: $${resource.price_usd}`);
      console.log(`   Waiting for payment proof...`);

      return {
        status: 402,
        body: {
          error: 'Payment Required',
          message: 'This resource requires payment before access',
          resource: {
            id: resource.id,
            name: resource.name,
            description: resource.description,
            price_usd: resource.price_usd,
            category: resource.category
          },
          payment_info: {
            recipient_wallet: SELLER_WALLET,
            chain: this.config.chain,
            token: this.config.token,
            token_contract: this.config.tokenContract,
            decimals: this.config.decimals,
            commission_address: COMMISSION_ADDRESS,
            commission_rate: COMMISSION_RATE,
            total_amount_usd: resource.price_usd,
            merchant_amount_usd: resource.price_usd * (1 - COMMISSION_RATE),
            commission_amount_usd: resource.price_usd * COMMISSION_RATE
          },
          instructions: [
            '1. Sign two blockchain transactions (merchant + commission)',
            '2. Submit payment proof via x-payment header',
            '3. Format: \'merchant_tx_hash,commission_tx_hash\''
          ]
        }
      };
    }

    // Payment provided → Verify using MCP tool
    console.log(`\n🔍 [SELLER] Verifying payment for: ${resource.name}`);

    // Parse payment header
    const parts = paymentHeader.split(',');
    if (parts.length !== 2) {
      console.log(`   ❌ Invalid payment header format`);
      return {
        status: 400,
        body: {
          error: 'Invalid payment header format',
          expected_format: 'merchant_tx_hash,commission_tx_hash',
          received: paymentHeader
        }
      };
    }

    const txHashMerchant = parts[0].trim();
    const txHashCommission = parts[1].trim();

    console.log(`   Merchant TX: ${txHashMerchant.substring(0, 20)}...`);
    console.log(`   Commission TX: ${txHashCommission.substring(0, 20)}...`);

    // Verify merchant payment via MCP tool with retry logic
    console.log(`   📡 Calling MCP tool: agentpay_verify_payment...`);

    // Adaptive retry strategy based on payment amount
    let maxRetries: number;
    let retryDelay: number;

    if (resource.price_usd < 1.0) {
      maxRetries = 6; // More retries for optimistic mode
      retryDelay = 10; // Longer delays
      console.log(`   💨 Optimistic mode expected (payment <$1)`);
      console.log(`   ⏳ Will retry up to ${maxRetries} times over ~90 seconds`);
    } else {
      maxRetries = 12; // Extended retries for public RPC propagation
      retryDelay = 10;
      console.log(`   ✅ Synchronous mode expected (payment ≥$1)`);
      console.log(`   ⏳ Will retry up to ${maxRetries} times over ~120 seconds`);
    }

    let verification: any = null;
    let lastError: string | null = null;

    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        verification = await callMcpTool('agentpay_verify_payment', {
          tx_hash: txHashMerchant,
          chain: this.config.chain
        });

        // Check verification result
        if (verification.verified) {
          const status = verification.status || 'unknown';
          if (status === 'pending') {
            console.log(`   💨 Payment verified (OPTIMISTIC MODE)`);
            console.log(`   ✅ Accepting payment`);
          } else {
            console.log(`   ✅ Payment verified (ON-CHAIN CONFIRMED)`);
          }
          break;
        } else if (verification.status === 'pending' && attempt < maxRetries - 1) {
          console.log(`   ⏳ Payment status: PENDING (attempt ${attempt + 1}/${maxRetries}), retrying in ${retryDelay}s...`);
          await new Promise(resolve => setTimeout(resolve, retryDelay * 1000));
        } else if (verification.error === 'Payment not found' && attempt < maxRetries - 1) {
          console.log(`   ⏳ Payment not found yet (attempt ${attempt + 1}/${maxRetries}), retrying in ${retryDelay}s...`);
          await new Promise(resolve => setTimeout(resolve, retryDelay * 1000));
        } else {
          lastError = verification.error || 'Unknown verification error';
          break;
        }
      } catch (error: any) {
        lastError = error.message;
        if (attempt < maxRetries - 1) {
          console.log(`   ⏳ Verification error (attempt ${attempt + 1}/${maxRetries}), retrying in ${retryDelay}s...`);
          console.log(`      Error: ${lastError}`);
          await new Promise(resolve => setTimeout(resolve, retryDelay * 1000));
        } else {
          break;
        }
      }
    }

    if (!verification || !verification.verified) {
      const errorMsg = lastError || 'Unknown verification error';
      console.log(`   ❌ Payment verification failed: ${errorMsg}`);
      return {
        status: 403,
        body: {
          error: 'Payment verification failed',
          message: errorMsg,
          tx_hash: txHashMerchant
        }
      };
    }

    // Verify amount matches resource price (allow $0.01 tolerance)
    const paidAmount = parseFloat(verification.amount_usd || '0');
    const expectedMerchantAmount = resource.price_usd * (1 - COMMISSION_RATE);

    if (Math.abs(paidAmount - expectedMerchantAmount) > 0.01) {
      console.log(`   ❌ Amount mismatch: expected $${expectedMerchantAmount.toFixed(2)}, got $${paidAmount.toFixed(2)}`);
      return {
        status: 403,
        body: {
          error: 'Payment amount mismatch',
          expected_usd: expectedMerchantAmount,
          received_usd: paidAmount,
          tolerance: 0.01
        }
      };
    }

    // Payment verified → Deliver resource
    console.log(`   ✅ Payment verified successfully!`);
    console.log(`   💰 Amount: $${paidAmount.toFixed(2)}`);
    console.log(`   📦 Delivering resource to buyer...`);

    return {
      status: 200,
      body: {
        message: 'Payment verified. Resource access granted.',
        resource: resource.data,
        payment_confirmation: {
          merchant_tx: txHashMerchant,
          commission_tx: txHashCommission,
          amount_verified_usd: paidAmount,
          verification_time: verification.timestamp,
          blockchain_explorer: `${this.config.explorer}/tx/${txHashMerchant}`
        },
        delivery_info: {
          resource_id: resource.id,
          resource_name: resource.name,
          delivered_at: verification.timestamp
        }
      }
    };
  }
}

// ========================================
// EXPRESS API
// ========================================

const app = express();
app.use(express.json());

let seller: SellerAgentMCP;

app.get('/resource', async (req: Request, res: Response) => {
  const resourceId = req.query.resource_id as string;
  const paymentHeader = req.headers['x-payment'] as string | undefined;

  if (!resourceId) {
    return res.status(400).json({
      error: 'Missing resource_id parameter',
      usage: 'GET /resource?resource_id=<id>',
      catalog_endpoint: '/catalog'
    });
  }

  const response = await seller.handleResourceRequest(resourceId, paymentHeader);
  return res.status(response.status).json(response.body);
});

app.get('/catalog', (req: Request, res: Response) => {
  return res.status(200).json(seller.listCatalog());
});

app.get('/health', (req: Request, res: Response) => {
  return res.status(200).json({
    status: 'healthy',
    seller_wallet: SELLER_WALLET,
    resources_available: Object.keys(seller.catalog).length
  });
});

app.post('/webhooks/payment', async (req: Request, res: Response) => {
  try {
    const payload = req.body;
    const signature = req.headers['x-webhook-signature'] as string || '';

    const result = seller.handleWebhook(payload, signature);
    return res.status(200).json(result);
  } catch (error: any) {
    console.error(`❌ Webhook error: ${error.message}`);
    return res.status(500).json({ error: error.message });
  }
});

// ========================================
// MAIN
// ========================================

async function main() {
  console.log('\n' + '='.repeat(60));
  console.log('🏪 SELLER AGENT - RESOURCE MARKETPLACE API (MCP)');
  console.log('='.repeat(60));
  console.log();
  console.log('This agent provides resources for sale to buyer agents.');
  console.log('Buyers can discover resources and purchase with blockchain payments.');
  console.log();
  console.log('Payment verification uses MCP tools instead of REST API SDK.');
  console.log();

  // Load commission address
  COMMISSION_ADDRESS = await getCommissionAddress();

  // Load chain/token configuration
  console.log('\n🔧 CHAIN & TOKEN CONFIGURATION');
  console.log('='.repeat(60));
  const config = getChainConfig();

  console.log(`\nUsing configuration from .env:`);
  console.log(`  Chain: ${config.chain.charAt(0).toUpperCase() + config.chain.slice(1)} (ID: ${config.chainId})`);
  console.log(`  Token: ${config.token} (${config.decimals} decimals)`);
  console.log(`  To change: Edit PAYMENT_CHAIN and PAYMENT_TOKEN in .env file`);
  console.log('='.repeat(60));

  // Initialize seller agent
  seller = new SellerAgentMCP(config);

  // Set default prices to $0.01
  console.log(`\n💵 Setting all resources to default price: $0.01`);
  for (const resId in seller.catalog) {
    seller.catalog[resId].price_usd = 0.01;
  }

  console.log(`\n✅ Final prices:`);
  for (const resId in seller.catalog) {
    const res = seller.catalog[resId];
    console.log(`   - ${res.name}: $${res.price_usd}`);
  }

  console.log();
  console.log(`📋 Endpoints:`);
  console.log(`   GET /catalog                - List all resources`);
  console.log(`   GET /resource?resource_id=<id>  - Purchase resource`);
  console.log(`   POST /webhooks/payment      - Webhook for payment notifications`);
  console.log(`   GET /health                 - Health check`);
  console.log();

  console.log('='.repeat(60));
  console.log('🔔 WEBHOOK CONFIGURATION (PRODUCTION MODE)');
  console.log('='.repeat(60));
  console.log();
  console.log('For production deployment, configure webhooks to receive');
  console.log('automatic payment notifications from AgentGatePay.');
  console.log();
  console.log('⚠️  For local testing, webhooks require a public URL.');
  console.log('   Options: ngrok, localtunnel, Render, Railway, etc.');
  console.log();
  console.log('⚠️  Skipping webhook configuration (using manual verification)');
  console.log('   Note: For production, webhooks provide better UX and scalability');

  console.log();
  console.log(`💡 MCP Tools Used:`);
  console.log(`   - agentpay_verify_payment (payment verification)`);
  console.log();
  console.log('='.repeat(60));
  console.log();
  console.log('💡 Next step: Run the buyer agent (4a_mcp_buyer_agent.ts)');
  console.log();

  // Start Express API
  app.listen(SELLER_API_PORT, '0.0.0.0', () => {
    console.log(`🚀 Seller API listening on http://0.0.0.0:${SELLER_API_PORT}`);
  });
}

main().catch(console.error);
