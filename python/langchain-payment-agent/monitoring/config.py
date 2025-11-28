"""
Chain and Token Configuration Module

Manages multi-chain and multi-token configuration for AgentGatePay payments.
Supports: Ethereum, Base, Polygon, Arbitrum with USDC, USDT, DAI tokens.
"""

import os
import json
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


# ========================================
# CHAIN CONFIGURATIONS
# ========================================

CHAIN_CONFIG = {
    'ethereum': {
        'chain_id': 1,
        'name': 'Ethereum Mainnet',
        'rpc_url_default': 'https://eth-mainnet.public.blastapi.io',
        'rpc_url_env': 'ETHEREUM_RPC_URL',
        'explorer': 'https://etherscan.io',
        'gas_price_gwei': 30,
        'enabled': True
    },
    'base': {
        'chain_id': 8453,
        'name': 'Base',
        'rpc_url_default': 'https://mainnet.base.org',
        'rpc_url_env': 'BASE_RPC_URL',
        'explorer': 'https://basescan.org',
        'gas_price_gwei': 1,
        'enabled': True
    },
    'polygon': {
        'chain_id': 137,
        'name': 'Polygon',
        'rpc_url_default': 'https://polygon-rpc.com',
        'rpc_url_env': 'POLYGON_RPC_URL',
        'explorer': 'https://polygonscan.com',
        'gas_price_gwei': 50,
        'enabled': True
    },
    'arbitrum': {
        'chain_id': 42161,
        'name': 'Arbitrum One',
        'rpc_url_default': 'https://arb1.arbitrum.io/rpc',
        'rpc_url_env': 'ARBITRUM_RPC_URL',
        'explorer': 'https://arbiscan.io',
        'gas_price_gwei': 1,
        'enabled': True
    }
}


# ========================================
# TOKEN CONFIGURATIONS
# ========================================

TOKEN_CONFIG = {
    'USDC': {
        'name': 'USD Coin',
        'decimals': 6,
        'symbol': 'USDC',
        'contracts': {
            'ethereum': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
            'base': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
            'polygon': '0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359',
            'arbitrum': '0xaf88d065e77c8cC2239327C5EDb3A432268e5831'
        }
    },
    'USDT': {
        'name': 'Tether USD',
        'decimals': 6,
        'symbol': 'USDT',
        'contracts': {
            'ethereum': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
            'polygon': '0xc2132D05D31c914a87C6611C10748AEb04B58e8F',
            'arbitrum': '0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9',
            'base': None  # USDT not widely supported on Base
        }
    },
    'DAI': {
        'name': 'Dai Stablecoin',
        'decimals': 18,  # DAI uses 18 decimals!
        'symbol': 'DAI',
        'contracts': {
            'ethereum': '0x6B175474E89094C44Da98b954EedeAC495271d0F',
            'polygon': '0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063',
            'arbitrum': '0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1',
            'base': '0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb'
        }
    }
}


# ========================================
# CONFIGURATION DATA CLASS
# ========================================

@dataclass
class ChainConfig:
    """Chain and token configuration"""
    chain: str
    token: str
    chain_id: int
    rpc_url: str
    token_contract: str
    decimals: int
    explorer: str
    gas_price_gwei: int
    last_updated: str


# ========================================
# CONFIGURATION FILE PATH
# ========================================

CONFIG_FILE = os.path.expanduser("~/.agentgatepay_config.json")


# ========================================
# HELPER FUNCTIONS
# ========================================

def get_supported_chains() -> List[str]:
    """Get list of supported chain names"""
    return [chain for chain, config in CHAIN_CONFIG.items() if config['enabled']]


def get_supported_tokens(chain: str = None) -> List[str]:
    """
    Get list of supported tokens.

    Args:
        chain: If provided, only returns tokens supported on that chain

    Returns:
        List of token symbols
    """
    if chain:
        tokens = []
        for token, config in TOKEN_CONFIG.items():
            if config['contracts'].get(chain):
                tokens.append(token)
        return tokens
    else:
        return list(TOKEN_CONFIG.keys())


def get_token_contract(token: str, chain: str) -> Optional[str]:
    """Get token contract address for specific chain"""
    if token not in TOKEN_CONFIG:
        return None

    return TOKEN_CONFIG[token]['contracts'].get(chain)


def get_token_decimals(token: str) -> int:
    """Get token decimals"""
    if token not in TOKEN_CONFIG:
        raise ValueError(f"Unsupported token: {token}")

    return TOKEN_CONFIG[token]['decimals']


def get_chain_rpc_url(chain: str) -> str:
    """Get RPC URL for chain (checks env var first, then default)"""
    if chain not in CHAIN_CONFIG:
        raise ValueError(f"Unsupported chain: {chain}")

    config = CHAIN_CONFIG[chain]

    # Check environment variable first
    env_var = config['rpc_url_env']
    rpc_url = os.getenv(env_var)

    if rpc_url:
        return rpc_url

    # Fallback to default
    return config['rpc_url_default']


def get_chain_explorer(chain: str) -> str:
    """Get block explorer URL for chain"""
    if chain not in CHAIN_CONFIG:
        raise ValueError(f"Unsupported chain: {chain}")

    return CHAIN_CONFIG[chain]['explorer']


def validate_chain_token_combo(chain: str, token: str) -> bool:
    """Validate that token is supported on chain"""
    if chain not in CHAIN_CONFIG:
        return False

    if token not in TOKEN_CONFIG:
        return False

    return TOKEN_CONFIG[token]['contracts'].get(chain) is not None


# ========================================
# CONFIGURATION PERSISTENCE
# ========================================

def load_config() -> Optional[ChainConfig]:
    """
    Load configuration from ~/.agentgatepay_config.json

    Returns:
        ChainConfig object if file exists, None otherwise
    """
    if not os.path.exists(CONFIG_FILE):
        return None

    try:
        with open(CONFIG_FILE, 'r') as f:
            data = json.load(f)

        # Validate loaded config
        chain = data.get('chain', 'base')
        token = data.get('token', 'USDC')

        if not validate_chain_token_combo(chain, token):
            print(f"⚠️  Invalid chain/token combo in config: {chain}/{token}")
            return None

        return ChainConfig(
            chain=chain,
            token=token,
            chain_id=data.get('chain_id', CHAIN_CONFIG[chain]['chain_id']),
            rpc_url=data.get('rpc_url', get_chain_rpc_url(chain)),
            token_contract=data.get('token_contract', get_token_contract(token, chain)),
            decimals=data.get('decimals', get_token_decimals(token)),
            explorer=data.get('explorer', get_chain_explorer(chain)),
            gas_price_gwei=data.get('gas_price_gwei', CHAIN_CONFIG[chain]['gas_price_gwei']),
            last_updated=data.get('last_updated', datetime.now().isoformat())
        )

    except Exception as e:
        print(f"⚠️  Failed to load config: {e}")
        return None


def save_config(chain: str, token: str) -> ChainConfig:
    """
    Save chain/token configuration to ~/.agentgatepay_config.json

    Args:
        chain: Chain name (ethereum, base, polygon, arbitrum)
        token: Token symbol (USDC, USDT, DAI)

    Returns:
        ChainConfig object

    Raises:
        ValueError: If invalid chain/token combination
    """
    if not validate_chain_token_combo(chain, token):
        raise ValueError(f"Invalid chain/token combination: {chain}/{token}")

    config = ChainConfig(
        chain=chain,
        token=token,
        chain_id=CHAIN_CONFIG[chain]['chain_id'],
        rpc_url=get_chain_rpc_url(chain),
        token_contract=get_token_contract(token, chain),
        decimals=get_token_decimals(token),
        explorer=get_chain_explorer(chain),
        gas_price_gwei=CHAIN_CONFIG[chain]['gas_price_gwei'],
        last_updated=datetime.now().isoformat()
    )

    # Save to file
    data = {
        'chain': config.chain,
        'token': config.token,
        'chain_id': config.chain_id,
        'rpc_url': config.rpc_url,
        'token_contract': config.token_contract,
        'decimals': config.decimals,
        'explorer': config.explorer,
        'gas_price_gwei': config.gas_price_gwei,
        'last_updated': config.last_updated
    }

    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"✅ Configuration saved to {CONFIG_FILE}")

    except Exception as e:
        print(f"⚠️  Failed to save config: {e}")

    return config


def prompt_for_config() -> ChainConfig:
    """
    Interactive prompt for chain and token selection

    Returns:
        ChainConfig object with user's selections
    """
    print("=" * 60)
    print("⚙️  CHAIN & TOKEN CONFIGURATION")
    print("=" * 60)
    print("\nSupported Chains:")
    print("  1. Base (USDC, DAI) - Fast, low fees ⭐ RECOMMENDED")
    print("  2. Ethereum (USDC, USDT, DAI) - Most secure, higher fees")
    print("  3. Polygon (USDC, USDT, DAI) - Fast, low fees")
    print("  4. Arbitrum (USDC, USDT, DAI) - Fast, low fees")
    print()

    chain_input = input("Select chain (1-4, default: 1 for Base): ").strip()
    chain_map = {"1": "base", "2": "ethereum", "3": "polygon", "4": "arbitrum", "": "base"}
    selected_chain = chain_map.get(chain_input, "base")

    print(f"\n✅ Selected chain: {selected_chain.upper()}")
    print(f"\nSupported Tokens on {selected_chain}:")

    # Show available tokens for selected chain
    available_tokens = get_supported_tokens(selected_chain)

    if selected_chain == "base":
        print("  1. USDC (6 decimals) - Most widely used ⭐ RECOMMENDED")
        print("  2. DAI (18 decimals) - Decentralized stablecoin")
        token_options = {"1": "USDC", "2": "DAI", "": "USDC"}
    elif selected_chain in ["ethereum", "polygon", "arbitrum"]:
        print("  1. USDC (6 decimals) - Most widely used ⭐ RECOMMENDED")
        print("  2. USDT (6 decimals) - Tether stablecoin")
        print("  3. DAI (18 decimals) - Decentralized stablecoin")
        token_options = {"1": "USDC", "2": "USDT", "3": "DAI", "": "USDC"}
    else:
        token_options = {"": "USDC"}

    token_input = input(f"\nSelect token (default: 1 for USDC): ").strip()
    selected_token = token_options.get(token_input, "USDC")

    print(f"\n✅ Configuration:")
    print(f"   Chain: {selected_chain.upper()}")
    print(f"   Token: {selected_token}")
    print(f"   Decimals: {get_token_decimals(selected_token)}")
    print(f"   Explorer: {get_chain_explorer(selected_chain)}")
    print(f"   Config file: {CONFIG_FILE}")
    print()
    print(f"💡 To change later: Delete {CONFIG_FILE}")
    print()

    # Save and return
    return save_config(selected_chain, selected_token)


def get_or_create_config() -> ChainConfig:
    """
    Load existing config or prompt user to create new one

    Returns:
        ChainConfig object
    """
    config = load_config()

    if config:
        print(f"✅ Loaded configuration:")
        print(f"   Chain: {config.chain.upper()}")
        print(f"   Token: {config.token}")
        print(f"   Decimals: {config.decimals}")
        print(f"   Explorer: {config.explorer}")
        print()
        print(f"💡 To change: Delete {CONFIG_FILE}")
        print()
        return config
    else:
        print(f"\n⚙️  No configuration found. Let's set up your preferences!")
        print()
        return prompt_for_config()
