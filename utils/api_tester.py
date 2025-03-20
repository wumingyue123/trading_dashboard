import streamlit as st
from binance.spot import Spot
from binance.error import ClientError
from pybit.unified_trading import HTTP
import ccxt
import json
from datetime import datetime, timedelta

def test_binance_connection(api_key: str, api_secret: str) -> dict:
    """Test Binance API connection and endpoints"""
    try:
        client = Spot(api_key=api_key, api_secret=api_secret)

        # Test basic connection
        ping_result = client.ping()

        # Test account info
        account_info = client.account()

        return {
            'status': 'success',
            'message': 'Successfully connected to Binance API',
            'account_info': account_info
        }
    except ClientError as e:
        return {
            'status': 'error',
            'message': f'Binance API error: {str(e)}',
            'error_code': e.status_code if hasattr(e, 'status_code') else None,
            'error_data': e.response.json() if hasattr(e, 'response') else None
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }

def test_bybit_connection(api_key: str, api_secret: str) -> dict:
    """Test Bybit V5 API connection and endpoints"""
    try:
        exchange = HTTP(
            testnet=False,
            api_key=api_key,
            api_secret=api_secret
        )

        # Test server time
        server_time = exchange.get_server_time()

        # Test wallet balance
        balance = exchange.get_wallet_balance(accountType="UNIFIED")

        # Test positions with settleCoin parameter
        positions = exchange.get_positions(
            category="linear",
            settleCoin="USDT"
        )

        return {
            'status': 'success',
            'message': 'Successfully connected to Bybit API',
            'server_time': server_time,
            'balance': balance,
            'positions': positions
        }
    except Exception as e:
        error_msg = str(e)
        if "error sign" in error_msg.lower():
            return {
                'status': 'error',
                'message': 'Bybit API signature error. Please verify your API key and secret are correct.',
                'error_data': error_msg
            }
        elif "10004" in error_msg:
            return {
                'status': 'error',
                'message': 'API key validation failed. Please check if your IP is whitelisted in Bybit settings.',
                'error_data': error_msg
            }
        else:
            return {
                'status': 'error',
                'message': f'Bybit API error: {error_msg}',
                'error_data': str(e)
            }

def test_okx_connection(api_key: str, api_secret: str, passphrase: str) -> dict:
    """Test OKX API connection and endpoints"""
    try:
        exchange = ccxt.okx({
            'apiKey': api_key,
            'secret': api_secret,
            'password': passphrase,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
                'adjustForTimeDifference': True
            }
        })

        # Test server time
        server_time = exchange.fetch_time()

        # Test balance
        balance = exchange.fetch_balance()

        return {
            'status': 'success',
            'message': 'Successfully connected to OKX API',
            'server_time': server_time,
            'balance': balance
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'OKX API error: {str(e)}',
            'error_data': str(e)
        }

def run_api_tests():
    st.title("🔍 Exchange API Connection Tester")

    # Get credentials from session state
    if 'exchange_credentials' in st.session_state:
        credentials = st.session_state.exchange_credentials

        # Test Binance
        st.header("Binance API Test")
        if all(credentials['binance'].values()):
            result = test_binance_connection(
                credentials['binance']['api_key'],
                credentials['binance']['secret']
            )
            if result['status'] == 'success':
                st.success(result['message'])
                st.json(result['account_info'])
            else:
                st.error(result['message'])
                st.json(result)
        else:
            st.warning("Binance API credentials not configured")

        # Test Bybit
        st.header("Bybit API Test")
        if all(credentials['bybit'].values()):
            result = test_bybit_connection(
                credentials['bybit']['api_key'],
                credentials['bybit']['secret']
            )
            if result['status'] == 'success':
                st.success(result['message'])
                st.json(result)
            else:
                st.error(result['message'])
                if 'whitelisted' in result['message'].lower():
                    st.warning("⚠️ Please ensure your IP address is whitelisted in your Bybit account settings.")
                st.json(result)
        else:
            st.warning("Bybit API credentials not configured")

        # Test OKX
        st.header("OKX API Test")
        if all(credentials['okx'].values()):
            result = test_okx_connection(
                credentials['okx']['api_key'],
                credentials['okx']['secret'],
                credentials['okx']['password']
            )
            if result['status'] == 'success':
                st.success(result['message'])
                st.json(result)
            else:
                st.error(result['message'])
                st.json(result)
        else:
            st.warning("OKX API credentials not configured")
    else:
        st.error("No API credentials found in session state")

if __name__ == "__main__":
    run_api_tests()