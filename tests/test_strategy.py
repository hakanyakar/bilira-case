import pytest
from unittest.mock import Mock, AsyncMock, patch
import sys
import os


# Add src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Mock Config class
class MockConfig:
    TRADING_PAIR = 'BTCUSDT'
    SHORT_TERM_PERIOD = 5
    LONG_TERM_PERIOD = 10
    ORDER_QUANTITY = 0.001

# Import strategy after setting up MockConfig
with patch('src.config.Config', MockConfig):
    from src.strategy import SMAStrategy

class TestSMAStrategy:
    @pytest.fixture
    async def strategy_setup(self):
        """Setup strategy with mocked data"""
        database = Mock()
        exchange = Mock()
        redis = Mock()
        
        # Setup async mocks
        database.save_price = AsyncMock()
        database.save_signal = AsyncMock()
        database.select = AsyncMock()
        redis.set_price = AsyncMock()
        redis.get = AsyncMock()
        redis.calculate_sma = AsyncMock()
        exchange.create_market_order = AsyncMock()
        
        strategy = SMAStrategy(database, exchange, redis)
        return strategy, database, exchange, redis

    @pytest.mark.asyncio
    async def test_process_price(self, strategy_setup):
        """Test price processing functionality"""
        strategy, database, _, redis = strategy_setup
        
        symbol = MockConfig.TRADING_PAIR
        price = 50000.0
        
        await strategy.process_price(symbol, price)
        
        database.save_price.assert_called_once_with(symbol, price)
        redis.set_price.assert_called_once_with(symbol, price)

    @pytest.mark.asyncio
    async def test_calculate_sma_with_cache(self, strategy_setup):
        """Test SMA calculation with cached value"""
        strategy, _, _, redis = strategy_setup
        
        period = 10
        cached_value = "50000.0"
        redis.get.return_value = cached_value
        
        result = await strategy.calculate_sma(period)
        
        assert result == float(cached_value)
        redis.calculate_sma.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_buy_signal(self, strategy_setup):
        """Test buy signal generation"""
        strategy, database, exchange, _ = strategy_setup
        
        current_price = {'price': 50000.0}
        database.select.side_effect = [None, current_price]
        strategy.calculate_sma = AsyncMock(side_effect=[51000.0, 49000.0])
        
        await strategy.generate_signal()
        
        database.save_signal.assert_called_once()
        call_args = database.save_signal.call_args[0]
        assert call_args[1] == "BUY"
        exchange.create_market_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_sell_signal(self, strategy_setup):
        """Test sell signal generation"""
        strategy, database, exchange, _ = strategy_setup
        
        # Setup
        current_price = {'price': 50000.0}
        database.select.side_effect = [{'signal_type': 'BUY'}, current_price]
        strategy.calculate_sma = AsyncMock(side_effect=[48000.0, 50000.0])
        
        # Execute
        await strategy.generate_signal()
        
        # Assert
        database.save_signal.assert_called_once()
        call_args = database.save_signal.call_args[0]
        assert call_args[1] == "SELL"
        exchange.create_market_order.assert_called_once()
