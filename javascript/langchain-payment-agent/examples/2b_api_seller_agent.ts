#!/usr/bin/env tsx
/**
 * AgentGatePay + LangChain.js Integration - SELLER AGENT (REST API)
 *
 * This is the SELLER side of the marketplace interaction.
 * Run this FIRST, then run the buyer agent (2a_api_buyer_agent.ts).
 *
 * The seller agent:
 * - Provides a resource catalog (research papers, API access, etc.)
 * - Enforces HTTP 402 Payment Required protocol
 * - Verifies payments via AgentGatePay API
 * - Receives webhook notifications for automatic delivery (PRODUCTION MODE)
 * - Delivers resources after payment confirmation
 *
 * Usage:
 *     npm run example:2b
 *
 *     This starts an Express API on http://localhost:8000/resource
 *     The buyer agent will discover and purchase resources from this API.
 *
 * Requirements:
 * - npm install
 * - .env file with SELLER_API_KEY and SELLER_WALLET
 */

import { config } from 'dotenv';
import express, { Request, Response } from 'express';
import { createHmac, timingSafeEqual } from 'crypto';
import axios from 'axios';
import readline from 'readline';
import { AgentGatePay } from 'agentgatepay-sdk';
import { getChainConfig, type ChainConfig } from '../chain_config.js';

// Load environment variables
config();

// Helper function for user input
function question(prompt: string): Promise<string> {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });

  return new Promise((resolve) => {
    rl.question(prompt, (answer) => {
      rl.close();
      resolve(answer);
    });
  });
}

// ========================================
// CONFIGURATION
// ========================================

const AGENTPAY_API_URL = process.env.AGENTPAY_API_URL || 'https://api.agentgatepay.com';
const SELLER_API_KEY = process.env.SELLER_API_KEY!;
const SELLER_WALLET = process.env.SELLER_WALLET!;
const COMMISSION_RATE = 0.005; // 0.5%
const SELLER_API_PORT = parseInt(process.env.SELLER_API_PORT || '8000');

// Fetch commission address from API dynamically
async function getCommissionAddress(): Promise<string> {
  try {
    const response = await axios.get(`${AGENTPAY_API_URL}/v1/config/commission`, {
      headers: { 'x-api-key': SELLER_API_KEY }
    });
    return response.data.commission_address;
  } catch (error) {
    console.error('⚠️  Failed to fetch commission address:', error);
    return '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEbB'; // Fallback
  }
}

let COMMISSION_ADDRESS: string;

// Chain/token configuration
let CHAIN_CONFIG: ChainConfig;

// ========================================
// SELLER AGENT CLASS
// ========================================

interface Resource {
  id: string;
  name: string;
  price_usd: number;
  description: string;
  category: string;
  data: any;
}

class SellerAgent {
  private agentpay: AgentGatePay;
  private config: ChainConfig;
  private pendingDeliveries: Map<string, string> = new Map();
  private webhookSecret: string | null = null;
  public catalog: Record<string, Resource>;

  constructor(config: ChainConfig) {
    this.agentpay = new AgentGatePay({
      apiUrl: AGENTPAY_API_URL,
      apiKey: SELLER_API_KEY
    });

    this.config = config;

    // Resource catalog
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

    console.log(`\n💲 SELLER AGENT INITIALIZED`);
    console.log('='.repeat(60));
    console.log(`Wallet: ${SELLER_WALLET}`);
    console.log(`Chain: ${config.chain.toUpperCase()} (ID: ${config.chainId})`);
    console.log(`Token: ${config.token} (${config.decimals} decimals)`);
    console.log(`Explorer: ${config.explorer}`);
    console.log(`API URL: ${AGENTPAY_API_URL}`);
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
            'x-api-key': SELLER_API_KEY,
            'Content-Type': 'application/json'
          }
        }
      );

      if (response.status === 200) {
        const result = response.data;
        this.webhookSecret = result.webhook_secret;
        console.log(`   ✅ Webhook configured successfully`);
        console.log(`   Webhook ID: ${result.webhook_id}`);
        console.log(`   Secret: ${this.webhookSecret?.slice(0, 20)}... (for HMAC verification)`);
        return result;
      }
    } catch (error: any) {
      const errorMsg = error.response?.data?.error || error.message;
      console.log(`   ⚠️  Webhook configuration failed: ${errorMsg}`);
      return { error: errorMsg };
    }
  }

  verifyWebhookSignature(payload: string, signature: string): boolean {
    if (!this.webhookSecret) return false;

    const expectedSig = createHmac('sha256', this.webhookSecret)
      .update(payload)
      .digest('hex');

    try {
      return timingSafeEqual(Buffer.from(expectedSig), Buffer.from(signature));
    } catch {
      return false;
    }
  }

  handleWebhook(payload: any, signature: string): any {
    console.log(`\n🔔 [WEBHOOK] Received payment notification`);

    const event = payload.event;
    const txHash = payload.tx_hash;
    const amountUsd = payload.amount_usd;
    const merchantWallet = payload.merchant_wallet;

    console.log(`   Event: ${event}`);
    console.log(`   TX Hash: ${txHash?.slice(0, 20)}...`);
    console.log(`   Amount: $${amountUsd}`);
    console.log(`   Merchant: ${merchantWallet?.slice(0, 10)}...`);

    if (txHash && this.pendingDeliveries.has(txHash)) {
      const resourceId = this.pendingDeliveries.get(txHash)!;
      const resource = this.catalog[resourceId];

      if (resource) {
        console.log(`   📦 Auto-delivering resource: ${resource.name}`);

        const deliveryInfo = {
          resource_id: resourceId,
          resource_name: resource.name,
          tx_hash: txHash,
          amount: amountUsd,
          delivered_at: Date.now()
        };

        console.log(`   ✅ Resource delivered successfully!`);
        this.pendingDeliveries.delete(txHash);

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
            "3. Format: 'merchant_tx_hash,commission_tx_hash'"
          ]
        }
      };
    }

    // Payment provided → Verify
    console.log(`\n🔍 [SELLER] Verifying payment for: ${resource.name}`);

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

    console.log(`   Merchant TX: ${txHashMerchant.slice(0, 20)}...`);
    console.log(`   Commission TX: ${txHashCommission.slice(0, 20)}...`);

    console.log(`   📡 Calling AgentGatePay API for verification...`);

    // Adaptive retry strategy
    const maxRetries = resource.price_usd < 1.0 ? 6 : 12;
    const initialDelay = 10;
    let retryDelay = initialDelay;

    if (resource.price_usd < 1.0) {
      console.log(`   💨 Optimistic mode expected (payment <$1)`);
      console.log(`   ⏳ Will retry up to ${maxRetries} times over ~90 seconds`);
    } else {
      console.log(`   ✅ Synchronous mode expected (payment ≥$1)`);
      console.log(`   ⏳ Will retry up to ${maxRetries} times over ~120 seconds`);
    }

    let verification: any = null;
    let lastError: string | null = null;

    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        verification = await this.agentpay.payments.verify(txHashMerchant);

        if (verification.verified) {
          const status = verification.status || 'unknown';
          if (status === 'pending') {
            console.log(`   💨 Payment verified (OPTIMISTIC MODE - pending blockchain confirmation)`);
            console.log(`   ✅ Accepting payment, background worker will finalize within 1-2 minutes`);
          } else {
            console.log(`   ✅ Payment verified (ON-CHAIN CONFIRMED)`);
          }
          break;
        } else if (verification.status === 'pending' && attempt < maxRetries - 1) {
          console.log(`   ⏳ Payment status: PENDING (attempt ${attempt + 1}/${maxRetries}), retrying in ${retryDelay}s...`);
          await new Promise(resolve => setTimeout(resolve, retryDelay * 1000));
          if (resource.price_usd >= 1.0) {
            retryDelay = Math.min(retryDelay * 1.5, 10);
          }
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

    // Verify amount
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

  async fetchRevenueSummary(): Promise<any> {
    try {
      const response = await axios.get(`${AGENTPAY_API_URL}/v1/merchant/revenue`, {
        headers: { 'x-api-key': SELLER_API_KEY },
        params: { merchant_wallet: SELLER_WALLET }
      });

      if (response.status === 200) {
        return response.data;
      }
    } catch (error) {
      console.log('⚠️  Failed to fetch revenue');
    }
    return {};
  }
}

// ========================================
// EXPRESS API
// ========================================

const app = express();
app.use(express.json());

let seller: SellerAgent;

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
  res.status(response.status).json(response.body);
});

app.get('/catalog', (req: Request, res: Response) => {
  res.json(seller.listCatalog());
});

app.get('/health', (req: Request, res: Response) => {
  res.json({
    status: 'healthy',
    seller_wallet: SELLER_WALLET,
    resources_available: Object.keys(seller.catalog).length
  });
});

app.post('/webhooks/payment', (req: Request, res: Response) => {
  try {
    const payload = req.body;
    const signature = req.headers['x-webhook-signature'] as string || '';
    const result = seller.handleWebhook(payload, signature);
    res.json(result);
  } catch (error: any) {
    console.error(`❌ Webhook error: ${error.message}`);
    res.status(500).json({ error: error.message });
  }
});

// ========================================
// MAIN
// ========================================

async function main() {
  console.log('\n' + '='.repeat(60));
  console.log('🏪 SELLER AGENT - RESOURCE MARKETPLACE API');
  console.log('='.repeat(60));
  console.log();
  console.log('This agent provides resources for sale to buyer agents.');
  console.log('Buyers can discover resources and purchase with blockchain payments.');
  console.log();

  // Load chain config
  console.log('\n🔧 CHAIN & TOKEN CONFIGURATION');
  console.log('='.repeat(60));
  CHAIN_CONFIG = getChainConfig();

  console.log(`\nUsing configuration from .env:`);
  console.log(`  Chain: ${CHAIN_CONFIG.chain.charAt(0).toUpperCase() + CHAIN_CONFIG.chain.slice(1)} (ID: ${CHAIN_CONFIG.chainId})`);
  console.log(`  Token: ${CHAIN_CONFIG.token} (${CHAIN_CONFIG.decimals} decimals)`);
  console.log(`  To change: Edit PAYMENT_CHAIN and PAYMENT_TOKEN in .env file`);
  console.log('='.repeat(60));

  // Get commission address
  COMMISSION_ADDRESS = await getCommissionAddress();

  // Initialize seller
  seller = new SellerAgent(CHAIN_CONFIG);

  // Ask user to set resource prices
  console.log(`\n💵 Set resource prices (press Enter for default $0.01):`);
  for (const resId in seller.catalog) {
    const resource = seller.catalog[resId];
    const priceInput = await question(`   ${resource.name}: $`);

    if (priceInput.trim()) {
      try {
        const newPrice = parseFloat(priceInput.trim());
        if (newPrice > 0) {
          seller.catalog[resId].price_usd = newPrice;
          console.log(`      ✅ Set to $${newPrice}`);
        } else {
          console.log(`      ⚠️  Invalid price, using default $0.01`);
          seller.catalog[resId].price_usd = 0.01;
        }
      } catch (error) {
        console.log(`      ⚠️  Invalid input, using default $0.01`);
        seller.catalog[resId].price_usd = 0.01;
      }
    } else {
      // User pressed Enter without typing - default to $0.01
      seller.catalog[resId].price_usd = 0.01;
      console.log(`      ✅ Set to default: $0.01`);
    }
  }

  console.log(`\n✅ Final prices:`);
  for (const resId in seller.catalog) {
    console.log(`   - ${seller.catalog[resId].name}: $${seller.catalog[resId].price_usd}`);
  }

  console.log();
  console.log(`📋 Endpoints:`);
  console.log(`   GET /catalog                - List all resources`);
  console.log(`   GET /resource?resource_id=<id>  - Purchase resource`);
  console.log(`   POST /webhooks/payment      - Webhook for payment notifications`);
  console.log(`   GET /health                 - Health check`);
  console.log();

  // Ask about webhook configuration
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

  const webhookChoice = await question('Configure webhooks now? (y/n, default: n): ');

  if (webhookChoice.trim().toLowerCase() === 'y') {
    const webhookUrl = await question('Enter public webhook URL (e.g., https://your-domain.com/webhooks/payment): ');

    if (webhookUrl.trim()) {
      const result = await seller.configureWebhook(webhookUrl.trim());

      if (!result.error) {
        console.log(`\n✅ Webhooks enabled! Gateway will send notifications to:`);
        console.log(`   ${webhookUrl.trim()}`);
        console.log(`\n📦 Resources will be auto-delivered when payments are confirmed.`);
      } else {
        console.log(`\n⚠️  Continuing without webhooks (using manual verification)`);
      }
    } else {
      console.log(`\n⚠️  No URL provided - continuing without webhooks`);
    }
  } else {
    console.log(`\n⚠️  Skipping webhook configuration (using manual verification)`);
    console.log(`   Note: For production, webhooks provide better UX and scalability`);
  }

  console.log();
  console.log('='.repeat(60));
  // ========================================
  // REVENUE SUMMARY (Before starting server)
  // ========================================

  console.log('\n' + '='.repeat(60));
  console.log('📊 REVENUE SUMMARY');
  console.log('='.repeat(60));
  console.log('   Fetching your payment history from AgentGatePay...');
  console.log();

  const revenueData = await seller.fetchRevenueSummary();

  if (revenueData && revenueData.summary) {
    const stats = revenueData.summary;
    console.log(`   💰 Total Revenue: $${(stats.total_revenue_usd || 0).toFixed(2)}`);
    console.log(`   📈 Payment Count: ${stats.payment_count || 0}`);
    console.log(`   📊 Average Payment: $${(stats.average_payment_usd || 0).toFixed(2)}`);
    console.log(`   📅 Last 7 Days: $${(stats.last_7_days_usd || 0).toFixed(2)}`);
    console.log(`   📅 Last 30 Days: $${(stats.last_30_days_usd || 0).toFixed(2)}`);

    const payments = revenueData.recent_payments || [];
    if (payments.length > 0) {
      console.log(`\n   💳 Recent Payments (${payments.length}):`);
      payments.slice(0, 5).forEach((payment: any, i: number) => {
        const amount = payment.amount_usd || 0;
        const timestamp = (payment.paid_at || 'N/A').slice(0, 19);
        const txHash = (payment.tx_hash || 'N/A').slice(0, 20);
        console.log(`      ${i + 1}. $${amount.toFixed(2)} - ${timestamp} - ${txHash}...`);
      });
    }
  } else {
    console.log('   ℹ️  No revenue data found yet.');
    console.log('   💡 Start receiving payments to see your revenue here!');
  }

  console.log();
  console.log('='.repeat(60));
  console.log();
  console.log('💡 Next step: Run the buyer agent (2a_api_buyer_agent.ts)');
  console.log();

  // Start Express server
  app.listen(SELLER_API_PORT, '0.0.0.0', () => {
    console.log(`\n✅ Seller API running on http://localhost:${SELLER_API_PORT}`);
    console.log(`   Ready to accept buyer requests!\n`);
  });
}

main();
