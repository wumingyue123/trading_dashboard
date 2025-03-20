import streamlit as st
import plotly.graph_objects as go
import pandas as pd

def render_historical_pnl(historical_data: pd.DataFrame):
    if historical_data.empty:
        st.info("No historical data available")
        return
    
    fig = go.Figure()
    
    for exchange in historical_data['exchange'].unique():
        exchange_data = historical_data[historical_data['exchange'] == exchange]
        fig.add_trace(go.Bar(
            x=exchange_data['date'],
            y=exchange_data['realized_pnl'],
            name=exchange.capitalize(),
            marker_color='#2ECC71' if exchange_data['realized_pnl'].mean() >= 0 else '#E74C3C'
        ))
    
    fig.update_layout(
        title='Historical PnL by Exchange',
        barmode='group',
        plot_bgcolor='#1E1E1E',
        paper_bgcolor='#1E1E1E',
        font=dict(color='#FFFFFF'),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='#252525'),
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
