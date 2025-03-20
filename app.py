import streamlit as st
from components.funding_rates_updated import display_funding_rates
from utils.exchange_client import ExchangeClient
import gc
import time
import os
import pandas as pd
from datetime import datetime

# Set page config
st.set_page_config(
    page_title="Crypto Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
with open(os.path.join("styles", "custom.css")) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

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
st.title("🚀 Crypto Trading Dashboard")
st.markdown("Analyze your crypto positions and funding rates across multiple exchanges")

# Get exchange client
client = get_exchange_client()

# Store client in session state for cleanup
st.session_state.client = client

# Create tabs for different views
tab1, tab2, tab3 = st.tabs(["📊 Funding Rates", "💰 Portfolio", "📈 Market Overview"])

with tab1:
    display_funding_rates()

with tab2:
    st.markdown("### 💰 Portfolio Analysis")
    st.markdown("Portfolio analysis features coming soon...")
    # Placeholder for portfolio analysis

with tab3:
    st.markdown("### 📈 Market Overview")
    st.markdown("Market overview features coming soon...")
    # Placeholder for market overview

# Auto-refresh logic with cleanup
if auto_refresh:
    time.sleep(refresh_interval)
    # Clean up before refresh
    if 'client' in st.session_state:
        del st.session_state.client
    gc.collect()
    st.rerun() 