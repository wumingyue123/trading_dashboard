import streamlit as st
import pandas as pd

def render_positions_table(positions_df: pd.DataFrame):
    if positions_df.empty:
        st.info("No active positions found")
        return

    # Group positions by symbol (already normalized)
    grouped_positions = positions_df.groupby('symbol').agg({
        'exchange': lambda x: ', '.join(sorted(set(x))),
        'raw_symbol': lambda x: ', '.join(sorted(set(x))),
        'size': 'sum',
        'entry_price': 'mean',
        'current_price': 'mean',
        'pnl': 'sum'
    }).reset_index()

    # Format the display
    display_df = grouped_positions.copy()
    display_df['Token'] = display_df['symbol']
    display_df['Exchanges'] = display_df['exchange']
    display_df['Size'] = display_df['size'].round(4)
    display_df['Entry Price'] = display_df['entry_price'].apply(lambda x: f"${x:,.2f}")
    display_df['Current Price'] = display_df['current_price'].apply(lambda x: f"${x:,.2f}")
    display_df['PnL'] = display_df['pnl'].apply(lambda x: f"${x:,.2f}")

    st.dataframe(
        display_df[[
            'Token', 'Exchanges', 'Size', 'Entry Price',
            'Current Price', 'PnL'
        ]].style.apply(
            lambda x: ['color: #2ECC71' if float(x['PnL'].replace('$', '').replace(',', '')) >= 0 else 'color: #E74C3C' 
                      for _ in range(len(x))],
            axis=1
        ),
        height=400
    )