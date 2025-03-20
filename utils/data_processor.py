import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime, timedelta

class DataProcessor:
    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        """Normalize token symbols across different exchanges"""
        # Define symbol mappings for special cases
        symbol_mappings = {
            'SOLAYER':'LAYER',
            'TRUMPOFFICIAL':'TRUMP'
        }
        
        # Clean the symbol by removing all variations of USDT suffix and exchange-specific formats
        cleaned = symbol
        variations = [
            '/USDT:USDT', ':USDT', '/USDT', '-USDT', 'USDT',  # Standard USDT variations
            '-SWAP',  # OKX specific
            '-USD',   # Additional variations
            '/USD',
            'USD' # RabbitX specific
        ]
        for variation in variations:
            cleaned = cleaned.replace(variation, '')
        
        # Handle special case for tokens starting with multipliers (Bybit, Binance, OKX format: 1000TOSHI)
        if cleaned.startswith('1000000'):
            # Extract the base token (e.g., 1000PEPE -> PEPE)
            return cleaned[7:]
        elif cleaned.startswith('1M'):
            # Extract the base token (e.g., 1MPEPE -> PEPE)
            return cleaned[2:]
        elif cleaned.startswith('1000'):
            # Extract the base token (e.g., 1000PEPE -> PEPE)
            return cleaned[4:]
        
        # Handle Hyperliquid's "k" prefix format (e.g., kPEPE -> PEPE)
        if cleaned.startswith('k') and len(cleaned) > 1:
            # Check if the second character is uppercase to ensure it's a proper token name
            if len(cleaned) > 1 and cleaned[1].isupper():
                return cleaned[1:]
        
        # Handle RabbitX's format where multiplier is at the end (e.g., TOSHI1000 -> TOSHI)
        if cleaned.endswith('1000'):
            # Check if it's likely a multiplier suffix
            if cleaned[-4:].isdigit():
                return cleaned[:-4]
        elif cleaned.endswith('1M') or cleaned.endswith('1000000'):
            # Handle million multiplier suffix
            suffix_len = 2 if cleaned.endswith('1M') else 7
            return cleaned[:-suffix_len]
        
        # Return the mapped symbol if it exists, otherwise return the cleaned symbol
        for key, value in symbol_mappings.items():
            if key in cleaned:
                return value

        return cleaned

    @staticmethod
    def extract_price_multiplier(symbol: str) -> float:
        """Extract price multiplier from a symbol.
        
        Args:
            symbol: The token symbol that may contain a price multiplier.
            
        Returns:
            float: The price multiplier (1.0, 1000.0, 1000000.0 etc.)
        """
        # Default multiplier
        multiplier = 1.0
        
        # Clean the symbol by removing all variations of USDT suffix and exchange-specific formats
        cleaned = symbol
        variations = [
            '/USDT:USDT', ':USDT', '/USDT', '-USDT', 'USDT',  # Standard USDT variations
            '-SWAP',  # OKX specific
            '-USD',   # Additional variations
            '/USD',
        ]
        for variation in variations:
            cleaned = cleaned.replace(variation, '')
        
        # Handle Bybit, Binance, OKX format: multiplier at start (e.g., 1000PEPE)
        if cleaned.startswith('1000000'):
            multiplier = 1000000.0
        elif cleaned.startswith('1000'):
            multiplier = 1000.0
        elif cleaned.startswith('1M'):
            multiplier = 1000000.0
        
        # Handle Hyperliquid's "k" prefix format (kPEPE = 1000 x PEPE)
        elif cleaned.startswith('k') and len(cleaned) > 1 and cleaned[1].isupper():
            multiplier = 1000.0
        
        # Handle RabbitX's format where multiplier is at the end (e.g., TOSHI1000)
        elif cleaned.endswith('1000') and cleaned[-4:].isdigit():
            multiplier = 1000.0
        elif cleaned.endswith('1M'):
            multiplier = 1000000.0
        elif cleaned.endswith('1000000'):
            multiplier = 1000000.0
        
        return multiplier

    @staticmethod
    def generate_mock_data():
        """Generate mock data for testing when exchange connections fail"""
        today = datetime.now()
        dates = [(today - timedelta(days=x)).date() for x in range(30)]
        exchanges = ['binance', 'bybit', 'okx']

        mock_data = []
        for exchange in exchanges:
            exchange_data = pd.DataFrame({
                'date': dates,
                'realized_pnl': 0,
                'exchange': 'failed'
            })
            mock_data.append(exchange_data)

        return pd.concat(mock_data, ignore_index=True)

    def aggregate_positions(self, positions: List[Dict], has_active_exchanges: bool) -> pd.DataFrame:
        """Aggregate positions data into a DataFrame"""
        if not positions:
            # Return empty DataFrame with correct columns
            return pd.DataFrame(columns=['exchange', 'symbol', 'raw_symbol', 'size', 'entry_price', 'current_price', 'pnl'])
        
        # Create DataFrame from positions
        df = pd.DataFrame(positions)
        
        # Sort by symbol for consistency
        df = df.sort_values('symbol')
        
        return df

    def calculate_daily_pnl(self, pnl_history: Dict[str, pd.DataFrame], has_active_exchanges: bool) -> pd.DataFrame:
        """Calculate daily PnL from balance history"""
        if not pnl_history:
            # Return empty DataFrame with correct columns
            return pd.DataFrame(columns=['date', 'exchange', 'realized_pnl'])
        
        # Combine all exchange PnL histories
        all_pnl = []
        for exchange, df in pnl_history.items():
            if not df.empty:
                # Ensure the DataFrame has the required columns
                if 'date' not in df.columns:
                    print(f"Warning: 'date' column missing in {exchange} PnL data")
                    continue
                if 'realized_pnl' not in df.columns:
                    print(f"Warning: 'realized_pnl' column missing in {exchange} PnL data")
                    continue
                
                df['exchange'] = exchange
                all_pnl.append(df)
                print(f"Added PnL data for {exchange}: {len(df)} records")
        
        if not all_pnl:
            print("No valid PnL data found")
            return pd.DataFrame(columns=['date', 'exchange', 'realized_pnl'])
            
        combined_pnl = pd.concat(all_pnl, ignore_index=True)
        print(f"Combined PnL data: {len(combined_pnl)} records")
        return combined_pnl

    def calculate_summary_metrics(self, positions_df: pd.DataFrame, daily_pnl: pd.DataFrame) -> Dict:
        """Calculate summary metrics from positions and PnL data"""
        metrics = {
            'total_pnl': 0.0,
            'daily_pnl': 0.0,
            'active_positions': '0',
            'exchange_pnl': {},
            'daily_pnl_by_exchange': {}
        }
        
        try:
            # Calculate total PnL from daily PnL data
            if not daily_pnl.empty:
                print("Calculating metrics from PnL data...")
                print(f"Daily PnL data shape: {daily_pnl.shape}")
                print(f"Daily PnL columns: {daily_pnl.columns.tolist()}")
                
                # Calculate total PnL (sum of all realized PnL)
                metrics['total_pnl'] = daily_pnl['realized_pnl'].sum()
                print(f"Total PnL: {metrics['total_pnl']}")
                
                # Calculate daily PnL (most recent day's PnL for each exchange)
                latest_pnl = daily_pnl.groupby('exchange').first()
                metrics['daily_pnl'] = latest_pnl['realized_pnl'].sum()
                print(f"Daily PnL: {metrics['daily_pnl']}")
                
                # Calculate PnL by exchange (total for each exchange)
                exchange_pnl = daily_pnl.groupby('exchange')['realized_pnl'].sum()
                metrics['exchange_pnl'] = exchange_pnl.to_dict()
                print(f"Exchange PnL: {metrics['exchange_pnl']}")
                
                # Calculate daily PnL by exchange (most recent for each)
                metrics['daily_pnl_by_exchange'] = latest_pnl['realized_pnl'].to_dict()
                print(f"Daily PnL by exchange: {metrics['daily_pnl_by_exchange']}")
            else:
                print("No daily PnL data available")
            
            # Count active positions
            if not positions_df.empty:
                metrics['active_positions'] = str(len(positions_df))
                print(f"Active positions: {metrics['active_positions']}")
            
        except Exception as e:
            print(f"Error calculating summary metrics: {str(e)}")
        
        return metrics