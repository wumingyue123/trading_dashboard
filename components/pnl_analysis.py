import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Any, Optional, Tuple
from utils.exchange_client import ExchangeClient
from utils.data_processor import DataProcessor
import gc
import logging
import time
from datetime import datetime, timedelta

def get_client() -> ExchangeClient:
    """Get exchange client from session state or create a new one.
    
    Returns:
        ExchangeClient: The exchange client instance.
    """
    return st.session_state.client if 'client' in st.session_state else ExchangeClient()

def get_account_balances() -> Dict[str, float]:
    """Get current account balances for all exchanges.
    
    Returns:
        Dict[str, float]: Dictionary mapping exchange names to their current balances.
    """
    client = get_client()
    balances = {}
    
    # Get balances for each exchange
    try:
        balances['binance'] = client.get_binance_balance() or 0.0
    except Exception as e:
        st.error(f"Error fetching Binance balance: {str(e)}")
        balances['binance'] = 0.0
        
    try:
        balances['bybit'] = client.get_usdt_balance('bybit') or 0.0
    except Exception as e:
        st.error(f"Error fetching Bybit balance: {str(e)}")
        balances['bybit'] = 0.0
        
    try:
        balances['okx'] = client.get_okx_balance() or 0.0
    except Exception as e:
        st.error(f"Error fetching OKX balance: {str(e)}")
        balances['okx'] = 0.0
        
    try:
        balances['hyperliquid'] = client.get_hyperliquid_balance() or 0.0
    except Exception as e:
        st.error(f"Error fetching Hyperliquid balance: {str(e)}")
        balances['hyperliquid'] = 0.0
        
    try:
        balances['rabbitx'] = client.get_rabbitx_balance() or 0.0
    except Exception as e:
        st.error(f"Error fetching RabbitX balance: {str(e)}")
        balances['rabbitx'] = 0.0
    
    return balances

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_net_transfers(exchange: str) -> float:
    """Get net transfers (transfers in - transfers out) for centralized exchanges.
    
    Args:
        exchange: Name of the exchange.
        
    Returns:
        float: Net transfer amount (positive means more transfers in than out).
    """
    # NOTE: This would require API integration with the exchanges to get transfer history.
    # For this prototype, we'll use mock data that would be replaced with actual API calls.
    client = get_client()

    # Mock data for demonstration
    if exchange == 'binance':
        """
        Example response:
        [
        {
            "counterParty":"master",
            "email":"master@test.com",
            "type":1,  // 1 for transfer in, 2 for transfer out
            "asset":"BTC",
            "qty":"1",
            "fromAccountType":"SPOT",
            "toAccountType":"SPOT",
            "status":"SUCCESS", // status: PROCESS / SUCCESS / FAILURE
            "tranId":11798835829,
            "time":1544433325000
        },
        {
            "counterParty":"subAccount",
            "email":"sub2@test.com",
            "type":1,                                 
            "asset":"ETH",
            "qty":"2",
            "fromAccountType":"SPOT",
            "toAccountType":"COIN_FUTURE",
            "status":"SUCCESS",
            "tranId":11798829519,
            "time":1544433326000
        }
        ]"""
    # For Binance, we need to get the subaccount transfer history
    # This would be replaced with actual API calls in production
    if exchange == 'binance':
        try:
            transfers = client.binance_client.get_subaccount_transfer_history()
            # Calculate net transfers from SPOT to UM_FUTURE
            net_transfers = sum([
                float(transfer['qty']) if transfer['fromAccountType'] == 'SPOT' and transfer['toAccountType'] == 'UM_FUTURE' else
                -float(transfer['qty']) if transfer['fromAccountType'] == 'UM_FUTURE' and transfer['toAccountType'] == 'SPOT' else 0
                for transfer in transfers
            ])
            # Print the net transfers in green
            print(f"\033[92mNet transfers for Binance: ${transfers}\033[0m")
            return net_transfers
        except Exception as e:
            logging.error(f"Error fetching Binance subaccount transfers: {str(e)}")
            return 0.0

    if exchange == 'bybit':
        try:
            transfers = client.bybit_client.get_transfer_list()
            # Calculate net transfers from SPOT to UM_FUTURE
            net_transfers = sum([
                float(transfer['qty']) if transfer['type'] == 'TRANSFER_IN' else
                -float(transfer['qty']) if transfer['type'] == 'TRANSFER_OUT' else 0
            ])
            # Print the net transfers in green
            print(f"\033[91mNet transfers for Bybit: ${transfers}\033[0m")
            return net_transfers
        except Exception as e:
            logging.error(f"Error fetching Bybit subaccount transfers: {str(e)}")
            return 0.0
    # Get net subaccount transfer data for Binance
    mock_data = {
        'binance': 5000.0,  # Net $5000 transferred in
        'bybit': 3000.0,    # Net $3000 transferred in
        'okx': 2000.0       # Net $2000 transferred in
    }
    
    return mock_data.get(exchange, 0.0)

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_net_deposits(exchange: str) -> float:
    """Get net deposits (deposits - withdrawals) for decentralized exchanges.
    
    Args:
        exchange: Name of the exchange.
        
    Returns:
        float: Net deposit amount (positive means more deposits than withdrawals).
    """
    # NOTE: This would require API integration with the exchanges to get deposit/withdrawal history.
    # For this prototype, we'll use mock data that would be replaced with actual API calls.
    
    # Mock data for demonstration
    mock_data = {
        'hyperliquid': 4000.0,  # Net $4000 deposited
        'rabbitx': 2500.0       # Net $2500 deposited
    }
    
    return mock_data.get(exchange, 0.0)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_funding_payments_by_symbol(exchange: str, days: int = 30) -> Dict[str, float]:
    """Get funding payments grouped by symbol for a specific exchange.
    
    Args:
        exchange: Name of the exchange.
        days: Number of days to look back for funding payments.
        
    Returns:
        Dict[str, float]: Dictionary mapping symbols to their funding payment amounts.
    """
    client = get_client()
    
    # Set appropriate credentials based on exchange
    if exchange == 'hyperliquid':
        hyperliquid_wallet = st.session_state.exchange_credentials.get('hyperliquid', {}).get('api_key', "")
        hyperliquid_key = st.session_state.exchange_credentials.get('hyperliquid', {}).get('secret', "")
        
        if hyperliquid_wallet and hyperliquid_key:
            client._hyperliquid_api_key = hyperliquid_wallet
            client._hyperliquid_secret = hyperliquid_key
    
    elif exchange == 'rabbitx':
        rabbitx_creds = st.session_state.exchange_credentials.get('rabbitx', {})
        if rabbitx_creds:
            client._rabbitx_api_key = rabbitx_creds.get('api_key', "")
            client._rabbitx_secret = rabbitx_creds.get('secret', "")
            client._rabbitx_jwt_token = rabbitx_creds.get('jwt_token', "")
    
    # Get funding payments
    try:
        return client.calculate_funding_payments(exchange, days)
    except Exception as e:
        st.error(f"Error calculating funding payments for {exchange}: {str(e)}")
        return {}

def calculate_pnl(current_balances: Dict[str, float]) -> Tuple[Dict[str, float], float]:
    """Calculate PnL for each exchange and total PnL.
    
    Args:
        current_balances: Current account balances for each exchange.
        
    Returns:
        Tuple[Dict[str, float], float]: Dictionary of PnL per exchange and total PnL.
    """
    pnl_by_exchange = {}
    total_pnl = 0.0
    
    # Calculate PnL for centralized exchanges (current equity - net transfers)
    for exchange in ['binance', 'bybit', 'okx']:
        current_balance = current_balances.get(exchange, 0.0)
        net_transfers = get_net_transfers(exchange)
        pnl = current_balance - net_transfers
        pnl_by_exchange[exchange] = pnl
        total_pnl += pnl
    
    # Calculate PnL for decentralized exchanges (current equity - net deposits)
    for exchange in ['hyperliquid', 'rabbitx']:
        current_balance = current_balances.get(exchange, 0.0)
        net_deposits = get_net_deposits(exchange)
        pnl = current_balance - net_deposits
        pnl_by_exchange[exchange] = pnl
        total_pnl += pnl
    
    return pnl_by_exchange, total_pnl

def aggregate_funding_payments(days: int = 30) -> Tuple[Dict[str, Dict[str, float]], Dict[str, float], float]:
    """Aggregate funding payments across all exchanges by symbol.
    
    Args:
        days: Number of days to look back for funding payments.
        
    Returns:
        Tuple containing:
            - Dict[str, Dict[str, float]]: Funding payments per exchange, per symbol
            - Dict[str, float]: Total funding payments per symbol
            - float: Total funding payments across all symbols and exchanges
    """
    # Get funding payments by exchange and symbol
    funding_by_exchange = {}
    total_by_symbol = {}
    total_funding = 0.0
    
    # Get funding payments for each exchange
    for exchange in ['binance', 'bybit', 'okx', 'hyperliquid', 'rabbitx']:
        funding_payments = get_funding_payments_by_symbol(exchange, days)
        funding_by_exchange[exchange] = funding_payments
        
        # Aggregate by symbol across exchanges
        for symbol, amount in funding_payments.items():
            if symbol not in total_by_symbol:
                total_by_symbol[symbol] = 0.0
            total_by_symbol[symbol] += amount
            total_funding += amount
    
    return funding_by_exchange, total_by_symbol, total_funding

def display_pnl_analysis(days: int):
    """Display PnL analysis tab content.
    
    Args:
        days (int): Number of days to analyze
    """
    st.subheader("💰 PnL Analysis")
    
    # Get current account balances
    current_balances = get_account_balances()
    
    # Calculate PnL
    pnl_by_exchange, total_pnl = calculate_pnl(current_balances)
    
    # Get funding payments data
    funding_by_exchange, total_funding_by_symbol, total_funding = aggregate_funding_payments(days)
    
    # Display overall PnL analysis
    st.markdown("### 📊 Overall PnL Analysis")
    
    # Create metrics for overall PnL
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Total PnL",
            f"${total_pnl:,.2f}",
            help="Total profit/loss across all exchanges"
        )
    with col2:
        st.metric(
            "Total Funding",
            f"${total_funding:,.2f}",
            help="Total funding payments received/paid across all exchanges"
        )
    with col3:
        st.metric(
            "Net Trading PnL",
            f"${(total_pnl - total_funding):,.2f}",
            help="PnL attributable to trading (excluding funding)"
        )
    
    # Clean up memory
    gc.collect() 