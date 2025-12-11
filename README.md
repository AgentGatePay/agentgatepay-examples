● # AgentGatePay Examples

  Examples and workflow templates for autonomous AI agent payments.

  Automate crypto payments (USDC/USDT/DAI) across Ethereum, Base, Polygon, and Arbitrum using zero-code n8n workflows, AI framework integrations, and API demos.
  AgentGatePay currently supports multi-chain cryptocurrency payments. We are actively working to expand support for additional payment methods.
  If you would like to see a specific payment method or feature, please contact support@agentgatepay.com.
  Your feedback helps shape our roadmap.

  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
  [![GitHub stars](https://img.shields.io/github/stars/AgentGatePay/agentgatepay-examples)](https://github.com/AgentGatePay/agentgatepay-examples/stargazers)

  ---

  ## Supported Payment Methods

  **Cryptocurrencies:** USDC, USDT, DAI
  **Blockchains:** Ethereum, Base, Polygon, Arbitrum

  **Supported Combinations:**
  - USDC: All chains (Ethereum, Base, Polygon, Arbitrum)
  - USDT: Ethereum, Polygon, Arbitrum (not available on Base)
  - DAI: All chains (Ethereum, Base, Polygon, Arbitrum)

  **Gas Tokens Required:**
  - Ethereum: ETH
  - Base: ETH
  - Polygon: MATIC
  - Arbitrum: ETH

  ---

  ## Quick Start

  ### n8n Workflows

  For automation users who want zero-code blockchain payment workflows:

  1. Import workflow JSON from `n8n/` directory into your N8N platform
  2. Configure your AgentGatePay API key
  3. Set up notifications (Slack, Email, or Discord)
  4. Deploy transaction signing service using one-click Render deploy
  5. Activate workflow to begin monitoring payments

  Complete setup time: approximately 5-10 minutes.

  [Full n8n Setup Guide](n8n/README.md)

  ### AI Framework Integrations

  Production examples for popular AI agent frameworks using AgentGatePay SDKs.

  **Python Framework Examples:**
  - [LangChain Integration](python/langchain-payment-agent/) - Autonomous tool-calling agents with payment capabilities (10 complete examples)

  **JavaScript/TypeScript Framework Examples:**
  - [LangChain.js Integration](javascript/langchain-payment-agent/) - Node.js/TypeScript agents with blockchain payments (10 complete examples)

  **Need help with other platforms or languages?** Contact support@agentgatepay.com and we'll help you integrate AgentGatePay with your framework.

  ---

  ## Repository Contents

  ### n8n Workflows (Available)

  Production-ready n8n templates for autonomous blockchain payment automation:

  **Buyer Agent Workflow**
  - Autonomous payment for API resources using pre-authorized mandates
  - Multi-chain support (Ethereum, Base, Polygon, Arbitrum)
  - Budget management with AP2 mandate protocol
  - Automatic transaction signing via Render or Railway service
  - Configuration time: 10 minutes

  **Seller Resource API Workflow**
  - Monetize n8n webhooks and APIs with cryptocurrency payments
  - HTTP 402 Payment Required protocol implementation
  - On-chain payment verification
  - Automatic resource delivery upon payment confirmation
  - Customizable resource catalog

  **Buyer Monitoring Dashboard**
  - Real-time spending analytics (track outgoing payments)
  - Mandate budget tracking (remaining balance, spent amount, utilization percentage)
  - Transaction history (payments YOU sent to merchants)
  - Multi-wallet support
  - Budget depletion and spending alerts

  **Seller Monitoring Dashboard**
  - Revenue analytics (total, daily, weekly, monthly breakdowns)
  - Payment tracking (payments YOU received from buyers)
  - Multi-chain revenue breakdown
  - Top buyers analytics
  - Webhook delivery status tracking

  [Browse n8n workflows](n8n/)

  ---

  ### AI Framework Examples (Available)

  Official SDK integration examples for popular AI agent frameworks.

  **Python SDK Examples** ([Browse Python examples](python/langchain-payment-agent/))
  - **LangChain** - Payment-enabled tool agents, API marketplace agents, budget-managed research assistants (10 complete examples)
  - **REST API Integration** - Integration guides for any framework
  - **MCP Integration** - Model Context Protocol (15 tools)

  **JavaScript/TypeScript SDK Examples** ([Browse JavaScript examples](javascript/langchain-payment-agent/))
  - **LangChain.js** - Node.js/TypeScript payment agents, Express.js webhook servers (10 complete examples)
  - **REST API Integration** - Integration guides for any JavaScript framework
  - **MCP Integration** - Model Context Protocol (15 tools)

  ---

  ## Features

  - **AIF (Agent Interaction Firewall)** - First firewall built for AI agents with rate limiting and reputation system
  - Multi-chain blockchain support (Ethereum, Base, Polygon, Arbitrum)
  - Multi-token support (USDC, USDT, DAI) with automatic decimal handling
  - Real-time notifications (Slack, Email, Discord, Webhooks)
  - Complete audit log integration for compliance tracking
  - Production-ready error handling and retry logic
  - Webhook signature verification (HMAC)
  - Budget management using AP2 mandate system with TTL and scope controls
  - One-click deployment for transaction signing service
  - Comprehensive documentation with troubleshooting guides

  ---

  ## Prerequisites

  **For n8n Workflows:**
  - AgentGatePay API key
  - n8n instance (Cloud or self-hosted)
  - Ethereum-compatible wallet funded with payment tokens (USDC, USDT, or DAI) and gas tokens
  - Transaction signing service (deployed via Render or Railway)

  **For Framework Integrations:**
  - Python 3.9+ or Node.js 18+ (framework dependent)
  - AgentGatePay SDK: `pip install agentgatepay-sdk` or `npm install agentgatepay-sdk`
  - AgentGatePay API key
  - Ethereum-compatible wallet funded with payment tokens and gas tokens

  ---

  ## Documentation

  - **API Endpoint:** https://api.agentgatepay.com - REST API for payments, mandates, webhooks
  - **MCP Endpoint:** https://mcp.agentgatepay.com - Model Context Protocol (15 tools)
  - [SDK Repository](https://github.com/AgentGatePay/agentgatepay-sdks) - Official SDKs (JavaScript + Python)
  - [Python SDK on PyPI](https://pypi.org/project/agentgatepay-sdk/) - Install: `pip install agentgatepay-sdk`
  - [JavaScript SDK on npm](https://www.npmjs.com/package/agentgatepay-sdk/) - Install: `npm install agentgatepay-sdk`
  - [n8n Complete Guide](n8n/README.md) - Full setup, configuration, and troubleshooting
  - [Python LangChain Examples](python/langchain-payment-agent/README.md) - Complete guide with multi-token/chain configuration
  - [JavaScript/TypeScript LangChain.js Examples](javascript/langchain-payment-agent/README.md) - Complete guide with multi-token/chain configuration

  ---

  ## Contributing

  Contributions are welcome. To contribute:

  1. Fork this repository
  2. Create a feature branch (`git checkout -b feature/new-example`)
  3. Commit your changes (`git commit -m 'Add new integration example'`)
  4. Push to the branch (`git push origin feature/new-example`)
  5. Open a Pull Request

  For bugs or feature requests, please email support@agentgatepay.com.

  ---

  ## Feedback and Feature Requests

  AgentGatePay is actively expanding payment method support beyond cryptocurrency. Planned additions include:

  - Credit and debit card processing (Stripe, Square)
  - Bank transfers (ACH, SEPA)
  - PayPal, Venmo, Cash App
  - Regional payment methods (Alipay, WeChat Pay, PIX)
  - Mobile payment integrations

  **To request features or provide feedback:**
  - Email: support@agentgatepay.com

  Your input directly influences development priorities.

  ---

  ## License

  MIT License - see [LICENSE](LICENSE) file for details.

  Free for production use, modification, and distribution. Commercial use permitted.

  ---

  ## Acknowledgments

  If you are using AgentGatePay in production, please star this repository. Stars help other developers discover these integration tools.

  ---

  **API Endpoint:** [api.agentgatepay.com](https://api.agentgatepay.com)
  **MCP Endpoint:** [mcp.agentgatepay.com](https://mcp.agentgatepay.com)

  Maintained by the AgentGatePay team.


