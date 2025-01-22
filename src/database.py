import psycopg2
from psycopg2.extras import RealDictCursor
from config import Config
from datetime import datetime

class Database:
    def __init__(self):
        self.conn = psycopg2.connect(
            host=Config.POSTGRES_HOST,
            database=Config.POSTGRES_DB,
            user=Config.POSTGRES_USER,
            password=Config.POSTGRES_PASSWORD
        )
        self.create_tables()
    
    def create_tables(self):
        with self.conn.cursor() as cur:
            # Create price table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS prices (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP,
                    symbol VARCHAR(20),
                    price DECIMAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create orders table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id SERIAL PRIMARY KEY,
                    order_id VARCHAR(50),
                    symbol VARCHAR(20),
                    side VARCHAR(10),
                    quantity DECIMAL,
                    price DECIMAL,
                    status VARCHAR(20),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create signals table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP,
                    symbol VARCHAR(20),
                    signal_type VARCHAR(10),
                    price DECIMAL,
                    short_sma DECIMAL,
                    long_sma DECIMAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        self.conn.commit()

    async def select(self, _columns = "*", _from = "", _limit = ""):

        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(f"SELECT {_columns} FROM {_from} ORDER BY id DESC {_limit}")
            result = cur.fetchall()
        
            if len(result) == 1:
                return result[0]
            elif len(result) > 1:
                return result
            else:
                return None
            
        
    async def save_price(self, symbol: str, price: float):
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO prices (timestamp, symbol, price) VALUES (%s, %s, %s)",
                (datetime.now(), symbol, price)
            )
        self.conn.commit()


    async def save_signal(self, symbol: str, signal_type: str, price: float, short_sma: float, long_sma: float):
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO signals (timestamp, symbol, signal_type, price, short_sma, long_sma) VALUES (%s, %s, %s, %s, %s, %s)",
                (datetime.now(), symbol, signal_type, price, short_sma, long_sma)
            )
        self.conn.commit()


    async def save_order(self, order_id: int, symbol: str, side: str, quantity: float, price: float, status: str):
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO orders (order_id, symbol, side, quantity, price, status) VALUES (%s, %s, %s, %s, %s, %s)",
                (order_id, symbol, side, quantity, price, status)
            )
        self.conn.commit()