# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Wheel Strategy Options Backtesting Simulator - a test-driven, Dockerized backtester for the wheel options strategy (sell cash-secured puts → get assigned → sell covered calls → repeat).

## Commands

```bash
# Build and run in Docker
docker-compose build
docker-compose run wheel --help
docker-compose run wheel run SPY --capital 100000 --dte 30 --delta 0.20
docker-compose run wheel benchmark SPY --start 2020-01-01 --end 2024-12-31

# Run tests
docker-compose run test                    # All tests
docker-compose run test tests/unit/        # Unit tests only
docker-compose run test -k test_config     # Single test pattern

# Development shell
docker-compose run dev

# Web UI (Streamlit)
docker compose up ui              # Start at http://localhost:8501

# Local development (without Docker)
pip install -e .[dev]
pytest -v
wheel-backtest --help
```

## Architecture

```
src/wheel_backtest/
├── cli.py          # Click CLI entry point
├── config.py       # Pydantic settings (BacktestConfig)
├── data/           # Data providers (abstract base + implementations)
│   ├── provider.py         # OptionsDataProvider ABC
│   ├── philippdubach.py    # Free historical options data (2008-2025)
│   ├── yfinance_provider.py # Underlying prices (needed: philippdubach underlying is empty)
│   └── cache.py            # Disk caching layer
├── engine/         # Core backtesting logic
│   ├── portfolio.py   # Cash, shares, positions tracking
│   ├── options.py     # Strike selection by delta/DTE
│   ├── wheel.py       # State machine: SELLING_PUTS → HOLDING_STOCK → SELLING_CALLS
│   └── backtest.py    # Main simulation loop
├── analytics/      # Performance analysis
│   ├── metrics.py     # CAGR, Sharpe, drawdown
│   ├── benchmark.py   # Buy-and-hold comparison
│   └── equity.py      # Equity curve tracking
├── reports/        # Output generation
│   ├── transactions.py # CSV transaction log
│   └── charts.py       # Matplotlib visualizations
├── storage/        # Persistence
│   └── history.py     # SQLite backtest history
└── ui/             # Streamlit web interface
    └── app.py          # Main dashboard
```

## Key Design Decisions

| Decision | Choice | Notes |
|----------|--------|-------|
| Data Source | philippdubach/options-data | FREE, 24.6M records, full Greeks, 2008-2025, 104 tickers |
| Underlying Prices | yfinance | philippdubach underlying.parquet is empty |
| Fill Timing | End-of-day | All trades execute at EOD prices |
| Early Assignment | Ignored | Options only exercise at expiration |
| Mark-to-Market | Mid-price (bid+ask)/2 | For open position valuation |
| Rolling | None | Hold options to expiration |

## Data Provider

Primary data source: `https://static.philippdubach.com/data/options/{ticker}/options.parquet`

- Requires User-Agent header for downloads
- Options data validated: correct delta ranges, put-call parity holds
- Uses unadjusted underlying prices (options reference actual market prices)
- See `docs/DATA_SOURCES.md` for full research on alternatives (ORATS, EODHD, Polygon)

## Configuration

Environment variables prefixed with `WHEEL_`:
- `WHEEL_CACHE_DIR` - Data cache directory (default: ./cache)
- `WHEEL_OUTPUT_DIR` - Output directory (default: ./output)

## Implementation Status

- [x] Milestone 1: Docker + CLI + Config + Tests ✅ COMPLETE
- [x] Milestone 2: Data Providers + Caching ✅ COMPLETE
- [x] Milestone 3: Buy-and-Hold Benchmark ✅ COMPLETE
- [x] Milestone 4: Portfolio + Wheel Engine ✅ COMPLETE
- [x] Milestone 5: Full Backtest Integration ✅ COMPLETE
- [x] Milestone 6: Delta-Based Strike Selection ✅ COMPLETE
- [x] Milestone 7: Performance Metrics & Charts ✅ COMPLETE
- [ ] Milestone 8: Backtest History Storage (NEXT)
- [ ] Milestone 9: Streamlit Web UI

Full implementation plan: `.claude/plans/mighty-jumping-flurry.md`
