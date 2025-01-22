import redis
import logging
from config import Config
from datetime import datetime
import numpy as np
import json

class RedisManager:
    def __init__(self):
        self.client = redis.Redis(
            host=Config.REDIS_HOST,
            port=Config.REDIS_PORT,
            decode_responses=True
        )

        self.client.flushall()
    
    async def set_sma(self, key, value):
        """
        Set a sma in Redis for the given pair.
        """
        self.client.set(key, value)


    async def get(self, key):
        """
        Get value for spesific key.
        """
        return self.client.get(key)

    async def set_price(self, key, price):
        """
        Set a price in Redis for the given pair with the current timestamp.
        """

        time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        time_score = datetime.now().timestamp()
        
        data = {
            'price': float(price),
            'time': time_str
        }

        self.client.zadd(key, {json.dumps(data): time_score})

    async def calculate_sma(self, pair, window):
        """
        Calculate the Simple Moving Average (SMA) for a given pair over a specified window size.
        """
        try:
            # Get latest prices from Redis
            prices = self.client.zrange(pair, -window, -1, withscores=True)

            if len(prices) < window:
                logging.info(f"Not enough data to calculate SMA for {pair} ({window})")
                return None

            price_values = [
                float(json.loads(price_data[0])['price']) 
                for price_data in prices
            ]

            sma = np.mean(price_values)
        
            return float(sma)

        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON data: {e}")
            return None
        except Exception as e:
            logging.error(f"Error calculating SMA: {e}")
            return None
