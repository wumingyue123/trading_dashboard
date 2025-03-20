from typing import Dict, Any, Optional
import logging
from datetime import datetime, timedelta

class FeeTracker:
    def __init__(self, exchange_client):
        self.exchange_client = exchange_client
        self.fees: Dict[str, float] = {
            'binance': 0.0,
            'bybit': 0.0,
            'okx': 0.0,
            'hyperliquid': 0.0,
            'rabbitx': 0.0
        }
        
    async def update_fees(self) -> Dict[str, float]:
        """Update and return trading fees for all exchanges"""
        try:
            # Reset fees at the start of update
            self.fees = {
                'binance': 0.0,
                'bybit': 0.0,
                'okx': 0.0,
                'hyperliquid': 0.0,
                'rabbitx': 0.0
            }

            # Binance Fees
            if self.exchange_client.binance_client:
                try:
                    # Get active positions first
                    positions = self.exchange_client.get_positions('binance')
                    active_symbols = set(pos['raw_symbol'] for pos in positions)

                    # Get trading fee info for the last 30 days
                    fee_history = self.exchange_client.binance_client.fapiPrivateGetIncome({
                        'incomeType': 'COMMISSION',
                        'startTime': int((datetime.now() - timedelta(days=30)).timestamp() * 1000),
                        'endTime': int(datetime.now().timestamp() * 1000)
                    })
                    self.fees['binance'] = abs(sum(float(entry['income']) for entry in fee_history))

                    # Get fee rates for active symbols
                    for symbol in active_symbols:
                        try:
                            fee_info = self.exchange_client.binance_client.fapiPrivateGetCommissionRate({
                                'symbol': symbol
                            })
                            if fee_info:
                                maker_rate = float(fee_info.get('makerCommissionRate', 0))
                                taker_rate = float(fee_info.get('takerCommissionRate', 0))
                                logging.info(f"Binance fee rates for {symbol}: Maker={maker_rate}, Taker={taker_rate}")
                        except Exception as e:
                            logging.error(f"Error fetching Binance fee rates for {symbol}: {e}")

                    logging.info(f"Successfully fetched Binance fees: {self.fees['binance']}")
                except Exception as e:
                    logging.error(f"Error fetching Binance fees: {e}")

            # Bybit Fees
            if self.exchange_client.bybit_client:
                try:
                    # First get all active positions to know which symbols to check
                    positions = self.exchange_client.get_positions('bybit')
                    active_symbols = set(pos['raw_symbol'] for pos in positions)
                    total_fees = 0.0

                    # Get trading history for fees
                    fee_history = self.exchange_client.bybit_client.get_wallet_fund_records(
                        accountType="UNIFIED",
                        coin="USDT",
                        walletFundType="TRADING_FEE"
                    )
                    if fee_history and 'result' in fee_history and 'list' in fee_history['result']:
                        total_fees = abs(sum(float(entry['amount']) for entry in fee_history['result']['list']))

                    # Get current fee rates for active symbols
                    for symbol in active_symbols:
                        try:
                            fee_rates = self.exchange_client.bybit_client.get_fee_rates(
                                category="linear",
                                symbol=symbol
                            )
                            if fee_rates and 'result' in fee_rates and 'list' in fee_rates['result']:
                                fee_info = fee_rates['result']['list'][0]
                                logging.info(f"Bybit fee rates for {symbol}: Maker={fee_info['makerFeeRate']}, Taker={fee_info['takerFeeRate']}")
                        except Exception as e:
                            logging.error(f"Error fetching Bybit fee rates for {symbol}: {e}")

                    self.fees['bybit'] = total_fees
                    logging.info(f"Successfully fetched Bybit fees: {self.fees['bybit']}")
                except Exception as e:
                    logging.error(f"Error fetching Bybit fees: {e}")

            # OKX Fees
            if self.exchange_client.okx_client:
                try:
                    # Get active positions
                    positions = self.exchange_client.get_positions('okx')
                    active_symbols = set(pos['raw_symbol'] for pos in positions)

                    # Get bills history for trading fees
                    fee_history = self.exchange_client.okx_client.fetch_ledger(
                        params={'type': 'fee'}
                    )
                    self.fees['okx'] = abs(sum(abs(float(entry['fee'])) for entry in fee_history if entry.get('fee')))

                    # Get fee rates for active instruments
                    for symbol in active_symbols:
                        try:
                            fee_info = self.exchange_client.okx_client.fetch_trading_fee(symbol)
                            if fee_info:
                                maker_rate = float(fee_info.get('maker', 0))
                                taker_rate = float(fee_info.get('taker', 0))
                                logging.info(f"OKX fee rates for {symbol}: Maker={maker_rate}, Taker={taker_rate}")
                        except Exception as e:
                            logging.error(f"Error fetching OKX fee rates for {symbol}: {e}")

                    logging.info(f"Successfully fetched OKX fees: {self.fees['okx']}")
                except Exception as e:
                    logging.error(f"Error fetching OKX fees: {e}")

            # RabbitX Fees
            if self.exchange_client.rabbitx_client:
                try:
                    # Get active positions
                    positions = self.exchange_client.get_positions('rabbitx')
                    active_symbols = set(pos['raw_symbol'] for pos in positions)

                    # Get trading history and calculate fees
                    trades = self.exchange_client.rabbitx_client.trades.list(p_limit=100)
                    self.fees['rabbitx'] = abs(sum(float(trade.get('fee', 0)) for trade in trades))

                    # Get fee tiers if available
                    try:
                        account_info = self.exchange_client.rabbitx_client.account.info()
                        if account_info:
                            maker_rate = float(account_info.get('makerFee', 0))
                            taker_rate = float(account_info.get('takerFee', 0))
                            logging.info(f"RabbitX fee rates: Maker={maker_rate}, Taker={taker_rate}")
                    except Exception as e:
                        logging.error(f"Error fetching RabbitX fee rates: {e}")

                    logging.info(f"Successfully fetched RabbitX fees: {self.fees['rabbitx']}")
                except Exception as e:
                    logging.error(f"Error fetching RabbitX fees: {e}")

            # Hyperliquid Fees
            if self.exchange_client._hyperliquid_api_key and self.exchange_client._hyperliquid_secret:
                try:
                    # Get active positions
                    positions = self.exchange_client.get_positions('hyperliquid')
                    active_symbols = set(pos['raw_symbol'] for pos in positions)

                    # Get trading history from Hyperliquid
                    response = self.exchange_client._make_hyperliquid_request(
                        '/info',
                        method='POST',
                        data={
                            "type": "userFills",
                            "user": self.exchange_client._hyperliquid_api_key
                        }
                    )
                    if response:
                        self.fees['hyperliquid'] = abs(sum(float(fill.get('fee', 0)) for fill in response))

                        # Get fee tiers if available
                        try:
                            user_state = self.exchange_client._make_hyperliquid_request(
                                '/info',
                                method='POST',
                                data={
                                    "type": "userState",
                                    "user": self.exchange_client._hyperliquid_api_key
                                }
                            )
                            if user_state:
                                maker_rate = float(user_state.get('makerFeeRate', 0))
                                taker_rate = float(user_state.get('takerFeeRate', 0))
                                logging.info(f"Hyperliquid fee rates: Maker={maker_rate}, Taker={taker_rate}")
                        except Exception as e:
                            logging.error(f"Error fetching Hyperliquid fee rates: {e}")

                        logging.info(f"Successfully fetched Hyperliquid fees: {self.fees['hyperliquid']}")
                except Exception as e:
                    logging.error(f"Error fetching Hyperliquid fees: {e}")

            logging.info(f"Updated fees for all exchanges: {self.fees}")
            return self.fees

        except Exception as e:
            logging.error(f"Error updating fees: {e}")
            return self.fees

    def get_total_fees(self) -> float:
        """Get total fees across all exchanges"""
        return sum(self.fees.values())

    def get_fees_by_exchange(self) -> Dict[str, float]:
        """Get fees broken down by exchange"""
        return self.fees.copy() 