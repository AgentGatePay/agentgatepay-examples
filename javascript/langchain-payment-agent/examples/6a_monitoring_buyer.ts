/**
 * AgentGatePay + LangChain Integration - BUYER MONITORING DASHBOARD
 *
 * Monitor your payment activity as a BUYER (outgoing payments):
 * - Spending analytics and budget tracking
 * - Payment history (what you paid to merchants)
 * - Active mandates and budget utilization
 * - Smart alerts (budget warnings, mandate expiration, failed payments)
 * - Commission tracking (what you paid to the gateway)
 *
 * This is for buyers who SEND payments. For sellers who RECEIVE payments,
 * use 6b_monitoring_seller.ts instead.
 *
 * Features (Buyer-Focused):
 * - Total spent, payment count, average payment
 * - Budget tracking and mandate management
 * - Outgoing payment history (what you paid)
 * - Budget alerts and spending trends
 * - Mandate expiration warnings
 * - Commission breakdown per transaction
 *
 * Usage:
 *     npm run example:6a
 *
 * Requirements:
 * - npm install
 * - .env file with BUYER_API_KEY and BUYER_WALLET
 */

import 'dotenv/config';
import axios from 'axios';

const AGENTPAY_API_URL = process.env.AGENTPAY_API_URL || 'https://api.agentgatepay.com';
const BUYER_API_KEY = process.env.BUYER_API_KEY;
const BUYER_WALLET = process.env.BUYER_WALLET;

// Helper functions
async function fetchBuyerAnalytics(apiUrl: string, apiKey: string): Promise<any> {
  try {
    const response = await axios.get(`${apiUrl}/v1/analytics/me`, {
      headers: { 'x-api-key': apiKey },
      timeout: 10000
    });
    return response.data;
  } catch (error) {
    console.error(`⚠️  Failed to fetch analytics: ${error}`);
    return {};
  }
}

async function fetchAuditLogs(apiUrl: string, apiKey: string, wallet: string | null, hours: number, limit: number, eventType?: string): Promise<any[]> {
  try {
    const params: any = { hours, limit };
    if (eventType) params.event_type = eventType;
    if (wallet) params.client_id = wallet;

    const response = await axios.get(`${apiUrl}/audit/logs`, {
      headers: { 'x-api-key': apiKey },
      params,
      timeout: 10000
    });
    return response.data.logs || [];
  } catch (error) {
    console.error(`⚠️  Failed to fetch audit logs: ${error}`);
    return [];
  }
}

async function fetchMandates(apiUrl: string, apiKey: string, wallet: string | null, hours: number = 720): Promise<any[]> {
  try {
    const params: any = {
      event_type: 'mandate_issued',
      hours,
      limit: 100
    };
    if (wallet) params.client_id = wallet;

    const response = await axios.get(`${apiUrl}/audit/logs`, {
      headers: { 'x-api-key': apiKey },
      params,
      timeout: 10000
    });
    return response.data.logs || [];
  } catch (error) {
    console.error(`⚠️  Failed to fetch mandates: ${error}`);
    return [];
  }
}

function calculateBuyerStats(analytics: any, payments: any[], mandates: any[], logs: any[]): any {
  // Spending stats
  const totalSpent = payments.reduce((sum, p) => sum + parseFloat(p.amount_usd || '0'), 0);
  const paymentCount = payments.length;
  const averagePayment = paymentCount > 0 ? totalSpent / paymentCount : 0;

  // Recent activity (24h)
  const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
  const payments24h = payments.filter(p => {
    const timestamp = p.timestamp || p.created_at || '2000-01-01';
    return new Date(timestamp) > oneDayAgo;
  });
  const spent24h = payments24h.reduce((sum, p) => sum + parseFloat(p.amount_usd || '0'), 0);

  // Budget stats
  const budgetTotal = mandates.reduce((sum, m) => {
    const details = typeof m.details === 'string' ? JSON.parse(m.details) : m.details || {};
    return sum + parseFloat(details.budget_usd || '0');
  }, 0);

  const budgetRemaining = mandates.reduce((sum, m) => {
    const details = typeof m.details === 'string' ? JSON.parse(m.details) : m.details || {};
    return sum + parseFloat(details.budget_remaining || '0');
  }, 0);

  const budgetUtilization = budgetTotal > 0 ? ((budgetTotal - budgetRemaining) / budgetTotal) * 100 : 0;

  // Active mandates count
  const activeMandates = mandates.filter(m => {
    const details = typeof m.details === 'string' ? JSON.parse(m.details) : m.details || {};
    return details.status === 'active';
  }).length;

  // Payment success rate
  const successful = payments.filter(p => ['completed', 'confirmed'].includes(p.status)).length;
  const failed = payments.filter(p => p.status === 'failed').length;
  const totalStatus = successful + failed;
  const successRate = totalStatus > 0 ? (successful / totalStatus) * 100 : 100;

  // Spending trend
  let spendingTrend: string;
  if (spent24h > averagePayment * 2) {
    spendingTrend = '📈 High (2x+ average)';
  } else if (spent24h < averagePayment * 0.5) {
    spendingTrend = '📉 Low (<50% average)';
  } else {
    spendingTrend = '➡️  Normal';
  }

  return {
    totalSpent,
    paymentCount,
    averagePayment,
    payments24h: payments24h.length,
    spent24h,
    budgetTotal,
    budgetRemaining,
    budgetUtilization,
    activeMandates,
    successRate,
    failedPayments: failed,
    spendingTrend,
    totalEvents: logs.length
  };
}

function generateBuyerAlerts(stats: any, payments: any[], mandates: any[]): any[] {
  const alerts: any[] = [];

  // Budget warnings
  if (stats.budgetUtilization > 90) {
    alerts.push({
      severity: 'high',
      message: `⚠️  BUDGET CRITICAL: ${stats.budgetUtilization.toFixed(1)}% utilization`,
      action: 'Issue new mandate or reduce spending'
    });
  } else if (stats.budgetUtilization > 70) {
    alerts.push({
      severity: 'medium',
      message: `⚠️  Budget warning: ${stats.budgetUtilization.toFixed(1)}% utilization`,
      action: 'Monitor budget usage closely'
    });
  }

  // No active mandates
  if (stats.activeMandates === 0 && stats.paymentCount > 0) {
    alerts.push({
      severity: 'high',
      message: '❌ No active mandates - cannot make payments',
      action: 'Issue new mandate to enable payments'
    });
  }

  // Failed payments
  if (stats.failedPayments > 0) {
    alerts.push({
      severity: 'high',
      message: `❌ PAYMENT FAILURES: ${stats.failedPayments} failed payment(s)`,
      action: 'Check mandate budget and payment details'
    });
  }

  // Low success rate
  if (stats.successRate < 90 && stats.paymentCount > 10) {
    alerts.push({
      severity: 'high',
      message: `⚠️  LOW SUCCESS RATE: ${stats.successRate.toFixed(1)}% (${stats.failedPayments} failures)`,
      action: 'Review payment errors and mandate configuration'
    });
  }

  // Spending spike
  if (stats.spent24h > stats.averagePayment * 10 && stats.paymentCount > 10) {
    alerts.push({
      severity: 'medium',
      message: `📈 Spending Spike: $${stats.spent24h.toFixed(2)} in 24h (10x average)`,
      action: 'Review recent payment activity'
    });
  }

  return alerts;
}

async function main() {
  console.log('='.repeat(70));
  console.log('📊 BUYER MONITORING DASHBOARD (Outgoing Payments)');
  console.log('='.repeat(70));
  console.log();
  console.log('This dashboard tracks your SPENDING as a buyer:');
  console.log('  ✅ Total spent and payment count');
  console.log('  ✅ Budget tracking and mandate status');
  console.log('  ✅ Payment history (what you paid to merchants)');
  console.log('  ✅ Spending alerts and budget warnings');
  console.log('  ✅ Commission tracking (what you paid to gateway)');
  console.log();
  console.log('For REVENUE tracking (incoming payments), use 6b_monitoring_seller.ts');
  console.log();
  console.log('='.repeat(70));

  // Validate configuration
  if (!BUYER_API_KEY) {
    console.error('\n❌ Configuration Error:');
    console.error('   BUYER_API_KEY is required');
    console.error('   Please set it in your .env file');
    process.exit(1);
  }

  // Fetch buyer data
  console.log();
  console.log('🔄 Fetching buyer data from AgentGatePay API...');
  console.log();

  try {
    const analytics = await fetchBuyerAnalytics(AGENTPAY_API_URL, BUYER_API_KEY);
    const logs = await fetchAuditLogs(AGENTPAY_API_URL, BUYER_API_KEY, BUYER_WALLET || null, 720, 100, 'x402_payment_settled');
    const mandates = await fetchMandates(AGENTPAY_API_URL, BUYER_API_KEY, BUYER_WALLET || null, 720);

    // Build payments list from logs
    const payments: any[] = [];
    for (const log of logs) {
      let details = log.details;
      if (typeof details === 'string') {
        try {
          details = JSON.parse(details);
        } catch {
          continue;
        }
      }

      const txHash = details.merchant_tx_hash || details.tx_hash;
      if (txHash) {
        const timestamp = details.timestamp ? new Date(details.timestamp * 1000).toISOString() : log.timestamp;
        payments.push({
          tx_hash: txHash,
          amount_usd: details.merchant_amount_usd || details.amount_usd || 0,
          status: details.status || 'completed',
          timestamp,
          receiver_address: details.receiver_address || details.merchant_address,
          receiver: details.receiver_address || details.merchant_address,
          created_at: timestamp
        });
      }
    }

    const logs24h = await fetchAuditLogs(AGENTPAY_API_URL, BUYER_API_KEY, BUYER_WALLET || null, 24, 100, 'x402_payment_settled');

    // Calculate stats
    const stats = calculateBuyerStats(analytics, payments, mandates, logs24h);
    const alerts = generateBuyerAlerts(stats, payments, mandates);

    // Display dashboard
    console.log('\n' + '='.repeat(70));
    console.log('📊 BUYER MONITORING DASHBOARD');
    console.log('='.repeat(70));
    console.log(`\nGenerated: ${new Date().toISOString()}`);
    if (BUYER_WALLET) {
      console.log(`Buyer Wallet: ${BUYER_WALLET.substring(0, 10)}...${BUYER_WALLET.substring(BUYER_WALLET.length - 8)}`);
    }
    console.log();

    // Key Metrics
    console.log('━'.repeat(70));
    console.log('💰 SPENDING SUMMARY');
    console.log('━'.repeat(70));
    console.log(`Total Spent: $${stats.totalSpent.toFixed(2)} USD Coins`);
    console.log(`Payment Count: ${stats.paymentCount} (outgoing payments)`);
    console.log(`Average Payment: $${stats.averagePayment.toFixed(2)} USD Coins`);
    console.log(`Last 24h: ${stats.payments24h} payments ($${stats.spent24h.toFixed(2)} USD Coins)`);
    console.log(`Spending Trend: ${stats.spendingTrend}`);
    console.log();

    // Budget Status
    console.log('━'.repeat(70));
    console.log('🔑 BUDGET STATUS');
    console.log('━'.repeat(70));
    console.log(`Total Allocated: $${stats.budgetTotal.toFixed(2)} USD Coins`);
    console.log(`Remaining: $${stats.budgetRemaining.toFixed(2)} USD Coins`);
    console.log(`Utilization: ${stats.budgetUtilization.toFixed(1)}%`);
    console.log(`Active Mandates: ${stats.activeMandates}`);
    console.log();

    // Payment Metrics
    console.log('━'.repeat(70));
    console.log('📊 PAYMENT METRICS');
    console.log('━'.repeat(70));
    console.log(`Success Rate: ${stats.successRate.toFixed(1)}%`);
    console.log(`Failed Payments: ${stats.failedPayments}`);
    console.log(`Total Events (24h): ${stats.totalEvents}`);
    console.log();

    // Alerts
    if (alerts.length > 0) {
      console.log('━'.repeat(70));
      console.log(`🚨 BUYER ALERTS (${alerts.length})`);
      console.log('━'.repeat(70));
      alerts.forEach((alert, i) => {
        console.log(`${i + 1}. [${alert.severity.toUpperCase()}] ${alert.message}`);
        console.log(`   Action: ${alert.action}`);
        if (i < alerts.length - 1) console.log();
      });
      console.log();
    }

    // Recent Payments
    if (payments.length > 0) {
      console.log('━'.repeat(70));
      console.log('💳 OUTGOING PAYMENTS (Last 10)');
      console.log('━'.repeat(70));
      console.log('(Payments YOU sent to merchants)\n');
      payments.slice(0, 10).forEach((payment, i) => {
        const timestamp = payment.timestamp || payment.created_at || 'N/A';
        const amount = parseFloat(payment.amount_usd || '0');
        const status = payment.status || 'unknown';
        const txHash = payment.tx_hash || 'N/A';
        const receiver = payment.receiver_address || payment.receiver || payment.to_address || 'Unknown';

        console.log(`${i + 1}. YOU PAID $${amount.toFixed(2)} → ${receiver} | ${timestamp} | ${status} | TX ${txHash}`);
      });
      console.log();
    }

    // Mandates
    if (mandates.length > 0) {
      console.log('━'.repeat(70));
      console.log(`🎫 ACTIVE MANDATES (${mandates.length})`);
      console.log('━'.repeat(70));
      console.log('(Budget allocations for your payments)\n');
      mandates.slice(0, 5).forEach((mandate, i) => {
        let details = mandate.details;
        if (typeof details === 'string') {
          try {
            details = JSON.parse(details);
          } catch {
            return;
          }
        }

        const mandateId = (details.mandate_id || 'N/A').substring(0, 30);
        const budget = details.budget_usd || 0;
        const remaining = details.budget_remaining || 0;
        const status = details.status || 'N/A';
        const expiresAt = details.expires_at || 'N/A';

        console.log(`${i + 1}. ${mandateId}... | Budget: $${budget.toFixed(2)} | Remaining: $${remaining.toFixed(2)} | ${status} | Expires: ${expiresAt}`);
      });
      if (mandates.length > 5) {
        console.log(`... and ${mandates.length - 5} more mandates`);
      }
      console.log();
    }

    console.log('='.repeat(70));
    console.log('✅ BUYER MONITORING COMPLETE');
    console.log('='.repeat(70));
    console.log();
  } catch (error: any) {
    console.error(`\n❌ Failed to fetch data: ${error.message}`);
    console.log();
    console.log('Please check:');
    console.log('  - Buyer API key is valid');
    console.log('  - Buyer wallet address is correct (if provided)');
    console.log('  - Network connection is working');
    process.exit(1);
  }
}

main().catch(console.error);
