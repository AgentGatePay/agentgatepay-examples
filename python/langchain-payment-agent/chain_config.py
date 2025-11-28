"""
Simple chain/token configuration from .env file.

To change chain or token, edit your .env file:
- PAYMENT_CHAIN=base (options: base, ethereum, polygon, arbitrum)
- PAYMENT_TOKEN=USDC (options: USDC, USDT, DAI - check availability per chain)
"""

import os
from dataclasses import dataclass

# Token contracts
USDC_CONTRACTS = {
    "ethereum": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "base": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "polygon": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
    "arbitrum": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
}

USDT_CONTRACTS = {
    "ethereum": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    "polygon": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
    "arbitrum": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
    "base": None  # USDT not supported on Base
}

DAI_CONTRACTS = {
    "ethereum": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
    "polygon": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",
    "arbitrum": "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
    "base": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb"
}

CHAIN_IDS = {
    "ethereum": 1,
    "base": 8453,
    "polygon": 137,
    "arbitrum": 42161
}

EXPLORERS = {
    "ethereum": "https://etherscan.io",
    "base": "https://basescan.org",
    "polygon": "https://polygonscan.com",
    "arbitrum": "https://arbiscan.io"
}

@dataclass
class ChainConfig:
    chain: str
    token: str
    chain_id: int
    rpc_url: str
    token_contract: str
    decimals: int
    explorer: str


def get_chain_config():
    """Load chain/token config from environment variables"""
    chain = os.getenv('PAYMENT_CHAIN', 'base').lower()
    token = os.getenv('PAYMENT_TOKEN', 'USDC').upper()

    # Validate chain
    if chain not in CHAIN_IDS:
        raise ValueError(f"Invalid PAYMENT_CHAIN: {chain}. Options: base, ethereum, polygon, arbitrum")

    # Get token contract
    if token == 'USDC':
        token_contract = USDC_CONTRACTS.get(chain)
        decimals = 6
    elif token == 'USDT':
        token_contract = USDT_CONTRACTS.get(chain)
        decimals = 6
        if not token_contract:
            raise ValueError(f"USDT not available on {chain}. Use USDC or DAI instead.")
    elif token == 'DAI':
        token_contract = DAI_CONTRACTS.get(chain)
        decimals = 18  # DAI uses 18 decimals
    else:
        raise ValueError(f"Invalid PAYMENT_TOKEN: {token}. Options: USDC, USDT, DAI")

    # Get RPC URL
    if chain == 'base':
        rpc_url = os.getenv('BASE_RPC_URL', 'https://mainnet.base.org')
    elif chain == 'ethereum':
        rpc_url = os.getenv('ETHEREUM_RPC_URL', 'https://eth-mainnet.public.blastapi.io')
    elif chain == 'polygon':
        rpc_url = os.getenv('POLYGON_RPC_URL', 'https://polygon-rpc.com')
    elif chain == 'arbitrum':
        rpc_url = os.getenv('ARBITRUM_RPC_URL', 'https://arb1.arbitrum.io/rpc')

    return ChainConfig(
        chain=chain,
        token=token,
        chain_id=CHAIN_IDS[chain],
        rpc_url=rpc_url,
        token_contract=token_contract,
        decimals=decimals,
        explorer=EXPLORERS[chain]
    )
