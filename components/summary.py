import streamlit as st
import plotly.graph_objects as go
from typing import Dict
import pandas as pd

def render_summary_metrics(metrics: Dict):
    # Total metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Total USDT PnL",
            f"${metrics['total_pnl']:,.2f}",
            delta=None,
            delta_color="normal"
        )

    with col2:
        st.metric(
            "Daily USDT PnL",
            f"${metrics['daily_pnl']:,.2f}",
            delta=None,
            delta_color="normal"
        )

    with col3:
        st.metric(
            "Total USDT Balance Changes",
            metrics['active_positions'],
            delta=None,
            delta_color="normal"
        )

    # Per-exchange metrics
    st.subheader("USDT PnL by Exchange")
    exchange_cols = st.columns(3)

    for i, exchange in enumerate(['binance', 'bybit', 'okx']):
        with exchange_cols[i]:
            # Current PnL
            current_pnl = metrics['exchange_pnl'].get(exchange, 0)
            daily_pnl = metrics['daily_pnl_by_exchange'].get(exchange, 0)

            st.metric(
                f"{exchange.capitalize()}",
                f"${current_pnl:,.2f}",
                delta=f"Daily: ${daily_pnl:,.2f}",
                delta_color="normal" if daily_pnl >= 0 else "inverse"
            )

def render_pnl_chart(pnl_data: pd.DataFrame):
    if pnl_data.empty:
        st.info("No USDT PnL data available")
        return

    fig = go.Figure()

    # Plot individual exchange lines
    for exchange in pnl_data['exchange'].unique():
        exchange_data = pnl_data[pnl_data['exchange'] == exchange]
        fig.add_trace(go.Scatter(
            x=exchange_data['date'],
            y=exchange_data['realized_pnl'].cumsum(),  # Show cumulative PnL
            mode='lines+markers',
            name=f"{exchange.capitalize()} USDT PnL",
            line=dict(width=2)
        ))

    # Add total PnL line
    total_by_date = pnl_data.groupby('date')['realized_pnl'].sum().cumsum()
    fig.add_trace(go.Scatter(
        x=total_by_date.index,
        y=total_by_date.values,
        mode='lines',
        name='Total USDT PnL',
        line=dict(width=3, color='#3498DB'),
        opacity=0.8
    ))

    fig.update_layout(
        title='Cumulative USDT PnL',
        plot_bgcolor='#1E1E1E',
        paper_bgcolor='#1E1E1E',
        font=dict(color='#FFFFFF'),
        xaxis=dict(
            showgrid=False,
            title='Date'
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='#252525',
            title='Cumulative USDT PnL'
        ),
        margin=dict(l=0, r=0, t=30, b=0),
        height=300,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    st.plotly_chart(fig, use_container_width=True)