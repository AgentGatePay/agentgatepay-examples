#!/usr/bin/env tsx
/**
 * AgentGatePay + LangChain.js Integration - Example 1a: REST API + Local Signing
 *
 * This example demonstrates a simple autonomous payment flow using:
 * - AgentGatePay REST API (via published SDK v1.1.4+)
 * - LangChain.js agent with payment tools
 * - Local transaction signing (private key in .env)
 * - Multi-chain blockchain payments (Base, Ethereum, Polygon, Arbitrum)
 * - Multi-token support (USDC, USDT, DAI)
 *
 * Flow:
 * 1. Configure chain and token (from .env file)
 * 2. Issue AP2 mandate ($100 budget)
 * 3. Sign blockchain transactions locally (ethers.js)
 * 4. Submit payment proof to AgentGatePay
 * 5. Verify payment completion and view audit logs
 *
 * Requirements:
 * - npm install
 * - .env file with configuration (see .env.example)
 *
 * Multi-Chain Configuration:
 * - Edit .env file: PAYMENT_CHAIN=base (options: base, ethereum, polygon, arbitrum)
 * - Edit .env file: PAYMENT_TOKEN=USDC (options: USDC, USDT, DAI)
 * - Note: USDT not available on Base, DAI uses 18 decimals
 *
 * For Production: See Example 1b (external TX signing service)
 */

import { config } from 'dotenv';
import { ethers } from 'ethers';
import axios from 'axios';
import { AgentGatePay } from 'agentgatepay-sdk';
import { ChatOpenAI } from '@langchain/openai';
import { createReactAgent } from '@langchain/langgraph/prebuilt';
import { tool } from '@langchain/core/tools';
import { z } from 'zod';
import { saveMandate, getMandate } from '../utils/index.js';
import { getChainConfig, displayChainConfig } from '../chain_config.js';

// Load environment variables
config();

// ========================================
// TRANSACTION SIGNING
// ========================================
//
// This example uses LOCAL SIGNING (ethers.js with private key).
//
// ⚠️ WARNING: Local signing is NOT recommended for production!
//
// For production deployments, use an external signing service:
// - Option 1: Docker container
// - Option 2: Render one-click deploy (https://github.com/AgentGatePay/TX)
// - Option 3: Railway deployment
// - Option 4: Self-hosted service
//
// See Example 1b (examples/1b_api_with_tx_service.ts) for external signing usage.
//
// ========================================

// ========================================
// CONFIGURATION
// ========================================

const AGENTPAY_API_URL = process.env.AGENTPAY_API_URL || 'https://api.agentgatepay.com';
const BUYER_API_KEY = process.env.BUYER_API_KEY!;
const BUYER_EMAIL = process.env.BUYER_EMAIL!;
const BUYER_PRIVATE_KEY = process.env.BUYER_PRIVATE_KEY!;
const SELLER_WALLET = process.env.SELLER_WALLET!;

// Payment configuration
const RESOURCE_PRICE_USD = 0.01;
const MANDATE_BUDGET_USD = 100.0;

// Chain configuration (loaded in main)
let chainConfig: Awaited<ReturnType<typeof getChainConfig>>;
let agentpay: AgentGatePay;
let provider: ethers.JsonRpcProvider;
let buyerWallet: ethers.Wallet;

// ========================================
// HELPER FUNCTIONS
// ========================================

interface CommissionConfig {
  commission_address: string;
  commission_rate: number;
}

async function getCommissionConfig(): Promise<CommissionConfig | null> {
  try {
    const response = await axios.get(`${AGENTPAY_API_URL}/v1/config/commission`, {
      headers: { 'x-api-key': BUYER_API_KEY }
    });
    return response.data;
  } catch (error) {
    console.error('⚠️  Failed to fetch commission config:', error);
    return null;
  }
}

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

// Global mandate storage
let currentMandate: any = null;
let merchantTxHash: string | null = null;
let commissionTxHash: string | null = null;
let signedAmountUsd: number | null = null;

// Tool 1: Issue Mandate
const issueMandateTool = tool(
  async ({ budgetUsd }: { budgetUsd: number }): Promise<string> => {
    try {
      const agentId = `research-assistant-${buyerWallet.address}`;
      const existingMandate = getMandate(agentId);

      if (existingMandate) {
        const token = existingMandate.mandate_token;

        // Get LIVE budget from gateway
        const verifyResponse = await axios.post(
          `${AGENTPAY_API_URL}/mandates/verify`,
          { mandate_token: token },
          { headers: { 'x-api-key': BUYER_API_KEY, 'Content-Type': 'application/json' } }
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

      const mandate = await agentpay.mandates.issue({
        subject: agentId,
        budget: budgetUsd,
        scope: 'resource.read,payment.execute',
        ttlMinutes: 168 * 60
      });

      // Store mandate with budget info
      const token = mandate.mandateToken;
      const mandateWithBudget = {
        mandate_token: token,
        budget_usd: budgetUsd,
        budget_remaining: budgetUsd // Initially, remaining = total
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

// Tool 2: Sign Blockchain Payment
const signBlockchainPaymentTool = tool(
  async ({ amountUsd, recipient }: { amountUsd: number; recipient: string }): Promise<string> => {
    try {
      const commissionConfig = await getCommissionConfig();
      if (!commissionConfig) {
        return 'Error: Failed to fetch commission config';
      }

      const { commission_address: commissionAddress, commission_rate: commissionRate } = commissionConfig;

      console.log(`\n💳 Signing payment ($${amountUsd} ${chainConfig.token})...`);
      console.log(`   Chain: ${chainConfig.chain.charAt(0).toUpperCase() + chainConfig.chain.slice(1)} (ID: ${chainConfig.chainId})`);
      console.log(`   Token: ${chainConfig.token} (${chainConfig.decimals} decimals)`);

      const commissionAmountUsd = amountUsd * commissionRate;
      const merchantAmountUsd = amountUsd - commissionAmountUsd;
      const merchantAmountAtomic = BigInt(Math.floor(merchantAmountUsd * (10 ** chainConfig.decimals)));
      const commissionAmountAtomic = BigInt(Math.floor(commissionAmountUsd * (10 ** chainConfig.decimals)));

      // ERC-20 transfer function signature
      const transferFunctionSignature = ethers.keccak256(ethers.toUtf8Bytes('transfer(address,uint256)')).slice(0, 10);

      // Fetch nonce once for both transactions
      const nonce = await provider.getTransactionCount(buyerWallet.address);

      console.log(`   📤 TX 1/2 (merchant)...`);
      const recipientClean = recipient.replace('0x', '').toLowerCase();
      const recipientBytes = ethers.zeroPadValue('0x' + recipientClean, 32);

      const merchantData = ethers.concat([
        transferFunctionSignature,
        recipientBytes,
        ethers.zeroPadValue(ethers.toBeHex(merchantAmountAtomic), 32)
      ]);

      const merchantTx = {
        nonce,
        to: chainConfig.tokenContract,
        value: 0,
        gasLimit: 100000,
        gasPrice: (await provider.getFeeData()).gasPrice,
        data: merchantData,
        chainId: chainConfig.chainId
      };

      const signedMerchantTx = await buyerWallet.signTransaction(merchantTx);
      const txHashMerchantRaw = await provider.broadcastTransaction(signedMerchantTx);
      const txHashMerchant = txHashMerchantRaw.hash;
      console.log(`   ✅ TX 1/2 sent: ${txHashMerchant.slice(0, 20)}...`);

      console.log(`   📤 TX 2/2 (commission)...`);
      const commissionAddrClean = commissionAddress.replace('0x', '').toLowerCase();
      const commissionAddrBytes = ethers.zeroPadValue('0x' + commissionAddrClean, 32);

      const commissionData = ethers.concat([
        transferFunctionSignature,
        commissionAddrBytes,
        ethers.zeroPadValue(ethers.toBeHex(commissionAmountAtomic), 32)
      ]);

      const commissionTx = {
        nonce: nonce + 1,
        to: chainConfig.tokenContract,
        value: 0,
        gasLimit: 100000,
        gasPrice: (await provider.getFeeData()).gasPrice,
        data: commissionData,
        chainId: chainConfig.chainId
      };

      const signedCommissionTx = await buyerWallet.signTransaction(commissionTx);
      const txHashCommissionRaw = await provider.broadcastTransaction(signedCommissionTx);
      const txHashCommission = txHashCommissionRaw.hash;
      console.log(`   ✅ TX 2/2 sent: ${txHashCommission.slice(0, 20)}...`);

      merchantTxHash = txHashMerchant;
      commissionTxHash = txHashCommission;
      signedAmountUsd = amountUsd;

      return `TX_HASHES:${txHashMerchant},${txHashCommission}`;
    } catch (error: any) {
      console.error(`❌ Payment failed: ${error.message}`);
      throw new Error(`Payment failed: ${error.message}`);
    }
  },
  {
    name: 'sign_payment',
    description: 'Sign and execute a blockchain payment on the configured network and token. Creates two transactions: merchant payment and gateway commission. Input should be an object with amountUsd and recipientAddress.',
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
          { headers: { 'x-api-key': BUYER_API_KEY, 'Content-Type': 'application/json' } }
        );

        if (verifyResponse.status === 200) {
          const newBudget = verifyResponse.data.budget_remaining;
          console.log(`   ✅ Budget updated: $${newBudget}`);

          if (currentMandate) {
            currentMandate.budget_remaining = newBudget;
            const agentId = `research-assistant-${buyerWallet.address}`;
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
  modelName: 'gpt-4',
  temperature: 0,
  openAIApiKey: process.env.OPENAI_API_KEY
});

const systemPrompt = `You are an autonomous AI agent that can make blockchain payments for resources.

Follow this workflow:
1. Issue a payment mandate with the specified budget using the issue_mandate tool
   - The tool returns: MANDATE_TOKEN:{token}
   - Extract the token after the colon
2. Sign the blockchain payment for the specified amount to the recipient using the sign_payment tool
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
  console.log('AGENTGATEPAY + LANGCHAIN.JS: BASIC PAYMENT DEMO (REST API)');
  console.log('='.repeat(80));
  console.log();
  console.log('This demo shows an autonomous agent making a blockchain payment using:');
  console.log('  - AgentGatePay REST API (latest SDK)');
  console.log('  - LangChain.js agent framework');
  console.log('  - Multi-chain blockchain payments (Base/Ethereum/Polygon/Arbitrum)');
  console.log('  - Multi-token support (USDC/USDT/DAI)');
  console.log();

  // Load chain/token configuration
  console.log('\nCHAIN & TOKEN CONFIGURATION');
  console.log('='.repeat(80));

  chainConfig = getChainConfig();
  displayChainConfig(chainConfig);

  // Initialize clients
  agentpay = new AgentGatePay({
    apiUrl: AGENTPAY_API_URL,
    apiKey: BUYER_API_KEY
  });

  provider = new ethers.JsonRpcProvider(chainConfig.rpcUrl);
  buyerWallet = new ethers.Wallet(BUYER_PRIVATE_KEY, provider);

  console.log(`\nInitialized AgentGatePay client: ${AGENTPAY_API_URL}`);
  console.log(`Initialized ethers.js provider: ${chainConfig.chain.charAt(0).toUpperCase() + chainConfig.chain.slice(1)} network`);
  console.log(`Buyer wallet: ${buyerWallet.address}\n`);

  // Check for existing mandate
  const agentId = `research-assistant-${buyerWallet.address}`;
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
  const tools = [issueMandateTool, signBlockchainPaymentTool, submitAndVerifyPaymentTool];

  const agent = createReactAgent({
    llm,
    tools,
    messageModifier: systemPrompt
  });

  // Agent task
  const task = `Purchase a ${purpose} for $${RESOURCE_PRICE_USD} USD.

Steps:
1. Issue a payment mandate with a $${mandateBudget} budget (or reuse existing)
2. Sign blockchain payment of $${RESOURCE_PRICE_USD} to seller: ${SELLER_WALLET}
3. Submit payment proof to AgentGatePay with mandate token

The mandate token and transaction hashes will be available after steps 1 and 2.`;

  try {
    // Run agent
    const result = await agent.invoke({ messages: [{ role: 'user', content: task }] });

    console.log('\n' + '='.repeat(80));
    console.log('PAYMENT WORKFLOW COMPLETED');
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
      console.log(`curl '${AGENTPAY_API_URL}/audit/logs?client_id=${buyerWallet.address}&event_type=x402_payment_settled&limit=10' \\`);
      console.log(`  -H 'x-api-key: ${BUYER_API_KEY}' | jq`);
      console.log(`\n# Recent payments (24h):`);
      console.log(`curl '${AGENTPAY_API_URL}/audit/logs?client_id=${buyerWallet.address}&event_type=x402_payment_settled&hours=24' \\`);
      console.log(`  -H 'x-api-key: ${BUYER_API_KEY}' | jq`);
      console.log(`\n# Payment verification (by tx_hash):`);
      console.log(`curl '${AGENTPAY_API_URL}/v1/payments/verify/${merchantTxHash}' \\`);
      console.log(`  -H 'x-api-key: ${BUYER_API_KEY}' | jq`);
    }
  } catch (error: any) {
    console.error(`\n\n❌ Error: ${error.message}`);
    console.error(error.stack);
  }
}

// Run main function
main();
