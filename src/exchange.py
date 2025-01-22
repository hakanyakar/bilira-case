import logging
from binance import BinanceSocketManager
from binance import AsyncClient, BinanceSocketManager

from config import Config
from utils import monitor_operation


class BinanceExchange:
    def __init__(self, price_callback):
        self.client = AsyncClient(
            Config.BINANCE_API_KEY, 
            Config.BINANCE_API_SECRET,
            testnet=Config.USE_TESTNET
        )
        self.bm = BinanceSocketManager(self.client)
        self.depth_ts = self.bm.depth_socket(Config.TRADING_PAIR, Config.DEPTH)

        self.price_callback = price_callback

    async def start(self):
        await self.handle_order_book_message()

    async def handle_order_book_message(self):
        try:
            async with self.depth_ts as tscm:
                while True:
                    res = await tscm.recv()
                    bids = res['bids']
                    asks = res['asks']

                    mid_price = (float(bids[0][0]) + float(asks[0][0])) / 2
                    await self.price_callback(Config.TRADING_PAIR, mid_price)

            await self.client.close_connection()
        except Exception as e:
            logging.error(f"Error processing message: {e}")

    @monitor_operation('create_market_order')
    async def create_market_order(self, symbol: str, side: str, quantity: float):
        """
        Create market order.
        """
        try:
            order = await self.client.create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=quantity
            )
            return order
        except Exception as e:
            logging.error(f"Market order creation error: {e}")
            return None 