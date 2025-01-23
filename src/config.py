import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Exchange settings
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
    BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET')
    TRADING_PAIR = 'BTCUSDT'
    DEPTH = '5'
    USE_TESTNET = True
    
    # Strategy settings
    SHORT_TERM_PERIOD = 5
    LONG_TERM_PERIOD = 20
    ORDER_QUANTITY = 0.001
    STRATEGY_TIME_INTERVAL = 30

    # Database settings
    POSTGRES_HOST = os.getenv('POSTGRES_HOST')
    POSTGRES_DB = os.getenv('POSTGRES_DB')
    POSTGRES_USER = os.getenv('POSTGRES_USER')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
    
    # Redis settings
    REDIS_HOST = os.getenv('REDIS_HOST')
    REDIS_PORT = 6379