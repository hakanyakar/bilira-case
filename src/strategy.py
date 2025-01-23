import logging

from config import Config
from database import Database
from exchange import BinanceExchange
from redis_client import RedisManager
from utils import monitor_operation

class SMAStrategy:
    """
    BUY signals when the short-term average crosses above the long-term average, 
    and SELL signals when it crosses below
    """
    def __init__(self, database: Database, exchange: BinanceExchange, redis: RedisManager):
        self.database = database
        self.exchange = exchange
        self.redis = redis
        self.short_period = Config.SHORT_TERM_PERIOD
        self.long_period = Config.LONG_TERM_PERIOD
        self.order_quantity = Config.ORDER_QUANTITY
        self.strategy_time_interval = Config.STRATEGY_TIME_INTERVAL

    @monitor_operation("process_price")
    async def process_price(self, symbol: str, price: float):
        await self.database.save_price(symbol, price)
        await self.redis.set_price(symbol, price)


    @monitor_operation("sma_calculation")
    async def calculate_sma(self, period):
        cached_sma = await self.redis.get(f"{Config.TRADING_PAIR}:{period}")

        if not cached_sma:
            cached_sma = await self.redis.calculate_sma(Config.TRADING_PAIR, period)

        if cached_sma:
            return float(cached_sma)
            

    @monitor_operation("generate_signal")
    async def generate_signal(self):
        """
        Signal generation for sma crossover
        """
        last_signal = await self.database.select("*", "signals", "LIMIT 1", return_single=True)
        current_price = await self.database.select("price", "prices", "LIMIT 1", return_single=True)
        short_sma = await self.calculate_sma(self.short_period)
        long_sma = await self.calculate_sma(self.long_period)

        if not current_price:
            return 
        
        if not short_sma or not long_sma:
            return
        
        if not last_signal:
            if not short_sma or not long_sma:
                return
            else:
                if short_sma > long_sma:
                    signal_type = "BUY"
                else:
                    signal_type = "SELL"
        else:
            if short_sma > long_sma and last_signal['signal_type'] == "SELL":
                signal_type = "BUY"
            elif short_sma < long_sma and last_signal['signal_type'] == "BUY":
                signal_type = "SELL"
            else:
                return
            
        await self.database.save_signal(Config.TRADING_PAIR, signal_type, current_price['price'], short_sma, long_sma)
        logging.info(f"Generated {signal_type} signal at price {current_price['price']}")

        # Execute trade based on signal
        try:
            if signal_type == "BUY":
                order = await self.exchange.create_market_order(
                    symbol=Config.TRADING_PAIR,
                    side=signal_type,
                    quantity=self.order_quantity
                )
            elif signal_type == "SELL":
                order = await self.exchange.create_market_order(
                    symbol=Config.TRADING_PAIR,
                    side=signal_type,
                    quantity=self.order_quantity
                )
              
            await self.database.save_order(order['orderId'], Config.TRADING_PAIR, signal_type, order['origQty'], current_price['price'], order['status'])
            logging.info(f"Created {signal_type} order at {current_price['price']} price.")
        except Exception as e:
            logging.error(f"Failed to execute order: {str(e)}")
        

    