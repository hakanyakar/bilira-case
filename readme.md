# Bilira Case Project Algorithmic Trading

A Python-based cryptocurrency trading bot that implements a Simple Moving Average (SMA) crossover strategy for automated trading on Binance.

## Features

- Real-time price monitoring via Binance orderbook WebSocket
- SMA crossover strategy implementation
- PostgreSQL database for storing prices, signals, and orders
- Redis caching for optimized SMA calculations
- Prometheus metrics for monitoring
- FastAPI endpoints for metrics and monitoring
- Unit tests

## Prerequisites

- Docker and Docker Compose
- Binance API credentials

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/crypto-trading-bot.git
```

2. Navigate to the project directory:

```bash
cd crypto-trading-bot
```

2. Create a `.env` file with your configuration:



2. Services:
- Trading Bot API: `http://localhost:8080`
- Prometheus metrics: `http://localhost:8000`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`


Edit `src/config.py` to customize trading parameters:
- Trading pair
- SMA periods
- Order quantity
- Database settings
- Redis settings


## Strategy Details

The bot implements a Simple Moving Average (SMA) crossover strategy:
- Generates BUY signals when short-term SMA crosses above long-term SMA
- Generates SELL signals when short-term SMA crosses below long-term SMA
- Uses Redis caching for efficient SMA calculations
- Stores all signals and trades in PostgreSQL database

## Monitoring

The bot includes comprehensive monitoring:
- Operation latency
- CPU and memory usage
- Error counts
- Data loss events
- Trading signals and executions

Access monitoring endpoints:
- Performance metrics: `http://localhost:8080/api/monitoring/performance`
- Error metrics: `http://localhost:8080/api/monitoring/errors`
- Prometheus metrics: `http://localhost:8000`
