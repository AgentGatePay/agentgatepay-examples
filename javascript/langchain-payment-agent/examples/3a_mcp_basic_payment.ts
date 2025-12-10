#!/usr/bin/env tsx
/**
 * AgentGatePay + LangChain.js Integration - Example 3a: MCP + Local Signing
 *
 * This example demonstrates the SAME payment flow as Example 1a,
 * but using AgentGatePay's MCP (Model Context Protocol) tools instead of REST API.
 *
 * MCP Advantages:
 * - Native tool discovery (framework can list all 15 AgentGatePay tools)
 * - Standardized JSON-RPC 2.0 protocol
 * - Future-proof (Anthropic-backed standard)
 * - Cleaner separation between agent logic and API calls
 *
 * MCP Tools Used:
 * - agentpay_issue_mandate - Issue AP2 payment mandate
 * - agentpay_submit_payment - Submit blockchain payment proof
 * - agentpay_verify_mandate - Verify mandate is valid
 *
 * Flow:
 * 1. Issue AP2 mandate ($100 budget) via MCP
 * 2. Sign blockchain transactions locally (ethers.js)
 * 3. Submit payment and verify budget via MCP tools
 *
 * Requirements:
 * - npm install
 * - .env file with configuration (see .env.example)
 *
 * For Production: See Example 3b (MCP + external TX signing)
 * For REST API Version: See Example 1a (REST API + local signing)
 */

import { config } from 'dotenv';
import { ethers } from 'ethers';
import axios from 'axios';
import { ChatOpenAI } from '@langchain/openai';
import { createReactAgent } from '@langchain/langgraph/prebuilt';
import { tool } from '@langchain/core/tools';
import { z } from 'zod';
import { createInterface } from 'readline';
import { saveMandate, getMandate } from '../utils/index.js';
import { getChainConfig, displayChainConfig, type ChainConfig } from '../chain_config.js';

config();

const AGENTPAY_API_URL = process.env.AGENTPAY_API_URL || 'https://api.agentgatepay.com';
const AGENTPAY_MCP_ENDPOINT = process.env.MCP_API_URL || 'https://mcp.agentgatepay.com';
const BUYER_API_KEY = process.env.BUYER_API_KEY!;
const BUYER_PRIVATE_KEY = process.env.BUYER_PRIVATE_KEY!;
const SELLER_WALLET = process.env.SELLER_WALLET!;

const RESOURCE_PRICE_USD = 0.01;
const MANDATE_BUDGET_USD = 100.0;

let chainConfig: ChainConfig;
let provider: ethers.JsonRpcProvider;
let buyerWallet: ethers.Wallet;
let currentMandate: any = null;
let merchantTxHash: string | null = null;
let commissionTxHash: string | null = null;

// MCP Tool Wrapper
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

  console.log(`   📡 Calling MCP tool: ${toolName}`);

  const response = await axios.post(AGENTPAY_MCP_ENDPOINT, payload, {
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': BUYER_API_KEY
    }
  });

  if (response.data.error) {
    throw new Error(`MCP error: ${JSON.stringify(response.data.error)}`);
  }

  const contentText = response.data.result.content[0].text;
  return JSON.parse(contentText);
}

function decodeMandateToken(token: string): any {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return {};
    let payload_b64 = parts[1];
    const padding = 4 - (payload_b64.length % 4);
    if (padding !== 4) payload_b64 += '='.repeat(padding);
    const payloadJson = Buffer.from(payload_b64, 'base64url').toString('utf8');
    return JSON.parse(payloadJson);
  } catch {
    return {};
  }
}

async function getCommissionConfig(): Promise<any> {
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

// Tool 1: Issue Mandate via MCP
const mcpIssueMandateTool = tool(
  async ({ budgetUsd }: { budgetUsd: number }): Promise<string> => {
    try {
      const agentId = `research-assistant-${buyerWallet.address}`;
      const existingMandate = getMandate(agentId);

      if (existingMandate) {
        const token = existingMandate.mandate_token;
        try {
          const verifyResult = await callMcpTool('agentpay_verify_mandate', {
            mandate_token: token
          });

          const budgetRemaining = verifyResult.valid ? verifyResult.budget_remaining : 'Unknown';
          console.log(`\n♻️  Reusing mandate (Budget: $${budgetRemaining})`);
          currentMandate = { ...existingMandate, budget_remaining: budgetRemaining };
          return `MANDATE_TOKEN:${token}`;
        } catch {
          const tokenData = decodeMandateToken(token);
          const budgetRemaining = tokenData.budget_remaining || existingMandate.budget_usd || 'Unknown';
          console.log(`\n♻️  Reusing mandate (Budget: $${budgetRemaining})`);
          currentMandate = { ...existingMandate, budget_remaining: budgetRemaining };
          return `MANDATE_TOKEN:${token}`;
        }
      }

      console.log(`\n🔐 Creating mandate ($${budgetUsd})...`);

      const mandate = await callMcpTool('agentpay_issue_mandate', {
        subject: agentId,
        budget_usd: budgetUsd,
        scope: 'resource.read,payment.execute',
        ttl_minutes: 168 * 60
      });

      const token = mandate.mandate_token;
      const mandateWithBudget = {
        ...mandate,  // Include ALL MCP response fields (expires_at, subject, scope, etc.)
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
    name: 'issue_mandate_mcp',
    description: 'Issue AP2 mandate using MCP tool. Input: budgetUsd (number)',
    schema: z.object({ budgetUsd: z.number().describe('Budget amount in USD') })
  }
);

// Tool 2: Sign Payment (same as Example 1a)
const signPaymentTool = tool(
  async ({ amountUsd, recipient }: { amountUsd: number; recipient: string }): Promise<string> => {
    try {
      const commissionConfig = await getCommissionConfig();
      if (!commissionConfig) return 'Error: Failed to fetch commission config';

      console.log(`\n💳 Signing payment ($${amountUsd} ${chainConfig.token})...`);
      console.log(`   Chain: ${chainConfig.chain.charAt(0).toUpperCase() + chainConfig.chain.slice(1)} (ID: ${chainConfig.chainId})`);
      console.log(`   Token: ${chainConfig.token} (${chainConfig.decimals} decimals)`);

      const commissionAmountUsd = amountUsd * commissionConfig.commission_rate;
      const merchantAmountUsd = amountUsd - commissionAmountUsd;
      const merchantAmountAtomic = BigInt(Math.floor(merchantAmountUsd * (10 ** chainConfig.decimals)));
      const commissionAmountAtomic = BigInt(Math.floor(commissionAmountUsd * (10 ** chainConfig.decimals)));

      const transferSig = ethers.keccak256(ethers.toUtf8Bytes('transfer(address,uint256)')).slice(0, 10);
      const nonce = await provider.getTransactionCount(buyerWallet.address);

      console.log(`   📤 TX 1/2 (merchant)...`);
      const recipientBytes = ethers.zeroPadValue(ethers.getAddress(recipient), 32);
      const merchantData = ethers.concat([
        transferSig,
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
      const txMerchant = await provider.broadcastTransaction(signedMerchantTx);
      merchantTxHash = txMerchant.hash;
      console.log(`   ✅ TX 1/2 sent: ${merchantTxHash.slice(0, 20)}...`);

      console.log(`   📤 TX 2/2 (commission)...`);
      const commissionBytes = ethers.zeroPadValue(ethers.getAddress(commissionConfig.commission_address), 32);
      const commissionData = ethers.concat([
        transferSig,
        commissionBytes,
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
      const txCommission = await provider.broadcastTransaction(signedCommissionTx);
      commissionTxHash = txCommission.hash;
      console.log(`   ✅ TX 2/2 sent: ${commissionTxHash.slice(0, 20)}...`);

      return `TX_HASHES:${merchantTxHash},${commissionTxHash}`;
    } catch (error: any) {
      console.error(`❌ Payment failed: ${error.message}`);
      throw new Error(`Payment failed: ${error.message}`);
    }
  },
  {
    name: 'sign_payment',
    description: 'Sign blockchain payment locally (ethers.js). Input: amountUsd, recipient',
    schema: z.object({
      amountUsd: z.number().describe('Payment amount in USD'),
      recipient: z.string().describe('Recipient address')
    })
  }
);

// Tool 3: Submit and Verify via MCP
const mcpSubmitAndVerifyTool = tool(
  async (): Promise<string> => {
    if (!currentMandate || !merchantTxHash) {
      return 'Error: Must issue mandate and sign payment first';
    }

    console.log(`\n📤 [MCP] Submitting payment proof...`);

    try {
      const result = await callMcpTool('agentpay_submit_payment', {
        mandate_token: currentMandate.mandate_token,
        tx_hash: merchantTxHash,
        tx_hash_commission: commissionTxHash,
        chain: chainConfig.chain,
        token: chainConfig.token
      });

      console.log(`✅ Payment submitted via MCP`);
      console.log(`   Status: ${result.status || 'N/A'}`);

      console.log(`   🔍 Fetching updated budget...`);
      const verifyResult = await callMcpTool('agentpay_verify_mandate', {
        mandate_token: currentMandate.mandate_token
      });

      if (verifyResult.valid) {
        const newBudget = verifyResult.budget_remaining;
        console.log(`   ✅ Budget updated: $${newBudget}`);

        if (currentMandate) {
          currentMandate.budget_remaining = newBudget;
          const agentId = `research-assistant-${buyerWallet.address}`;
          saveMandate(agentId, currentMandate);
        }

        return `Success! Paid: $${RESOURCE_PRICE_USD}, Remaining: $${newBudget}`;
      } else {
        console.log(`   ⚠️  Could not fetch updated budget`);
        return `Success! Paid: $${RESOURCE_PRICE_USD}`;
      }
    } catch (error: any) {
      console.error(`❌ Payment submission failed: ${error.message}`);
      return `Error: ${error.message}`;
    }
  },
  {
    name: 'submit_and_verify_payment',
    description: 'Submit payment proof via MCP and verify updated budget. No input needed.',
    schema: z.object({})
  }
);

const llm = new ChatOpenAI({
  modelName: 'gpt-4',
  temperature: 0,
  openAIApiKey: process.env.OPENAI_API_KEY
});

const systemPrompt = `You are an autonomous AI agent using AgentGatePay MCP tools for payments.

Follow this workflow:
1. Issue mandate using MCP tool (issue_mandate_mcp) with the specified budget
   - Returns: "MANDATE_TOKEN:{token}" - extract token
2. Sign blockchain payment locally (sign_payment) for specified amount to recipient
   - Returns: "TX_HASHES:{merchant_tx},{commission_tx}" - extract hashes
3. Submit payment and verify budget using MCP tool (submit_and_verify_payment)
   - Automatically uses mandate and transaction hashes from previous steps

IMPORTANT:
- All three steps must complete successfully
- Parse tool outputs to extract values
- If any tool returns an error, STOP immediately and report
- Do NOT retry failed operations`;

async function main() {
  console.log('='.repeat(80));
  console.log('AGENTGATEPAY + LANGCHAIN.JS: BASIC PAYMENT DEMO (MCP TOOLS)');
  console.log('='.repeat(80));
  console.log();
  console.log('This demo shows an autonomous agent making a blockchain payment using:');
  console.log('  - AgentGatePay MCP tools (JSON-RPC 2.0)');
  console.log('  - LangChain.js agent framework');
  console.log('  - Multi-chain blockchain payments (Base/Ethereum/Polygon/Arbitrum)');
  console.log('  - Multi-token support (USDC/USDT/DAI)');
  console.log();

  console.log('\nCHAIN & TOKEN CONFIGURATION');
  console.log('='.repeat(80));
  chainConfig = getChainConfig();
  displayChainConfig(chainConfig);

  provider = new ethers.JsonRpcProvider(chainConfig.rpcUrl);
  buyerWallet = new ethers.Wallet(BUYER_PRIVATE_KEY, provider);

  console.log(`\nInitialized AgentGatePay MCP client: ${AGENTPAY_MCP_ENDPOINT}`);
  console.log(`Initialized ethers.js provider: ${chainConfig.chain.charAt(0).toUpperCase() + chainConfig.chain.slice(1)} network`);
  console.log(`Buyer wallet: ${buyerWallet.address}\n`);

  const agentId = `research-assistant-${buyerWallet.address}`;
  const existingMandate = getMandate(agentId);

  let mandateBudget: number;
  let purpose: string;

  if (existingMandate) {
    const token = existingMandate.mandate_token;
    try {
      const verifyResult = await callMcpTool('agentpay_verify_mandate', { mandate_token: token });
      const budgetRemaining = verifyResult.valid ? verifyResult.budget_remaining : 'Unknown';
      console.log(`\n♻️  Using existing mandate (Budget: $${budgetRemaining})`);
      console.log(`   Token: ${token.slice(0, 50)}...`);
      console.log(`   To delete: rm ../.agentgatepay_mandates.json\n`);
      mandateBudget = typeof budgetRemaining === 'number' ? budgetRemaining : MANDATE_BUDGET_USD;
    } catch {
      const tokenData = decodeMandateToken(token);
      const budgetRemaining = tokenData.budget_remaining || 'Unknown';
      console.log(`\n♻️  Using existing mandate (Budget: $${budgetRemaining})`);
      mandateBudget = typeof budgetRemaining === 'number' ? budgetRemaining : MANDATE_BUDGET_USD;
    }
    purpose = 'research resource';
  } else {
    // Prompt user for input (matching Python and Script 1a behavior)
    const readline = createInterface({
      input: process.stdin,
      output: process.stdout
    });

    const askQuestion = (query: string): Promise<string> => {
      return new Promise(resolve => readline.question(query, resolve));
    };

    const budgetInput = await askQuestion('\n💰 Enter mandate budget in USD Coins (default: 100): ');
    mandateBudget = budgetInput.trim() ? parseFloat(budgetInput.trim()) : MANDATE_BUDGET_USD;

    const purposeInput = await askQuestion('📝 Enter payment purpose (default: research resource): ');
    purpose = purposeInput.trim() || 'research resource';

    readline.close();
    console.log();
  }

  const tools = [mcpIssueMandateTool, signPaymentTool, mcpSubmitAndVerifyTool];
  const agent = createReactAgent({ llm, tools, messageModifier: systemPrompt });

  const task = `Purchase a ${purpose} for $${RESOURCE_PRICE_USD} USD.

Steps:
1. Issue a payment mandate with a $${mandateBudget} budget (or reuse existing)
2. Sign blockchain payment of $${RESOURCE_PRICE_USD} to seller: ${SELLER_WALLET}
3. Submit payment proof to AgentGatePay with mandate token

The mandate token and transaction hashes will be available after steps 1 and 2.`;

  try {
    const result = await agent.invoke({ messages: [{ role: 'user', content: task }] });

    console.log('\n' + '='.repeat(80));
    console.log('PAYMENT WORKFLOW COMPLETED');
    console.log('='.repeat(80));

    if (result.messages && result.messages.length > 0) {
      const finalMessage = result.messages[result.messages.length - 1];
      console.log(`\nResult: ${finalMessage.content}`);
    }

    if (currentMandate) {
      console.log(`\nFinal Status:`);
      console.log(`  Mandate: ${currentMandate.mandate_token.slice(0, 50)}...`);
      console.log(`  Budget remaining: $${currentMandate.budget_remaining}`);
    }

    if (merchantTxHash) {
      console.log(`\nBlockchain Transactions:`);
      console.log(`  Merchant TX: ${chainConfig.explorer}/tx/${merchantTxHash}`);
      console.log(`  Commission TX: ${chainConfig.explorer}/tx/${commissionTxHash}`);

      console.log(`\nGateway Audit Logs (copy-paste these commands):`);
      console.log(`\n# All payment logs (by wallet):`);
      console.log(`curl '${AGENTPAY_API_URL}/audit/logs?client_id=${buyerWallet.address}&event_type=x402_payment_settled&limit=10' \\`);
      console.log(`  -H 'x-api-key: ${BUYER_API_KEY}' | jq`);
    }
  } catch (error: any) {
    console.error(`\n\n❌ Error: ${error.message}`);
    console.error(error.stack);
  }
}

main();
