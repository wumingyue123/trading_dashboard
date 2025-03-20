import streamlit as st
from components.funding_rates_updated import display_funding_rates
from components.pnl_analysis import display_pnl_analysis
from utils.exchange_client import ExchangeClient
import gc
import time
import os
import pandas as pd
from datetime import datetime, timedelta
from components.positions import render_positions_table
import plotly.express as px
import asyncio
import logging

# Set page config
st.set_page_config(
    page_title="Crypto Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add custom CSS for better UI
st.markdown("""
<style>
    /* Main title */
    .main-title {
        font-size: 2rem !important;
        padding-bottom: 0.5rem;
    }
    
    /* Section headers */
    h2 {
        font-size: 1.5rem !important;
        padding-top: 1rem !important;
        padding-bottom: 0.5rem !important;
    }
    
    h3 {
        font-size: 1.2rem !important;
        padding-top: 0.8rem !important;
        padding-bottom: 0.3rem !important;
    }
    
    /* Metric containers */
    [data-testid="stMetricValue"] {
        font-size: 1.1rem !important;
    }
    
    [data-testid="stMetricDelta"] {
        font-size: 0.8rem !important;
    }
    
    /* Tables */
    .dataframe {
        font-size: 0.9rem !important;
    }
    
    /* Reduce spacing between elements */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 1rem !important;
    }
    
    /* Exchange sections */
    .exchange-section {
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 0.5rem;
    }
    
    .exchange-section h3 {
        margin-top: 0 !important;
    }
    
    /* Dividers */
    hr {
        margin: 0.5rem 0 !important;
    }
    
    /* Sidebar */
    .css-1d391kg {
        padding-top: 1rem !important;
    }
    
    /* Metric labels */
    .metric-label {
        font-size: 0.8rem !important;
        color: #888;
    }
    
    /* Make tables more compact */
    .stDataFrame {
        font-size: 0.9rem !important;
    }
    
    div[data-testid="stDataFrameResizable"] {
        font-size: 0.9rem !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize exchange client
@st.cache_resource(ttl=3600)  # Cache for 1 hour
def get_exchange_client():
    """Get a cached instance of the ExchangeClient with credentials from Streamlit secrets.

    Returns:
        ExchangeClient: An initialized exchange client instance.
    """
    return ExchangeClient()

# Clean up old resources before creating new ones
if 'client' in st.session_state:
    del st.session_state.client

# Force garbage collection
gc.collect()

print('session secrets', st.secrets)

# Clear session state for credentials
if 'exchange_credentials' in st.session_state:
    del st.session_state.exchange_credentials

# Initialize session state for credentials if not exists
if 'exchange_credentials' not in st.session_state:
    print("Checking credentials")
    print(st.secrets)
    # Load credentials from secrets
    hyperliquid_wallet = st.secrets.get("HYPERLIQUID_API_KEY")
    hyperliquid_key = st.secrets.get("HYPERLIQUID_SECRET_KEY")

    # Extract credentials for each exchange
    binance_api_key = st.secrets.get("BINANCE_API_KEY")
    binance_secret = st.secrets.get("BINANCE_SECRET")
    
    bybit_api_key = st.secrets.get("BYBIT_API_KEY")
    bybit_secret = st.secrets.get("BYBIT_SECRET")
    
    okx_api_key = st.secrets.get("OKX_API_KEY")
    okx_secret = st.secrets.get("OKX_SECRET")
    okx_password = st.secrets.get("OKX_PASSWORD")
    
    rabbitx_api_key = st.secrets.get("RABBITX_API_KEY")
    rabbitx_secret = st.secrets.get("RABBITX_SECRET_KEY")
    rabbitx_jwt_token = st.secrets.get("RABBITX_JWT_TOKEN")

    # Log credential status without printing actual values
    print(f"Loading Binance credentials:")
    print(f"API Key present: {bool(binance_api_key)}")
    print(f"Secret present: {bool(binance_secret)}")
    
    print(f"Loading Bybit credentials:")
    print(f"API Key present: {bool(bybit_api_key)}")
    print(f"Secret present: {bool(bybit_secret)}")
    
    print(f"Loading OKX credentials:")
    print(f"API Key present: {bool(okx_api_key)}")
    print(f"Secret present: {bool(okx_secret)}")
    print(f"Password present: {bool(okx_password)}")
    
    print(f"Loading RabbitX credentials:")
    print(f"API Key present: {bool(rabbitx_api_key)}")
    print(f"Secret present: {bool(rabbitx_secret)}")
    print(f"JWT Token present: {bool(rabbitx_jwt_token)}")
    
    print(f"Loading Hyperliquid credentials:")
    print(f"Wallet Address present: {bool(hyperliquid_wallet)}")
    print(f"Private Key present: {bool(hyperliquid_key)}")
    
    # Check if any credentials are missing
    if not binance_api_key or not binance_secret:
        raise ValueError("Binance credentials are missing. Please check your configuration.")
    if not bybit_api_key or not bybit_secret:
        raise ValueError("Bybit credentials are missing. Please check your configuration.")
    if not okx_api_key or not okx_secret or not okx_password:
        raise ValueError("OKX credentials are missing. Please check your configuration.")
    if not hyperliquid_wallet or not hyperliquid_key:
        raise ValueError("Hyperliquid credentials are missing. Please check your configuration.")
    if not rabbitx_api_key or not rabbitx_secret or not rabbitx_jwt_token:
        raise ValueError("RabbitX credentials are missing. Please check your configuration.")
    
    st.session_state.exchange_credentials = {
        'binance': {
            'api_key': binance_api_key,
            'secret': binance_secret
        },
        'bybit': {
            'api_key': bybit_api_key,
            'secret': bybit_secret
        },
        'okx': {
            'api_key': okx_api_key,
            'secret': okx_secret,
            'password': okx_password
        },
        'hyperliquid': {
            'api_key': hyperliquid_wallet,
            'secret': hyperliquid_key
        },
        'rabbitx': {
            'api_key': rabbitx_api_key,
            'secret': rabbitx_secret,
            'jwt_token': rabbitx_jwt_token
        }
    }

# Configure sidebar
with st.sidebar:
    st.markdown("## 🧰 Dashboard Controls")
    
    # Exchange filters
    st.markdown("### 📊 Exchange Filters")
    selected_exchanges = st.multiselect(
        "Select Exchanges",
        ["Binance", "Bybit", "OKX", "Hyperliquid", "RabbitX"],
        default=["Binance", "Bybit", "OKX", "Hyperliquid", "RabbitX"]
    )
    
    # Time period selection (for historical data)
    st.markdown("### ⏱️ Time Settings")
    auto_refresh = st.checkbox("Auto-refresh Data", value=True)
    refresh_interval = st.select_slider(
        "Refresh Interval",
        options=[30, 60, 120, 300],
        value=60,
        format_func=lambda x: f"{x} seconds"
    )
    
    # Date range
    date_options = [
        "Last 24 hours",
        "Last 7 days",
        "Last 14 days",
        "Last 30 days",
        "Custom range"
    ]
    selected_date_range = st.selectbox("Date Range", date_options, index=1)
    
    if selected_date_range == "Custom range":
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start date", value=pd.to_datetime("today") - pd.Timedelta(days=7))
        with col2:
            end_date = st.date_input("End date", value=pd.to_datetime("today"))
    
    # Display modes
    st.markdown("### 🎨 Display Options")
    theme_mode = st.radio("Theme", ["Dark", "Light"], horizontal=True)
    display_mode = st.radio(
        "View Mode",
        ["Compact", "Detailed"],
        horizontal=True,
        help="Choose between compact or detailed view"
    )
    
    st.markdown("---")
    st.markdown(f"**Last updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Credits
    st.markdown("---")
    st.caption("© 2024 Crypto Trading Dashboard")

# Main content
st.markdown('<p class="main-title">🚀 Crypto Trading Dashboard</p>', unsafe_allow_html=True)
st.markdown('<p style="font-size: 1rem;">Analyze your crypto positions and funding rates across multiple exchanges</p>', unsafe_allow_html=True)

# Get exchange client
client = get_exchange_client()

# Store client in session state for cleanup
st.session_state.client = client

# Consolidated time period selector at the top
st.markdown("---")
days = st.selectbox(
    "Select Time Period for Analysis",
    options=[
        (1, "1 day"),
        (7, "7 days"),
        (14, "14 days"),
        (30, "30 days")
    ],
    index=1,  # Default to 7 days
    help="Select the number of days to analyze metrics and funding payments",
    format_func=lambda x: x[1]  # Display the formatted string
)[0]  # Get the actual number value

async def update_dashboard_data(client):
    # Get positions and funding data from all exchanges first
    all_positions = []
    delta_exposure = {}
    total_funding_pnl = 0
    total_position_value = 0
    total_pnl = 0
    total_delta = 0  # Initialize total_delta

    # Get trading fees
    fees_by_exchange = await client.fee_tracker.update_fees()
    total_fees = client.fee_tracker.get_total_fees()

    # Dictionary to store funding intervals by exchange and symbol
    funding_intervals = {
        'hyperliquid': 1,  # 1 hour interval
        'bybit': 8,        # 8 hour interval
        'binance': 8,      # 8 hour interval
        'okx': 8,          # 8 hour interval
        'rabbitx': 1       # 1 hour interval
    }

    for exchange in [e.lower() for e in selected_exchanges]:
        try:
            positions = client.get_positions(exchange)
            
            if positions:
                # Get funding rates and calculate funding PnL for each position
                for pos in positions:
                    pos['exchange'] = exchange
                    symbol = pos['raw_symbol']
                    
                    # Calculate position value and delta
                    position_value = abs(pos['size'] * pos['current_price'])
                    position_delta = pos['size'] * pos['current_price'] * (1 if pos['side'].lower() == 'long' else -1)
                    total_position_value += position_value
                    total_delta += position_delta  # Add to total_delta
                    
                    # Get funding rate history for this position
                    funding_history = client.get_funding_rate_history(exchange, symbol, days)
                    
                    if not funding_history.empty:
                        # Get the funding interval for this exchange
                        interval_hours = funding_intervals.get(exchange, 8)  # Default to 8 hours if not specified
                        
                        # Calculate number of funding periods in the selected time range
                        periods_in_timeframe = (days * 24) / interval_hours
                        
                        # Calculate average funding rate for the period
                        avg_funding_rate = funding_history['fundingRate'].mean()
                        
                        # Calculate funding PnL
                        # If long position: we pay negative rates and receive positive rates
                        # If short position: we pay positive rates and receive negative rates
                        position_multiplier = 1 if pos['side'].lower() == 'long' else -1
                        funding_pnl = position_value * avg_funding_rate * periods_in_timeframe * position_multiplier
                        
                        # Store funding PnL in position data
                        pos['funding_pnl'] = funding_pnl
                        total_funding_pnl += funding_pnl
                    else:
                        pos['funding_pnl'] = 0
                    
                    # Update remaining metrics
                    total_pnl += pos['pnl']
                    
                all_positions.extend(positions)
                
                # Calculate delta exposure
                for pos in positions:
                    symbol = pos['symbol']
                    delta = pos['size'] * pos['current_price'] * (1 if pos['side'].lower() == 'long' else -1)
                    
                    if symbol not in delta_exposure:
                        delta_exposure[symbol] = {
                            'total_delta': 0,
                            'exchanges': {ex.lower(): 0 for ex in selected_exchanges},
                            'funding_pnl': 0
                        }
                    
                    delta_exposure[symbol]['total_delta'] += delta
                    delta_exposure[symbol]['exchanges'][exchange] = delta
                    delta_exposure[symbol]['funding_pnl'] += pos['funding_pnl']
        except Exception as e:
            st.error(f"Error fetching {exchange} positions: {str(e)}")

    # Calculate total delta and trading PnL
    trading_pnl = total_pnl - total_funding_pnl

    return {
        'all_positions': all_positions,
        'delta_exposure': delta_exposure,
        'total_funding_pnl': total_funding_pnl,
        'total_position_value': total_position_value,
        'total_pnl': total_pnl,
        'fees_by_exchange': fees_by_exchange,
        'total_fees': total_fees,
        'total_delta': total_delta  # Include total_delta in returned data
    }

def main():
    # Initialize the client
    client = ExchangeClient()
    
    # Get dashboard data asynchronously
    dashboard_data = asyncio.run(update_dashboard_data(client))
    
    # Use the dashboard data to render the UI
    days = 30  # or however you calculate this
    
    # Display consolidated metrics at the top
    st.markdown("### 📊 Overview")

    # First row: Position Value, Total PnL, Delta Exposure
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Total Position Value",
            f"${dashboard_data['total_position_value']:,.2f}",
            help="Total notional value of all positions"
        )
    with col2:
        st.metric(
            "Total PnL",
            f"${dashboard_data['total_pnl']:,.2f}",
            help="Total profit/loss including funding"
        )
    with col3:
        st.metric(
            "Net Delta Exposure",
            f"${dashboard_data['total_delta']:,.2f}",
            help="Total delta exposure across all exchanges"
        )

    # Second row: Funding PnL, Trading PnL, Fees
    col1, col2, col3 = st.columns(3)
    with col1:
        daily_funding = dashboard_data['total_funding_pnl'] / days
        st.metric(
            "Funding PnL",
            f"${dashboard_data['total_funding_pnl']:,.2f}",
            f"${daily_funding:,.2f}/day",
            help="Total funding payments received/paid"
        )
    with col2:
        st.metric(
            "Trading PnL",
            f"${dashboard_data['total_pnl']:,.2f}",
            help="PnL from trading (excluding funding)"
        )
    with col3:
        daily_fees = dashboard_data['total_fees'] / days if days > 0 else 0
        st.metric(
            "Total Fees",
            f"${dashboard_data['total_fees']:,.2f}",
            f"${daily_fees:,.2f}/day",
            help="Total trading fees across all exchanges"
        )

    # Add fee breakdown by exchange
    st.markdown("### 💰 Fee Breakdown by Exchange")
    fee_data = []
    for exchange, fee in dashboard_data['fees_by_exchange'].items():
        if fee != 0:  # Only show exchanges with non-zero fees
            daily_avg = fee / days if days > 0 else 0
            fee_data.append({
                'Exchange': exchange.capitalize(),
                'Trading Fees': f"${abs(fee):,.2f}",
                'Daily Average': f"${abs(daily_avg):,.2f}"
            })

    if fee_data:
        fee_df = pd.DataFrame(fee_data)
        st.dataframe(
            fee_df,
            column_config={
                "Exchange": st.column_config.TextColumn("Exchange", width="medium"),
                "Trading Fees": st.column_config.TextColumn("Trading Fees", width="medium"),
                "Daily Average": st.column_config.TextColumn("Daily Average", width="medium")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("No trading fees recorded for the selected period")

    st.markdown("---")

    # Display delta exposure by token next
    st.subheader("Delta Exposure by Token")
    show_dollar_value = st.toggle("Show Delta in Dollar Value", value=True, help="Toggle between dollar value and token quantity")

    if dashboard_data['delta_exposure']:
        delta_data = []
        for symbol, data in dashboard_data['delta_exposure'].items():
            # Calculate token quantity delta for each exchange
            exchange_deltas = {}
            for exchange in [e.lower() for e in selected_exchanges]:
                if show_dollar_value:
                    exchange_deltas[exchange] = data['exchanges'][exchange]
                else:
                    # Find the current price from positions to convert dollar delta back to token quantity
                    exchange_positions = [p for p in dashboard_data['all_positions'] if p['exchange'] == exchange and p['symbol'] == symbol]
                    if exchange_positions:
                        current_price = exchange_positions[0]['current_price']
                        exchange_deltas[exchange] = data['exchanges'][exchange] / current_price if current_price != 0 else 0
                    else:
                        exchange_deltas[exchange] = 0

            row = {
                'Token': symbol,
                'Total Delta': (f"${data['total_delta']:,.2f}" if show_dollar_value 
                              else f"{sum(exchange_deltas.values()):,.4f} {symbol}"),
                'Funding PnL': f"${data['funding_pnl']:,.2f}",
            }
            
            # Add exchange-specific deltas
            for exchange in [e.lower() for e in selected_exchanges]:
                delta_value = exchange_deltas[exchange]
                row[f"{exchange.capitalize()} Delta"] = (f"${delta_value:,.2f}" if show_dollar_value 
                                                       else f"{delta_value:,.4f} {symbol}")
            delta_data.append(row)
        
        # Sort by absolute total delta
        if show_dollar_value:
            delta_data.sort(key=lambda x: abs(float(x['Total Delta'].replace('$', '').replace(',', ''))), reverse=True)
        else:
            delta_data.sort(key=lambda x: abs(float(x['Total Delta'].split()[0].replace(',', ''))), reverse=True)
        
        delta_df = pd.DataFrame(delta_data)
        st.dataframe(delta_df, hide_index=True)
    else:
        st.info("No active positions found")

    # Add Arbitrage Opportunities section
    st.markdown("### 📊 Cross-Exchange Arbitrage Positions")

    # Create a dictionary to store positions by token
    positions_by_token = {}
    for pos in dashboard_data['all_positions']:
        token = pos['symbol']
        exchange = pos['exchange']
        if token not in positions_by_token:
            positions_by_token[token] = {}
        positions_by_token[token][exchange] = {
            'size': pos['size'],
            'current_price': pos['current_price'],
            'side': pos['side']
        }

    # Filter tokens that have positions on multiple exchanges
    arb_opportunities = []
    for token, exchange_data in positions_by_token.items():
        if len(exchange_data) > 1:
            exchanges = list(exchange_data.keys())
            
            # Calculate price spreads
            for i in range(len(exchanges)):
                for j in range(i + 1, len(exchanges)):
                    exchange1, exchange2 = exchanges[i], exchanges[j]
                    price1 = exchange_data[exchange1]['current_price']
                    price2 = exchange_data[exchange2]['current_price']
                    price_spread = abs(price1 - price2)
                    price_spread_bps = (price_spread / min(price1, price2)) * 10000  # Convert to basis points
                    
                    # Get funding rates for both exchanges
                    funding_rate1 = 0
                    funding_rate2 = 0
                    try:
                        funding_df1 = client.get_funding_rate_history(exchange1, token, days=1)
                        if not funding_df1.empty:
                            funding_rate1 = funding_df1.iloc[-1]['fundingRate']
                    except Exception as e:
                        logging.error(f"Error getting funding rate for {token} on {exchange1}: {e}")
                    
                    try:
                        funding_df2 = client.get_funding_rate_history(exchange2, token, days=1)
                        if not funding_df2.empty:
                            funding_rate2 = funding_df2.iloc[-1]['fundingRate']
                    except Exception as e:
                        logging.error(f"Error getting funding rate for {token} on {exchange2}: {e}")
                    
                    funding_spread = abs(funding_rate1 - funding_rate2)
                    funding_spread_bps = funding_spread * 10000  # Convert to basis points
                    
                    arb_opportunities.append({
                        'Token': token,
                        'Exchange Pair': f"{exchange1.capitalize()} - {exchange2.capitalize()}",
                        'Price Spread': f"{price_spread_bps:.1f} bps",
                        'Funding Rate Spread': f"{funding_spread_bps:.1f} bps"
                    })

    if arb_opportunities:
        arb_df = pd.DataFrame(arb_opportunities)
        st.dataframe(
            arb_df,
            column_config={
                "Token": st.column_config.TextColumn("Token", width="medium"),
                "Exchange Pair": st.column_config.TextColumn("Exchange Pair", width="medium"),
                "Price Spread": st.column_config.TextColumn("Price Spread", width="medium"),
                "Funding Rate Spread": st.column_config.TextColumn("Funding Rate Spread", width="medium")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("No cross-exchange arbitrage positions found")

    st.markdown("---")

    # Display Top Positions by Size
    st.subheader("🔝 Top Positions by Size")
    if dashboard_data['all_positions']:
        top_positions = sorted(dashboard_data['all_positions'], key=lambda x: abs(x['size'] * x['current_price']), reverse=True)[:6]
        top_size_df = pd.DataFrame([{
            'Token': p['symbol'],
            'Exchange': p['exchange'].capitalize(),
            'Side': p['side'].upper(),
            'Size': f"{p['size']} {p['symbol']}",
            'Notional Value': f"${abs(p['size'] * p['current_price']):,.2f}",
            'Entry Price': f"${p['entry_price']:,.2f}",
            'Current Price': f"${p['current_price']:,.2f}",
        } for p in top_positions])
        
        st.dataframe(
            top_size_df.style.apply(
                lambda row: ['color: #2ECC71' if row['Side'] == 'LONG' else 'color: #E74C3C' for _ in row],
                axis=1
            ),
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("No active positions found")

    # Display per-exchange metrics
    st.markdown("---")
    st.subheader("Exchange Overview")
    exchange_metrics = {}

    # Calculate metrics per exchange
    for exchange in [e.lower() for e in selected_exchanges]:
        exchange_positions = [p for p in dashboard_data['all_positions'] if p['exchange'] == exchange]
        total_value = sum(abs(p['size'] * p['current_price']) for p in exchange_positions)
        exchange_delta = sum(p['size'] * p['current_price'] * (1 if p['side'].lower() == 'long' else -1) for p in exchange_positions)
        exchange_funding = sum(p['funding_pnl'] for p in exchange_positions)
        
        exchange_metrics[exchange] = {
            'total_value': total_value,
            'delta': exchange_delta,
            'funding_pnl': exchange_funding,
            'position_count': len(exchange_positions)
        }

    # Display exchange metrics vertically with metrics side by side
    for exchange in [e.lower() for e in selected_exchanges]:
        st.markdown(f'<div class="exchange-section">', unsafe_allow_html=True)
        st.markdown(f"### {exchange.capitalize()}")
        metrics = exchange_metrics[exchange]
        
        # Display metrics in columns
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown('<p class="metric-label">Total Position Value</p>', unsafe_allow_html=True)
            st.metric("", f"${metrics['total_value']:,.2f}")
        with col2:
            st.markdown('<p class="metric-label">Net Delta</p>', unsafe_allow_html=True)
            st.metric("", f"${metrics['delta']:,.2f}")
        with col3:
            st.markdown('<p class="metric-label">Funding PnL</p>', unsafe_allow_html=True)
            st.metric("", f"${metrics['funding_pnl']:,.2f}")
        with col4:
            st.markdown('<p class="metric-label">Position Count</p>', unsafe_allow_html=True)
            st.metric("", metrics['position_count'])
        
        # Display positions table for this exchange
        if exchange_positions := [p for p in dashboard_data['all_positions'] if p['exchange'] == exchange]:
            positions_df = pd.DataFrame([{
                'Token': p['symbol'],
                'Side': p['side'].upper(),
                'Size': f"{p['size']} {p['symbol']}",
                'Entry Price': f"${p['entry_price']:,.2f}",
                'Current Price': f"${p['current_price']:,.2f}",
                'PnL': f"${p['pnl']:,.2f}",
                'Funding PnL': f"${p['funding_pnl']:,.2f}"
            } for p in exchange_positions])
            
            st.markdown(f"#### Active Positions on {exchange.capitalize()}")
            st.dataframe(
                positions_df.style.apply(
                    lambda row: ['color: #2ECC71' if row['Side'] == 'LONG' else 'color: #E74C3C' for _ in row],
                    axis=1
                ),
                column_config={
                    "Token": st.column_config.TextColumn("Token", width="medium"),
                    "Side": st.column_config.TextColumn("Side", width="small"),
                    "Size": st.column_config.TextColumn("Size", width="medium"),
                    "Entry Price": st.column_config.TextColumn("Entry Price", width="medium"),
                    "Current Price": st.column_config.TextColumn("Current Price", width="medium"),
                    "PnL": st.column_config.TextColumn("PnL", width="medium"),
                    "Funding PnL": st.column_config.TextColumn("Funding PnL", width="medium")
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info(f"No active positions on {exchange.capitalize()}")
        
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # Display Funding Rate Charts for Active Positions
    st.header("📈 Funding Rate History")

    # Get active positions for each exchange
    for exchange in [e.lower() for e in selected_exchanges]:
        exchange_positions = [p for p in dashboard_data['all_positions'] if p['exchange'] == exchange]
        if exchange_positions:
            st.subheader(f"{exchange.capitalize()} Funding Rates")
            
            # Get symbols from active positions
            active_symbols = [p['raw_symbol'] for p in exchange_positions]
            
            # Get funding rate history for each symbol
            for symbol in active_symbols:
                try:
                    funding_history = client.get_funding_rate_history(exchange, symbol, days)
                    if not funding_history.empty:
                        # Determine the correct column names based on the exchange
                        time_col = 'fundingTime'
                        if 'fundingRateTimestamp' in funding_history.columns:
                            time_col = 'fundingRateTimestamp'
                        
                        # Create funding rate chart
                        fig = px.line(
                            funding_history,
                            x=time_col,
                            y='fundingRate',
                            title=f"{symbol} Funding Rate",
                            labels={'fundingRate': 'Funding Rate (%)', time_col: 'Time'},
                        )
                        
                        # Customize the chart
                        fig.update_traces(mode='lines+markers')
                        fig.update_layout(
                            yaxis=dict(
                                tickformat='.4%',
                                title='Funding Rate'
                            ),
                            xaxis=dict(
                                title='Time'
                            ),
                            showlegend=False
                        )
                        
                        # Add horizontal line at y=0
                        fig.add_hline(
                            y=0,
                            line_dash="dash",
                            line_color="gray",
                            opacity=0.5
                        )
                        
                        # Color positive rates green and negative rates red
                        fig.update_traces(
                            line=dict(
                                color='#2ECC71',
                                width=2
                            ),
                            marker=dict(
                                color=funding_history['fundingRate'].apply(
                                    lambda x: '#2ECC71' if x >= 0 else '#E74C3C'
                                )
                            )
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info(f"No funding rate data available for {symbol}")
                except Exception as e:
                    st.error(f"Error fetching funding rates for {symbol}: {str(e)}")
        else:
            st.info(f"No active positions on {exchange.capitalize()}")

    # Auto-refresh logic with cleanup
    if auto_refresh:
        time.sleep(refresh_interval)
        # Clean up before refresh
        if 'client' in st.session_state:
            del st.session_state.client
        gc.collect()
        st.rerun()

if __name__ == "__main__":
    main() 