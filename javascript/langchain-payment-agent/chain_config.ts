/**
 * Chain Configuration
 *
 * Multi-chain/token configuration for AgentGatePay payments.
 * Loads from environment variables and provides token contracts, RPCs, explorers.
 */

import { config } from 'dotenv';
config();

export interface ChainConfig {
  chain: string;
  token: string;
  chainId: number;
  rpcUrl: string;
  tokenContract: string;
  decimals: number;
  explorer: string;
}

// Token contract addresses per chain
const TOKEN_CONTRACTS: Record<string, Record<string, string>> = {
  USDC: {
    base: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
    ethereum: '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
    polygon: '0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359',
    arbitrum: '0xaf88d065e77c8cC2239327C5EDb3A432268e5831'
  },
  USDT: {
    ethereum: '0xdAC17F958D2ee523a2206206994597C13D831ec7',
    polygon: '0xc2132D05D31c914a87C6611C10748AEb04B58e8F',
    arbitrum: '0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9'
  },
  DAI: {
    base: '0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb',
    ethereum: '0x6B175474E89094C44Da98b954EedeAC495271d0F',
    polygon: '0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063',
    arbitrum: '0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1'
  }
};

// Chain metadata
const CHAIN_METADATA: Record<string, { chainId: number; explorer: string }> = {
  base: { chainId: 8453, explorer: 'https://basescan.org' },
  ethereum: { chainId: 1, explorer: 'https://etherscan.io' },
  polygon: { chainId: 137, explorer: 'https://polygonscan.com' },
  arbitrum: { chainId: 42161, explorer: 'https://arbiscan.io' }
};

// Token decimals
const TOKEN_DECIMALS: Record<string, number> = {
  USDC: 6,
  USDT: 6,
  DAI: 18
};

/**
 * Get chain configuration from environment variables
 */
export function getChainConfig(): ChainConfig {
  const chain = (process.env.PAYMENT_CHAIN || 'base').toLowerCase();
  const token = (process.env.PAYMENT_TOKEN || 'USDC').toUpperCase();

  // Validate chain
  if (!['base', 'ethereum', 'polygon', 'arbitrum'].includes(chain)) {
    throw new Error(`Invalid chain: ${chain}. Must be one of: base, ethereum, polygon, arbitrum`);
  }

  // Validate token
  if (!['USDC', 'USDT', 'DAI'].includes(token)) {
    throw new Error(`Invalid token: ${token}. Must be one of: USDC, USDT, DAI`);
  }

  // Check if token is available on chain
  const tokenContract = TOKEN_CONTRACTS[token]?.[chain];
  if (!tokenContract) {
    throw new Error(`Token ${token} is not available on ${chain} network`);
  }

  // Get RPC URL from environment
  const rpcEnvVar = `${chain.toUpperCase()}_RPC_URL`;
  const rpcUrl = process.env[rpcEnvVar];
  if (!rpcUrl) {
    throw new Error(`RPC URL not found. Set ${rpcEnvVar} in .env file`);
  }

  // Get chain metadata
  const metadata = CHAIN_METADATA[chain];
  if (!metadata) {
    throw new Error(`Chain metadata not found for: ${chain}`);
  }

  return {
    chain,
    token,
    chainId: metadata.chainId,
    rpcUrl,
    tokenContract,
    decimals: TOKEN_DECIMALS[token],
    explorer: metadata.explorer
  };
}

/**
 * Display chain configuration
 */
export function displayChainConfig(config: ChainConfig): void {
  console.log('\nCHAIN & TOKEN CONFIGURATION');
  console.log('='.repeat(80));
  console.log(`\nUsing configuration from .env:`);
  console.log(`  Chain: ${config.chain.charAt(0).toUpperCase() + config.chain.slice(1)} (ID: ${config.chainId})`);
  console.log(`  Token: ${config.token} (${config.decimals} decimals)`);
  console.log(`  RPC: ${config.rpcUrl}`);
  console.log(`  Contract: ${config.tokenContract}`);
  console.log(`\nTo change chain/token: Edit PAYMENT_CHAIN and PAYMENT_TOKEN in .env file`);
  console.log('='.repeat(80));
}
