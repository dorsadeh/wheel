# Wheel Strategy Backtester

A test-driven options backtesting simulator for the wheel strategy.

## Quick Start

```bash
# Build
docker compose build

# Run backtest
docker compose run wheel run SPY --capital 100000 --dte 30 --delta 0.20

# Run tests
docker compose run test

# Run web UI
docker compose up ui              # Start at http://localhost:8501
```

## What is the Wheel Strategy?

1. **Sell cash-secured puts** on a stock you want to own
2. **If assigned**, you now own shares at the strike price
3. **Sell covered calls** against those shares
4. **If called away**, you sell shares at the strike price
5. **Repeat** from step 1

## Features

- Delta-based strike selection
- Full transaction log with P/L tracking
- Equity curve visualization
- Buy-and-hold benchmark comparison
- Configurable DTE, delta targets, and commissions

## Documentation

- [Data Sources Research](docs/DATA_SOURCES.md) - Options data providers comparison
