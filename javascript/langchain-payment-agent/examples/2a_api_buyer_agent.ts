/**
 * AgentGatePay + LangChain Integration - BUYER AGENT (REST API)
 *
 * This is the BUYER side of the marketplace interaction.
 * Run the seller agent FIRST (2b_api_seller_agent.ts), then run this buyer.
 *
 * The buyer agent:
 * - Autonomously discovers resources from seller APIs
 * - Issues payment mandates with budget control
 * - Signs blockchain transactions (2 TX: merchant + commission)
 * - Submits payment proofs to sellers
 * - Retrieves purchased resources
 *
 * Usage:
 *     # Make sure seller is running first!
 *     npm run example:2b  # In another terminal
 *
 *     # Then run buyer
 *     npm run example:2a
 *
 * Requirements:
 * - npm install
 * - .env file with BUYER_API_KEY, BUYER_PRIVATE_KEY, BUYER_WALLET
 * - Seller API running on http://localhost:8000
 */

import 'dotenv/config';
import axios from 'axios';
import { ethers } from 'ethers';
import readline from 'readline';
import { ChatOpenAI } from '@langchain/openai';
import { tool } from '@langchain/core/tools';
import { createReactAgent } from '@langchain/langgraph/prebuilt';
import { z } from 'zod';
import { AgentGatePay } from 'agentgatepay-sdk';
import { getChainConfig, ChainConfig } from '../chain_config.js';
import { saveMandate, getMandate, StoredMandate } from '../utils/index.js';

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
// TRANSACTION SIGNING
// ========================================
//
// This example uses LOCAL SIGNING (ethers.js with private key).
//
// ⚠️ WARNING: Local signing is NOT recommended for production!
//
// For production deployments, use an external signing service:
// - Option 1: Docker container (see docs/TX_SIGNING_OPTIONS.md)
// - Option 2: Render one-click deploy (https://github.com/AgentGatePay/TX)
// - Option 3: Railway deployment
// - Option 4: Self-hosted service
//
// See docs/TX_SIGNING_OPTIONS.md for complete guide.
// See Example 1b (examples/1b_api_with_tx_service.ts) for external signing usage.
//
// ========================================

// ========================================
// CONFIGURATION
// ========================================

const AGENTPAY_API_URL = process.env.AGENTPAY_API_URL || 'https://api.agentgatepay.com';
const BUYER_API_KEY = process.env.BUYER_API_KEY;
const BUYER_PRIVATE_KEY = process.env.BUYER_PRIVATE_KEY;

// Seller API URL (can be changed to discover from multiple sellers)
const SELLER_API_URL = process.env.SELLER_API_URL || 'http://localhost:8000';

// Payment configuration
const MANDATE_BUDGET_USD = parseFloat(process.env.MANDATE_BUDGET_USD || '100.0');

// ========================================
// BUYER AGENT CLASS
// ========================================

interface Resource {
  id: string;
  name: string;
  price_usd: number;
  description: string;
  category: string;
}

interface PaymentInfo {
  resource_id: string;
  resource_name: string;
  price_usd: number;
  recipient: string;
  commission_address: string;
  commission_rate: number;
  merchant_tx?: string;
  commission_tx?: string;
  resource_data?: any;
}

class BuyerAgent {
  private agentpay: AgentGatePay;
  private config: ChainConfig;
  private provider: ethers.JsonRpcProvider;
  private wallet: ethers.Wallet;
  public currentMandate: StoredMandate | null = null;
  public lastPayment: PaymentInfo | null = null;
  private discoveredResources: Resource[] = [];

  constructor(config: ChainConfig) {
    // Initialize AgentGatePay client
    this.agentpay = new AgentGatePay({
      apiUrl: AGENTPAY_API_URL,
      apiKey: BUYER_API_KEY!
    });

    this.config = config;

    // Initialize ethers.js with config RPC
    this.provider = new ethers.JsonRpcProvider(config.rpcUrl);
    this.wallet = new ethers.Wallet(BUYER_PRIVATE_KEY!, this.provider);

    console.log(`\n🤖 BUYER AGENT INITIALIZED`);
    console.log('='.repeat(60));
    console.log(`Wallet: ${this.wallet.address}`);
    console.log(`Chain: ${config.chain.toUpperCase()} (ID: ${config.chainId})`);
    console.log(`Token: ${config.token} (${config.decimals} decimals)`);
    console.log(`RPC: ${config.rpcUrl.substring(0, 50)}...`);
    console.log(`API URL: ${AGENTPAY_API_URL}`);
    console.log(`Seller API: ${SELLER_API_URL}`);
    console.log('='.repeat(60));
  }

  async getCommissionConfig(): Promise<any> {
    try {
      const response = await axios.get(
        `${AGENTPAY_API_URL}/v1/config/commission`,
        { headers: { 'x-api-key': BUYER_API_KEY || '' } }
      );
      return response.data;
    } catch (error) {
      console.error(`⚠️  Failed to fetch commission config: ${error}`);
      return null;
    }
  }

  decodeMandateToken(token: string): any {
    try {
      const parts = token.split('.');
      if (parts.length !== 3) return {};

      let payloadB64 = parts[1];
      const padding = 4 - (payloadB64.length % 4);
      if (padding !== 4) {
        payloadB64 += '='.repeat(padding);
      }

      const payloadJson = Buffer.from(payloadB64, 'base64url').toString('utf-8');
      return JSON.parse(payloadJson);
    } catch {
      return {};
    }
  }

  async issueMandate(budgetUsd: number, ttlMinutes: number = 10080, purpose: string = 'general purchases'): Promise<string> {
    console.log(`\n🔐 [BUYER] Issuing mandate with $${budgetUsd} budget for ${ttlMinutes} minutes...`);
    console.log(`   Purpose: ${purpose}`);

    try {
      // Check if mandate already exists
      const agentId = `buyer-agent-${this.wallet.address}`;
      const existingMandate = getMandate(agentId);

      if (existingMandate) {
        const token = existingMandate.mandate_token;

        // Get LIVE budget from gateway
        console.log(`   🔍 Fetching live budget from API...`);
        let budgetRemaining: any = 'Unknown';

        try {
          const verifyResponse = await axios.post(
            `${AGENTPAY_API_URL}/mandates/verify`,
            { mandate_token: token },
            {
              headers: {
                'x-api-key': BUYER_API_KEY || '',
                'Content-Type': 'application/json'
              }
            }
          );

          if (verifyResponse.status === 200) {
            budgetRemaining = verifyResponse.data.budget_remaining;
          } else {
            
            const tokenData = this.decodeMandateToken(token);
            budgetRemaining = tokenData.budget_remaining || existingMandate.budget_usd || 'Unknown';
          }
        } catch {
          
          const tokenData = this.decodeMandateToken(token);
          budgetRemaining = tokenData.budget_remaining || existingMandate.budget_usd || 'Unknown';
        }

        console.log(`♻️  Reusing existing mandate (Budget: $${budgetRemaining})`);
        this.currentMandate = { ...existingMandate, budget_remaining: budgetRemaining };
        return `MANDATE_TOKEN:${token}`;
      }

      // Create new mandate
      const mandate = await this.agentpay.mandates.issue(
        agentId,
        budgetUsd,
        'resource.read,payment.execute',
        ttlMinutes
      );

      // Fetch live budget from API
      const token = mandate.mandate_token;
      console.log(`   🔍 Fetching live budget from API...`);

      let budgetRemaining: any = budgetUsd;
      try {
        const verifyResponse = await axios.post(
          `${AGENTPAY_API_URL}/mandates/verify`,
          { mandate_token: token },
          {
            headers: {
              'x-api-key': BUYER_API_KEY || '',
              'Content-Type': 'application/json'
            }
          }
        );

        if (verifyResponse.status === 200) {
          budgetRemaining = verifyResponse.data.budget_remaining;
        } else {
          
          const tokenData = this.decodeMandateToken(token);
          budgetRemaining = tokenData.budget_remaining || budgetUsd;
        }
      } catch {
        
        const tokenData = this.decodeMandateToken(token);
        budgetRemaining = tokenData.budget_remaining || budgetUsd;
      }

      // Store with decoded budget AND purpose
      const mandateWithBudget = {
        ...mandate,
        budget_usd: budgetUsd,
        budget_remaining: budgetRemaining,
        purpose: purpose
      };

      this.currentMandate = mandateWithBudget;
      saveMandate(agentId, mandateWithBudget);

      console.log(`✅ Mandate issued successfully`);
      console.log(`   Token: ${mandate.mandate_token.substring(0, 50)}...`);
      console.log(`   Budget: $${budgetUsd}`);
      console.log(`   Purpose: ${purpose}`);

      return `MANDATE_TOKEN:${token}`;
    } catch (error: any) {
      const errorMsg = `Failed to issue mandate: ${error.message}`;
      console.error(`❌ ${errorMsg}`);
      return errorMsg;
    }
  }

  async discoverCatalog(sellerUrl: string): Promise<string> {
    console.log(`\n🔍 [BUYER] Discovering catalog from: ${sellerUrl}`);

    try {
      const response = await axios.get(`${sellerUrl}/catalog`, { timeout: 10000 });

      if (response.status === 200) {
        const catalog = response.data;
        this.discoveredResources = catalog.catalog || [];

        console.log(`✅ Discovered ${this.discoveredResources.length} resources:`);
        for (const res of this.discoveredResources) {
          console.log(`   - ${res.name} ($${res.price_usd}) [ID: ${res.id}]`);
        }

        // Return detailed resource info with IDs for agent to parse
        const resourcesList: string[] = [];
        for (const res of this.discoveredResources) {
          resourcesList.push(`ID: '${res.id}', Name: '${res.name}', Price: $${res.price_usd}, Description: '${res.description}'`);
        }

        return `Found ${this.discoveredResources.length} resources:\n${resourcesList.join('\n')}\n\nIMPORTANT: Use the 'ID' field (e.g., 'market-data-api') when calling request_resource, NOT the name or description.`;
      } else {
        const errorMsg = `Catalog discovery failed: HTTP ${response.status}`;
        console.error(`❌ ${errorMsg}`);
        return errorMsg;
      }
    } catch (error: any) {
      const errorMsg = `Catalog discovery error: ${error.message}`;
      console.error(`❌ ${errorMsg}`);
      return errorMsg;
    }
  }

  async requestResource(resourceId: string): Promise<string> {
    console.log(`\n📋 [BUYER] Requesting resource: ${resourceId}`);

    try {
      const response = await axios.get(
        `${SELLER_API_URL}/resource`,
        {
          params: { resource_id: resourceId },
          timeout: 10000,
          validateStatus: (status) => status < 500 // Accept all status codes < 500
        }
      );

      if (response.status === 402) {
        // Payment required
        const data = response.data;
        const paymentInfo = data.payment_info || {};

        console.log(`💳 Payment required:`);
        console.log(`   Resource: ${data.resource.name}`);
        console.log(`   Price: $${data.resource.price_usd}`);
        console.log(`   Recipient: ${paymentInfo.recipient_wallet?.substring(0, 20)}...`);

        // Store payment info for later
        this.lastPayment = {
          resource_id: resourceId,
          resource_name: data.resource.name,
          price_usd: data.resource.price_usd,
          recipient: paymentInfo.recipient_wallet,
          commission_address: paymentInfo.commission_address,
          commission_rate: paymentInfo.commission_rate
        };

        return `Resource '${data.resource.name}' costs $${data.resource.price_usd}. Payment required to access.`;
      } else if (response.status === 200) {
        // Already paid (shouldn't happen on first request)
        console.log(`✅ Resource already accessed`);
        return 'Resource accessed successfully';
      } else if (response.status === 404) {
        const error = response.data.error || 'Resource not found';
        console.error(`❌ ${error}`);
        return `Error: ${error}`;
      } else {
        const error = response.data.error || 'Unknown error';
        console.error(`❌ Request failed: ${error}`);
        return `Request failed: ${error}`;
      }
    } catch (error: any) {
      const errorMsg = `Resource request error: ${error.message}`;
      console.error(`❌ ${errorMsg}`);
      return errorMsg;
    }
  }

  async executePayment(): Promise<string> {
    if (!this.lastPayment) {
      return 'Error: No payment request pending. Call request_resource first.';
    }

    if (!this.currentMandate) {
      return 'Error: No mandate issued. Call issue_mandate first.';
    }

    const paymentInfo = this.lastPayment;
    console.log(`\n💳 [BUYER] Executing payment: $${paymentInfo.price_usd} to ${paymentInfo.recipient.substring(0, 10)}...`);

    try {
      // Fetch live commission config
      const commissionConfig = await this.getCommissionConfig();
      if (!commissionConfig) {
        return 'Error: Failed to fetch commission configuration';
      }

      const commissionAddress = commissionConfig.commission_address;
      console.log(`   ✅ Using live commission address: ${commissionAddress.substring(0, 10)}...`);

      // Calculate amounts (using config decimals)
      const totalUsd = paymentInfo.price_usd;
      const commissionRate = paymentInfo.commission_rate;
      const commissionUsd = totalUsd * commissionRate;
      const merchantUsd = totalUsd - commissionUsd;

      const merchantAtomic = BigInt(Math.floor(merchantUsd * 10 ** this.config.decimals));
      const commissionAtomic = BigInt(Math.floor(commissionUsd * 10 ** this.config.decimals));

      console.log(`   Merchant: $${merchantUsd.toFixed(4)} (${merchantAtomic} atomic)`);
      console.log(`   Commission: $${commissionUsd.toFixed(4)} (${commissionAtomic} atomic)`);

      // ERC-20 transfer function
      const transferSig = ethers.id('transfer(address,uint256)').substring(0, 10);

      // Get nonce ONCE before both transactions
      const merchantNonce = await this.provider.getTransactionCount(this.wallet.address);
      console.log(`   📊 Current nonce: ${merchantNonce}`);

      // Get gas price
      const feeData = await this.provider.getFeeData();
      const gasPrice = feeData.gasPrice || ethers.parseUnits('50', 'gwei');

      // TX 1: Merchant payment
      console.log(`   📤 Signing merchant transaction...`);
      const merchantData = transferSig +
        ethers.zeroPadValue(paymentInfo.recipient, 32).substring(2) +
        ethers.zeroPadValue(ethers.toBeHex(merchantAtomic), 32).substring(2);

      const merchantTx = {
        to: this.config.tokenContract,
        value: 0,
        data: merchantData,
        nonce: merchantNonce,
        gasLimit: 100000,
        gasPrice: gasPrice,
        chainId: this.config.chainId
      };

      const signedMerchant = await this.wallet.signTransaction(merchantTx);
      const merchantTxResponse = await this.provider.broadcastTransaction(signedMerchant);
      const txHashMerchant = merchantTxResponse.hash;
      console.log(`   ✅ Merchant TX sent: ${txHashMerchant}`);

      // TX 2: Commission payment (sign and send immediately - parallel execution)
      console.log(`   📤 Signing commission transaction...`);
      const commissionData = transferSig +
        ethers.zeroPadValue(commissionAddress, 32).substring(2) +
        ethers.zeroPadValue(ethers.toBeHex(commissionAtomic), 32).substring(2);

      const commissionTx = {
        to: this.config.tokenContract,
        value: 0,
        data: commissionData,
        nonce: merchantNonce + 1,
        gasLimit: 100000,
        gasPrice: gasPrice,
        chainId: this.config.chainId
      };

      const signedCommission = await this.wallet.signTransaction(commissionTx);
      const commissionTxResponse = await this.provider.broadcastTransaction(signedCommission);
      const txHashCommission = commissionTxResponse.hash;
      console.log(`   ✅ Commission TX sent: ${txHashCommission}`);

      // Store transaction hashes
      this.lastPayment.merchant_tx = txHashMerchant;
      this.lastPayment.commission_tx = txHashCommission;

      console.log(`\n💳 Processing payment...`);

      // Submit payment to gateway in parallel with on-chain verification
      const gatewayPromise = (async () => {
        console.log(`   📤 Submitting payment to gateway...`);
        const paymentPayload = {
          scheme: 'eip3009',
          tx_hash: txHashMerchant,
          tx_hash_commission: txHashCommission
        };
        const paymentB64 = Buffer.from(JSON.stringify(paymentPayload)).toString('base64');

        const url = `${AGENTPAY_API_URL}/x402/resource?chain=${this.config.chain}&token=${this.config.token}&price_usd=${totalUsd}`;
        const gatewayResponse = await axios.get(url, {
          headers: {
            'x-api-key': BUYER_API_KEY || '',
            'x-mandate': this.currentMandate!.mandate_token,
            'x-payment': paymentB64
          },
          timeout: 120000
        });
        console.log(`   ✅ Gateway response received`);
        return gatewayResponse;
      })();

      // Verify transactions on-chain (120s timeout for Ethereum public RPCs)
      console.log(`   🔍 Verifying transactions on-chain...`);
      try {
        const receiptMerchant = await this.provider.waitForTransaction(txHashMerchant, 1, 120000);
        console.log(`   ✅ Merchant TX confirmed (block ${receiptMerchant!.blockNumber})`);

        const receiptCommission = await this.provider.waitForTransaction(txHashCommission, 1, 120000);
        console.log(`   ✅ Commission TX confirmed (block ${receiptCommission!.blockNumber})`);
      } catch (error) {
        console.log(`   ⚠️  Verification failed: ${error}`);
      }

      // Wait for gateway response
      let gatewayResponse;
      try {
        gatewayResponse = await Promise.race([
          gatewayPromise,
          new Promise((_, reject) => setTimeout(() => reject(new Error('Gateway timeout')), 90000))
        ]) as any;
      } catch (error: any) {
        return `Gateway error: ${error.message}`;
      }

      if (!gatewayResponse) {
        return 'Gateway timeout - please check payment status manually';
      }

      if (gatewayResponse.status >= 400) {
        const result = gatewayResponse.data || {};
        const error = result.error || gatewayResponse.statusText;
        console.error(`❌ Gateway error (${gatewayResponse.status}): ${error}`);
        return `Failed: ${error}`;
      }

      const result = gatewayResponse.data;
      console.log(`   🔍 Gateway response: ${JSON.stringify(result)}`);

      if (result.message || result.success || result.paid || ['confirmed', 'pending'].includes(result.status)) {
        const status = result.status || 'unknown';
        if (status === 'pending') {
          console.log(`✅ Payment accepted (OPTIMISTIC MODE - pending background verification)`);
        } else {
          console.log(`✅ Payment recorded successfully`);
        }

        // Fetch updated budget
        console.log(`   🔍 Fetching updated budget...`);
        try {
          const verifyResponse = await axios.post(
            `${AGENTPAY_API_URL}/mandates/verify`,
            { mandate_token: this.currentMandate!.mandate_token },
            {
              headers: {
                'x-api-key': BUYER_API_KEY || '',
                'Content-Type': 'application/json'
              }
            }
          );

          if (verifyResponse.status === 200) {
            const verifyData = verifyResponse.data;
            const newBudget = verifyData.budget_remaining || 'Unknown';
            console.log(`   ✅ Budget updated: $${newBudget}`);

            if (this.currentMandate) {
              this.currentMandate.budget_remaining = newBudget;
              // Also sync budget_usd from gateway
              const budgetAllocated = verifyData.budget_allocated;
              if (budgetAllocated !== undefined) {
                this.currentMandate.budget_usd = budgetAllocated;
              }
              const agentId = `buyer-agent-${this.wallet.address}`;
              saveMandate(agentId, this.currentMandate);
            }

            return `Payment successful! Paid $${totalUsd}, Budget remaining: $${newBudget}. IMPORTANT: Now call claim_resource to submit payment proof to seller and receive the resource.`;
          } else {
            return `Payment successful! Paid $${totalUsd}. IMPORTANT: Now call claim_resource to submit payment proof to seller and receive the resource.`;
          }
        } catch {
          return `Payment successful! Paid $${totalUsd}. IMPORTANT: Now call claim_resource to submit payment proof to seller and receive the resource.`;
        }
      } else {
        const error = result.error || 'Unknown error';
        console.error(`❌ Failed: ${error}`);
        return `Failed: ${error}`;
      }
    } catch (error: any) {
      const errorMsg = `Payment failed: ${error.message}`;
      console.error(`❌ ${errorMsg}`);
      return errorMsg;
    }
  }

  async claimResource(): Promise<string> {
    if (!this.lastPayment || !this.lastPayment.merchant_tx) {
      return 'Error: No payment executed. Call execute_payment first.';
    }

    const paymentInfo = this.lastPayment;
    console.log(`\n📦 [BUYER] Claiming resource: ${paymentInfo.resource_name}`);

    // Retry claim up to 12 times with 10-second delays
    const maxRetries = 12;
    const retryDelay = 10; // seconds

    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        // Submit payment proof to seller
        const paymentHeader = `${paymentInfo.merchant_tx},${paymentInfo.commission_tx}`;

        const response = await axios.get(
          `${SELLER_API_URL}/resource`,
          {
            params: { resource_id: paymentInfo.resource_id },
            headers: { 'x-payment': paymentHeader },
            timeout: 30000,
            validateStatus: (status) => status < 500 // Accept all status codes < 500
          }
        );

        if (response.status === 200) {
          // SUCCESS - resource delivered
          const data = response.data;
          console.log(`✅ Resource delivered!`);
          console.log(`   Resource: ${paymentInfo.resource_name}`);
          console.log(`   Payment verified: ${data.payment_confirmation.amount_verified_usd} USD`);

          // Store resource
          this.lastPayment!.resource_data = data.resource;

          return `Resource '${paymentInfo.resource_name}' received successfully! Payment verified: $${data.payment_confirmation.amount_verified_usd}`;
        } else {
          const error = response.data.error || 'Unknown error';

          // If this is not the last attempt, retry after delay
          if (attempt < maxRetries - 1) {
            console.log(`⚠️  Claim attempt ${attempt + 1} failed: ${error}`);
            console.log(`   Retrying in ${retryDelay} seconds (payment may still be propagating)...`);
            await new Promise(resolve => setTimeout(resolve, retryDelay * 1000));
            continue;
          } else {
            // Last attempt failed
            console.error(`❌ Claim failed after ${maxRetries} attempts: ${error}`);
            return `Claim failed after ${maxRetries} retries: ${error}. Payment was recorded, but seller couldn't verify it. Try claiming again manually.`;
          }
        }
      } catch (error: any) {
        // If this is not the last attempt, retry after delay
        if (attempt < maxRetries - 1) {
          console.log(`⚠️  Claim attempt ${attempt + 1} error: ${error.message}`);
          console.log(`   Retrying in ${retryDelay} seconds...`);
          await new Promise(resolve => setTimeout(resolve, retryDelay * 1000));
          continue;
        } else {
          // Last attempt failed
          const errorMsg = `Claim error after ${maxRetries} attempts: ${error.message}`;
          console.error(`❌ ${errorMsg}`);
          return errorMsg;
        }
      }
    }

    return 'Claim failed: Maximum retries exceeded';
  }
}

// ========================================
// MAIN
// ========================================

let buyer: BuyerAgent;
let mandateTtlMinutes = 10080;
let mandatePurpose = 'general purchases';

async function main() {
  console.log('\n' + '='.repeat(60));
  console.log('🤖 BUYER AGENT - AUTONOMOUS RESOURCE PURCHASER');
  console.log('='.repeat(60));
  console.log();
  console.log('This agent autonomously discovers and purchases resources');
  console.log('from seller APIs using blockchain payments.');
  console.log();
  console.log('='.repeat(60));

  // Load chain/token configuration
  console.log('\n🔧 CHAIN & TOKEN CONFIGURATION');
  console.log('='.repeat(60));
  const config = getChainConfig();

  console.log(`\nUsing configuration from .env:`);
  console.log(`  Chain: ${config.chain.charAt(0).toUpperCase() + config.chain.slice(1)} (ID: ${config.chainId})`);
  console.log(`  Token: ${config.token} (${config.decimals} decimals)`);
  console.log(`  RPC: ${config.rpcUrl}`);
  console.log(`\nTo change: Edit PAYMENT_CHAIN and PAYMENT_TOKEN in .env file`);
  console.log('='.repeat(60));

  // Initialize buyer agent
  buyer = new BuyerAgent(config);

  // Check for existing mandate
  const agentId = `buyer-agent-${buyer.wallet.address}`;
  const existingMandate = getMandate(agentId);

  let mandateBudget = MANDATE_BUDGET_USD;
  let userNeed = 'research papers and academic content';

  if (existingMandate) {
    const token = existingMandate.mandate_token;

    // Get LIVE budget from gateway
    let budgetRemaining: any = 'Unknown';
    try {
      const verifyResponse = await axios.post(
        `${AGENTPAY_API_URL}/mandates/verify`,
        { mandate_token: token },
        {
          headers: {
            'x-api-key': BUYER_API_KEY || '',
            'Content-Type': 'application/json'
          }
        }
      );

      if (verifyResponse.status === 200) {
        budgetRemaining = verifyResponse.data.budget_remaining;
      } else {
        
        const tokenData = buyer.decodeMandateToken(token);
        budgetRemaining = tokenData.budget_remaining || existingMandate.budget_usd || 'Unknown';
      }
    } catch {
      
      const tokenData = buyer.decodeMandateToken(token);
      budgetRemaining = tokenData.budget_remaining || existingMandate.budget_usd || 'Unknown';
    }

    // Extract mandate purpose
    mandatePurpose = existingMandate.purpose || 'general purchases';

    console.log(`\n♻️  Using existing mandate`);
    console.log(`   Purpose: ${mandatePurpose}`);
    console.log(`   Budget remaining: $${budgetRemaining}`);
    console.log(`   Token: ${existingMandate.mandate_token?.substring(0, 50)}...`);
    console.log(`   To delete: rm ../.agentgatepay_mandates.json\n`);
    mandateBudget = budgetRemaining !== 'Unknown' ? parseFloat(budgetRemaining) : MANDATE_BUDGET_USD;
    userNeed = mandatePurpose; // Use mandate purpose for purchases
  } else {
    // Ask user for mandate parameters
    const budgetInput = await question('\n💰 Enter mandate budget in USD Coins (default: 100): ');
    mandateBudget = budgetInput.trim() ? parseFloat(budgetInput.trim()) : MANDATE_BUDGET_USD;

    // Ask user for mandate TTL duration
    console.log(`\n⏰ Set mandate duration (format: number + unit)`);
    console.log(`   Examples: 10m (10 minutes), 2h (2 hours), 7d (7 days)`);
    let ttlInput = await question('   Enter duration (default: 7d): ');
    ttlInput = ttlInput.trim().toLowerCase();

    if (!ttlInput) {
      ttlInput = '7d';
    }

    // Parse duration
    const match = ttlInput.match(/^(\d+)([mhd])$/);

    if (match) {
      const value = parseInt(match[1]);
      const unit = match[2];

      let unitName: string;
      if (unit === 'm') {
        mandateTtlMinutes = value;
        unitName = 'minutes';
      } else if (unit === 'h') {
        mandateTtlMinutes = value * 60;
        unitName = 'hours';
      } else if (unit === 'd') {
        mandateTtlMinutes = value * 1440;
        unitName = 'days';
      } else {
        mandateTtlMinutes = 10080;
        unitName = '7 days';
      }

      console.log(`   ✅ Mandate will be valid for ${value} ${unitName} (${mandateTtlMinutes} minutes)`);
    } else {
      console.log(`   ⚠️  Invalid format, using default: 7 days`);
      mandateTtlMinutes = 10080;
    }

    // Ask user for mandate PURPOSE
    console.log(`\n🎯 What is this mandate for? (This defines what resources can be purchased)`);
    console.log(`   Examples from our seller:`);
    console.log(`   1. Research papers and academic content`);
    console.log(`   2. Market data and API access`);
    console.log(`   3. AI training datasets`);
    console.log(`   Or enter custom purpose in natural language`);
    const purposeInput = await question('\n   Enter mandate purpose (default: research papers): ');

    if (purposeInput.trim() === '1') {
      userNeed = 'research papers and academic content';
    } else if (purposeInput.trim() === '2') {
      userNeed = 'market data and API access';
    } else if (purposeInput.trim() === '3') {
      userNeed = 'AI training datasets';
    } else if (purposeInput.trim()) {
      userNeed = purposeInput.trim();
    } else {
      userNeed = 'research papers and academic content';
    }

    console.log(`   ✅ Mandate purpose: ${userNeed}`);

    // Set global mandate_purpose for tool use
    mandatePurpose = userNeed;
  }

  // Define tools
  const issueMandateTool = tool(
    async ({ budget }: { budget: number }): Promise<string> => {
      return await buyer.issueMandate(budget, mandateTtlMinutes, mandatePurpose);
    },
    {
      name: 'issue_mandate',
      description: 'Issue AP2 payment mandate with specified budget (USD). Use FIRST before any purchases. Input: budget amount as number. Returns: MANDATE_TOKEN:{token}',
      schema: z.object({
        budget: z.number().describe('Budget amount in USD')
      })
    }
  );

  const discoverCatalogTool = tool(
    async ({ sellerUrl }: { sellerUrl: string }): Promise<string> => {
      return await buyer.discoverCatalog(sellerUrl);
    },
    {
      name: 'discover_catalog',
      description: 'Discover resource catalog from seller API. Input: seller_url (e.g., \'http://localhost:8000\')',
      schema: z.object({
        sellerUrl: z.string().describe('Seller API URL')
      })
    }
  );

  const requestResourceTool = tool(
    async ({ resourceId }: { resourceId: string }): Promise<string> => {
      return await buyer.requestResource(resourceId);
    },
    {
      name: 'request_resource',
      description: 'Request specific resource and get payment requirements. Input: resource_id string.',
      schema: z.object({
        resourceId: z.string().describe('Resource ID')
      })
    }
  );

  const executePaymentTool = tool(
    async ({ _unused }: { _unused?: string | null }): Promise<string> => {
      return await buyer.executePayment();
    },
    {
      name: 'execute_payment',
      description: 'Execute blockchain payment (2 transactions) AND submit to gateway. No input needed. After this succeeds, you MUST call claim_resource to complete the purchase and get the resource.',
      schema: z.object({
        _unused: z.string().optional().nullable().describe('No input needed')
      })
    }
  );

  const claimResourceTool = tool(
    async ({ _unused }: { _unused?: string | null }): Promise<string> => {
      return await buyer.claimResource();
    },
    {
      name: 'claim_resource',
      description: 'Claim resource after payment by submitting payment proof to seller. No input needed.',
      schema: z.object({
        _unused: z.string().optional().nullable().describe('No input needed')
      })
    }
  );

  const tools = [issueMandateTool, discoverCatalogTool, requestResourceTool, executePaymentTool, claimResourceTool];

  // System prompt for agent behavior
  const systemPrompt = `You are an autonomous buyer agent that discovers and purchases resources from sellers.

Workflow:
1. Issue mandate with budget - Returns MANDATE_TOKEN:{token}
2. Discover catalog from seller
3. Request ONE specific resource (gets payment requirements)
4. Execute payment - Signs blockchain TX AND submits to gateway (single step, optimized for speed)
5. Claim resource (submit payment proof to seller)

CRITICAL RULES:
- Buy ONE resource at a time (never request multiple resources simultaneously)
- Complete the full workflow (request → pay → claim) for one resource before considering another
- The execute_payment tool is optimized for micro-transactions - combines blockchain signing and gateway submission into ONE atomic operation

Think step by step and complete the workflow for ONE resource.`;

  // Create agent
  const llm = new ChatOpenAI({
    modelName: 'gpt-4o-mini',
    temperature: 0,
    openAIApiKey: process.env.OPENAI_API_KEY
  });

  const agent = createReactAgent({ llm, tools, messageModifier: systemPrompt });

  // Check seller availability
  console.log(`\n📡 Checking seller API: ${SELLER_API_URL}`);
  try {
    const health = await axios.get(`${SELLER_API_URL}/health`, { timeout: 5000 });
    if (health.status === 200) {
      console.log(`✅ Seller API is running`);
    } else {
      console.log(`⚠️  Seller API returned: HTTP ${health.status}`);
    }
  } catch {
    console.error(`❌ Seller API is NOT running!`);
    console.error(`   Please start the seller first: npm run example:2b`);
    process.exit(1);
  }

  // Agent task
  const task = `
The user wants: "${userNeed}"

Your job is to autonomously find and purchase the best matching resource.

Steps:
1. Issue a mandate with $${mandateBudget} budget
2. Discover the catalog from ${SELLER_API_URL}
3. Analyze the catalog and identify which resource best matches: "${userNeed}"
4. Request that resource to get payment details - USE THE 'ID' FIELD FROM CATALOG
5. If price is acceptable (under $${mandateBudget}), execute payment (fast - one step!)
6. Claim the resource by submitting payment proof to seller

CRITICAL INSTRUCTIONS FOR STEP 4:
- The catalog returns resources in this format:
  ID: 'market-data-api', Name: 'Premium Market Data API Access', Price: $5.0
- When you call request_resource, you MUST use the 'ID' field (e.g., 'market-data-api')
- DO NOT use the name, description, or purpose text
- Example: request_resource('market-data-api') ✓
- Example: request_resource('market data and API access') ✗ WRONG

Choose the resource whose name/description best matches "${userNeed}", then use its ID.
  `;

  try {
    // Run agent
    const result = await agent.invoke({
      messages: [{ role: 'user', content: task }]
    });

    console.log('\n' + '='.repeat(60));
    console.log('✅ BUYER AGENT COMPLETED');
    console.log('='.repeat(60));

    // Extract final message
    if (result.messages && result.messages.length > 0) {
      const finalMessage = result.messages[result.messages.length - 1].content;
      console.log(`\nResult: ${finalMessage}`);
    }

    // Display final status
    if (buyer.currentMandate) {
      console.log(`\n📊 Final Status:`);
      console.log(`   Budget remaining: $${buyer.currentMandate.budget_remaining || 'N/A'}`);
    }

    if (buyer.lastPayment && buyer.lastPayment.merchant_tx) {
      console.log(`   Merchant TX: ${config.explorer}/tx/${buyer.lastPayment.merchant_tx}`);
      console.log(`   Commission TX: ${config.explorer}/tx/${buyer.lastPayment.commission_tx}`);

      // Display gateway audit logs with curl commands
      console.log(`\nGateway Audit Logs (copy-paste these commands):`);
      console.log(`\n# All payment logs (by wallet):`);
      console.log(`curl '${AGENTPAY_API_URL}/audit/logs?client_id=${buyer.wallet.address}&event_type=x402_payment_settled&limit=10' \\`);
      console.log(`  -H 'x-api-key: ${BUYER_API_KEY}' | python3 -m json.tool`);
      console.log(`\n# Recent payments (24h):`);
      console.log(`curl '${AGENTPAY_API_URL}/audit/logs?client_id=${buyer.wallet.address}&event_type=x402_payment_settled&hours=24' \\`);
      console.log(`  -H 'x-api-key: ${BUYER_API_KEY}' | python3 -m json.tool`);
      console.log(`\n# Payment verification (by tx_hash):`);
      console.log(`curl '${AGENTPAY_API_URL}/v1/payments/verify/${buyer.lastPayment.merchant_tx}' \\`);
      console.log(`  -H 'x-api-key: ${BUYER_API_KEY}' | python3 -m json.tool`);
    }

    if (buyer.lastPayment && buyer.lastPayment.resource_data) {
      console.log(`\n📦 Received Resource:`);
      const resource = buyer.lastPayment.resource_data;

      // Display resource data based on type
      if (resource.title) {
        // Research paper format
        console.log(`   Title: ${resource.title}`);
        console.log(`   Authors: ${resource.authors?.join(', ')}`);
        if (resource.abstract) {
          console.log(`   Abstract: ${resource.abstract.substring(0, 100)}...`);
        }
        if (resource.pdf_url) {
          console.log(`   PDF: ${resource.pdf_url}`);
        }
      } else if (resource.service) {
        // API service format
        console.log(`   Service: ${resource.service}`);
        console.log(`   Base URL: ${resource.base_url}`);
        console.log(`   API Key: ${resource.api_key}`);
        console.log(`   Rate Limit: ${resource.rate_limit}`);
      } else if (resource.name) {
        // Dataset format
        console.log(`   Name: ${resource.name}`);
        console.log(`   Samples: ${resource.samples || 'N/A'}`);
        if (resource.format) {
          console.log(`   Format: ${resource.format}`);
        }
        if (resource.download_url) {
          console.log(`   Download: ${resource.download_url}`);
        }
      } else {
        // Generic format (fallback)
        console.log(`   Data: ${JSON.stringify(resource)}`);
      }
    }
  } catch (error: any) {
    if (error.message === 'User interrupted') {
      console.log('\n\n⚠️  Buyer agent interrupted by user');
    } else {
      console.error(`\n\n❌ Error: ${error.message}`);
      console.error(error.stack);
    }
  }
}

main().catch(console.error);
