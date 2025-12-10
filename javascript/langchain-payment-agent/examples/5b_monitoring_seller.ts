/**
 * AgentGatePay + LangChain Integration - SELLER MONITORING DASHBOARD
 *
 * Monitor your revenue as a SELLER (incoming payments):
 * - Revenue analytics and payment tracking
 * - Incoming payments from buyers
 * - Webhook delivery status
 * - Top buyers analysis
 * - Smart alerts (payment failures, webhook issues)
 *
 * This is for sellers who RECEIVE payments. For buyers who SEND payments,
 * use 6a_monitoring_buyer.ts instead.
 *
 * Features (Seller-Focused):
 * - Total revenue, payment count, average payment
 * - Revenue trends and growth analysis
 * - Incoming payment history (what you received)
 * - Webhook configuration and delivery tracking
 * - Top buyers ranking
 * - Payment success rate monitoring
 *
 * Usage:
 *     npm run example:6b
 *
 * Requirements:
 * - npm install
 * - .env file with SELLER_API_KEY and SELLER_WALLET
 */

import 'dotenv/config';
import axios from 'axios';

const AGENTPAY_API_URL = process.env.AGENTPAY_API_URL || 'https://api.agentgatepay.com';
const SELLER_API_KEY = process.env.SELLER_API_KEY;
const SELLER_WALLET = process.env.SELLER_WALLET;

// Helper functions
async function fetchMerchantRevenue(apiUrl: string, apiKey: string, wallet: string): Promise<any> {
  try {
    const response = await axios.get(`${apiUrl}/v1/merchant/revenue`, {
      headers: { 'x-api-key': apiKey },
      params: { wallet },
      timeout: 10000
    });
    return response.data;
  } catch (error) {
    console.error(`⚠️  Failed to fetch revenue: ${error}`);
    return {};
  }
}

async function fetchPaymentList(apiUrl: string, apiKey: string, wallet: string, limit: number = 50): Promise<any[]> {
  try {
    const response = await axios.get(`${apiUrl}/v1/payments/list`, {
      headers: { 'x-api-key': apiKey },
      params: { wallet, limit },
      timeout: 10000
    });
    return response.data.payments || [];
  } catch (error) {
    console.error(`⚠️  Failed to fetch payments: ${error}`);
    return [];
  }
}

async function fetchWebhooks(apiUrl: string, apiKey: string): Promise<any[]> {
  try {
    const response = await axios.get(`${apiUrl}/v1/webhooks/list`, {
      headers: { 'x-api-key': apiKey },
      timeout: 10000
    });
    return response.data.webhooks || [];
  } catch (error) {
    console.error(`⚠️  Failed to fetch webhooks: ${error}`);
    return [];
  }
}

async function fetchAuditLogs(apiUrl: string, apiKey: string, hours: number = 24, limit: number = 50): Promise<any[]> {
  try {
    const response = await axios.get(`${apiUrl}/audit/logs`, {
      headers: { 'x-api-key': apiKey },
      params: {
        event_type: 'x402_payment_settled',
        hours,
        limit
      },
      timeout: 10000
    });
    return response.data.logs || [];
  } catch (error) {
    console.error(`⚠️  Failed to fetch audit logs: ${error}`);
    return [];
  }
}

function calculateSellerStats(revenue: any, payments: any[], webhooks: any[], logs: any[]): any {
  const totalRevenue = revenue.total_usd || 0;
  const paymentCount = revenue.count || 0;
  const averagePayment = paymentCount > 0 ? revenue.average_usd || 0 : 0;
  const revenueThisMonth = revenue.revenue_this_month || 0;

  // Recent activity (24h)
  const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
  const payments24h = payments.filter(p => {
    const timestamp = p.timestamp || p.created_at || '2000-01-01';
    return new Date(timestamp) > oneDayAgo;
  });
  const revenue24h = payments24h.reduce((sum, p) => sum + parseFloat(p.amount_usd || '0'), 0);

  // Webhook stats
  const totalWebhooks = webhooks.length;
  const activeWebhooks = webhooks.filter(w => w.active).length;

  // Top buyers
  const topBuyers = (revenue.top_buyers || []).slice(0, 5);

  // Payment success rate
  const successful = payments.filter(p => ['completed', 'confirmed'].includes(p.status)).length;
  const failed = payments.filter(p => p.status === 'failed').length;
  const totalStatus = successful + failed;
  const successRate = totalStatus > 0 ? (successful / totalStatus) * 100 : 100;

  return {
    totalRevenue,
    paymentCount,
    averagePayment,
    revenueThisMonth,
    payments24h: payments24h.length,
    revenue24h,
    totalWebhooks,
    activeWebhooks,
    topBuyers,
    successRate,
    failedPayments: failed,
    totalEvents: logs.length
  };
}

function generateSellerAlerts(stats: any, payments: any[], webhooks: any[]): any[] {
  const alerts: any[] = [];

  // Webhook failures
  if (stats.totalWebhooks > 0 && stats.activeWebhooks === 0) {
    alerts.push({
      severity: 'high',
      message: `⚠️  All webhooks inactive (${stats.totalWebhooks} total)`,
      action: 'Check webhook configuration and test delivery'
    });
  }

  // No payments in 24h
  if (stats.payments24h === 0 && stats.totalEvents === 0 && stats.paymentCount > 0) {
    alerts.push({
      severity: 'medium',
      message: '⏰ No payments received in last 24 hours',
      action: 'Review - may be normal or check if service is accessible'
    });
  }

  // Failed payments
  if (stats.failedPayments > 0) {
    alerts.push({
      severity: 'high',
      message: `❌ PAYMENT FAILURES: ${stats.failedPayments} failed payment(s)`,
      action: 'Review failed transactions and notify buyers'
    });
  }

  // Low success rate
  if (stats.successRate < 90 && stats.paymentCount > 10) {
    alerts.push({
      severity: 'high',
      message: `⚠️  LOW SUCCESS RATE: ${stats.successRate.toFixed(1)}% (${stats.failedPayments} failures)`,
      action: 'Investigate common failure causes'
    });
  }

  // No webhooks configured
  if (stats.totalWebhooks === 0 && stats.paymentCount > 5) {
    alerts.push({
      severity: 'medium',
      message: 'ℹ️  No webhooks configured - missing payment notifications',
      action: 'Configure webhook to receive real-time payment alerts'
    });
  }

  // Revenue spike
  if (stats.revenue24h > stats.averagePayment * 20 && stats.paymentCount > 10) {
    alerts.push({
      severity: 'low',
      message: `📈 Revenue Spike: $${stats.revenue24h.toFixed(2)} in 24h (20x average)`,
      action: 'High demand detected - ensure service capacity'
    });
  }

  return alerts;
}

async function main() {
  console.log('='.repeat(70));
  console.log('💲 SELLER MONITORING DASHBOARD (Incoming Payments)');
  console.log('='.repeat(70));
  console.log();
  console.log('This dashboard tracks your REVENUE as a seller:');
  console.log('  ✅ Total revenue and payment count');
  console.log('  ✅ Incoming payment history (what buyers paid you)');
  console.log('  ✅ Webhook delivery tracking');
  console.log('  ✅ Top buyers analysis');
  console.log('  ✅ Payment success rate monitoring');
  console.log();
  console.log('For SPENDING tracking (outgoing payments), use 6a_monitoring_buyer.ts');
  console.log();
  console.log('='.repeat(70));

  // Validate configuration
  if (!SELLER_API_KEY || !SELLER_WALLET) {
    console.error('\n❌ Configuration Error:');
    console.error('   SELLER_API_KEY and SELLER_WALLET are required');
    console.error('   Please set them in your .env file');
    process.exit(1);
  }

  // Fetch seller data
  console.log();
  console.log('🔄 Fetching seller data from AgentGatePay API...');
  console.log();

  try {
    const revenue = await fetchMerchantRevenue(AGENTPAY_API_URL, SELLER_API_KEY, SELLER_WALLET);
    const payments = await fetchPaymentList(AGENTPAY_API_URL, SELLER_API_KEY, SELLER_WALLET, 100);
    const webhooks = await fetchWebhooks(AGENTPAY_API_URL, SELLER_API_KEY);
    const logs = await fetchAuditLogs(AGENTPAY_API_URL, SELLER_API_KEY, 24, 100);

    // Calculate stats
    const stats = calculateSellerStats(revenue, payments, webhooks, logs);
    const alerts = generateSellerAlerts(stats, payments, webhooks);

    // Display dashboard
    console.log('\n' + '='.repeat(70));
    console.log('💲 SELLER MONITORING DASHBOARD');
    console.log('='.repeat(70));
    console.log(`\nGenerated: ${new Date().toISOString()}`);
    console.log(`Seller Wallet: ${SELLER_WALLET.substring(0, 10)}...${SELLER_WALLET.substring(SELLER_WALLET.length - 8)}`);
    console.log();

    // Key Metrics
    console.log('━'.repeat(70));
    console.log('💰 REVENUE SUMMARY');
    console.log('━'.repeat(70));
    console.log(`Total Revenue: $${stats.totalRevenue.toFixed(2)} USD Coins`);
    console.log(`Payment Count: ${stats.paymentCount} (incoming payments)`);
    console.log(`Average Payment: $${stats.averagePayment.toFixed(2)} USD Coins`);
    console.log(`This Month: $${stats.revenueThisMonth.toFixed(2)} USD Coins`);
    console.log(`Last 24h: ${stats.payments24h} payments ($${stats.revenue24h.toFixed(2)} USD Coins)`);
    console.log();

    // Webhook Status
    console.log('━'.repeat(70));
    console.log('🔗 WEBHOOK STATUS');
    console.log('━'.repeat(70));
    console.log(`Total Webhooks: ${stats.totalWebhooks}`);
    console.log(`Active Webhooks: ${stats.activeWebhooks}`);
    if (stats.totalWebhooks > 0) {
      console.log(`\nConfigured webhooks:`);
      webhooks.slice(0, 5).forEach((webhook, i) => {
        const url = (webhook.url || 'N/A').substring(0, 50);
        const status = webhook.active ? '✅ Active' : '❌ Inactive';
        console.log(`  ${i + 1}. ${url}... | ${status}`);
      });
    } else {
      console.log('\n⚠️  No webhooks configured');
    }
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
      console.log(`🚨 SELLER ALERTS (${alerts.length})`);
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
      console.log('💳 INCOMING PAYMENTS (Last 10)');
      console.log('━'.repeat(70));
      console.log('(Payments buyers sent to YOU)\n');
      payments.slice(0, 10).forEach((payment, i) => {
        const paidAt = payment.paid_at || 0;
        const timestamp = typeof paidAt === 'string' ? paidAt : (typeof paidAt === 'number' && paidAt > 0 ? new Date(paidAt * 1000).toISOString() : 'N/A');
        const amount = parseFloat(payment.amount_usd || '0');
        const status = payment.status || 'unknown';
        const txHash = payment.tx_hash || 'N/A';
        const buyer = payment.from_address || payment.payer_address || payment.payer || payment.sender_address || payment.client_id || 'Unknown';

        console.log(`${i + 1}. YOU RECEIVED $${amount.toFixed(2)} ← ${buyer} | ${timestamp} | ${status} | TX ${txHash}`);
      });
      console.log();
    }

    // Top Buyers
    if (stats.topBuyers.length > 0) {
      console.log('━'.repeat(70));
      console.log(`👥 TOP BUYERS (${stats.topBuyers.length})`);
      console.log('━'.repeat(70));
      console.log('(Buyers who paid you the most)\n');
      stats.topBuyers.forEach((buyer: any, i: number) => {
        const buyerId = (buyer.buyer_id || 'N/A').substring(0, 20);
        const totalSpent = buyer.total_spent || 0;
        const count = buyer.payment_count || 0;
        console.log(`${i + 1}. ${buyerId}... | $${totalSpent.toFixed(2)} | ${count} payments`);
      });
      console.log();
    }

    // Payment breakdown with commission
    if (logs.length > 0) {
      const merchantPayments: any[] = [];
      const commissionPayments: any[] = [];

      for (const log of logs) {
        let details = log.details;
        if (typeof details === 'string') {
          try {
            details = JSON.parse(details);
          } catch {
            continue;
          }
        }

        // Extract merchant and commission info
        const merchantTx = details.merchant_tx_hash;
        const commissionTx = details.commission_tx_hash;

        // Get amounts - merchant gets amount_usd or merchant_amount_usd
        const merchantAmount = details.merchant_amount_usd || details.amount_usd || 0;
        const commissionAmount = details.commission_amount_usd || details.commission_usd || 0;

        // Convert timestamp
        const timestampUnix = details.timestamp || log.timestamp || 0;
        let timestampReadable: string;
        try {
          if (typeof timestampUnix === 'string') {
            timestampReadable = timestampUnix;
          } else {
            timestampReadable = new Date(parseInt(timestampUnix.toString()) * 1000).toISOString();
          }
        } catch {
          timestampReadable = String(timestampUnix);
        }

        // Extract buyer address
        const buyer = details.payer_address || details.sender_address || details.payer || log.client_id || 'Unknown';

        if (merchantTx) {
          merchantPayments.push({
            tx_hash: merchantTx,
            amount_usd: parseFloat(String(merchantAmount)),
            timestamp: timestampReadable,
            buyer
          });
        }

        if (commissionTx) {
          commissionPayments.push({
            tx_hash: commissionTx,
            amount_usd: parseFloat(String(commissionAmount)),
            timestamp: timestampReadable,
            buyer
          });
        }
      }

      // Display payments received from buyers
      if (merchantPayments.length > 0) {
        console.log('━'.repeat(70));
        console.log(`💰 PAYMENTS RECEIVED FROM BUYERS (Last ${Math.min(20, merchantPayments.length)})`);
        console.log('━'.repeat(70));
        console.log('(Full payment amounts you received from buyers)\n');
        merchantPayments.slice(0, 20).forEach((payment, i) => {
          const txHash = payment.tx_hash;
          const amount = payment.amount_usd || 0;
          const buyer = String(payment.buyer || 'Unknown');
          const timestamp = payment.timestamp || 'N/A';
          console.log(`${i + 1}. YOU RECEIVED $${amount.toFixed(4)} ← ${buyer} | ${timestamp} | TX ${txHash}`);
        });
        console.log();
      }

      // Display commission payments deducted
      if (commissionPayments.length > 0) {
        console.log('━'.repeat(70));
        console.log(`💸 COMMISSION DEDUCTED BY GATEWAY (Last ${Math.min(20, commissionPayments.length)})`);
        console.log('━'.repeat(70));
        console.log('(0.5% gateway commission on each transaction)\n');
        commissionPayments.slice(0, 20).forEach((payment, i) => {
          const txHash = payment.tx_hash;
          const commission = payment.amount_usd || 0;
          const buyer = String(payment.buyer || 'Unknown');
          const timestamp = payment.timestamp || 'N/A';
          console.log(`${i + 1}. $${commission.toFixed(4)} → Gateway (from ${buyer}) | ${timestamp} | TX ${txHash}`);
        });
        console.log();
      }
    }

    // Calculate additional metrics
    console.log('━'.repeat(70));
    console.log('💡 ADDITIONAL METRICS');
    console.log('━'.repeat(70));

    // Calculate unique buyers
    const uniqueBuyers = new Set<string>();
    for (const log of logs) {
      let details = log.details;
      if (typeof details === 'string') {
        try {
          details = JSON.parse(details);
        } catch {
          continue;
        }
      }
      const buyer = details.payer_address || details.sender_address || details.payer || log.client_id;
      if (buyer) {
        uniqueBuyers.add(buyer);
      }
    }

    // Calculate commission total
    const totalCommission = logs.reduce((sum, log) => {
      let details = log.details;
      if (typeof details === 'string') {
        try {
          details = JSON.parse(details);
        } catch {
          return sum;
        }
      }
      return sum + parseFloat(String(details.commission_amount_usd || 0));
    }, 0);

    // Calculate original amounts
    const merchantReceived = stats.totalRevenue;
    const originalAmount = merchantReceived > 0 ? merchantReceived / 0.995 : 0; // Reverse calculate from 99.5%

    console.log(`Unique Buyers: ${uniqueBuyers.size}`);
    console.log(`Original Amount (buyer paid): $${originalAmount.toFixed(2)} USD Coins`);
    console.log(`Merchant Received (99.5%): $${merchantReceived.toFixed(2)} USD Coins`);
    console.log(`Commission Deducted (0.5%): $${totalCommission.toFixed(4)} USD Coins`);
    console.log();

    // MANUAL CURL COMMANDS WITH LIVE OUTPUT
    console.log('━'.repeat(70));
    console.log('📋 CURL COMMANDS & LIVE OUTPUT (Last 10 Results)');
    console.log('━'.repeat(70));
    console.log('\n💡 Each section shows:');
    console.log('   1. Full CURL command (copy/paste to get ALL data)');
    console.log('   2. Live execution results (limited to last 10 for readability)\n');
    console.log('━'.repeat(70));
    console.log();

    // Helper function to hide sensitive gateway information
    function hideGatewayInfo(data: any): any {
      if (typeof data === 'object' && data !== null && !Array.isArray(data)) {
        const result: any = {};
        for (const [key, value] of Object.entries(data)) {
          if (key === 'commission_address') {
            result[key] = '[HIDDEN]';
          } else {
            result[key] = hideGatewayInfo(value);
          }
        }
        return result;
      } else if (Array.isArray(data)) {
        return data.map(item => hideGatewayInfo(item));
      } else {
        return data;
      }
    }

    // 1. Seller revenue analytics
    console.log('1️⃣  SELLER REVENUE ANALYTICS (All Time)\n');
    console.log(`curl '${AGENTPAY_API_URL}/v1/merchant/revenue?wallet=${SELLER_WALLET}' \\`);
    console.log(`  -H 'x-api-key: ${SELLER_API_KEY}'\n`);
    console.log('🔄 Executing...\n');
    try {
      const response = await axios.get(`${AGENTPAY_API_URL}/v1/merchant/revenue`, {
        headers: { 'x-api-key': SELLER_API_KEY || '' },
        params: { wallet: SELLER_WALLET },
        timeout: 10000
      });
      if (response.status === 200) {
        const revData = response.data;
        const cleanData = hideGatewayInfo(revData);
        console.log('✅ Response (JSON):');
        console.log(JSON.stringify(cleanData, null, 2));
      } else {
        console.log(`❌ Failed (HTTP ${response.status})`);
      }
    } catch (error: any) {
      console.log(`❌ Error: ${error.message}`);
    }
    console.log('\n' + '━'.repeat(70) + '\n');

    // 2. ALL payments received
    console.log('2️⃣  ALL PAYMENTS RECEIVED (Showing Last 10)\n');
    console.log(`curl '${AGENTPAY_API_URL}/v1/payments/list?wallet=${SELLER_WALLET}' \\`);
    console.log(`  -H 'x-api-key: ${SELLER_API_KEY}'\n`);
    console.log('🔄 Executing...\n');
    try {
      const response = await axios.get(`${AGENTPAY_API_URL}/v1/payments/list`, {
        headers: { 'x-api-key': SELLER_API_KEY || '' },
        params: { wallet: SELLER_WALLET },
        timeout: 10000
      });
      if (response.status === 200) {
        const payData = response.data;
        const payList = (payData.payments || []).slice(0, 10);
        const result = { payments: payList, count: (payData.payments || []).length, showing: payList.length };
        const cleanData = hideGatewayInfo(result);
        console.log(`✅ Response (showing last 10 of ${(payData.payments || []).length} total):`);
        console.log(JSON.stringify(cleanData, null, 2));
      } else {
        console.log(`❌ Failed (HTTP ${response.status})`);
      }
    } catch (error: any) {
      console.log(`❌ Error: ${error.message}`);
    }
    console.log('\n' + '━'.repeat(70) + '\n');

    // 3-5. Payment events (24h, 7d, 30d)
    const timeRanges: Array<[string, number]> = [['24h', 24], ['7 days', 168], ['30 days', 720]];
    for (let idx = 0; idx < timeRanges.length; idx++) {
      const [timeLabel, hours] = timeRanges[idx];
      console.log(`${idx + 3}️⃣  PAYMENT EVENTS (Last ${timeLabel}) - Showing Last 10\n`);
      console.log(`curl '${AGENTPAY_API_URL}/audit/logs?event_type=x402_payment_settled&hours=${hours}' \\`);
      console.log(`  -H 'x-api-key: ${SELLER_API_KEY}'\n`);
      console.log('🔄 Executing...\n');
      try {
        const response = await axios.get(`${AGENTPAY_API_URL}/audit/logs`, {
          headers: { 'x-api-key': SELLER_API_KEY || '' },
          params: { event_type: 'x402_payment_settled', hours },
          timeout: 10000
        });
        if (response.status === 200) {
          const data = response.data;
          const allLogs = data.logs || [];
          const eventLogs = allLogs.slice(0, 10);
          const result = { logs: eventLogs, count: allLogs.length, showing: eventLogs.length };
          const cleanData = hideGatewayInfo(result);
          console.log(`✅ Response (showing last 10 of ${allLogs.length} total):`);
          console.log(JSON.stringify(cleanData, null, 2));
        } else {
          console.log(`❌ No events found (HTTP ${response.status})`);
        }
      } catch (error: any) {
        console.log(`❌ Error: ${error.message}`);
      }
      console.log('\n' + '━'.repeat(70) + '\n');
    }

    // 6. Commission events
    console.log('6️⃣  COMMISSION EVENTS (Last 30 days) - Showing Last 10\n');
    console.log(`curl '${AGENTPAY_API_URL}/audit/logs?event_type=x402_payment_settled&hours=720' \\`);
    console.log(`  -H 'x-api-key: ${SELLER_API_KEY}'\n`);
    console.log('💡 Note: Filtering for events with commission data embedded\n');
    console.log('🔄 Executing...\n');
    try {
      const response = await axios.get(`${AGENTPAY_API_URL}/audit/logs`, {
        headers: { 'x-api-key': SELLER_API_KEY || '' },
        params: { event_type: 'x402_payment_settled', hours: 720 },
        timeout: 10000
      });
      if (response.status === 200) {
        const data = response.data;
        const allLogs = data.logs || [];

        // Filter for logs with commission data
        const commissionLogs: any[] = [];
        for (const log of allLogs) {
          let details = log.details;
          if (typeof details === 'string') {
            try {
              details = JSON.parse(details);
            } catch {
              continue;
            }
          }

          // Only include if has commission data
          if (details.commission_tx_hash) {
            commissionLogs.push({
              id: log.id,
              timestamp: log.timestamp,
              commission_tx_hash: details.commission_tx_hash,
              commission_amount_usd: details.commission_amount_usd,
              related_buyer: details.payer_address || details.sender_address,
              status: details.status || 'completed'
            });
          }
        }

        const commLogs = commissionLogs.slice(0, 10);
        const result = { commission_events: commLogs, count: commissionLogs.length, showing: commLogs.length };
        const cleanData = hideGatewayInfo(result);
        console.log(`✅ Response (showing last 10 of ${commissionLogs.length} commission events):`);
        console.log(JSON.stringify(cleanData, null, 2));
      } else {
        console.log(`❌ No payment events (HTTP ${response.status})`);
      }
    } catch (error: any) {
      console.log(`❌ Error: ${error.message}`);
    }
    console.log('\n' + '━'.repeat(70) + '\n');

    // 7. Payments from specific buyer
    if (uniqueBuyers.size > 0) {
      const exampleBuyer = Array.from(uniqueBuyers)[0];
      console.log('7️⃣  PAYMENTS FROM SPECIFIC BUYER - Showing Last 10\n');
      console.log(`curl '${AGENTPAY_API_URL}/audit/logs?event_type=x402_payment_settled&client_id=${exampleBuyer}' \\`);
      console.log(`  -H 'x-api-key: ${SELLER_API_KEY}'\n`);
      console.log('🔄 Executing...\n');
      try {
        const response = await axios.get(`${AGENTPAY_API_URL}/audit/logs`, {
          headers: { 'x-api-key': SELLER_API_KEY || '' },
          params: { event_type: 'x402_payment_settled', client_id: exampleBuyer },
          timeout: 10000
        });
        if (response.status === 200) {
          const data = response.data;
          const allLogs = data.logs || [];
          const buyerLogs = allLogs.slice(0, 10);
          const result = { buyer: exampleBuyer, logs: buyerLogs, count: allLogs.length, showing: buyerLogs.length };
          const cleanData = hideGatewayInfo(result);
          console.log(`✅ Response (showing last 10 of ${allLogs.length} total from buyer):`);
          console.log(JSON.stringify(cleanData, null, 2));
        } else {
          console.log(`❌ No payments from this buyer (HTTP ${response.status})`);
        }
      } catch (error: any) {
        console.log(`❌ Error: ${error.message}`);
      }
      console.log('\n' + '━'.repeat(70) + '\n');
    }

    // 8. Webhook configuration
    console.log('8️⃣  WEBHOOK CONFIGURATION\n');
    console.log(`curl '${AGENTPAY_API_URL}/v1/webhooks/list' \\`);
    console.log(`  -H 'x-api-key: ${SELLER_API_KEY}'\n`);
    console.log('🔄 Executing...\n');
    const webhookResult = { webhooks: webhooks.slice(0, 10), total: stats.totalWebhooks, active: stats.activeWebhooks };
    const cleanWebhooks = hideGatewayInfo(webhookResult);
    console.log('✅ Response (showing first 10):');
    console.log(JSON.stringify(cleanWebhooks, null, 2));
    console.log('\n' + '━'.repeat(70) + '\n');

    // 9. Webhook delivery events
    console.log('9️⃣  WEBHOOK DELIVERY EVENTS (Last 30 days) - Showing Last 10\n');
    console.log(`curl '${AGENTPAY_API_URL}/audit/logs?event_type=webhook_delivered&hours=720' \\`);
    console.log(`  -H 'x-api-key: ${SELLER_API_KEY}'\n`);
    console.log('🔄 Executing...\n');
    try {
      const response = await axios.get(`${AGENTPAY_API_URL}/audit/logs`, {
        headers: { 'x-api-key': SELLER_API_KEY || '' },
        params: { event_type: 'webhook_delivered', hours: 720 },
        timeout: 10000
      });
      if (response.status === 200) {
        const data = response.data;
        const allLogs = data.logs || [];
        const whLogs = allLogs.slice(0, 10);
        const result = { logs: whLogs, count: allLogs.length, showing: whLogs.length };
        const cleanData = hideGatewayInfo(result);
        console.log(`✅ Response (showing last 10 of ${allLogs.length} total):`);
        console.log(JSON.stringify(cleanData, null, 2));
      } else {
        console.log(`❌ No webhook events (HTTP ${response.status})`);
      }
    } catch (error: any) {
      console.log(`❌ Error: ${error.message}`);
    }
    console.log('\n' + '━'.repeat(70) + '\n');

    // 10. Payment verification
    if (payments.length > 0) {
      const latestTx = payments[0].tx_hash;
      if (latestTx) {
        console.log('🔟 PAYMENT VERIFICATION (Latest Payment)\n');
        console.log(`curl '${AGENTPAY_API_URL}/v1/payments/verify/${latestTx}' \\`);
        console.log(`  -H 'x-api-key: ${SELLER_API_KEY}'\n`);
        console.log('🔄 Executing...\n');
        try {
          const response = await axios.get(`${AGENTPAY_API_URL}/v1/payments/verify/${latestTx}`, {
            headers: { 'x-api-key': SELLER_API_KEY || '' },
            timeout: 10000
          });
          if (response.status === 200) {
            const verifyData = response.data;
            const cleanData = hideGatewayInfo(verifyData);
            console.log('✅ Response:');
            console.log(JSON.stringify(cleanData, null, 2));
          } else {
            console.log(`❌ Verification failed (HTTP ${response.status})`);
          }
        } catch (error: any) {
          console.log(`❌ Error: ${error.message}`);
        }
        console.log('\n' + '━'.repeat(70) + '\n');
      }
    }

    // Additional manual commands
    console.log('➕ ADDITIONAL COMMANDS (Templates)\n');
    console.log('   Verify specific payment (replace YOUR_TX_HASH):');
    console.log(`   curl '${AGENTPAY_API_URL}/v1/payments/verify/YOUR_TX_HASH' \\`);
    console.log(`     -H 'x-api-key: ${SELLER_API_KEY}'\n`);
    console.log('   Get audit logs by transaction (replace YOUR_TX_HASH):');
    console.log(`   curl '${AGENTPAY_API_URL}/audit/logs/transaction/YOUR_TX_HASH' \\`);
    console.log(`     -H 'x-api-key: ${SELLER_API_KEY}'\n`);

    console.log('='.repeat(70));
    console.log('✅ SELLER MONITORING COMPLETE');
    console.log('='.repeat(70));
    console.log();
  } catch (error: any) {
    console.error(`\n❌ Failed to fetch data: ${error.message}`);
    console.log();
    console.log('Please check:');
    console.log('  - Seller API key is valid');
    console.log('  - Seller wallet address is correct');
    console.log('  - Network connection is working');
    process.exit(1);
  }
}

main().catch(console.error);
