import pytest
from typing import Dict, List, Any, Optional, Union, TYPE_CHECKING
import pandas as pd
from utils.data_processor import DataProcessor

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


class TestDataProcessor:
    """Test cases for the DataProcessor class."""
    
    def test_normalize_symbol_standard(self) -> None:
        """Test normalize_symbol with standard symbols without multipliers."""
        dp = DataProcessor()
        
        # Test standard symbols
        assert dp.normalize_symbol("BTC") == "BTC"
        assert dp.normalize_symbol("ETH") == "ETH"
        assert dp.normalize_symbol("SOL") == "SOL"
        
        # Test with various USDT suffixes
        assert dp.normalize_symbol("BTC/USDT") == "BTC"
        assert dp.normalize_symbol("ETH-USDT") == "ETH"
        assert dp.normalize_symbol("SOL:USDT") == "SOL"
        assert dp.normalize_symbol("BTC/USDT:USDT") == "BTC"
        assert dp.normalize_symbol("ETH-USD") == "ETH"
        assert dp.normalize_symbol("SOL/USD") == "SOL"
        
        # Test with SWAP suffix (OKX specific)
        assert dp.normalize_symbol("BTC-USDT-SWAP") == "BTC"
        assert dp.normalize_symbol("ETH-SWAP") == "ETH"
        
        # Test with special mappings
        assert dp.normalize_symbol("SOLAYER") == "LAYER"

    def test_normalize_symbol_rabbitx_format(self) -> None:
        """Test normalize_symbol with RabbitX specific format (without separator)."""
        dp = DataProcessor()
        
        # Test RabbitX format without separators
        assert dp.normalize_symbol("BTCUSD") == "BTC"
        assert dp.normalize_symbol("ETHUSD") == "ETH"
        assert dp.normalize_symbol("SOLUSD") == "SOL"
        assert dp.normalize_symbol("PEPE1000USD") == "PEPE"
        assert dp.normalize_symbol("TOSHI1000USD") == "TOSHI"
    def test_normalize_symbol_multipliers_at_start(self) -> None:
        """Test normalize_symbol with formats having multipliers at the beginning (Bybit, Binance, OKX)."""
        dp = DataProcessor()
        
        # Test 1000x multiplier (e.g., 1000PEPE)
        assert dp.normalize_symbol("1000PEPE") == "PEPE"
        assert dp.normalize_symbol("1000TOSHI") == "TOSHI"
        assert dp.normalize_symbol("1000PEPE/USDT") == "PEPE"
        assert dp.normalize_symbol("1000SOL-USDT") == "SOL"
        
        # Test 1M multiplier (e.g., 1MPEPE)
        assert dp.normalize_symbol("1MPEPE") == "PEPE"
        assert dp.normalize_symbol("1MTOSHI") == "TOSHI"
        assert dp.normalize_symbol("1MPEPE/USDT") == "PEPE"
        
        # Test 1000000 multiplier
        assert dp.normalize_symbol("1000000PEPE") == "PEPE"
        assert dp.normalize_symbol("1000000TOSHI") == "TOSHI"
        assert dp.normalize_symbol("1000000SOL-USDT") == "SOL"
    
    def test_normalize_symbol_hyperliquid_format(self) -> None:
        """Test normalize_symbol with Hyperliquid's 'k' prefix format."""
        dp = DataProcessor()
        
        # Test k prefix (e.g., kPEPE)
        assert dp.normalize_symbol("kPEPE") == "PEPE"
        assert dp.normalize_symbol("kTOSHI") == "TOSHI"
        assert dp.normalize_symbol("kSOL") == "SOL"
        
        # Edge cases
        assert dp.normalize_symbol("k") == "k"  # Should not change if only 'k'
        assert dp.normalize_symbol("ktest") == "ktest"  # Shouldn't change if second char is not uppercase
    
    def test_normalize_symbol_multipliers_at_end(self) -> None:
        """Test normalize_symbol with RabbitX format (multiplier at end)."""
        dp = DataProcessor()
        
        # Test 1000x multiplier at end (e.g., TOSHI1000)
        assert dp.normalize_symbol("PEPE1000") == "PEPE"
        assert dp.normalize_symbol("TOSHI1000") == "TOSHI"
        assert dp.normalize_symbol("SOL1000") == "SOL"
        
        # Test 1M or 1000000 multiplier at end
        assert dp.normalize_symbol("PEPE1M") == "PEPE"
        assert dp.normalize_symbol("TOSHI1000000") == "TOSHI"
        
        # Non-multiplier numbers at the end (should not change)
        assert dp.normalize_symbol("BTC100") == "BTC100"  # Not a standard multiplier
        assert dp.normalize_symbol("ETH123") == "ETH123"  # Not a standard multiplier
    
    def test_normalize_symbol_complex_cases(self) -> None:
        """Test normalize_symbol with complex and edge cases."""
        dp = DataProcessor()
        
        # Combined formats
        assert dp.normalize_symbol("1000PEPE-USDT-SWAP") == "PEPE"
        assert dp.normalize_symbol("kSOL/USDT") == "SOL"
        assert dp.normalize_symbol("TOSHI1000-USD") == "TOSHI"
        
        # Non-standard symbols that should remain unchanged
        assert dp.normalize_symbol("BTC-ETH") == "BTC-ETH"
        assert dp.normalize_symbol("100X") == "100X"  # Not a standard multiplier format
        
        # Case sensitivity
        assert dp.normalize_symbol("btc") == "btc"  # Lowercase should remain lowercase
        assert dp.normalize_symbol("1000btc") == "1000btc"  # No change if second part not uppercase
    
    def test_extract_price_multiplier(self) -> None:
        """Test extract_price_multiplier method."""
        dp = DataProcessor()
        
        # Standard symbols (no multiplier)
        assert dp.extract_price_multiplier("BTC") == 1.0
        assert dp.extract_price_multiplier("ETH/USDT") == 1.0
        assert dp.extract_price_multiplier("SOL-USDT-SWAP") == 1.0
        
        # Bybit/Binance/OKX format (multiplier at start)
        assert dp.extract_price_multiplier("1000PEPE") == 1000.0
        assert dp.extract_price_multiplier("1000TOSHI/USDT") == 1000.0
        assert dp.extract_price_multiplier("1MPEPE") == 1000000.0
        assert dp.extract_price_multiplier("1000000SOL") == 1000000.0
        
        # Hyperliquid format (k prefix)
        assert dp.extract_price_multiplier("kPEPE") == 1000.0
        assert dp.extract_price_multiplier("kSOL/USDT") == 1000.0
        
        # RabbitX format (multiplier at end)
        assert dp.extract_price_multiplier("PEPE1000") == 1000.0
        assert dp.extract_price_multiplier("TOSHI1M") == 1000000.0
        assert dp.extract_price_multiplier("SOL1000000") == 1000000.0
        
        # Edge cases
        assert dp.extract_price_multiplier("BTC100") == 1.0  # Not a standard multiplier
        assert dp.extract_price_multiplier("k") == 1.0  # Just 'k' is not a multiplier
        assert dp.extract_price_multiplier("ktest") == 1.0  # Second char not uppercase 