import asyncio
import logging
import uvicorn
import os
import signal

from fastapi import FastAPI, Request
from datetime import datetime
from prometheus_client import start_http_server
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from exchange import BinanceExchange
from database import Database
from utils import OPERATION_LATENCY, OPERATION_ERRORS, CPU_USAGE, MEMORY_USAGE, DATA_LOSS_COUNTER
from strategy import SMAStrategy
from redis_client import RedisManager



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
template_dir = os.path.join(BASE_DIR, "templates")

operations = ["process_price", "sma_calculation", "generate_signal", "create_market_order"]

db = Database()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "Trading Dashboard",
        }
    )


@app.get("/signals", response_class=HTMLResponse)
async def signals(request: Request):

    signals = await db.select(_columns='*', _from="signals")
    formatted_signals = []

    if signals:
        for signal in signals:

            formatted_signal = {
                "symbol": str(signal["symbol"]),
                "signal_type": str(signal["signal_type"]).upper(),
                "price": float(signal["price"]) if signal["price"] is not None else 0.0,
                "short_sma": float(signal["short_sma"]) if signal["short_sma"] is not None else 0.0,
                "long_sma": float(signal["long_sma"]) if signal["long_sma"] is not None else 0.0,
                "created_at": signal["created_at"] if isinstance(signal["created_at"], datetime) else datetime.now(),
            }
            formatted_signals.append(formatted_signal)

    
    return templates.TemplateResponse(
        "signals.html",
        {
            "request": request,
            "title": "Trading Dashboard",
            "signals": formatted_signals
        }
    )


@app.get("/orders", response_class=HTMLResponse)
async def orders(request: Request):

    orders = await db.select(_columns='*', _from="orders")
    formatted_orders = []

    if orders:
        for order in orders:
            formatted_order = {
                "order_id": str(order["order_id"]),
                "symbol": str(order["symbol"]),
                "side": str(order["side"]).upper(),
                "quantity": float(order["quantity"]) if order["quantity"] is not None else 0.0,
                "price": float(order["price"]) if order["price"] is not None else 0.0,
                "status": str(order["status"]).upper(),
                "created_at": order["created_at"] if isinstance(order["created_at"], datetime) else datetime.now(),
                "updated_at": order["updated_at"] if isinstance(order["updated_at"], datetime) else datetime.now(),
            }

            formatted_orders.append(formatted_order)

    return templates.TemplateResponse(
        "orders.html",
        {
            "request": request,
            "title": "Trading Dashboard",
            "orders": formatted_orders
        }
    )


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
