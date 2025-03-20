import streamlit as st
from typing import Dict

def render_balance_metrics(balances: Dict[str, Dict]):
    # Create columns for each exchange
    cols = st.columns(3)

    # Define all exchanges
    exchanges = ['binance', 'bybit', 'okx']

    # Display balances for each exchange
    for idx, exchange in enumerate(exchanges):
        with cols[idx]:
            balance = balances.get(exchange, {})

            # Get USDT balance
            usdt_balance = balance.get('currencies', {}).get('USDT', 0)

            # Display USDT balance
            st.metric(
                f"{exchange.capitalize()} USDT Balance",
                f"${usdt_balance:,.2f}",
                delta=None
            )

            #This section is removed because it displays all balances and was replaced by the edited code
            #if balance.get('currencies'):
            #    with st.expander("View Holdings"):
            #        for currency, amount in balance['currencies'].items():
            #            st.text(f"{currency}: {amount:,.8f}")
            #elif not balance:
            #    st.info("No balance data - Configure API keys")