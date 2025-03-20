import streamlit as st
import time
from src.exchange_client import ExchangeClient
from utils.data_processor import DataProcessor
from components.positions import render_positions_table
from components.funding_rates_updated import (
    display_funding_rates,
    get_cached_positions,
    get_cached_funding_history,
    get_cached_funding_payments
)
import json
from binance.spot import Spot as Client
from pybit.unified_trading import HTTP
import okx.Account as Account
import gc
import ccxt
import psutil
import os

# Page configuration
st.set_page_config(
    page_title="Funding Rate Dashboard",
    page_icon="📈",
    layout="wide"
)

# Memory management function
def check_memory_usage():
    process = psutil.Process(os.getpid())
    memory_usage = process.memory_info().rss / 1024 / 1024  # Convert to MB
    if memory_usage > 500:  # If memory usage exceeds 500MB
        st.warning(f"High memory usage detected ({memory_usage:.2f}MB). Clearing cache...")
        st.cache_data.clear()
        gc.collect()
        return True
    return False

# Load custom CSS
with open('styles/custom.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Clear session state for credentials
if 'exchange_credentials' in st.session_state:
    del st.session_state.exchange_credentials

# Initialize session state for credentials if not exists
if 'exchange_credentials' not in st.session_state:
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

    # Print debug info for all credentials
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

# Initialize clients with proper cleanup
@st.cache_resource(ttl=1800)  # Cache for 30 minutes
def get_exchange_client():
    """Get a cached instance of ExchangeClient"""
    # Get RabbitX credentials
    rabbitx_creds = st.session_state.exchange_credentials.get('rabbitx', {})
    client = ExchangeClient(
        rabbitx_api_key=rabbitx_creds.get('api_key', ""),
        rabbitx_api_secret=rabbitx_creds.get('secret', ""),
        rabbitx_testnet=False,
        rabbitx_jwt_token=rabbitx_creds.get('jwt_token', "")
    )
    
    # Set Hyperliquid credentials if available
    hyperliquid_creds = st.session_state.exchange_credentials.get('hyperliquid', {})
    if hyperliquid_creds:
        client._hyperliquid_api_key = hyperliquid_creds.get('api_key', "")
        client._hyperliquid_secret = hyperliquid_creds.get('secret', "")
        print(f"\nInitializing ExchangeClient with Hyperliquid credentials:")
        print(f"Wallet Address present: {bool(client._hyperliquid_api_key)}")
        print(f"Private Key present: {bool(client._hyperliquid_secret)}")
    
    return client

@st.cache_resource(ttl=1800)  # Cache for 30 minutes
def get_data_processor():
    """Get a cached instance of DataProcessor"""
    return DataProcessor()

# Clean up old resources before creating new ones
if 'client' in st.session_state:
    del st.session_state.client
if 'processor' in st.session_state:
    del st.session_state.processor

# Force garbage collection
gc.collect()

# Initialize clients
client = get_exchange_client()
processor = get_data_processor()

# Store clients in session state for cleanup
st.session_state.client = client
st.session_state.processor = processor

# Check memory usage
check_memory_usage()

# Sidebar Settings
st.sidebar.title("Exchange Settings")

# Function to create API input fields
def create_api_fields(exchange, required_fields):
    st.sidebar.subheader(f"{exchange.capitalize()}")
    values = {}
    
    # Debug output for Hyperliquid and RabbitX
    if exchange in ['hyperliquid', 'rabbitx']:
        print(f"\nCreating {exchange.capitalize()} API fields:")
        print(f"Current session state: {st.session_state.exchange_credentials.get(exchange, {})}")
    
    for field in required_fields:
        # Special handling for Hyperliquid fields
        if exchange == 'hyperliquid':
            field_label = "Wallet Address" if field == "api_key" else "Private Key"
            secret_key = "HYPERLIQUID_API_KEY" if field == "api_key" else "HYPERLIQUID_SECRET_KEY"
            # Get value from session state first, then secrets
            default_value = st.session_state.exchange_credentials.get('hyperliquid', {}).get(
                field,
                st.secrets.get(secret_key, "")
            )
            print(f"Loading {field_label}: {bool(default_value)}")  # Debug output
        # Special handling for RabbitX fields
        elif exchange == 'rabbitx':
            if field == "api_key":
                field_label = "API Key"
                secret_key = "RABBITX_API_KEY"
            elif field == "secret":
                field_label = "Secret Key"
                secret_key = "RABBITX_SECRET_KEY"
            elif field == "jwt_token":
                field_label = "JWT Token"
                secret_key = "RABBITX_JWT_TOKEN"
            # Get value from session state first, then secrets
            default_value = st.session_state.exchange_credentials.get('rabbitx', {}).get(
                field,
                st.secrets.get(secret_key, "")
            )
            print(f"Loading RabbitX {field_label}: {bool(default_value)}")  # Debug output
        else:
            field_label = field.replace('_', ' ').title()
            secret_key = f"{exchange.upper()}_{field.upper()}"
            default_value = st.secrets.get(secret_key, "")
        
        value = st.sidebar.text_input(
            f"{exchange.capitalize()} {field_label}",
            type="password",
            key=f"{exchange}_{field}",
            value=default_value,
            help=f"Enter your {exchange.capitalize()} {field_label.lower()}"
        )
        values[field] = value
    
    # Add a test connection button with debug output
    if all(values.values()):
        if st.sidebar.button(f"Test {exchange.capitalize()} Connection", key=f"test_{exchange}_connection_1"):
            try:
                if exchange == 'binance':
                    client.binance_client = Client(api_key=values['api_key'], api_secret=values['secret'])
                    test_result = client.test_binance_connection()
                    if test_result:
                        st.sidebar.success(f"✅ {exchange.capitalize()} Connected Successfully!")
                    else:
                        st.sidebar.error(f"❌ {exchange.capitalize()} Connection Failed")
                elif exchange == 'bybit':
                    client.bybit_client = HTTP(testnet=False, api_key=values['api_key'], api_secret=values['secret'])
                    test_result = client.bybit_client.get_wallet_balance(accountType="UNIFIED")
                    st.sidebar.success(f"✅ {exchange.capitalize()} Connected Successfully!")
                elif exchange == 'okx':
                    try:
                        client._okx_client = ccxt.okx({
                            'apiKey': values['api_key'],
                            'secret': values['secret'],
                            'password': values['password'],
                            'enableRateLimit': True,
                            'options': {
                                'defaultType': 'swap',
                                'adjustForTimeDifference': True
                            }
                        })
                        test_result = client.test_okx_connection()
                        if test_result:
                            st.sidebar.success(f"✅ {exchange.capitalize()} Connected Successfully!")
                        else:
                            st.sidebar.error(f"❌ {exchange.capitalize()} Connection Failed")
                    except Exception as e:
                        st.sidebar.error(f"❌ {exchange.capitalize()} Error: {str(e)}")
                elif exchange == 'hyperliquid':
                    api_key = values['api_key']
                    api_secret = values['secret']
                    
                    print(f"\nTesting Hyperliquid connection:")
                    print(f"Wallet Address provided: {bool(api_key)}")
                    print(f"Private Key provided: {bool(api_secret)}")
                    
                    if api_key and api_secret:
                        try:
                            # Update credentials
                            st.session_state.exchange_credentials[exchange] = {
                                'api_key': api_key,
                                'secret': api_secret
                            }
                            
                            # Ensure proper initialization
                            client._hyperliquid_api_key = api_key
                            client._hyperliquid_secret = api_secret
                            
                            # Test connection with debug output
                            print("Attempting to test Hyperliquid connection...")
                            test_result = client.test_hyperliquid_connection()
                            print(f"Hyperliquid test result: {test_result}")
                            
                            if test_result:
                                st.sidebar.success(f"✅ {exchange.capitalize()} Connected Successfully!")
                            else:
                                st.sidebar.error(f"❌ {exchange.capitalize()} Connection Failed")
                        except Exception as e:
                            print(f"Hyperliquid connection error: {str(e)}")
                            st.sidebar.error(f"❌ {exchange.capitalize()} Error: {str(e)}")
                    else:
                        st.sidebar.warning(f"Enter all {exchange.capitalize()} credentials to test connection")
                elif exchange == 'rabbitx':
                    api_key = values['api_key']
                    api_secret = values['secret']
                    
                    print(f"\nTesting RabbitX connection:")
                    print(f"API Key provided: {bool(api_key)}")
                    print(f"Secret Key provided: {bool(api_secret)}")
                    
                    if api_key and api_secret:
                        try:
                            # Update credentials
                            st.session_state.exchange_credentials[exchange] = {
                                'api_key': api_key,
                                'secret': api_secret
                            }
                            
                            # Ensure proper initialization
                            client._rabbitx_api_key = api_key
                            client._rabbitx_secret = api_secret
                            
                            # Test connection with debug output
                            print("Attempting to test RabbitX connection...")
                            test_result = client.test_rabbitx_connection()
                            print(f"RabbitX test result: {test_result}")
                            
                            if test_result:
                                st.sidebar.success(f"✅ {exchange.capitalize()} Connected Successfully!")
                            else:
                                st.sidebar.error(f"❌ {exchange.capitalize()} Connection Failed")
                        except Exception as e:
                            print(f"RabbitX connection error: {str(e)}")
                            st.sidebar.error(f"❌ {exchange.capitalize()} Error: {str(e)}")
                    else:
                        st.sidebar.warning(f"Enter all {exchange.capitalize()} credentials to test connection")
            except Exception as e:
                print(f"Connection error for {exchange}: {str(e)}")
                st.sidebar.error(f"❌ {exchange.capitalize()} Error: {str(e)}")
    else:
        st.sidebar.warning(f"Enter all {exchange.capitalize()} credentials to test connection")
    
    return values

# Create API fields for each exchange
credentials = {}
credentials['binance'] = create_api_fields('binance', ['api_key', 'secret'])
credentials['bybit'] = create_api_fields('bybit', ['api_key', 'secret'])
credentials['okx'] = create_api_fields('okx', ['api_key', 'secret'])
credentials['hyperliquid'] = create_api_fields('hyperliquid', ['api_key', 'secret'])
credentials['rabbitx'] = create_api_fields('rabbitx', ['api_key', 'secret'])

# Update session state with new credentials
st.session_state.exchange_credentials = credentials

# Check if any exchange is configured
has_active_exchanges = any(all(creds.values()) for creds in credentials.values())

# Refresh button and auto-refresh
col1, col2 = st.columns([8, 2])
with col2:
    auto_refresh = st.checkbox("Auto-refresh (1m)", value=True)
    if st.button("🔄 Refresh Data"):
        # Clean up before refresh
        if 'client' in st.session_state:
            del st.session_state.client
        if 'processor' in st.session_state:
            del st.session_state.processor
        gc.collect()
        st.rerun()

# Display funding rates first
display_funding_rates(client)

st.markdown("---")
st.subheader("📊 Current Positions")

# Get all positions with memory management
all_positions = []
error_logs = []

# Get positions from exchanges with chunking
for exchange in ['binance', 'bybit', 'okx', 'hyperliquid', 'rabbitx']:
    try:
        positions = get_cached_positions(exchange)
        if positions:
            # Process positions in chunks to save memory
            chunk_size = 50
            for i in range(0, len(positions), chunk_size):
                chunk = positions[i:i + chunk_size]
                all_positions.extend(chunk)
                # Check memory after each chunk
                if check_memory_usage():
                    st.warning(f"Memory limit reached while processing {exchange} positions. Some data may be incomplete.")
                    break
    except Exception as e:
        error_logs.append(f"Error fetching {exchange} positions: {str(e)}")
        continue

# Display any errors in an expander
if error_logs:
    with st.expander("🔍 Debug Information", expanded=False):
        st.error("Some errors occurred while fetching data:")
        for error in error_logs:
            st.text(error)

# Process and display positions
positions_df = processor.aggregate_positions(all_positions, has_active_exchanges=True)
render_positions_table(positions_df)

# Clear unnecessary data
del all_positions
del positions_df
gc.collect()

# Auto-refresh logic with cleanup
if auto_refresh:
    time.sleep(60)
    # Clean up before refresh
    if 'client' in st.session_state:
        del st.session_state.client
    if 'processor' in st.session_state:
        del st.session_state.processor
    st.cache_data.clear()
    gc.collect()
    st.rerun()