import streamlit as st
import pandas as pd
import plotly.express as px
from utils.exchange_client import ExchangeClient
from utils.data_processor import DataProcessor
import gc
import logging
import time

# Initialize DataProcessor
data_processor = DataProcessor()

# Don't initialize client at module level - move to function
# client = st.session_state.client if 'client' in st.session_state else ExchangeClient()

# Cache the funding rate history data
@st.cache_data(ttl=300, max_entries=100)  # Cache for 5 minutes, limit entries
def get_cached_funding_history(exchange: str, symbol: str, days: int, start_time: int = None, end_time: int = None):
    """Cached wrapper for funding rate history"""
    try:
        # Get client from session state inside the function
        client = st.session_state.client if 'client' in st.session_state else ExchangeClient()
        
        # Get RabbitX credentials from session state
        rabbitx_creds = st.session_state.exchange_credentials.get('rabbitx', {})
        
        # Ensure Hyperliquid credentials are set
        if exchange == 'hyperliquid':
            hyperliquid_wallet = st.session_state.exchange_credentials.get('hyperliquid', {}).get('api_key', "")
            hyperliquid_key = st.session_state.exchange_credentials.get('hyperliquid', {}).get('secret', "")
            
            if hyperliquid_wallet and hyperliquid_key:
                client._hyperliquid_api_key = hyperliquid_wallet
                client._hyperliquid_secret = hyperliquid_key
                print(f"Set Hyperliquid credentials for funding history fetch")
        elif exchange == 'rabbitx':
            rabbitx_creds = st.session_state.exchange_credentials.get('rabbitx', {})
            client._rabbitx_api_key = rabbitx_creds.get('api_key', "")
            client._rabbitx_secret = rabbitx_creds.get('secret', "")
            client._rabbitx_jwt_token = rabbitx_creds.get('jwt_token', "")
        elif exchange == 'bybit':
            bybit_creds = st.session_state.exchange_credentials.get('bybit', {})
            client._bybit_api_key = bybit_creds.get('api_key', "")
            client._bybit_secret = bybit_creds.get('secret', "")
            
        # Ensure symbol is properly formatted for each exchange
        if exchange == 'bybit':
            # Bybit requires uppercase symbols without special characters
            symbol = symbol.upper().replace('/', '').replace(':', '')
            if not symbol.endswith('USDT'):
                symbol = f"{symbol}USDT"
            print(f"Using formatted Bybit symbol for funding history: {symbol}")
        elif exchange == 'okx':
            if not symbol.endswith('-USDT-SWAP'):
                symbol = f"{symbol}-USDT-SWAP"
            print(f"Using formatted OKX symbol for funding history: {symbol}")
            
        return client.get_funding_rate_history(exchange, symbol, days, start_time, end_time)
    except Exception as e:
        print(f"Error in get_cached_funding_history for {exchange} {symbol}: {str(e)}")
        return pd.DataFrame()

# Cache position data
@st.cache_data(ttl=60, max_entries=50)  # Cache for 1 minute, limit entries
def get_cached_positions(exchange: str):
    """Cached wrapper for positions"""
    
    # Get client from session state inside the function
    client = st.session_state.client if 'client' in st.session_state else ExchangeClient()
    
    # Ensure Hyperliquid credentials are set
    if exchange == 'hyperliquid':
        hyperliquid_wallet = st.session_state.exchange_credentials.get('hyperliquid', {}).get('api_key')
        hyperliquid_key = st.session_state.exchange_credentials.get('hyperliquid', {}).get('secret')
        # Check if Hyperliquid credentials are empty when accessing Hyperliquid exchange
        if not hyperliquid_wallet or not hyperliquid_key:
            raise ValueError("Hyperliquid credentials are missing. Please check your configuration.")
        if hyperliquid_wallet and hyperliquid_key:
            client._hyperliquid_api_key = hyperliquid_wallet
            client._hyperliquid_secret = hyperliquid_key
            print(f"Set Hyperliquid credentials for positions fetch")
            print(f"Wallet Address present: {bool(hyperliquid_wallet)}")
            print(f"Private Key present: {bool(hyperliquid_key)}")
    
    elif exchange == 'rabbitx':
        # Get RabbitX credentials from session state
        rabbitx_creds = st.session_state.exchange_credentials.get('rabbitx', {})
        # Check if RabbitX credentials are empty when accessing RabbitX exchange
        if not rabbitx_creds.get('api_key') or not rabbitx_creds.get('secret') or not rabbitx_creds.get('jwt_token'):
            raise ValueError("RabbitX credentials are missing. Please check your configuration.")
        client._rabbitx_api_key = rabbitx_creds.get('api_key', "")
        client._rabbitx_secret = rabbitx_creds.get('secret', "")
        client._rabbitx_jwt_token = rabbitx_creds.get('jwt_token', "")

    return client.get_positions(exchange)

# Cache funding payments calculation
@st.cache_data(ttl=300, max_entries=50)  # Cache for 5 minutes, limit entries
def get_cached_funding_payments(exchange: str, days: int):
    """Cached wrapper for funding payments"""
    
    # Get client from session state inside the function
    client = st.session_state.client if 'client' in st.session_state else ExchangeClient()
    
    # Ensure Hyperliquid credentials are set
    if exchange == 'hyperliquid':
        hyperliquid_wallet = st.session_state.exchange_credentials.get('hyperliquid', {}).get('api_key', "")
        hyperliquid_key = st.session_state.exchange_credentials.get('hyperliquid', {}).get('secret', "")
        
        if hyperliquid_wallet and hyperliquid_key:
            client._hyperliquid_api_key = hyperliquid_wallet
            client._hyperliquid_secret = hyperliquid_key
            print(f"Set Hyperliquid credentials for funding payments fetch")
            print(f"Wallet Address present: {bool(hyperliquid_wallet)}")
            print(f"Private Key present: {bool(hyperliquid_key)}")
    
    elif exchange == 'rabbitx':
        rabbitx_creds = st.session_state.exchange_credentials.get('rabbitx', {})
        if rabbitx_creds:
            client._rabbitx_api_key = rabbitx_creds.get('api_key', "")
            client._rabbitx_secret = rabbitx_creds.get('secret', "")
            client._rabbitx_jwt_token = rabbitx_creds.get('jwt_token', "")
            print(f"Set RabbitX credentials for funding payments fetch")
            print(f"API Key present: {bool(rabbitx_creds.get('api_key'))}")
            print(f"Secret present: {bool(rabbitx_creds.get('secret'))}")
            print(f"JWT Token present: {bool(rabbitx_creds.get('jwt_token'))}")
    
    return client.calculate_funding_payments(exchange, days)

def display_funding_rates():
    """Display funding rates and related information."""
    
    st.subheader("📊 Funding Rate Dashboard")
    
    # Add time period selector
    days = st.selectbox(
        "Select Time Period",
        options=[
            (1, "1 day"),
            (7, "7 days"),
            (14, "14 days"),
            (30, "30 days")
        ],
        index=1,  # Default to 7 days
        help="Select the number of days to calculate funding payments for",
        format_func=lambda x: x[1]  # Display the formatted string
    )[0]  # Get the actual number value
    
    # Initialize variables
    all_positions = []
    total_exposure = 0
    total_funding = 0
    daily_funding = 0
    
    # Get all historical positions and funding payments for the selected time period
    historical_positions = {}
    historical_funding_payments = {}
    funding_intervals = {}  # Store funding intervals by exchange and symbol
    all_funding_rates = []  # Store all funding rates for charts
    
    # First, get all positions and funding data
    for exchange in ['bybit', 'binance', 'okx', 'hyperliquid', 'rabbitx']:
        try:
            # Get historical positions for the time period
            positions = get_cached_positions(exchange)
            if positions:
                # Process positions in chunks
                chunk_size = 50
                for i in range(0, len(positions), chunk_size):
                    chunk = positions[i:i + chunk_size]
                    all_positions.extend(chunk)
                    
                    # Calculate metrics for this chunk
                    total_exposure += sum(abs(pos['size'] * pos['current_price']) for pos in chunk)
                    
                    # Get funding payments for this chunk
                    funding_payments = get_cached_funding_payments(exchange, days)
                    historical_funding_payments.update(funding_payments)
                    total_funding += sum(funding_payments.values())
                    
                    # Clear chunk from memory
                    del chunk
            
            # Store positions for later use
            historical_positions[exchange] = positions
            
            # Get funding intervals (using default values since get_funding_interval is not implemented)
            funding_intervals[exchange] = {
                'hyperliquid': 1,
                'bybit': 8,
                'binance': 8,
                'okx': 8,
                'rabbitx': 1
            }.get(exchange.lower(), 8)
            
            # Process funding rates for charts
            for pos in positions:
                normalized = data_processor.normalize_symbol(pos['symbol'])
                raw = pos['symbol']
                # Format symbol according to exchange requirements
                if exchange == 'okx' and not raw.endswith('-USDT-SWAP'):
                    raw = f"{normalized}-USDT-SWAP"
                elif exchange == 'bybit':
                    raw = raw.upper().replace('/', '').replace(':', '').replace('-', '')
                    if not raw.endswith('USDT'):
                        raw = f"{raw}USDT"
                elif exchange == 'binance':
                    raw = raw.upper().replace('/', '').replace(':', '')
                    if not raw.endswith('USDT'):
                        raw = f"{raw}USDT"
                
                print(f"Processing funding rates for {exchange} {raw}")
                
                # Get funding rate history
                end_time = int(time.time() * 1000)
                start_time = end_time - (days * 24 * 60 * 60 * 1000)
                
                funding_history = get_cached_funding_history(
                    exchange,
                    raw,
                    days,
                    start_time=start_time,
                    end_time=end_time
                )
                
                if not funding_history.empty:
                    print(f"Got funding history for {exchange} {normalized}: {len(funding_history)} entries")
                    
                    # Process funding history for charts
                    if 'fundingRateTimestamp' in funding_history.columns:
                        time_col = 'fundingRateTimestamp'
                    elif 'fundingTime' in funding_history.columns:
                        time_col = 'fundingTime'
                    else:
                        continue
                    
                    funding_history['symbol'] = normalized
                    
                    try:
                        if 'fundingRate' in funding_history.columns:
                            funding_history['fundingRate'] = funding_history['fundingRate'].astype(str).apply(lambda x: float(x))
                            
                            if exchange in ['bybit', 'binance']:
                                funding_history['fundingRate'] = funding_history['fundingRate'] * 100
                            
                            funding_history = funding_history.dropna(subset=['fundingRate'])
                            funding_history = funding_history[~funding_history['fundingRate'].isin([float('inf'), float('-inf')])]
                            
                            if not funding_history.empty:
                                funding_history = funding_history.sort_values([time_col], ascending=[True])
                                funding_history = funding_history[[time_col, 'fundingRate', 'symbol']]
                                all_funding_rates.append(funding_history)
                    except Exception as e:
                        print(f"Error processing funding rates for {exchange} {normalized}: {str(e)}")
                        continue
                        
        except Exception as e:
            print(f"Error fetching historical data for {exchange}: {str(e)}")
            continue

    # Display overall summary section
    st.markdown("### 📈 Overall Summary")
    
    # Key metrics in columns for overall summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Total Position Value",
            f"${total_exposure:,.2f}",
            help="Total notional value of all positions across exchanges"
        )
    with col2:
        daily_funding = total_funding / days if days > 0 else 0
        st.metric(
            f"Total Funding ({days}d)",
            f"${total_funding:,.2f}",
            f"${daily_funding:,.2f}/day",
            help="Total funding payments received/paid across exchanges"
        )
    with col3:
        st.metric(
            "Active Positions",
            len(all_positions),
            help="Number of active positions across all exchanges"
        )

    # Display per-token metrics including historical positions
    token_metrics = []
    processed_symbols = set()  # Track symbols we've processed
    
    # First process current positions
    for pos in all_positions:
        symbol = pos['symbol']
        exchange = pos['exchange'].lower()
        processed_symbols.add(symbol)  # Mark this symbol as processed
        
        normalized_symbol = data_processor.normalize_symbol(symbol)
        notional_size = abs(pos['size'] * pos['current_price'])
        raw_funding_pnl = historical_funding_payments.get(symbol, 0)  # Get historical funding PnL
        
        # Get funding interval from our collected data
        funding_interval = funding_intervals.get(exchange, 8)  # Default to 8h if not found
        
        # Normalize funding PnL to 8h intervals for fair comparison
        normalized_funding_pnl = raw_funding_pnl
        if funding_interval != 8:
            # If interval is shorter, we need to adjust the PnL to what it would be at 8h intervals
            normalization_factor = 8 / funding_interval
            normalized_funding_pnl = raw_funding_pnl / normalization_factor
        
        # Calculate APY based on normalized 8h funding
        if normalized_funding_pnl != 0 and notional_size != 0:
            # Calculate periods per year (using 8h as standard interval)
            periods_per_year = (365 * 24) / 8  # Number of 8h periods in a year
            # Calculate APY using the normalized funding PnL
            funding_apy = (normalized_funding_pnl / notional_size * (periods_per_year / (days * 24 / 8))) * 100
        else:
            funding_apy = 0
        
        token_metrics.append({
            'symbol': normalized_symbol,
            'exchange': exchange,
            'notional_size': notional_size,
            'raw_funding_pnl': raw_funding_pnl,
            'normalized_funding_pnl': normalized_funding_pnl,
            'funding_interval': f"{funding_interval}h",
            'funding_apy': funding_apy,
            'side': pos['side'].upper(),
            'status': 'ACTIVE'
        })
    
    # Now process historical positions that aren't currently active
    for exchange, positions in historical_positions.items():
        if not isinstance(positions, list):
            continue
            
        for pos in positions:
            symbol = pos['symbol']
            if symbol not in processed_symbols:  # Only process if we haven't already
                normalized_symbol = data_processor.normalize_symbol(symbol)
                notional_size = abs(pos['size'] * pos['current_price'])
                raw_funding_pnl = historical_funding_payments.get(symbol, 0)
                
                # Get funding interval from our collected data
                funding_interval = funding_intervals.get(exchange, 8)  # Default to 8h if not found
                
                # Normalize funding PnL
                normalized_funding_pnl = raw_funding_pnl
                if funding_interval != 8:
                    normalization_factor = 8 / funding_interval
                    normalized_funding_pnl = raw_funding_pnl / normalization_factor
                
                # Calculate APY (using the last known position size)
                if normalized_funding_pnl != 0 and notional_size != 0:
                    periods_per_year = (365 * 24) / 8
                    funding_apy = (normalized_funding_pnl / notional_size * (periods_per_year / (days * 24 / 8))) * 100
                else:
                    funding_apy = 0
                
                token_metrics.append({
                    'symbol': normalized_symbol,
                    'exchange': exchange,
                    'notional_size': notional_size,
                    'raw_funding_pnl': raw_funding_pnl,
                    'normalized_funding_pnl': normalized_funding_pnl,
                    'funding_interval': f"{funding_interval}h",
                    'funding_apy': funding_apy,
                    'side': pos['side'].upper(),
                    'status': 'CLOSED'
                })
                processed_symbols.add(symbol)  # Mark as processed

    # Display funding rate charts
    if all_funding_rates:
        for exchange in ['bybit', 'binance', 'okx', 'hyperliquid', 'rabbitx']:
            exchange_rates = [df for df in all_funding_rates if any(df['symbol'].str.contains(exchange))]
            if exchange_rates:
                try:
                    combined_df = pd.concat(exchange_rates, ignore_index=True)
                    time_col = 'fundingRateTimestamp' if 'fundingRateTimestamp' in combined_df.columns else 'fundingTime'
                    
                    # Ensure timestamp is in correct format
                    if pd.api.types.is_numeric_dtype(combined_df[time_col]):
                        combined_df[time_col] = pd.to_datetime(combined_df[time_col], unit='ms')
                    
                    fig = px.scatter(
                        combined_df,
                        x=time_col,
                        y='fundingRate',
                        color='symbol',
                        title=f'Funding Rates History - {exchange.capitalize()}',
                        labels={
                            time_col: 'Time',
                            'fundingRate': 'Funding Rate (%)',
                            'symbol': 'Token'
                        }
                    )
                    
                    fig.update_layout(
                        xaxis_title='Time',
                        yaxis_title='Funding Rate (%)',
                        legend_title='Token',
                        hovermode='x unified',
                        height=400,
                        showlegend=True
                    )
                    
                    fig.update_traces(mode='lines+markers')
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    print(f"Error creating chart for {exchange}: {str(e)}")
                    st.error(f"Error creating funding rate chart for {exchange}: {str(e)}")

    # Display metrics tables
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🔝 Top Positions by Size")
        top_size_df = pd.DataFrame([{
            'Token': t['symbol'],
            'Exchange': t['exchange'].capitalize(),
            'Side': t['side'],
            'Size': f"${t['notional_size']:,.0f}",
            'Interval': t['funding_interval'],
            'Status': t['status']
        } for t in sorted(token_metrics, key=lambda x: abs(x['notional_size']), reverse=True)[:5]])
        st.dataframe(top_size_df, hide_index=True, use_container_width=True)
    
    with col2:
        st.markdown("#### 💰 Top Funding Earners (8h Normalized)")
        top_funding_df = pd.DataFrame([{
            'Token': t['symbol'],
            'Exchange': t['exchange'].capitalize(),
            'Raw PnL': f"${t['raw_funding_pnl']:,.2f}",
            'Norm. PnL (8h)': f"${t['normalized_funding_pnl']:,.2f}",
            'APY': f"{t['funding_apy']:,.2f}%",
            'Interval': t['funding_interval'],
            'Status': t['status']
        } for t in sorted(token_metrics, key=lambda x: x['normalized_funding_pnl'], reverse=True)[:5]])
        st.dataframe(top_funding_df, hide_index=True, use_container_width=True)

    # Clear memory
    del historical_positions
    del historical_funding_payments
    del funding_intervals
    del all_funding_rates
    gc.collect() 