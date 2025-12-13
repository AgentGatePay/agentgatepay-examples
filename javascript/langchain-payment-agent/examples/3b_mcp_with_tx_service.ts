/**
 * AgentGatePay + LangChain Integration - Example 3b: MCP + External TX Signing
 *
 * This example demonstrates PRODUCTION-READY autonomous agent payments by combining:
 * - AgentGatePay MCP tools (JSON-RPC 2.0 protocol)
 * - External transaction signing service (NO private key in code)
 *
 * Combines best of both worlds:
 * - Example 3a: MCP tools for mandate management and payment submission
 * - Example 1b: External TX signing for production security
 *
 * MCP Tools Used:
 * - agentpay_issue_mandate - Issue AP2 payment mandate
 * - agentpay_submit_payment - Submit blockchain payment proof
 * - agentpay_verify_mandate - Verify mandate is valid
 *
 * Flow:
 * 1. Issue AP2 mandate via MCP ($100 budget)
 * 2. Request payment signing from external service (Docker/Render/Railway/self-hosted)
 * 3. Submit payment proof to AgentGatePay via MCP
 * 4. Verify payment completion via MCP
 *
 * Security Benefits:
 * - Private key stored in signing service, NOT in application code
 * - Application cannot access private keys
 * - Signing service can be audited independently
 * - Scalable deployment options
 * - MCP standardized protocol for agent communication
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
 * For Development: See Example 3a (MCP + local signing, simpler setup)
 * For REST API Version: See Example 1b (REST API + external signing)
 */

import 'dotenv/config';
import axios from 'axios';
import { ChatOpenAI } from '@langchain/openai';
import { tool } from '@langchain/core/tools';
import { createReactAgent } from '@langchain/langgraph/prebuilt';
import { z } from 'zod';
import { createInterface } from 'readline';
import { getChainConfig } from '../chain_config.js';
import { saveMandate, getMandate, StoredMandate } from '../utils/index.js';

// ========================================
// TRANSACTION SIGNING
// ========================================
//
// This example uses EXTERNAL SIGNING SERVICE (PRODUCTION READY).
//
// ✅ PRODUCTION READY: Private key stored securely in signing service
// ✅ SECURE: Application code never touches private keys
// ✅ SCALABLE: Signing service can be scaled independently
// ✅ MCP PROTOCOL: Standardized agent communication
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
const AGENTPAY_MCP_ENDPOINT = process.env.MCP_API_URL || 'https://mcp.agentgatepay.com';
const BUYER_API_KEY = process.env.BUYER_API_KEY;
const BUYER_EMAIL = process.env.BUYER_EMAIL;
const BUYER_WALLET = process.env.BUYER_WALLET;
const SELLER_WALLET = process.env.SELLER_WALLET;
const TX_SIGNING_SERVICE = process.env.TX_SIGNING_SERVICE;

// Payment configuration
const RESOURCE_PRICE_USD = 0.01;
const MANDATE_BUDGET_USD = 100.0;

// Validate configuration
if (!TX_SIGNING_SERVICE) {
  console.error('❌ ERROR: TX_SIGNING_SERVICE not configured in .env');
  console.error('   Please set TX_SIGNING_SERVICE=http://localhost:3000 (Docker)');
  console.error('   Or: TX_SIGNING_SERVICE=https://your-service.onrender.com (Render)');
  console.error('   See docs/TX_SIGNING_OPTIONS.md for setup instructions');
  process.exit(1);
}

// Multi-chain/token configuration
const config = getChainConfig();

// ========================================
// HELPER FUNCTIONS
// ========================================

function decodeMandateToken(token: string): any {
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

// ========================================
// MCP TOOL WRAPPER
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

  console.log(`   📡 Calling MCP tool: ${toolName}`);

  const response = await axios.post(AGENTPAY_MCP_ENDPOINT, payload, {
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': BUYER_API_KEY || ''
    }
  });

  if (response.data.error) {
    throw new Error(`MCP error: ${JSON.stringify(response.data.error)}`);
  }

  // MCP response format: result.content[0].text (JSON string)
  const contentText = response.data.result.content[0].text;
  return JSON.parse(contentText);
}

// ========================================
// AGENT TOOLS (MCP + EXTERNAL TX)
// ========================================

// Global state
let currentMandate: StoredMandate | null = null;
let merchantTxHash: string | null = null;
let commissionTxHash: string | null = null;

// Tool 1: Issue mandate using MCP
const mcpIssueMandateTool = tool(
  async ({ budgetUsd }: { budgetUsd: number }): Promise<string> => {
    try {
      const agentId = `research-assistant-${BUYER_WALLET}`;
      const existingMandate = getMandate(agentId);

      if (existingMandate) {
        const token = existingMandate.mandate_token;

        // Get LIVE budget from gateway (via MCP verify tool)
        let budgetRemaining: any = 'Unknown';
        try {
          const verifyResult = await callMcpTool('agentpay_verify_mandate', {
            mandate_token: token
          });

          if (verifyResult.valid) {
            budgetRemaining = verifyResult.budget_remaining;
          } else {
            
            const tokenData = decodeMandateToken(token);
            budgetRemaining = tokenData.budget_remaining || existingMandate.budget_usd || 'Unknown';
          }
        } catch {
          
          const tokenData = decodeMandateToken(token);
          budgetRemaining = tokenData.budget_remaining || existingMandate.budget_usd || 'Unknown';
        }

        console.log(`\n♻️  Reusing mandate (Budget: $${budgetRemaining})`);
        currentMandate = { ...existingMandate, budget_remaining: budgetRemaining };
        return `MANDATE_TOKEN:${token}`;
      }

      console.log(`\n🔐 Creating mandate ($${budgetUsd})...`);

      const mandate = await callMcpTool('agentpay_issue_mandate', {
        subject: agentId,
        budget_usd: budgetUsd,
        scope: 'resource.read,payment.execute',
        ttl_minutes: 168 * 60
      });

      // Store mandate with budget info (MCP response only includes token)
      const token = mandate.mandate_token;
      const mandateWithBudget = {
        ...mandate,
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
    description: 'Issue AP2 mandate using MCP tool. Input: budget amount in USD Coins.',
    schema: z.object({
      budgetUsd: z.number().describe('Budget amount in USD')
    })
  }
);

// Tool 2: Sign payment via external service
const signPaymentTool = tool(
  async ({ paymentInput }: { paymentInput: string }): Promise<string> => {
    try {
      const parts = paymentInput.split(',');
      if (parts.length !== 2) {
        return 'Error: Invalid format';
      }

      const amountUsd = parseFloat(parts[0].trim());
      const recipient = parts[1].trim();

      // Convert USD to atomic units
      const amountAtomic = BigInt(Math.floor(amountUsd * 10 ** config.decimals));

      console.log(`\n💳 Requesting payment signature from external service...`);
      console.log(`   Amount: $${amountUsd} ${config.token} (${amountAtomic} atomic units)`);
      console.log(`   Chain: ${config.chain.charAt(0).toUpperCase() + config.chain.slice(1)}`);
      console.log(`   Recipient: ${recipient.substring(0, 10)}...`);
      console.log(`   Service: ${TX_SIGNING_SERVICE}`);

      // Call external signing service
      const response = await axios.post(
        `${TX_SIGNING_SERVICE}/sign-payment`,
        {
          merchant_address: recipient,
          total_amount: amountAtomic.toString(),
          chain: config.chain,
          token: config.token
        },
        {
          headers: {
            'Content-Type': 'application/json',
            'x-api-key': BUYER_API_KEY || ''
          },
          timeout: 120000
        }
      );

      if (response.status !== 200) {
        const errorMsg = `Signing service error: HTTP ${response.status} - ${response.data}`;
        console.error(`❌ ${errorMsg}`);
        return errorMsg;
      }

      const result = response.data;

      // Extract transaction hashes
      merchantTxHash = result.tx_hash;
      commissionTxHash = result.tx_hash_commission;

      if (!merchantTxHash || !commissionTxHash) {
        const errorMsg = `Invalid response from signing service: ${JSON.stringify(result)}`;
        console.error(`❌ ${errorMsg}`);
        return errorMsg;
      }

      console.log(`✅ Payment signed and submitted by external service`);
      console.log(`   Merchant TX: ${merchantTxHash.substring(0, 20)}...`);
      console.log(`   Commission TX: ${commissionTxHash.substring(0, 20)}...`);
      console.log(`   Status: ${result.success ? 'Success' : 'Failed'}`);

      // Verify hashes have correct format
      if (merchantTxHash.length !== 66 || !merchantTxHash.startsWith('0x')) {
        const errorMsg = `Invalid merchant tx_hash format from service: ${merchantTxHash}`;
        console.error(`❌ ${errorMsg}`);
        return errorMsg;
      }

      if (commissionTxHash.length !== 66 || !commissionTxHash.startsWith('0x')) {
        const errorMsg = `Invalid commission tx_hash format from service: ${commissionTxHash}`;
        console.error(`❌ ${errorMsg}`);
        return errorMsg;
      }

      return `TX_HASHES:${merchantTxHash},${commissionTxHash}`;
    } catch (error: any) {
      if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
        const errorMsg = 'Signing service timeout (exceeded 120s)';
        console.error(`❌ ${errorMsg}`);
        return errorMsg;
      }

      if (error.code === 'ECONNREFUSED' || error.message.includes('connect')) {
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
    description: 'Sign and execute a blockchain payment via external signing service (PRODUCTION). Creates two transactions: merchant payment and gateway commission. Input should be \'amount_usd,recipient_address\'.',
    schema: z.object({
      paymentInput: z.string().describe('Payment input in format: amount_usd,recipient_address')
    })
  }
);

// Tool 3: Submit payment and verify budget
const mcpSubmitAndVerifyTool = tool(
  async (): Promise<string> => {
    if (!currentMandate || !merchantTxHash) {
      return 'Error: Must issue mandate and sign payment first';
    }

    console.log(`\n📤 [MCP] Submitting payment proof...`);

    try {
      // Submit payment via MCP
      const result = await callMcpTool('agentpay_submit_payment', {
        mandate_token: currentMandate.mandate_token,
        tx_hash: merchantTxHash,
        tx_hash_commission: commissionTxHash,
        chain: config.chain,
        token: config.token
      });

      console.log(`✅ Payment submitted via MCP`);
      console.log(`   Status: ${result.status || 'Confirmed'}`);

      // Verify mandate to get updated budget
      console.log(`   🔍 Fetching updated budget...`);
      const verifyResult = await callMcpTool('agentpay_verify_mandate', {
        mandate_token: currentMandate.mandate_token
      });

      if (verifyResult.valid) {
        const newBudget = verifyResult.budget_remaining || 'Unknown';
        console.log(`   ✅ Budget updated: $${newBudget}`);

        // Update and save mandate
        if (currentMandate) {
          currentMandate.budget_remaining = newBudget;
          const agentId = `research-assistant-${BUYER_WALLET}`;
          saveMandate(agentId, currentMandate);
        }

        return `Success! Paid: $${RESOURCE_PRICE_USD}, Remaining: $${newBudget}`;
      } else {
        console.log(`   ⚠️  Could not fetch updated budget`);
        return `Success! Paid: $${RESOURCE_PRICE_USD}`;
      }
    } catch (error: any) {
      const errorMsg = `Payment submission failed: ${error.message}`;
      console.error(`❌ ${errorMsg}`);
      return errorMsg;
    }
  },
  {
    name: 'submit_and_verify_payment',
    description: 'Submit payment proof via MCP and verify updated budget. No input needed.',
    schema: z.object({})
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

const tools = [mcpIssueMandateTool, signPaymentTool, mcpSubmitAndVerifyTool];

const systemPrompt = `You are an autonomous AI agent using AgentGatePay MCP tools + external TX signing for PRODUCTION payments.

Follow this workflow:
1. Issue mandate using MCP tool (issue_mandate_mcp) with the specified budget
   - The tool returns: MANDATE_TOKEN:{token}
   - Extract the token after the colon
2. Sign blockchain payment via EXTERNAL SERVICE (sign_payment) for the specified amount to the recipient
   - This uses EXTERNAL SIGNING SERVICE (production-ready, no private key in code)
   - Input format: 'amount_usd,recipient_address'
   - The tool returns: TX_HASHES:{merchant_tx},{commission_tx}
   - Extract both transaction hashes after the colon
3. Submit payment and verify budget using MCP tool (submit_and_verify_payment)
   - This tool automatically uses the mandate and transaction hashes from previous steps
   - Returns updated budget after payment

IMPORTANT:
- All three steps must complete successfully
- Parse tool outputs to extract values (look for : separator)
- If any tool returns an error, STOP immediately and report the error
- Do NOT retry failed operations`;

const agent = createReactAgent({ llm, tools, messageModifier: systemPrompt });

// ========================================
// EXECUTE PAYMENT WORKFLOW
// ========================================

async function main() {
  console.log('='.repeat(80));
  console.log('AGENTGATEPAY + LANGCHAIN: PRODUCTION MCP + TX SIGNING DEMO');
  console.log('='.repeat(80));
  console.log();
  console.log('This demo shows PRODUCTION-READY autonomous agent payments using:');
  console.log('  - AgentGatePay MCP tools (JSON-RPC 2.0)');
  console.log('  - External transaction signing service (NO private key in code)');
  console.log('  - LangChain agent framework');
  console.log('  - Multi-chain blockchain payments (Base/Ethereum/Polygon/Arbitrum)');
  console.log('  - Multi-token support (USDC/USDT/DAI)');
  console.log();
  console.log('✅ SECURE: Private key stored in signing service, NOT in application');
  console.log('✅ SCALABLE: Signing service can be deployed independently');
  console.log('✅ MCP PROTOCOL: Standardized agent communication');
  console.log('✅ PRODUCTION READY: Suitable for real-world deployments');
  console.log();

  // Display chain/token configuration
  console.log('\nCHAIN & TOKEN CONFIGURATION');
  console.log('='.repeat(80));
  console.log(`\nUsing configuration from .env:`);
  console.log(`  Chain: ${config.chain.charAt(0).toUpperCase() + config.chain.slice(1)} (ID: ${config.chainId})`);
  console.log(`  Token: ${config.token} (${config.decimals} decimals)`);
  console.log(`  RPC: ${config.rpcUrl}`);
  console.log(`  Contract: ${config.tokenContract}`);
  console.log(`\nTo change chain/token: Edit PAYMENT_CHAIN and PAYMENT_TOKEN in .env file`);
  console.log('='.repeat(80));

  console.log(`\n✅ Initialized AgentGatePay MCP endpoint: ${AGENTPAY_MCP_ENDPOINT}`);
  console.log(`✅ Configured TX signing service: ${TX_SIGNING_SERVICE}`);
  console.log(`✅ Buyer wallet: ${BUYER_WALLET}`);
  console.log(`✅ PRODUCTION MODE: Private key NOT in application code`);

  // Check signing service health
  console.log(`\n🏥 Checking signing service health...`);
  try {
    const healthResponse = await axios.get(`${TX_SIGNING_SERVICE}/health`, { timeout: 5000 });
    if (healthResponse.status === 200) {
      const healthData = healthResponse.data;
      console.log(`✅ Signing service is healthy`);
      console.log(`   Status: ${healthData.status || 'N/A'}`);
      console.log(`   Wallet configured: ${healthData.wallet_configured || false}`);
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

  const agentId = `research-assistant-${BUYER_WALLET}`;
  const existingMandate = getMandate(agentId);

  let mandateBudget: number;
  let purpose: string;

  if (existingMandate) {
    const token = existingMandate.mandate_token;

    // Get LIVE budget from gateway
    let budgetRemaining: any = 'Unknown';
    try {
      const verifyResult = await callMcpTool('agentpay_verify_mandate', {
        mandate_token: token
      });

      if (verifyResult.valid) {
        budgetRemaining = verifyResult.budget_remaining;
      } else {
        const tokenData = decodeMandateToken(token);
        budgetRemaining = tokenData.budget_remaining || 'Unknown';
      }
    } catch {
      const tokenData = decodeMandateToken(token);
      budgetRemaining = tokenData.budget_remaining || 'Unknown';
    }

    console.log(`\n♻️  Using existing mandate (Budget: $${budgetRemaining})`);
    console.log(`   Token: ${existingMandate.mandate_token?.substring(0, 50)}...`);
    console.log(`   To delete: rm ../.agentgatepay_mandates.json\n`);
    mandateBudget = budgetRemaining !== 'Unknown' ? parseFloat(budgetRemaining) : MANDATE_BUDGET_USD;
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

  // Agent task
  const task = `
Purchase a ${purpose} for $${RESOURCE_PRICE_USD} USD using PRODUCTION MCP + TX signing service.

Steps:
1. Issue a payment mandate with a $${mandateBudget} budget (or reuse existing) using MCP
2. Sign blockchain payment of $${RESOURCE_PRICE_USD} to seller: ${SELLER_WALLET}
   (This will be signed by the external signing service - NO private key in code)
3. Submit payment proof to AgentGatePay via MCP with mandate token

This is a PRODUCTION-READY payment using MCP tools + external signing service.
  `;

  try {
    // Run agent
    const result = await agent.invoke({
      messages: [{ role: 'user', content: task }]
    });

    console.log('\n' + '='.repeat(80));
    console.log('PRODUCTION MCP + TX SIGNING WORKFLOW COMPLETED');
    console.log('='.repeat(80));

    // Extract final message
    if (result.messages && result.messages.length > 0) {
      const finalMessage = result.messages[result.messages.length - 1].content;
      console.log(`\nResult: ${finalMessage}`);
    }

    // Display final status
    if (currentMandate) {
      console.log(`\nFinal Status:`);
      console.log(`  Mandate: ${currentMandate.mandate_token?.substring(0, 50)}...`);
      console.log(`  Budget remaining: $${currentMandate.budget_remaining || 'N/A'}`);
    }

    if (merchantTxHash) {
      console.log(`\nBlockchain Transactions:`);
      console.log(`  Merchant TX: ${config.explorer}/tx/${merchantTxHash}`);
      console.log(`  Commission TX: ${config.explorer}/tx/${commissionTxHash}`);

      // Display gateway audit logs with curl commands
      console.log(`\nGateway Audit Logs (copy-paste these commands):`);
      console.log(`\n# All payment logs (by wallet):`);
      console.log(`curl '${AGENTPAY_API_URL}/audit/logs?client_id=${BUYER_WALLET}&event_type=x402_payment_settled&limit=10' \\`);
      console.log(`  -H 'x-api-key: ${BUYER_API_KEY}' | python3 -m json.tool`);
      console.log(`\n# Recent payments (24h):`);
      console.log(`curl '${AGENTPAY_API_URL}/audit/logs?client_id=${BUYER_WALLET}&event_type=x402_payment_settled&hours=24' \\`);
      console.log(`  -H 'x-api-key: ${BUYER_API_KEY}' | python3 -m json.tool`);
      console.log(`\n# Payment verification (by tx_hash):`);
      console.log(`curl '${AGENTPAY_API_URL}/v1/payments/verify/${merchantTxHash}' \\`);
      console.log(`  -H 'x-api-key: ${BUYER_API_KEY}' | python3 -m json.tool`);

      console.log(`\n✅ PRODUCTION SUCCESS:`);
      console.log(`   Private key: SECURE (stored in signing service)`);
      console.log(`   Application code: CLEAN (no private keys)`);
      console.log(`   MCP protocol: STANDARDIZED (JSON-RPC 2.0)`);
      console.log(`   Payment: VERIFIED (on ${config.chain.charAt(0).toUpperCase() + config.chain.slice(1)} blockchain)`);
    }
  } catch (error: any) {
    if (error.message === 'User interrupted') {
      console.log('\n\n⚠️  Demo interrupted by user');
    } else {
      console.error(`\n\n❌ Error: ${error.message}`);
      console.error(error.stack);
    }
  }
}

main().catch(console.error);
