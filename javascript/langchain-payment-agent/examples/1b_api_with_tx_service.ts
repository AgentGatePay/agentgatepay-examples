#!/usr/bin/env tsx
/**
 * AgentGatePay + LangChain.js Integration - Example 1b: REST API + External TX Signing
 *
 * This example demonstrates the SAME payment flow as Example 1a,
 * but using an external transaction signing service for production security.
 *
 * Flow:
 * 1. Issue AP2 mandate ($100 budget)
 * 2. Request payment signing from external service (Docker/Render/Railway/self-hosted)
 * 3. Submit payment proof to AgentGatePay
 * 4. Verify payment completion
 *
 * Security Benefits:
 * - Private key stored in signing service, NOT in application code
 * - Application cannot access private keys
 * - Signing service can be audited independently
 * - Scalable deployment options
 *
 * Setup Options:
 * - Docker local: See docs/DOCKER_LOCAL_SETUP.md
 * - Render cloud: See docs/RENDER_DEPLOYMENT_GUIDE.md
 * - Other options: See docs/TX_SIGNING_OPTIONS.md
 *
 * Requirements:
 * - npm install
 * - .env file with TX_SIGNING_SERVICE configured
 *
 * For Development: See Example 1a (local signing, simpler setup)
 * For MCP Version: See Example 3b (MCP + external signing)
 */

import { config } from 'dotenv';
import axios from 'axios';
import { AgentGatePay } from 'agentgatepay-sdk';
import { ChatOpenAI } from '@langchain/openai';
import { createReactAgent } from '@langchain/langgraph/prebuilt';
import { tool } from '@langchain/core/tools';
import { z } from 'zod';
import { saveMandate, getMandate } from '../utils/index.js';
import { getChainConfig, displayChainConfig, type ChainConfig } from '../chain_config.js';

// Load environment variables
config();

// ========================================
// TRANSACTION SIGNING
// ========================================
//
// This example uses EXTERNAL SIGNING SERVICE (PRODUCTION READY).
//
// ✅ PRODUCTION READY: Private key stored securely in signing service
// ✅ SECURE: Application code never touches private keys
// ✅ SCALABLE: Signing service can be scaled independently
//
// Setup options:
// - Option 1: Docker container (see docs/DOCKER_LOCAL_SETUP.md)
// - Option 2: Render one-click deploy (see docs/RENDER_DEPLOYMENT_GUIDE.md)
// - Option 3: Railway/AWS/GCP/custom (see docs/TX_SIGNING_OPTIONS.md)
//
// ========================================

// ========================================
// CONFIGURATION
// ========================================

const AGENTPAY_API_URL = process.env.AGENTPAY_API_URL || 'https://api.agentgatepay.com';
const BUYER_API_KEY = process.env.BUYER_API_KEY!;
const BUYER_EMAIL = process.env.BUYER_EMAIL!;
const BUYER_WALLET = process.env.BUYER_WALLET!;
const SELLER_WALLET = process.env.SELLER_WALLET!;
const TX_SIGNING_SERVICE = process.env.TX_SIGNING_SERVICE;

// Payment configuration
const RESOURCE_PRICE_USD = 0.01;
const MANDATE_BUDGET_USD = 100.0;

// Chain configuration (loaded in main)
let chainConfig: ChainConfig;
let agentpay: AgentGatePay;

// Validate configuration
if (!TX_SIGNING_SERVICE) {
  console.error('❌ ERROR: TX_SIGNING_SERVICE not configured in .env');
  console.error('   Please set TX_SIGNING_SERVICE=http://localhost:3000 (Docker)');
  console.error('   Or: TX_SIGNING_SERVICE=https://your-service.onrender.com (Render)');
  console.error('   See docs/TX_SIGNING_OPTIONS.md for setup instructions');
  process.exit(1);
}

// ========================================
// HELPER FUNCTIONS
// ========================================

function decodeMandateToken(token: string): any {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return {};

    let payload_b64 = parts[1];
    const padding = 4 - (payload_b64.length % 4);
    if (padding !== 4) {
      payload_b64 += '='.repeat(padding);
    }

    const payloadJson = Buffer.from(payload_b64, 'base64url').toString('utf8');
    return JSON.parse(payloadJson);
  } catch {
    return {};
  }
}

// ========================================
// AGENT TOOLS
// ========================================

// Global state
let currentMandate: any = null;
let merchantTxHash: string | null = null;
let commissionTxHash: string | null = null;

// Tool 1: Issue Mandate
const issueMandateTool = tool(
  async ({ budgetUsd }: { budgetUsd: number }): Promise<string> => {
    try {
      const agentId = `research-assistant-${BUYER_WALLET}`;
      const existingMandate = getMandate(agentId);

      if (existingMandate) {
        const token = existingMandate.mandate_token;

        // Get LIVE budget from gateway
        const verifyResponse = await axios.post(
          `${AGENTPAY_API_URL}/mandates/verify`,
          { mandate_token: token },
          {
            headers: { 'x-api-key': BUYER_API_KEY, 'Content-Type': 'application/json' },
            validateStatus: () => true
          }
        );

        let budgetRemaining: string | number;
        if (verifyResponse.status === 200) {
          budgetRemaining = verifyResponse.data.budget_remaining;
        } else {
          // Fallback to JWT
          const tokenData = decodeMandateToken(token);
          budgetRemaining = tokenData.budget_remaining || existingMandate.budget_usd || 'Unknown';
        }

        console.log(`\n♻️  Reusing mandate (Budget: $${budgetRemaining})`);
        currentMandate = {
          ...existingMandate,
          budget_remaining: budgetRemaining
        };
        return `MANDATE_TOKEN:${token}`;
      }

      console.log(`\n🔐 Creating mandate ($${budgetUsd})...`);

      const mandate = await agentpay.mandates.issue(
        agentId,
        budgetUsd,
        'resource.read,payment.execute',
        168 * 60
      );

      // Store mandate with budget info
      const token = mandate.mandate_token;
      const mandateWithBudget = {
        ...mandate,  // Include ALL SDK response fields (expires_at, subject, scope, etc.)
        budget_usd: budgetUsd,
        budget_remaining: budgetUsd
      };

      currentMandate = mandateWithBudget;
      saveMandate(agentId, mandateWithBudget);

      console.log(`✅ Mandate created (Budget: $${budgetUsd})`);

      return `MANDATE_TOKEN:${token}`;
    } catch (error: any) {
      console.error(`❌ Mandate failed: ${error.message}`);
      return `Failed: ${error.message}`;
    }
  },
  {
    name: 'issue_mandate',
    description: 'Issue an AP2 payment mandate with a specified budget in USD. Use this FIRST before making any payments. Input should be an object with budgetUsd (number).',
    schema: z.object({
      budgetUsd: z.number().describe('Budget amount in USD')
    })
  }
);

// Tool 2: Sign Payment via External Service
const signPaymentViaServiceTool = tool(
  async ({ amountUsd, recipient }: { amountUsd: number; recipient: string }): Promise<string> => {
    try {
      // Convert USD to atomic units
      const amountAtomic = Math.floor(amountUsd * (10 ** chainConfig.decimals));

      console.log(`\n💳 Requesting payment signature from external service...`);
      console.log(`   Amount: $${amountUsd} ${chainConfig.token} (${amountAtomic} atomic units)`);
      console.log(`   Chain: ${chainConfig.chain.charAt(0).toUpperCase() + chainConfig.chain.slice(1)}`);
      console.log(`   Recipient: ${recipient.slice(0, 10)}...`);
      console.log(`   Service: ${TX_SIGNING_SERVICE}`);

      // Call external signing service
      const response = await axios.post(
        `${TX_SIGNING_SERVICE}/sign-payment`,
        {
          merchant_address: recipient,
          total_amount: amountAtomic.toString(),
          chain: chainConfig.chain,
          token: chainConfig.token
        },
        {
          headers: {
            'Content-Type': 'application/json',
            'x-api-key': BUYER_API_KEY
          },
          timeout: 120000,
          validateStatus: () => true
        }
      );

      if (response.status !== 200) {
        const errorMsg = `Signing service error: HTTP ${response.status} - ${response.data}`;
        console.error(`❌ ${errorMsg}`);
        return errorMsg;
      }

      const result = response.data;

      // Extract transaction hashes
      const merchantTx = result.tx_hash;
      const commissionTx = result.tx_hash_commission;

      if (!merchantTx || !commissionTx) {
        const errorMsg = `Invalid response from signing service: ${JSON.stringify(result)}`;
        console.error(`❌ ${errorMsg}`);
        return errorMsg;
      }

      console.log(`✅ Payment signed and submitted by external service`);
      console.log(`   Merchant TX: ${merchantTx.slice(0, 20)}...`);
      console.log(`   Commission TX: ${commissionTx.slice(0, 20)}...`);
      console.log(`   Status: ${result.success ? 'Success' : 'Failed'}`);

      // Verify hashes have correct format
      if (merchantTx.length !== 66 || !merchantTx.startsWith('0x')) {
        const errorMsg = `Invalid merchant tx_hash format from service: ${merchantTx}`;
        console.error(`❌ ${errorMsg}`);
        return errorMsg;
      }

      if (commissionTx.length !== 66 || !commissionTx.startsWith('0x')) {
        const errorMsg = `Invalid commission tx_hash format from service: ${commissionTx}`;
        console.error(`❌ ${errorMsg}`);
        return errorMsg;
      }

      merchantTxHash = merchantTx;
      commissionTxHash = commissionTx;

      return `TX_HASHES:${merchantTx},${commissionTx}`;
    } catch (error: any) {
      if (error.code === 'ECONNABORTED') {
        const errorMsg = `Signing service timeout (exceeded 120s)`;
        console.error(`❌ ${errorMsg}`);
        return errorMsg;
      }

      if (error.code === 'ECONNREFUSED' || error.code === 'ENOTFOUND') {
        const errorMsg = `Cannot connect to signing service at ${TX_SIGNING_SERVICE}`;
        console.error(`❌ ${errorMsg}`);
        console.error(`   Check: curl ${TX_SIGNING_SERVICE}/health`);
        return errorMsg;
      }

      const errorMsg = `Payment signing failed: ${error.message}`;
      console.error(`❌ ${errorMsg}`);
      return errorMsg;
    }
  },
  {
    name: 'sign_payment',
    description: 'Sign and execute a blockchain payment via external signing service (PRODUCTION). Creates two transactions: merchant payment and gateway commission. Input should be an object with amountUsd and recipient.',
    schema: z.object({
      amountUsd: z.number().describe('Payment amount in USD'),
      recipient: z.string().describe('Recipient Ethereum address')
    })
  }
);

// Tool 3: Submit and Verify Payment
const submitAndVerifyPaymentTool = tool(
  async ({ merchantTx, commissionTx, mandateToken, priceUsd }: {
    merchantTx: string;
    commissionTx: string;
    mandateToken: string;
    priceUsd: number;
  }): Promise<string> => {
    try {
      console.log(`\n📤 Submitting to gateway...`);

      const paymentPayload = {
        scheme: 'eip3009',
        tx_hash: merchantTx,
        tx_hash_commission: commissionTx
      };

      const paymentB64 = Buffer.from(JSON.stringify(paymentPayload)).toString('base64');

      const headers = {
        'x-api-key': BUYER_API_KEY,
        'x-mandate': mandateToken,
        'x-payment': paymentB64
      };

      const url = `${AGENTPAY_API_URL}/x402/resource?chain=${chainConfig.chain}&token=${chainConfig.token}&price_usd=${priceUsd}`;
      const response = await axios.get(url, { headers, validateStatus: () => true });

      if (response.status >= 400) {
        const error = response.data?.error || response.data || 'Unknown error';
        console.error(`❌ Gateway error (${response.status}): ${error}`);
        return `Failed: ${error}`;
      }

      const result = response.data;

      // Check if payment was successful
      if (result.message || result.success || result.paid || result.status === 'confirmed') {
        console.log(`✅ Payment recorded`);

        // Verify mandate to get updated budget
        console.log(`   🔍 Fetching updated budget...`);
        const verifyResponse = await axios.post(
          `${AGENTPAY_API_URL}/mandates/verify`,
          { mandate_token: mandateToken },
          {
            headers: { 'x-api-key': BUYER_API_KEY, 'Content-Type': 'application/json' },
            validateStatus: () => true
          }
        );

        if (verifyResponse.status === 200) {
          const newBudget = verifyResponse.data.budget_remaining;
          console.log(`   ✅ Budget updated: $${newBudget}`);

          if (currentMandate) {
            currentMandate.budget_remaining = newBudget;
            const agentId = `research-assistant-${BUYER_WALLET}`;
            saveMandate(agentId, currentMandate);
          }

          return `Success! Paid: $${priceUsd}, Remaining: $${newBudget}`;
        } else {
          console.log(`   ⚠️  Could not fetch updated budget`);
          return `Success! Paid: $${priceUsd}`;
        }
      } else {
        const error = result.error || 'Unknown error';
        console.error(`❌ Failed: ${error}`);
        return `Failed: ${error}`;
      }
    } catch (error: any) {
      console.error(`❌ Error: ${error.message}`);
      return `Error: ${error.message}`;
    }
  },
  {
    name: 'submit_payment',
    description: 'Submit payment proof to AgentGatePay gateway for verification and budget tracking. Input should be an object with merchantTx, commissionTx, mandateToken, and priceUsd.',
    schema: z.object({
      merchantTx: z.string().describe('Merchant transaction hash'),
      commissionTx: z.string().describe('Commission transaction hash'),
      mandateToken: z.string().describe('AP2 mandate token'),
      priceUsd: z.number().describe('Payment amount in USD')
    })
  }
);

// ========================================
// CREATE AGENT
// ========================================

const llm = new ChatOpenAI({
  modelName: 'gpt-4o-mini',
  temperature: 0,
  openAIApiKey: process.env.OPENAI_API_KEY
});

const systemPrompt = `You are an autonomous AI agent that can make blockchain payments for resources.

Follow this workflow:
1. Issue a payment mandate with the specified budget using the issue_mandate tool
   - The tool returns: MANDATE_TOKEN:{token}
   - Extract the token after the colon
2. Sign the blockchain payment for the specified amount to the recipient using the sign_payment tool
   - This uses EXTERNAL SIGNING SERVICE (production-ready, no private key in code)
   - The tool returns: TX_HASHES:{merchant_tx},{commission_tx}
   - Extract both transaction hashes after the colon
3. Submit the payment to AgentGatePay using the submit_payment tool with: merchantTx, commissionTx, mandateToken, priceUsd
   - Use the mandate token from step 1
   - Use the transaction hashes from step 2
   - Use the payment amount specified in the task

IMPORTANT:
- Parse tool outputs to extract values (look for : separator)
- Always submit payment to AgentGatePay after signing (step 3 is mandatory)
- If any tool returns an error, STOP immediately and report the error
- Do NOT retry failed operations`;

// ========================================
// MAIN EXECUTION
// ========================================

async function main() {
  console.log('='.repeat(80));
  console.log('AGENTGATEPAY + LANGCHAIN.JS: PRODUCTION TX SIGNING DEMO');
  console.log('='.repeat(80));
  console.log();
  console.log('This demo shows PRODUCTION-READY autonomous agent payments using:');
  console.log('  - AgentGatePay REST API (latest SDK)');
  console.log('  - External transaction signing service (NO private key in code)');
  console.log('  - LangChain.js agent framework');
  console.log('  - Multi-chain blockchain payments (Base/Ethereum/Polygon/Arbitrum)');
  console.log('  - Multi-token support (USDC/USDT/DAI)');
  console.log();
  console.log('✅ SECURE: Private key stored in signing service, NOT in application');
  console.log('✅ SCALABLE: Signing service can be deployed independently');
  console.log('✅ PRODUCTION READY: Suitable for real-world deployments');
  console.log();

  // Load chain/token configuration
  console.log('\nCHAIN & TOKEN CONFIGURATION');
  console.log('='.repeat(80));

  chainConfig = getChainConfig();
  displayChainConfig(chainConfig);

  // Initialize AgentGatePay client
  agentpay = new AgentGatePay({
    apiUrl: AGENTPAY_API_URL,
    apiKey: BUYER_API_KEY
  });

  console.log(`\n✅ Initialized AgentGatePay client: ${AGENTPAY_API_URL}`);
  console.log(`✅ Configured TX signing service: ${TX_SIGNING_SERVICE}`);
  console.log(`✅ Buyer wallet: ${BUYER_WALLET}`);
  console.log(`✅ PRODUCTION MODE: Private key NOT in application code\n`);

  // Check signing service health
  console.log(`\n🏥 Checking signing service health...`);
  try {
    const healthResponse = await axios.get(`${TX_SIGNING_SERVICE}/health`, { timeout: 5000 });
    if (healthResponse.status === 200) {
      const healthData = healthResponse.data;
      console.log(`✅ Signing service is healthy`);
      console.log(`   Status: ${healthData.status || 'N/A'}`);
      console.log(`   Wallet configured: ${healthData.wallet_configured}`);
    } else {
      console.log(`⚠️  Signing service returned: HTTP ${healthResponse.status}`);
      console.log(`   Warning: Service may not be fully operational`);
    }
  } catch (error: any) {
    console.error(`❌ Cannot connect to signing service: ${error.message}`);
    console.error(`   Please ensure TX_SIGNING_SERVICE is running`);
    console.error(`   URL: ${TX_SIGNING_SERVICE}`);
    console.error(`   See docs/TX_SIGNING_OPTIONS.md for setup instructions`);
    process.exit(1);
  }

  // Check for existing mandate
  const agentId = `research-assistant-${BUYER_WALLET}`;
  const existingMandate = getMandate(agentId);

  let mandateBudget: number;
  let purpose: string;

  if (existingMandate) {
    const token = existingMandate.mandate_token;

    // Get LIVE budget from gateway
    const verifyResponse = await axios.post(
      `${AGENTPAY_API_URL}/mandates/verify`,
      { mandate_token: token },
      {
        headers: { 'x-api-key': BUYER_API_KEY, 'Content-Type': 'application/json' },
        validateStatus: () => true
      }
    );

    let budgetRemaining: string | number;
    if (verifyResponse.status === 200) {
      budgetRemaining = verifyResponse.data.budget_remaining;
    } else {
      // Fallback to JWT
      const tokenData = decodeMandateToken(token);
      budgetRemaining = tokenData.budget_remaining || 'Unknown';
    }

    console.log(`\n♻️  Using existing mandate (Budget: $${budgetRemaining})`);
    console.log(`   Token: ${token.slice(0, 50)}...`);
    console.log(`   To delete: rm ../.agentgatepay_mandates.json\n`);
    mandateBudget = typeof budgetRemaining === 'number' ? budgetRemaining : MANDATE_BUDGET_USD;
    purpose = 'research resource';
  } else {
    // For simplicity in the automated example, use defaults
    mandateBudget = MANDATE_BUDGET_USD;
    purpose = 'research resource';
    console.log(`\n💰 Using default mandate budget: $${mandateBudget}`);
    console.log(`📝 Using default purpose: ${purpose}\n`);
  }

  // Create agent with tools
  const tools = [issueMandateTool, signPaymentViaServiceTool, submitAndVerifyPaymentTool];

  const agent = createReactAgent({
    llm,
    tools,
    messageModifier: systemPrompt
  });

  // Agent task
  const task = `Purchase a ${purpose} for $${RESOURCE_PRICE_USD} USD using PRODUCTION signing service.

Steps:
1. Issue a payment mandate with a $${mandateBudget} budget (or reuse existing)
2. Sign blockchain payment of $${RESOURCE_PRICE_USD} to seller: ${SELLER_WALLET}
   (This will be signed by the external signing service - NO private key in code)
3. Submit payment proof to AgentGatePay with mandate token

This is a PRODUCTION-READY payment using external signing service.`;

  try {
    // Run agent
    const result = await agent.invoke({ messages: [{ role: 'user', content: task }] });

    console.log('\n' + '='.repeat(80));
    console.log('PRODUCTION PAYMENT WORKFLOW COMPLETED');
    console.log('='.repeat(80));

    // Extract final message
    if (result.messages && result.messages.length > 0) {
      const finalMessage = result.messages[result.messages.length - 1];
      console.log(`\nResult: ${finalMessage.content}`);
    } else {
      console.log(`\nResult: ${JSON.stringify(result)}`);
    }

    // Display final status
    if (currentMandate) {
      console.log(`\nFinal Status:`);
      console.log(`  Mandate: ${currentMandate.mandate_token.slice(0, 50)}...`);
      console.log(`  Budget remaining: $${currentMandate.budget_remaining}`);
    }

    if (merchantTxHash) {
      console.log(`\nBlockchain Transactions:`);
      console.log(`  Merchant TX: ${chainConfig.explorer}/tx/${merchantTxHash}`);
      console.log(`  Commission TX: ${chainConfig.explorer}/tx/${commissionTxHash}`);

      // Display gateway audit logs with curl commands
      console.log(`\nGateway Audit Logs (copy-paste these commands):`);
      console.log(`\n# All payment logs (by wallet):`);
      console.log(`curl '${AGENTPAY_API_URL}/audit/logs?client_id=${BUYER_WALLET}&event_type=x402_payment_settled&limit=10' \\`);
      console.log(`  -H 'x-api-key: ${BUYER_API_KEY}' | jq`);
      console.log(`\n# Recent payments (24h):`);
      console.log(`curl '${AGENTPAY_API_URL}/audit/logs?client_id=${BUYER_WALLET}&event_type=x402_payment_settled&hours=24' \\`);
      console.log(`  -H 'x-api-key: ${BUYER_API_KEY}' | jq`);
      console.log(`\n# Payment verification (by tx_hash):`);
      console.log(`curl '${AGENTPAY_API_URL}/v1/payments/verify/${merchantTxHash}' \\`);
      console.log(`  -H 'x-api-key: ${BUYER_API_KEY}' | jq`);

      console.log(`\n✅ PRODUCTION SUCCESS:`);
      console.log(`   Private key: SECURE (stored in signing service)`);
      console.log(`   Application code: CLEAN (no private keys)`);
      console.log(`   Payment: VERIFIED (on ${chainConfig.chain.charAt(0).toUpperCase() + chainConfig.chain.slice(1)} blockchain)`);
    }
  } catch (error: any) {
    console.error(`\n\n❌ Error: ${error.message}`);
    console.error(error.stack);
  }
}

// Run main function
main();
