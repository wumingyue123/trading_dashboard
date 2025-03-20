import streamlit as st
import pandas as pd
import plotly.express as px
from .exchange_client import ExchangeClient
from .data_processor import DataProcessor

def display_funding_rates(exchange_client: ExchangeClient):
    """Display funding rate payments for open positions"""
    # Initialize variables
    days = 7  # Default value
    selected_exchange = "bybit"  # Default value
    data_processor = DataProcessor()
    
    # Add custom CSS for smaller font in multi-select
    st.markdown("""
        <style>
        .stMultiSelect div div div div div {
            font-size: 0.8rem;
        }
        .stMultiSelect div div div div {
            font-size: 0.8rem;
        }
        .stMultiSelect div div div {
            font-size: 0.8rem;
        }
        .summary-metric {
            font-size: 1.2rem;
            margin-bottom: 1rem;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.subheader("📊 Funding Rate Dashboard")
    
    # Add time period selector
    col1, col2 = st.columns([2, 2])
    with col1:
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
    
    with col2:
        exchanges = ["bybit", "binance"]
        selected_exchange = st.selectbox(
            "Select Exchange",
            options=exchanges,
            index=0,
            help="Select the exchange to view funding payments for"
        )

    # Get positions and calculate funding payments for selected exchange
    positions = exchange_client.get_positions(selected_exchange)
    funding_payments = exchange_client.calculate_funding_payments(selected_exchange, days)
    
    if positions and funding_payments:
        # Calculate summary metrics
        total_exposure = sum(abs(pos['size'] * pos['current_price']) for pos in positions)
        total_funding = sum(funding_payments.values())
        daily_funding = total_funding / days
        
        # Calculate delta exposure by token using the existing positions data
        delta_exposure = {}
        
        # First get Bybit positions
        bybit_positions = exchange_client.get_positions('bybit')
        for pos in bybit_positions:
            normalized_symbol = data_processor.normalize_symbol(pos['symbol'])
            delta = pos['size'] * pos['current_price'] * (1 if pos['side'].lower() == 'long' else -1)
            if normalized_symbol not in delta_exposure:
                delta_exposure[normalized_symbol] = {'total_delta': 0, 'exchanges': {'bybit': 0, 'binance': 0}}
            delta_exposure[normalized_symbol]['total_delta'] += delta
            delta_exposure[normalized_symbol]['exchanges']['bybit'] = delta
        
        # Then get Binance positions
        binance_positions = exchange_client.get_positions('binance')
        for pos in binance_positions:
            normalized_symbol = data_processor.normalize_symbol(pos['symbol'])
            delta = pos['size'] * pos['current_price'] * (1 if pos['side'].lower() == 'long' else -1)
            if normalized_symbol not in delta_exposure:
                delta_exposure[normalized_symbol] = {'total_delta': 0, 'exchanges': {'bybit': 0, 'binance': 0}}
            delta_exposure[normalized_symbol]['total_delta'] += delta
            delta_exposure[normalized_symbol]['exchanges']['binance'] = delta
        
        # Display summary section at the top
        st.markdown("### 📈 Summary")
        
        # Key metrics in columns
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Total Position Value",
                f"${total_exposure:,.2f}",
                help="Total notional value of all positions"
            )
        with col2:
            st.metric(
                f"Total Funding ({days}d)",
                f"${total_funding:,.2f}",
                f"${daily_funding:,.2f}/day",
                help="Total funding payments received/paid"
            )
        with col3:
            net_delta = sum(data['total_delta'] for data in delta_exposure.values())
            st.metric(
                "Net Delta Exposure",
                f"${net_delta:,.2f}",
                help="Total delta exposure across all exchanges"
            )
        
        # Display Delta Exposure Section
        st.markdown("### 🎯 Delta Exposure")
        
        # Create delta exposure table data first
        delta_data = []
        total_delta = 0
        for symbol, data in delta_exposure.items():
            row = {
                'Token': symbol,
                'Total Delta': f"${data['total_delta']:,.2f}",
                'Bybit Delta': f"${data['exchanges']['bybit']:,.2f}",
                'Binance Delta': f"${data['exchanges']['binance']:,.2f}"
            }
            delta_data.append(row)
            total_delta += data['total_delta']
        
        # Sort by absolute total delta
        delta_data.sort(key=lambda x: abs(float(x['Total Delta'].replace('$', '').replace(',', ''))), reverse=True)
        
        # Display total delta prominently above the table
        st.metric(
            "Total Delta Exposure",
            f"${total_delta:,.2f}",
            help="Sum of all token deltas across exchanges"
        )
        
        # Add some spacing
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Display delta table
        delta_df = pd.DataFrame(delta_data)
        st.dataframe(
            delta_df,
            column_config={
                "Token": st.column_config.TextColumn("Token", width="medium"),
                "Total Delta": st.column_config.TextColumn("Total Delta", width="medium", help="Net delta exposure across all exchanges"),
                "Bybit Delta": st.column_config.TextColumn("Bybit Delta", width="medium", help="Delta exposure on Bybit"),
                "Binance Delta": st.column_config.TextColumn("Binance Delta", width="medium", help="Delta exposure on Binance")
            },
            hide_index=True,
        )
        
        st.markdown("---")
        
        # Calculate per-token metrics
        token_metrics = []
        for pos in positions:
            normalized_symbol = data_processor.normalize_symbol(pos['symbol'])
            notional_size = abs(pos['size'] * pos['current_price'])
            funding_pnl = funding_payments.get(pos['symbol'], 0)
            if funding_pnl != 0:  # Avoid division by zero
                funding_apy = (funding_pnl / notional_size * (365 / days)) * 100
            else:
                funding_apy = 0
            
            token_metrics.append({
                'symbol': normalized_symbol,
                'original_symbol': pos['symbol'],
                'notional_size': notional_size,
                'funding_pnl': funding_pnl,
                'funding_apy': funding_apy,
                'side': pos['side'].upper()
            })
        
        # Sort tokens by various metrics
        tokens_by_size = sorted(token_metrics, key=lambda x: abs(x['notional_size']), reverse=True)
        tokens_by_funding = sorted(token_metrics, key=lambda x: x['funding_pnl'], reverse=True)
        
        st.subheader("💼 Active Positions")
        
        # Top tokens tables
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🔝 Top Positions by Size")
            # Get current funding rates for each token
            current_rates = {}
            for t in tokens_by_size[:5]:
                funding_history = exchange_client.get_funding_rate_history(selected_exchange, t['original_symbol'], 1)
                if not funding_history.empty:
                    current_rates[t['symbol']] = funding_history['fundingRate'].iloc[0] * 100  # Convert to percentage
            
            top_size_df = pd.DataFrame([{
                'Token': t['symbol'],
                'Side': t['side'],
                'Size': f"${t['notional_size']:,.0f}",
                'Current Rate': f"{current_rates.get(t['symbol'], 0):.4f}%"
            } for t in tokens_by_size[:5]])
            st.dataframe(top_size_df, hide_index=True)
        
        with col2:
            st.markdown("#### 💰 Top Funding Earners/Payers")
            # Reuse current funding rates for top funding earners
            top_funding_df = pd.DataFrame([{
                'Token': t['symbol'],
                'Funding PnL': f"${t['funding_pnl']:,.2f}",
                'Current Rate': f"{current_rates.get(t['symbol'], 0):.4f}%"
            } for t in tokens_by_funding[:5]])
            st.dataframe(top_funding_df, hide_index=True)
        
        st.markdown("---")
        
        # Create a DataFrame for better display
        data = []
        for symbol, payment in funding_payments.items():
            # Get position details for this symbol
            positions = [p for p in exchange_client.get_positions(selected_exchange) if p['symbol'] == symbol]
            if positions:
                position = positions[0]
                normalized_symbol = data_processor.normalize_symbol(symbol)
                data.append({
                    "Token": normalized_symbol,
                    "Position Size": f"{position['size']} {normalized_symbol}",
                    "Side": position['side'].upper(),
                    "Entry Price": f"${position['entry_price']}",
                    "Funding Payment": f"${payment:,.4f}",
                    "Payment (bps)": f"{(payment / (position['size'] * position['entry_price']) * 10000):,.2f}"
                })
        
        if data:
            # Display detailed table
            st.markdown("### 📊 Position Details")
            df = pd.DataFrame(data)
            st.dataframe(
                df,
                column_config={
                    "Token": st.column_config.TextColumn("Token", width="medium"),
                    "Position Size": st.column_config.TextColumn("Position Size", width="medium"),
                    "Side": st.column_config.TextColumn("Side", width="small"),
                    "Entry Price": st.column_config.TextColumn("Entry Price", width="medium"),
                    "Funding Payment": st.column_config.TextColumn("Funding Payment", width="medium"),
                    "Payment (bps)": st.column_config.TextColumn("Payment (bps)", width="medium", help="Payment as basis points of position value")
                },
                hide_index=True,
            )
            
            # Add funding rate history chart
            st.subheader("Funding Rate History")
            
            # Get all tokens with funding rate history
            all_tokens = set()
            
            # Get funding history for both exchanges
            for exchange in ['bybit', 'binance']:
                # Get all symbols from the exchange
                exchange_positions = exchange_client.get_positions(exchange)
                for pos in exchange_positions:
                    normalized_symbol = data_processor.normalize_symbol(pos['symbol'])
                    all_tokens.add(normalized_symbol)
            
            # Sort tokens alphabetically
            available_tokens = sorted(all_tokens)
            
            # Add token selector
            selected_tokens = st.multiselect(
                "Select Tokens to Display",
                options=available_tokens,
                default=available_tokens[:5] if len(available_tokens) > 5 else available_tokens,
                help="Choose which tokens to show on the charts"
            )
            
            if selected_tokens:
                # Create a color map for consistent colors across charts
                color_sequence = px.colors.qualitative.Set1
                color_map = {token: color_sequence[i % len(color_sequence)] 
                           for i, token in enumerate(available_tokens)}
                
                # Function to create and display funding rate chart
                def display_exchange_funding_chart(exchange):
                    all_funding_rates = []
                    exchange_positions = exchange_client.get_positions(exchange)
                    symbol_map = {data_processor.normalize_symbol(pos['symbol']): pos['symbol'] 
                                for pos in exchange_positions}
                    
                    for normalized_symbol in selected_tokens:
                        # Get the original symbol for this token
                        original_symbol = symbol_map.get(normalized_symbol)
                        if original_symbol:
                            funding_history = exchange_client.get_funding_rate_history(exchange, original_symbol, days)
                            if not funding_history.empty:
                                time_col = 'fundingRateTimestamp' if 'fundingRateTimestamp' in funding_history.columns else 'fundingTime'
                                funding_history['symbol'] = normalized_symbol  # Use normalized symbol for display
                                funding_history['fundingRate'] = funding_history['fundingRate'] * 100  # Convert to percentage
                                funding_history = funding_history[[time_col, 'fundingRate', 'symbol']]
                                all_funding_rates.append(funding_history)
                    
                    if all_funding_rates:
                        # Combine all funding rates into a single DataFrame
                        combined_df = pd.concat(all_funding_rates, ignore_index=True)
                        time_col = 'fundingRateTimestamp' if 'fundingRateTimestamp' in combined_df.columns else 'fundingTime'
                        
                        # Create scatter plot using Plotly
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
                            },
                            color_discrete_map=color_map  # Use consistent colors
                        )
                        
                        # Update layout for better readability
                        fig.update_layout(
                            xaxis_title='Time',
                            yaxis_title='Funding Rate (%)',
                            legend_title='Token',
                            hovermode='x unified',
                            height=400,  # Fixed height for consistency
                            showlegend=True,  # Always show legend for consistency
                            yaxis_range=[
                                combined_df['fundingRate'].min() * 1.1 if combined_df['fundingRate'].min() < 0 else combined_df['fundingRate'].min() * 0.9,
                                combined_df['fundingRate'].max() * 1.1 if combined_df['fundingRate'].max() > 0 else combined_df['fundingRate'].max() * 0.9
                            ]  # Consistent y-axis range with some padding
                        )
                        
                        # Add lines connecting points for each symbol
                        fig.update_traces(mode='lines+markers')
                        
                        # Display the plot
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info(f"No funding rate data available for {exchange.capitalize()}")
                
                # Display charts one below the other
                st.markdown("#### Bybit Funding Rates")
                display_exchange_funding_chart("bybit")
                
                st.markdown("#### Binance Funding Rates")
                display_exchange_funding_chart("binance")
            else:
                st.warning("Please select at least one token to display.")
    else:
        st.info("No open positions found with funding payments.") 