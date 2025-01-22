import asyncio
import logging
import uvicorn
from fastapi import FastAPI
from datetime import datetime
from prometheus_client import start_http_server

from exchange import BinanceExchange
from database import Database
from utils import OPERATION_LATENCY, OPERATION_ERRORS, CPU_USAGE, MEMORY_USAGE, DATA_LOSS_COUNTER
from strategy import SMAStrategy
from redis_client import RedisManager



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

operations = ["process_price", "sma_calculation", "generate_signal", "create_market_order"]


@app.get("/api/monitoring/performance")
async def get_performance_metrics():
    """Get performance metrics for operations"""
    
    metrics = {}
    for name in operations:
        try:
            latency_samples = list(OPERATION_LATENCY.labels(operation_name=name).collect()[0].samples)
            cpu_samples = list(CPU_USAGE.labels(operation_name=name).collect()[0].samples)
            memory_samples = list(MEMORY_USAGE.labels(operation_name=name).collect()[0].samples)
            
            metrics[name] = {
                "latency": {
                    "sum": next((s.value for s in latency_samples if s.name.endswith('_sum')), 0),
                    "count": next((s.value for s in latency_samples if s.name.endswith('_count')), 0),
                },
                "cpu_usage_percent": next((s.value for s in cpu_samples), 0),
                "memory_usage_bytes": next((s.value for s in memory_samples), 0)
            }
            
            # Calculate average if count > 0
            if metrics[name]["latency"]["count"] > 0:
                metrics[name]["latency"]["average"] = (
                    metrics[name]["latency"]["sum"] / metrics[name]["latency"]["count"]
                )
            else:
                metrics[name]["latency"]["average"] = 0
                
        except Exception as e:
            logging.error(f"Error getting metrics for {name}: {str(e)}")
            metrics[name] = {
                "latency": {"sum": 0, "count": 0, "average": 0},
                "cpu_usage_percent": 0,
                "memory_usage_bytes": 0,
                "error": str(e)
            }
    
    return {
        "metrics": metrics,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/monitoring/errors")
async def get_error_metrics():
    """Get error metrics for operations"""
    errors = {}
    data_loss = {}
        
    for name in operations:
        errors[name] = OPERATION_ERRORS.labels(operation_name=name, error_type="Exception")._value.get()
        
        data_loss[name] = DATA_LOSS_COUNTER.labels(operation_name=name)._value.get()
    
    return {
        "errors": errors,
        "data_loss": data_loss
    }

class TradingApp:
    def __init__(self):
        self.database = Database()
        self.exchange = BinanceExchange(self.process_price)
        self.redis = RedisManager()
        self.strategy = SMAStrategy(self.database, self.exchange, self.redis)


    async def process_price(self, symbol: str, price: float):
        try:            
            await self.strategy.process_price(symbol, price)     
        except Exception as e:
            logger.error(f"Error processing price: {e}")

    async def start(self):
        try:
            await self.exchange.start()
        except Exception as e:
            logger.error(f"Application error: {e}")

    async def run_strategy(self):
        while True:
            try:
                await self.strategy.generate_signal()
                await asyncio.sleep(self.strategy.strategy_time_interval)  # Check for signals every x seconds
            except Exception as e:
                logging.error(f"Strategy error: {e}")
                await asyncio.sleep(5)

    async def main(self):
        trading_app = TradingApp()
        start_http_server(8000)  # Prometheus metrics endpoint
    
        config = uvicorn.Config(app, host="0.0.0.0", port=8080, loop="asyncio")
        server = uvicorn.Server(config)
    
        await asyncio.gather(
            trading_app.start(),
            trading_app.run_strategy(),
            server.serve()
        )


if __name__ == "__main__":
    asyncio.run(TradingApp().main()) 

    