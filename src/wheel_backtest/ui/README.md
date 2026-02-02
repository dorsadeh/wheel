# Wheel Strategy Backtester - Web UI

Interactive Streamlit web interface for the wheel options backtesting simulator.

## Features

### 🏠 Dashboard
- Overview of recent backtests
- Quick statistics (total backtests, average returns, best performance)
- Easy navigation to all features

### 🚀 Run Backtest
- Interactive form for configuring backtests
- Real-time parameter selection with sliders
- Instant results display with key metrics
- Automatic saving to history database

### 📊 History
- View all past backtests in a searchable table
- Filter by ticker symbol
- Sort by any metric (CAGR, Sharpe, returns, etc.)
- View detailed records
- Delete old backtests

### 🔍 Analysis
- Deep dive into specific backtest results
- Interactive equity curve charts
- Drawdown visualization
- Complete transaction log
- Downloadable CSV exports
- Full configuration details

### 📈 Benchmark
- Calculate buy-and-hold performance
- Compare passive vs. active strategies
- Equity curve and drawdown charts
- Cumulative returns visualization
- Export benchmark data

## Usage

### Start the UI

Using Docker (recommended):
```bash
docker compose up ui
```

Visit: http://localhost:8501

### Local Development

```bash
streamlit run src/wheel_backtest/ui/app.py
```

## Configuration

The UI uses environment variables for configuration:
- `WHEEL_CACHE_DIR` - Data cache directory (default: ./cache)
- `WHEEL_OUTPUT_DIR` - Output files directory (default: ./output)

These are automatically set in the Docker environment.

## Navigation

The UI uses Streamlit's multi-page app structure:
- Main page: Dashboard overview
- Page 1: Run new backtests
- Page 2: View history
- Page 3: Analyze specific backtests
- Page 4: Calculate benchmarks

Use the sidebar to navigate between pages.

## Tips

1. **Start with a short backtest**: Use 1-3 months of data to test configurations quickly
2. **Compare multiple runs**: Use the history page to identify best parameter combinations
3. **Benchmark everything**: Always compare your wheel strategy results against buy-and-hold
4. **Export data**: Download CSVs for further analysis in Excel or Python
5. **Track git commits**: The history saves git commit hashes for reproducibility

## Technical Notes

- Built with Streamlit 1.30+
- Uses SQLite for persistent history storage
- Charts generated using Streamlit's native charting (built on Altair)
- All computations run server-side (safe for sensitive data)
- No external analytics or tracking

## Troubleshooting

**UI won't start:**
- Ensure Streamlit is installed: `pip install streamlit>=1.30.0`
- Check port 8501 is available
- Verify Docker is running (if using Docker)

**No backtests showing:**
- Run a backtest first using the "Run Backtest" page
- Check that cache directory is accessible
- Verify database file exists: `./cache/backtest_history.db`

**Charts not displaying:**
- Ensure CSV files exist in the output directory
- Check file paths in backtest records
- Verify pandas can read the CSV files

**Performance issues:**
- Limit number of displayed records
- Use date ranges instead of full history
- Clear old backtests from history database
- Ensure cache directory has enough space
