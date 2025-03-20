import ccxt
import pandas as pd
from typing import Dict, List, Any, Optional, Union, TypedDict, cast
import streamlit as st
from datetime import datetime, timedelta
from pybit.unified_trading import HTTP
from .db_manager import DatabaseManager
from .data_processor import DataProcessor
from binance.error import ClientError
import okx.Account as Account
import okx.PublicData as PublicData
import okx.Trade as Trade
import requests
import hmac
import hashlib
import time
import json
import rabbitx
import aiohttp
from rabbitx import const
from rabbitx.client import Client as RabbitXClient, CandlePeriod, OrderSide, OrderType, TimeInForce
from rabbitx.client import OrderStatus
import asyncio
from urllib.parse import urlencode
import uuid
import logging

class BybitResponse(TypedDict):
    result: Dict[str, Dict[str, List[Dict[str, Any]]]]

class BalanceData(TypedDict):
    totalEquity: str
    asset: str
    walletBalance: str

class ExchangeClient:
    def __init__(self):
        self.exchanges: Dict[str, Any] = {}
        self._binance_client = None
        self._bybit_client: Optional[HTTP] = None
        self._okx_client = None
        self._okx_public_client = None
        self._okx_trade_client = None
        self._hyperliquid_api_key = None
        self._hyperliquid_secret = None
        self._hyperliquid_client = None
        self._rabbitx_api_key = None
        self._rabbitx_secret = None
        self._rabbitx_jwt_token = None
        self._rabbitx_client = None
        self._loop = None
        self.db_manager = DatabaseManager()
        self.data_processor = DataProcessor()
        self._clients_initialized = {
            'binance': False,
            'bybit': False,
            'okx': False,
            'hyperliquid': False,
            'rabbitx': False
        }
        logging.info("Initializing ExchangeClient")
        self._rabbitx_session = None  # Ensure this is initialized
        self._initialize_exchanges()

    @property
    def binance_client(self):
        return self._binance_client

    @binance_client.setter
    def binance_client(self, client):
        if self._binance_client:
            # Clean up old client if it exists
            if hasattr(self._binance_client, 'close'):
                try:
                    self._binance_client.close()
                except Exception as e:
                    print(f"Error closing Binance client: {e}")
        self._binance_client = client

    @property
    def bybit_client(self) -> Optional[HTTP]:
        return self._bybit_client

    @bybit_client.setter
    def bybit_client(self, client: Optional[HTTP]):
        self._bybit_client = client

    @property
    def okx_client(self):
        return self._okx_client

    @okx_client.setter
    def okx_client(self, client):
        self._okx_client = client

    @property
    def rabbitx_client(self):
        """Get the RabbitX client instance.

        Returns:
            Optional[rabbitx.client.Client]: The RabbitX client instance or None if not initialized.
        """
        return self._rabbitx_client

    @rabbitx_client.setter
    def rabbitx_client(self, client: Optional[RabbitXClient]):
        """Set the RabbitX client instance.

        Args:
            client: The RabbitX client instance to set.

        Raises:
            ValueError: If the client is initialized with empty API key, secret, or private JWT token.
        """
        if client is not None:
            # Extract credentials from client to validate
            self._rabbitx_api_key = getattr(client, 'api_key', None)
            self._rabbitx_secret = getattr(client, 'api_secret', None)
            self._rabbitx_jwt_token = getattr(client, 'private_jwt', None)
            
            if not self._rabbitx_api_key:
                raise ValueError("RabbitX API key cannot be empty")
            if not self._rabbitx_secret:
                raise ValueError("RabbitX secret cannot be empty")
            if not self._rabbitx_jwt_token:
                raise ValueError("RabbitX private JWT token cannot be empty")

        if hasattr(self, '_rabbitx_client') and self._rabbitx_client:
            # Clean up old client if it exists
            if hasattr(self._rabbitx_client.session, 'close'):
                try:
                    self._rabbitx_client.session.close()
                except Exception as e:
                    print(f"Error closing RabbitX client: {e}")

        self._rabbitx_client = client
        

    @property
    def hyperliquid_client(self):
        return self._hyperliquid_api_key, self._hyperliquid_secret

    @hyperliquid_client.setter
    def hyperliquid_client(self, api_key: str, secret: str):
        self._hyperliquid_api_key = api_key
        self._hyperliquid_secret = secret

    def _get_event_loop(self):
        """Get or create an event loop"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop

    def _run_async(self, coro):
        """Run an async coroutine in a synchronous context"""
        loop = self._get_event_loop()
        return loop.run_until_complete(coro)

    def _initialize_exchanges(self):
        """Initialize exchange connections with proper error handling"""
        try:
            # Load credentials from session state or secrets
            credentials = st.session_state.get('exchange_credentials', {})

            # Initialize RabbitX
            rabbitx_creds = credentials.get('rabbitx', {})
            # Print RabbitX credentials in green
           
            self._rabbitx_api_key = rabbitx_creds.get('api_key') or st.secrets.get("RABBITX_API_KEY")
            self._rabbitx_secret = rabbitx_creds.get('secret') or st.secrets.get("RABBITX_SECRET_KEY")
            self._rabbitx_jwt_token = rabbitx_creds.get('jwt_token') or st.secrets.get("RABBITX_JWT_TOKEN")
            # Check for missing RabbitX credentials
            missing_credentials = []
            if not self._rabbitx_api_key:
                missing_credentials.append("API Key")
            if not self._rabbitx_secret:
                missing_credentials.append("Secret Key")
            if not self._rabbitx_jwt_token:
                missing_credentials.append("JWT Token")
                
            if missing_credentials:
                missing_fields = ", ".join(missing_credentials)
                raise ValueError(f"RabbitX credentials incomplete. Missing: {missing_fields}. Please check your configuration.")

            # Initialize RabbitX    
            print("\nInitializing RabbitX...")
            print(f"\033[91mAPI Key present: {bool(self._rabbitx_api_key)}\033[0m" if not self._rabbitx_api_key else f"\033[92mAPI Key present: {self._rabbitx_api_key}\033[0m")
            print(f"\033[91mSecret present: {bool(self._rabbitx_secret)}\033[0m" if not self._rabbitx_secret else f"\033[92mSecret present: {self._rabbitx_secret}\033[0m")
            print(f"\033[91mJWT Token present: {bool(self._rabbitx_jwt_token)}\033[0m" if not self._rabbitx_jwt_token else f"\033[92mJWT Token present: {self._rabbitx_jwt_token}\033[0m")

            if self._rabbitx_api_key and self._rabbitx_secret:
                try:
                    self.rabbitx_client = RabbitXClient(api_url=const.URL,
                                                api_key=self._rabbitx_api_key,
                                                api_secret=self._rabbitx_secret,
                                                private_jwt=self._rabbitx_jwt_token,
                                                exchange='rbx')
                    # Test RabbitX connection
                    if self.test_rabbitx_connection():
                        print("Successfully connected to RabbitX")
                    else:
                        print("Failed to connect to RabbitX")
                except Exception as e:
                    print(f"Error initializing RabbitX client: {str(e)}")
            else:
                print("RabbitX credentials not found")
                self.rabbitx_client = None

            # Initialize Hyperliquid
            hyperliquid_creds = credentials.get('hyperliquid', {})
            self._hyperliquid_api_key = hyperliquid_creds.get('api_key') or st.secrets.get("HYPERLIQUID_API_KEY", "")
            self._hyperliquid_secret = hyperliquid_creds.get('secret') or st.secrets.get("HYPERLIQUID_SECRET_KEY", "")
            
            print("\nInitializing Hyperliquid...")
            print(f"\033[91mWallet address present: {bool(self._hyperliquid_api_key)}\033[0m" if not self._hyperliquid_api_key else f"\033[92mWallet address present: {self._hyperliquid_api_key}\033[0m")
            print(f"\033[91mPrivate key present: {bool(self._hyperliquid_secret)}\033[0m" if not self._hyperliquid_secret else f"\033[92mPrivate key present: {self._hyperliquid_secret}\033[0m")

            if self._hyperliquid_api_key and self._hyperliquid_secret:
                try:
                    # Ensure wallet address has 0x prefix
                    if self._hyperliquid_api_key and not self._hyperliquid_api_key.startswith('0x'):
                        self._hyperliquid_api_key = f"0x{self._hyperliquid_api_key}"
                    # Ensure private key has 0x prefix
                    if self._hyperliquid_secret and not self._hyperliquid_secret.startswith('0x'):
                        self._hyperliquid_secret = f"0x{self._hyperliquid_secret}"
                    
                    # Test connection
                    if self.test_hyperliquid_connection():
                        print("Successfully connected to Hyperliquid")
                    else:
                        print("Failed to connect to Hyperliquid")
                except Exception as e:
                    print(f"Error initializing Hyperliquid: {str(e)}")

            # Initialize OKX
            okx_creds = credentials.get('okx', {})
            okx_api_key = okx_creds.get('api_key') or st.secrets.get("OKX_API_KEY")
            okx_secret = okx_creds.get('secret') or st.secrets.get("OKX_SECRET")
            okx_passphrase = okx_creds.get('password') or st.secrets.get("OKX_PASSWORD")


            print("\nInitializing OKX...")
            print(f"\033[91mAPI Key present: {bool(okx_api_key)}\033[0m" if not okx_api_key else f"\033[92mAPI Key present: {okx_api_key}\033[0m")
            print(f"\033[91mSecret present: {bool(okx_secret)}\033[0m" if not okx_secret else f"\033[92mSecret present: {okx_secret}\033[0m")
            print(f"\033[91mPassphrase present: {bool(okx_passphrase)}\033[0m" if not okx_passphrase else f"\033[92mPassphrase present: {okx_passphrase}\033[0m")

            if okx_api_key and okx_secret and okx_passphrase:
                try:
                    print("Creating OKX client...")
                    # Initialize OKX with CCXT for better API compatibility
                    self._okx_client = ccxt.okx({
                        'apiKey': okx_api_key,
                        'secret': okx_secret,
                        'password': okx_passphrase,
                        'enableRateLimit': True,
                        'options': {
                            'defaultType': 'swap',
                            'adjustForTimeDifference': True
                        }
                    })
                    
                    # Configure the client
                    self._okx_client.load_markets()
                    print("Markets loaded")
                    
                    # Test connection with basic account info
                    print("Testing connection...")
                    balance = self._okx_client.fetch_balance()
                    print(f"Connection test successful: {balance is not None}")
                    
                    print("Successfully initialized OKX client")
                except Exception as e:
                    print(f"Error initializing OKX client: {str(e)}")
                    print(f"Error type: {type(e)}")
                    self._okx_client = None
            else:
                print("Missing OKX credentials - skipping initialization")

            # Initialize Binance
            binance_creds = credentials.get('binance', {})
            binance_api_key = binance_creds.get('api_key') or st.secrets.get("BINANCE_API_KEY", "")
            binance_secret = binance_creds.get('secret') or st.secrets.get("BINANCE_SECRET", "")

            print("\nInitializing Binance...")
            print(f"\033[91mAPI Key present: {bool(binance_api_key)}\033[0m" if not binance_api_key else f"\033[92mAPI Key present: {binance_api_key}\033[0m")
            print(f"\033[91mSecret present: {bool(binance_secret)}\033[0m" if not binance_secret else f"\033[92mSecret present: {binance_secret}\033[0m")

            if binance_api_key and binance_secret:
                try:
                    print("Initializing Binance client...")
                    self.binance_client = ccxt.binance({
                        'apiKey': binance_api_key,
                        'secret': binance_secret,
                        'enableRateLimit': True,
                        'options': {
                            'defaultType': 'future'
                        }
                    })
                    # Test connection
                    self.test_binance_connection()
                    print("Successfully connected to Binance")
                except Exception as e:
                    print(f"Error initializing Binance client: {str(e)}")
                    self.binance_client = None

            # Initialize Bybit
            bybit_creds = credentials.get('bybit', {})
            bybit_api_key = bybit_creds.get('api_key') or st.secrets.get("BYBIT_API_KEY", "")
            bybit_secret = bybit_creds.get('secret') or st.secrets.get("BYBIT_SECRET", "")

            print("\nInitializing Bybit...")
            print(f"\033[91mAPI Key present: {bool(bybit_api_key)}\033[0m" if not bybit_api_key else f"\033[92mAPI Key present: {bybit_api_key}\033[0m")
            print(f"\033[91mSecret present: {bool(bybit_secret)}\033[0m" if not bybit_secret else f"\033[92mSecret present: {bybit_secret}\033[0m")

            if bybit_api_key and bybit_secret:
                try:
                    print("Initializing Bybit client...")
                    self.bybit_client = HTTP(
                        testnet=False,
                        api_key=bybit_api_key,
                        api_secret=bybit_secret
                    )
                    # Test connection
                    self.bybit_client.get_wallet_balance(accountType="UNIFIED")
                    print("Successfully connected to Bybit")
                except Exception as e:
                    print(f"Error initializing Bybit client: {str(e)}")
                    self.bybit_client = None
        finally:
            print("\nExchange initialization complete:")
            print(f"\033[92mBinance client status: Initialized\033[0m" if self.binance_client else f"\033[91mBinance client status: Not initialized\033[0m")
            print(f"\033[92mBybit client status: Initialized\033[0m" if self.bybit_client else f"\033[91mBybit client status: Not initialized\033[0m")
            print(f"\033[92mOKX client status: Initialized\033[0m" if self._okx_client else f"\033[91mOKX client status: Not initialized\033[0m")
            print(f"\033[92mRabbitX client status: Initialized\033[0m" if self.rabbitx_client else f"\033[91mRabbitX client status: Not initialized\033[0m")
            print(f"\033[92mHyperliquid client status: Initialized\033[0m" if self._hyperliquid_api_key and self._hyperliquid_secret else f"\033[91mHyperliquid client status: Not initialized\033[0m")

    def __del__(self):
        """Clean up resources when the instance is destroyed"""
        if self._rabbitx_session:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._rabbitx_session.close())
            loop.close()
        if self._binance_client:
            if hasattr(self._binance_client, 'close'):
                try:
                    self._binance_client.close()
                except Exception as e:
                    print(f"Error closing Binance client: {e}")
        if self._bybit_client:
            if hasattr(self._bybit_client, 'close'):
                try:
                    self._bybit_client.close()
                except Exception as e:
                    print(f"Error closing Bybit client: {e}")
        if self._okx_client:
            if hasattr(self._okx_client, 'close'):
                try:
                    self._okx_client.close()
                except Exception as e:
                    print(f"Error closing OKX client: {e}")

    @st.cache_data(ttl=60)
    def test_hyperliquid_connection(_self):
        """Test connection to Hyperliquid."""
        try:
            print("\nTesting Hyperliquid connection...")
            print(f"API Key (wallet address): {_self._hyperliquid_api_key}")
            print(f"Private key present: {bool(_self._hyperliquid_secret)}")
            
            if not _self._hyperliquid_api_key or not _self._hyperliquid_secret:
                print("Missing Hyperliquid credentials")
                return False
            
            # Test connection by getting account info
            response = _self._make_hyperliquid_request(
                '/info',
                method='POST',
                data={
                    "type": "clearinghouseState",
                    "user": _self._hyperliquid_api_key
                }
            )
            
            print(f"Hyperliquid test connection response: {json.dumps(response, indent=2)}")
            
            if response and isinstance(response, dict):
                print("Successfully connected to Hyperliquid")
                return True
            return False
        except Exception as e:
            print(f"Error connecting to Hyperliquid: {str(e)}")
            return False

    @st.cache_data(ttl=60)
    def test_binance_connection(_self):
        """Test connection to Binance."""
        try:
            print("Testing Binance connection...")
            if not _self.binance_client:
                return False
            # Test connection by getting account info
            account_info = _self.binance_client.fetch_balance()
            print("Successfully connected to Binance")
            return True
        except Exception as e:
            print(f"Error connecting to Binance: {str(e)}")
            return False

    @st.cache_data(ttl=60)
    def test_okx_connection(_self):
        """Test connection to OKX."""
        try:
            print("Testing OKX connection...")
            if not _self._okx_client:
                print("OKX client not initialized")
                return False
            # Test connection by getting account info and print the response
            response = _self._okx_client.fetch_balance()
            print(f"OKX test connection response: {response}")
            if response:
                print("Successfully connected to OKX")
                return True
            return False
        except Exception as e:
            print(f"Error connecting to OKX: {str(e)}")
            return False

    @st.cache_data(ttl=60)
    def get_okx_balance(_self):
        """Get OKX account balance."""
        try:
            if not _self._okx_client:
                return 0.0
            response = _self._okx_client.fetch_balance()
            if response:
                total_equity = float(response.get('total', {}).get('USDT', 0))
                return total_equity
            return 0.0
        except Exception as e:
            print(f"Error in OKX balance fetch: {str(e)}")
            return 0.0

    @st.cache_data(ttl=60)
    def get_binance_balance(_self):
        """Get Binance account balance."""
        try:
            if not _self.binance_client:
                return 0.0
            account_info = _self.binance_client.fetch_balance()
            usdt_balance = account_info.get('USDT', {}).get('total', 0.0)
            return usdt_balance
        except Exception as e:
            print(f"Error in Binance balance fetch: {str(e)}")
            return 0.0

    @st.cache_data(ttl=60)
    def get_usdt_balance(_self, exchange_name: str) -> float:
        """Get current USDT balance for an exchange"""
        try:
            if exchange_name == 'binance':
                if not _self.binance_client:
                    return 0.0
                try:
                    account_info = _self.binance_client.fapiPrivateGetAccount()
                    for balance in account_info.get('assets', []):
                        balance_data = cast(Dict[str, Any], balance)
                        if balance_data.get('asset') == 'USDT':
                            balance_value = float(balance_data.get('walletBalance', 0))
                            _self.db_manager.record_balance(exchange_name, balance_value)
                            return balance_value
                    return 0.0
                except Exception as e:
                    print(f"Error fetching Binance USDT balance: {str(e)}")
                    return 0.0

            elif exchange_name == 'bybit':
                if not _self.bybit_client:
                    return 0.0
                try:
                    response = _self.bybit_client.get_wallet_balance(accountType="UNIFIED")
                    if response and isinstance(response, dict):
                        result = cast(Dict[str, Any], response.get('result', {}))
                        balance_list = result.get('list', [{}])
                        if balance_list:
                            balance_data = cast(Dict[str, Any], balance_list[0])
                            balance = float(balance_data.get('walletBalance', 0))
                            _self.db_manager.record_balance(exchange_name, balance)
                            return balance
                    return 0.0
                except Exception as e:
                    print(f"Error fetching Bybit USDT balance: {str(e)}")
                    return 0.0

            return 0.0
        except Exception as e:
            print(f"Error getting USDT balance for {exchange_name}: {str(e)}")
            return 0.0

    @st.cache_data(ttl=60)
    def get_positions(_self, exchange: str) -> List[Dict[str, Any]]:
        """Get positions from the specified exchange"""
        try:
            if exchange == 'hyperliquid':
                print("Fetching Hyperliquid positions...")
                try:
                    # Get positions from Hyperliquid API using POST request
                    response = _self._make_hyperliquid_request(
                        '/info',
                        method='POST',
                        data={
                            "type": "clearinghouseState",
                            "user": _self._hyperliquid_api_key
                        }
                    )
                    
                    print(f"Hyperliquid position response: {response}")
                    
                    positions: List[Dict[str, Any]] = []
                    if response and isinstance(response, dict):
                        # Process positions from clearinghouse state
                        all_positions = response.get('assetPositions', [])
                        for pos in all_positions:
                            try:
                                position_info = pos.get('position', {})
                                size = float(position_info.get('szi', 0))
                                if size != 0:  # Only include non-zero positions
                                    coin = position_info.get('coin', '')
                                    position_value = float(position_info.get('positionValue', 0))
                                    # Calculate current price from position value and size
                                    current_price = abs(position_value / size) if size != 0 else 0
                                    entry_price = float(position_info.get('entryPx', current_price))
                                    
                                    positions.append({
                                        'symbol': coin,
                                        'raw_symbol': coin,
                                        'size': size,
                                        'side': 'long' if size > 0 else 'short',
                                        'entry_price': entry_price,
                                        'current_price': current_price,
                                        'pnl': float(position_info.get('unrealizedPnl', 0)),
                                        'exchange': 'hyperliquid',
                                        'leverage': float(position_info.get('leverage', {}).get('value', 1.0)),
                                        'margin_mode': 'cross'
                                    })
                            except (ValueError, TypeError) as e:
                                print(f"Error processing position: {e}")
                                continue
                    
                    print(f"Processed Hyperliquid positions: {positions}")
                    return positions
                    
                except Exception as e:
                    print(f"Error fetching Hyperliquid positions: {str(e)}")
                    return []

            elif exchange == 'okx':
                print(f"Attempting to fetch OKX positions...")
                if not _self._okx_client:
                    print("OKX client is not initialized")
                    return []
                try:
                    # Use the new /api/v5/account/positions endpoint
                    print("Calling OKX positions API...")
                    response = _self._okx_client.fetch_positions()  # Changed to use CCXT's unified method
                    print(f"OKX API Response: {response}")
                    
                    # Get contract multipliers for OKX markets
                    contract_multipliers = _self._get_okx_contract_multipliers()
                    
                    if response:
                        positions = []
                        for pos in response:
                            if float(pos['contracts'] if 'contracts' in pos else pos.get('info', {}).get('pos', 0)) != 0:
                                try:
                                    # Get the raw symbol and normalized symbol
                                    raw_symbol = pos['symbol']
                                    normalized_symbol = _self.data_processor.normalize_symbol(raw_symbol.split(':')[0])
                                    
                                    # Get contract multiplier for this symbol (default to 1.0 if not found)
                                    contract_multiplier = contract_multipliers.get(raw_symbol, 1.0)
                                    
                                    # Get position size in contracts
                                    contracts = float(pos['contracts'] if 'contracts' in pos else pos['info']['pos'])
                                    
                                    # Apply contract multiplier to get accurate token amount
                                    adjusted_size = contracts * contract_multiplier
                                    
                                    positions.append({
                                        'exchange': exchange,
                                        'symbol': normalized_symbol,
                                        'raw_symbol': raw_symbol,
                                        'size': adjusted_size,  # Use adjusted size with contract multiplier
                                        'side': 'long' if (pos['side'] if 'side' in pos else pos['info']['posSide']).lower() == 'long' else 'short',
                                        'entry_price': float(pos['entryPrice'] if 'entryPrice' in pos else pos['info']['avgPx']),
                                        'current_price': float(pos['markPrice'] if 'markPrice' in pos else pos['info']['markPx']),
                                        'leverage': float(pos['leverage'] if 'leverage' in pos else pos['info']['lever']),
                                        'unrealized_pnl': float(pos['unrealizedPnl'] if 'unrealizedPnl' in pos else pos['info']['upl']),
                                        'margin_mode': (pos['marginMode'] if 'marginMode' in pos else pos['info'].get('mgnMode', 'cross')).lower(),
                                        'pnl': float(pos['unrealizedPnl'] if 'unrealizedPnl' in pos else pos['info']['upl']),
                                        'contract_multiplier': contract_multiplier  # Store the contract multiplier for reference
                                    })
                                except Exception as e:
                                    print(f"Error processing position: {str(e)}")
                                    print(f"Position data: {pos}")
                        print(f"Processed {len(positions)} OKX positions")
                        return positions
                    print("No response from OKX API")
                    return []
                except Exception as e:
                    print(f"Error fetching OKX positions: {str(e)}")
                    print(f"OKX client state: {_self._okx_client}")
                    return []

            elif exchange == 'bybit':
                if not _self.bybit_client:
                    return []
                try:
                    response = _self.bybit_client.get_positions(
                        category="linear",
                        settleCoin="USDT"
                    )
                    if response and 'result' in response and 'list' in response['result']:
                        positions = response['result']['list']
                        return [
                            {
                                'exchange': exchange,
                                'symbol': _self.data_processor.normalize_symbol(pos['symbol']),
                                'raw_symbol': pos['symbol'],
                                'size': float(pos['size']),
                                'side': 'long' if pos['side'].lower() == 'buy' else 'short',
                                'entry_price': float(pos['avgPrice'] if 'avgPrice' in pos else pos['entryPrice']),
                                'current_price': float(pos['markPrice']),
                                'leverage': float(pos['leverage']),
                                'unrealized_pnl': float(pos['unrealisedPnl']),
                                'margin_mode': pos.get('marginMode', 'cross').lower(),
                                'pnl': float(pos['unrealisedPnl'])
                            }
                            for pos in positions if float(pos['size']) > 0
                        ]
                except Exception as e:
                    print(f"Error fetching Bybit positions: {str(e)}")
                    return []
                    
            elif exchange == 'binance':
                if not _self.binance_client:
                    return []
                try:
                    _self.binance_client.options['defaultType'] = 'future'
                    raw_positions = _self.binance_client.fetch_positions()
                    
                    positions = []
                    for pos in raw_positions:
                        if float(pos['info']['positionAmt']) != 0:
                            side = 'short' if float(pos['info']['positionAmt']) < 0 else 'long'
                            size = abs(float(pos['info']['positionAmt']))
                            raw_symbol = pos['symbol']
                            positions.append({
                                'exchange': 'binance',
                                'symbol': _self.data_processor.normalize_symbol(raw_symbol),
                                'raw_symbol': raw_symbol,
                                'size': size,
                                'side': side,
                                'entry_price': float(pos['entryPrice']),
                                'current_price': float(pos['markPrice']),
                                'leverage': 1.0,
                                'unrealized_pnl': float(pos['unrealizedPnl']),
                                'margin_mode': pos['marginMode'],
                                'pnl': float(pos['unrealizedPnl'])
                            })
                    return positions
                    
                except Exception as e:
                    print(f"Error fetching Binance positions: {str(e)}")
                    return []
            elif exchange == 'rabbitx':
                if not _self.rabbitx_client:
                    return []
                try:
                    raw_positions = _self.rabbitx_client.positions.list()
                    print(f"\033[92mRabbitX positions: {raw_positions}\033[0m")
                    
                    positions = []
                    for pos in raw_positions:
                        if float(pos['size']) > 0:
                            side = 'long' if pos['side'].lower() == 'buy' else 'short'
                            positions.append({
                                'exchange': 'rabbitx',
                                'symbol': _self.data_processor.normalize_symbol(pos['market_id']),
                                'raw_symbol': pos['market_id'],
                                'size': float(pos['size']),
                                'side': side,
                                'entry_price': float(pos['entry_price']),
                                'current_price': float(pos['fair_price']),
                                'leverage': 1.0,
                                'unrealized_pnl': float(pos['unrealized_pnl']),
                                'margin_mode': 'cross',
                                'pnl': float(pos['unrealized_pnl'])
                            })
                    return positions
                    
                except Exception as e:
                    print(f"Error fetching RabbitX positions: {str(e)}")
                    return []
            return []
        except Exception as e:
            print(f"Error in get_positions: {str(e)}")
            return []

    @st.cache_data(ttl=300)
    def get_funding_rate_history(_self, exchange: str, symbol: str, days: int = 7) -> pd.DataFrame:
        """Get funding rate history for a symbol from the specified exchange"""
        try:
            if exchange == 'hyperliquid':
                print(f"Fetching Hyperliquid funding rates for {symbol}")
                try:
                    # Calculate start time based on days parameter
                    start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
                    end_time = int(datetime.now().timestamp() * 1000)
                    
                    # For Hyperliquid, use the symbol directly without modification
                    response = _self._make_hyperliquid_request(
                        '/info',
                        method='POST',
                        data={
                            "type": "fundingHistory",
                            "coin": symbol,  # Use symbol directly without modification
                            "startTime": start_time,
                            "endTime": end_time
                        }
                    )
                    
                    print(f"Hyperliquid funding rate response: {response}")
                    
                    if response and isinstance(response, list):
                        rates_data = []
                        for rate in response:
                            try:
                                rates_data.append({
                                    'fundingTime': pd.to_datetime(int(rate.get('time', 0)), unit='ms'),
                                    'fundingRate': float(rate.get('fundingRate', 0)),
                                    'symbol': symbol  # Keep original symbol
                                })
                            except (ValueError, TypeError) as e:
                                print(f"Error processing funding rate entry: {e}")
                                continue
                        
                        if rates_data:
                            df = pd.DataFrame(rates_data)
                            df = df.sort_values('fundingTime')
                            return df
                        
                    return pd.DataFrame([],columns=['fundingTime', 'fundingRate', 'symbol'])
                    
                except Exception as e:
                    print(f"Error fetching Hyperliquid funding rates for {symbol}: {str(e)}")
                    return pd.DataFrame([],columns=['fundingTime', 'fundingRate', 'symbol'])

            elif exchange == 'okx':
                if not _self._okx_client:
                    return pd.DataFrame()
                try:
                    since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
                    
                    # Format symbol for OKX - ensure it's in TOKEN-USDT-SWAP format
                    if not symbol.endswith('-USDT-SWAP'):
                        # Handle different input formats
                        if '/' in symbol:
                            base = symbol.split('/')[0]
                        elif ':' in symbol:
                            base = symbol.split(':')[0]
                        elif '-' in symbol:
                            base = symbol.split('-')[0]
                        else:
                            base = symbol
                        okx_symbol = f"{base}-USDT-SWAP"
                    else:
                        okx_symbol = symbol
                    
                    print(f"Fetching OKX funding rates for {okx_symbol}")
                    funding_rates = _self._okx_client.fetch_funding_rate_history(okx_symbol, since)
                    
                    if funding_rates:
                        formatted_rates = []
                        for rate in funding_rates:
                            formatted_rates.append({
                                'symbol': _self.data_processor.normalize_symbol(rate['symbol'].split(':')[0]),
                                'fundingRate': rate['fundingRate'],
                                'fundingTime': rate['timestamp']
                            })
                        
                        df = pd.DataFrame(formatted_rates)
                        if not df.empty:
                            df['fundingRate'] = df['fundingRate'].astype(float)
                            df['fundingTime'] = pd.to_datetime(df['fundingTime'], unit='ms')
                            return df[['fundingTime', 'fundingRate', 'symbol']]
                except Exception as e:
                    print(f"Error fetching OKX funding rates for {symbol}: {str(e)}")
                    return pd.DataFrame()

            elif exchange == 'bybit':
                if not _self.bybit_client:
                    return pd.DataFrame()
                try:
                    end_time = int(datetime.now().timestamp() * 1000)
                    start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
                    
                    bybit_symbol = symbol.replace('/', '').replace(':', '')
                    if bybit_symbol.endswith('USDT'):
                        bybit_symbol = bybit_symbol[:-4] + 'USDT'
                    
                    response = _self.bybit_client.get_funding_rate_history(
                        category="linear",
                        symbol=bybit_symbol,
                        startTime=start_time,
                        endTime=end_time,
                        limit=200
                    )
                    
                    if response and 'result' in response and 'list' in response['result']:
                        funding_rates = response['result']['list']
                        df = pd.DataFrame(funding_rates)
                        if not df.empty:
                            df['fundingRate'] = df['fundingRate'].astype(float)
                            df['fundingRateTimestamp'] = pd.to_datetime(df['fundingRateTimestamp'].astype(int), unit='ms')
                            return df
                except Exception as e:
                    print(f"Error fetching Bybit funding rates: {str(e)}")
                    return pd.DataFrame()
                    
            elif exchange == 'binance':
                if not _self.binance_client:
                    return pd.DataFrame()
                try:
                    since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
                    _self.binance_client.options['defaultType'] = 'future'
                    
                    clean_symbol = symbol
                    if ':USDT' in clean_symbol:
                        clean_symbol = clean_symbol.split(':')[0]
                    
                    try:
                        funding_rates = _self.binance_client.fetch_funding_rate_history(clean_symbol, since)
                        
                        formatted_rates = []
                        for rate in funding_rates:
                            formatted_rates.append({
                                'symbol': rate['symbol'],
                                'fundingRate': rate['fundingRate'],
                                'fundingTime': rate['timestamp']
                            })
                        
                        df = pd.DataFrame(formatted_rates)
                        if not df.empty:
                            df['fundingRate'] = df['fundingRate'].astype(float)
                            df['fundingTime'] = pd.to_datetime(df['fundingTime'], unit='ms')
                            return df[['fundingTime', 'fundingRate', 'symbol']]
                    except Exception as e:
                        print(f"Error fetching Binance funding rates for {clean_symbol}: {str(e)}")
                        return pd.DataFrame()
                except Exception as e:
                    print(f"Error in Binance funding rate history: {str(e)}")
                    return pd.DataFrame()
            
            return pd.DataFrame()
        except Exception as e:
            print(f"Error getting funding rates for {exchange}: {str(e)}")
            return pd.DataFrame()

    @st.cache_data(ttl=300)
    def calculate_funding_payments(_self, exchange: str, days: int = 7) -> Dict[str, float]:
        """Calculate total funding payments for all open positions over the specified period"""
        try:
            positions = _self.get_positions(exchange)
            funding_payments = {}
            
            for position in positions:
                try:
                    symbol = position['raw_symbol']
                    size = position['size']
                    
                    # Format symbol correctly for each exchange
                    if exchange == 'hyperliquid':
                        # Hyperliquid symbols are already in the correct format
                        pass
                    elif exchange == 'okx':
                        # For OKX, ensure we're using the correct symbol format (TOKEN-USDT-SWAP)
                        if not symbol.endswith('-USDT-SWAP'):
                            symbol = f"{symbol}-USDT-SWAP"
                    
                    print(f"Fetching funding rates for {exchange} position: {symbol}")
                    funding_rates_df = _self.get_funding_rate_history(exchange, symbol, days)
                    # If the funding rate dataframe is empty, set funding payment as NA
                    if funding_rates_df.empty:
                        funding_payments[symbol] = float('nan')  # Use NaN to represent NA
                        print(f"No funding rate data available for {symbol}, setting payment to NA")
                        continue
                    if not funding_rates_df.empty:
                        funding_rate_col = 'fundingRate'
                        total_funding = 0.0
                        
                        for _, row in funding_rates_df.iterrows():
                            funding_rate = float(row[funding_rate_col])
                            # Calculate funding payment based on position size and direction
                            payment = size * position['current_price'] * funding_rate * (-1 if position['side'] == 'short' else 1)
                            total_funding += payment
                        
                        funding_payments[symbol] = total_funding
                        print(f"Calculated funding payment for {symbol}: {total_funding}")
                except Exception as e:
                    print(f"Error calculating funding for {symbol}: {str(e)}")
                    continue
                
            return funding_payments
        except Exception as e:
            print(f"Error calculating funding payments for {exchange}: {str(e)}")
            return {}

    def _get_hyperliquid_signature(self, timestamp: int, data: str) -> str:
        """Generate signature for Hyperliquid API requests"""
        message = f"{timestamp}{data}"
        try:
            # Remove 0x prefix if present for bytes.fromhex
            hex_secret = self._hyperliquid_secret.replace('0x', '') if self._hyperliquid_secret else ''
            if not hex_secret:
                print("Warning: Hyperliquid secret is empty")
                return ''
            
            signature = hmac.new(
                bytes.fromhex(hex_secret),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            return signature
        except Exception as e:
            print(f"Error generating Hyperliquid signature: {str(e)}")
            return ''

    def _make_hyperliquid_request(self, endpoint: str, method: str = 'GET', data: Optional[Dict[str, Any]] = None) -> Union[Dict[str, Any], List[Any]]:
        """Make authenticated request to Hyperliquid API"""
        base_url = "https://api.hyperliquid.xyz"
        url = f"{base_url}{endpoint}"
        
        timestamp = int(time.time() * 1000)
        headers = {
            'Content-Type': 'application/json',
            'X-HL-Api-Key': self._hyperliquid_api_key,
            'X-HL-Timestamp': str(timestamp)
        }
        
        json_data = json.dumps(data) if data else ''
        if self._hyperliquid_secret:
            signature = self._get_hyperliquid_signature(timestamp, json_data)
            headers['X-HL-Signature'] = signature
            print(f"\nHyperliquid API Debug:")
            print(f"URL: {url}")
            print(f"Method: {method}")
            print(f"Headers: {json.dumps(headers, indent=2)}")
            if data:
                print(f"Request Data: {json_data}")
            print(f"Generated Signature: {signature}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            else:
                print(f"Making request to {url} with data: {json_data}")
                response = requests.post(url, headers=headers, json=data)
            
            print(f"\nResponse Status: {response.status_code}")
            print(f"Response Headers: {json.dumps(dict(response.headers), indent=2)}")
            print(f"Response Body: {response.text}")
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error making Hyperliquid request: {str(e)}")
            if hasattr(e, 'response'):
                print(f"Error Response Status: {e.response.status_code}")
                print(f"Error Response Headers: {json.dumps(dict(e.response.headers), indent=2)}")
                print(f"Error Response Body: {e.response.text}")
            return {} if method == 'POST' else []

    @st.cache_data(ttl=60)
    def get_hyperliquid_balance(_self):
        """Get Hyperliquid account balance."""
        try:
            if not _self._hyperliquid_api_key or not _self._hyperliquid_secret:
                return 0.0
            
            response = _self._make_hyperliquid_request(
                '/info',
                method='POST',
                data={
                    "type": "clearinghouseState",
                    "user": _self._hyperliquid_api_key
                }
            )
            
            if response and isinstance(response, dict):
                # Extract account value from marginSummary
                margin_summary = response.get('marginSummary', {})
                total_value = float(margin_summary.get('accountValue', 0))
                _self.db_manager.record_balance('hyperliquid', total_value)
                return total_value
            return 0.0
        except Exception as e:
            print(f"Error in Hyperliquid balance fetch: {str(e)}")
            return 0.0

    def _process_positions_data(self, positions_data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Process positions data into a DataFrame"""
        if not positions_data:
            return pd.DataFrame(columns=['symbol', 'raw_symbol', 'size', 'side', 'entry_price', 'current_price', 'pnl', 'exchange', 'leverage', 'margin_mode'])
        
        df = pd.DataFrame(positions_data)
        df = df.fillna(0)  # Fill NaN values with 0
        return df

    async def _initialize_rabbitx_session(self):
        logging.info("Initializing RabbitX session")
        if not hasattr(self, '_rabbitx_session'):
            self._rabbitx_session = aiohttp.ClientSession()
            print("RabbitX session initialized")

    async def _close_rabbitx_session(self):
        logging.info("Closing RabbitX session")
        if hasattr(self, '_rabbitx_session'):
            await self._rabbitx_session.close()
            delattr(self, '_rabbitx_session')
            print("RabbitX session closed")

    def test_rabbitx_connection(self) -> str:
        """Test RabbitX API connection"""

        if not self._rabbitx_api_key or not self._rabbitx_secret:
            return "RabbitX credentials not found"
            
        try:
            # Test connection using the /v1/account endpoint
            response = self.rabbitx_client.get_account()
            if response:
                return "Successfully connected to RabbitX"
            else:
                return "Failed to connect to RabbitX"
        except Exception as e:
            return f"Error connecting to RabbitX: {str(e)}"

    def get_rabbitx_positions(self) -> List[Dict[str, Any]]:
        """Get all positions from RabbitX.
        Example response

        {
            "success": true,
            "error": "",
            "result": [
                    {'entry_price': '25532.188679245283018867924528301886794',
                    'fair_price': '24351',
                    'id': 'pos-BTC-USD-tr-7615',
                    'liquidation_price': '26027.959333211210844477010441472797217',
                    'margin': '64.53015',
                    'market_id': 'BTC-USD',
                    'notional': '1290.603',
                    'profile_id': 7615,
                    'side': 'short',
                    'size': '0.053',
                    'unrealized_pnl': '62.603000000000000000000000000000000082'}
            ]
        }"""
        try:
            response = self.rabbitx_client.get_positions()
            if response and response.get('success'):
                return response.get('result', [])
            return []
        except Exception as e:
            print(f"Error getting RabbitX positions: {e}")
            return []

    def get_rabbitx_balance(self) -> float:
        """Get RabbitX account balance.
        
        Example response
        {
            "success": true,
            "error": "",
            "result": [
            {
            'account_equity': '10000000',
            'account_leverage': '1',
            'account_margin': '1',
            'balance': '10000000',
            'cum_trading_volume': '0',
            'cum_unrealized_pnl': '0',
            'health': '1',
            'id': 13,
            'last_liq_check': 0,
            'last_update': 1670396580648597,
            'leverage': {'BTC-USD': '20', 'ETH-USD': '1', 'SOL-USD': '1'},
            'profile_type': 'trader',
            'status': 'active',
            'total_notional': '0',
            'total_order_margin': '0',
            'total_position_margin': '0',
            'wallet': '0x8481cb01Ec35d43C116C3c272Fb026e6dD465e08',
            'withdrawable_balance': '10000000'}
            ]
        }
        """
        try:
            if not self._rabbitx_api_key or not self._rabbitx_secret:
                print("RabbitX credentials not initialized")
                return 0.0
            
            response = self.rabbitx_client.get_account()
            if response:
                total_equity = float(response.get('account_equity', 0))
                self.db_manager.record_balance('rabbitx', total_equity)
                return total_equity
            return 0.0
        except Exception as e:
            print(f"Error in RabbitX balance fetch: {str(e)}")
            return 0.0

    @st.cache_data(ttl=300)
    def get_rabbitx_funding_rate_history(_self, symbol: str, days: int = 7) -> pd.DataFrame:
        """Get funding rate history from RabbitX
        Response 
        {
            market_id string               
            funding_rate string
            timestamp int64               
        }"""
        try:
            if not _self._rabbitx_api_key or not _self._rabbitx_secret:
                print("RabbitX credentials not initialized")
                return pd.DataFrame()
            
            # Calculate start and end timestamps
            end_time = int(time.time() * 1000)
            start_time = end_time - (days * 24 * 60 * 60 * 1000)
            
            # Add -PERP suffix if not present
            if not symbol.endswith('-PERP'):
                symbol = f"{symbol}-PERP"
            
            # Get funding rates
            response = _self._make_rabbitx_request('/fundingrate', params={'market_id': symbol, 'start_time': start_time, 'end_time': end_time})
            
            if response:
                rates_data = []
                for rate in response:
                    try:
                        rates_data.append({
                            'fundingTime': pd.to_datetime(int(rate.get('timestamp', 0)), unit='ms'),
                            'fundingRate': float(rate.get('rate', 0)),
                            'symbol': symbol.replace('-PERP', '')
                        })
                    except (ValueError, TypeError) as e:
                        print(f"Error processing funding rate entry: {e}")
                        continue
                
                if rates_data:
                    df = pd.DataFrame(rates_data)
                    df = df.sort_values('fundingTime')
                    return df
            
            return pd.DataFrame()
        except Exception as e:
            print(f"Error fetching RabbitX funding rates for {symbol}: {str(e)}")
            return pd.DataFrame()

    def _get_okx_contract_multipliers(self) -> Dict[str, float]:
        """Get contract multipliers for OKX markets.
        
        Returns:
            Dict[str, float]: A dictionary mapping symbol to contract multiplier.
        """
        try:
            # Load markets if the client is initialized
            if not self._okx_client:
                return {}
            
            # Load markets to get contract sizes
            markets = self._okx_client.load_markets()
            
            # Create a dictionary of symbol -> contract_size
            multipliers = {}
            for symbol, market_data in markets.items():
                if 'contractSize' in market_data and market_data['contractSize'] is not None:
                    # Store the contract size as a float
                    multipliers[symbol] = float(market_data['contractSize'])
                else:
                    # Default to 1.0 if contract size is not specified
                    multipliers[symbol] = 1.0
                
            logging.info(f"Loaded {len(multipliers)} contract multipliers for OKX")
            return multipliers
        except Exception as e:
            logging.error(f"Error loading OKX contract multipliers: {e}")
            return {}