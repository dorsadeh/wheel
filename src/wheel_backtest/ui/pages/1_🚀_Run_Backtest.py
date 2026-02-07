"""Page for configuring and running new backtests."""

import json
from datetime import date, timedelta
from pathlib import Path

import streamlit as st
from wheel_backtest.config import BacktestConfig
from wheel_backtest.data.philippdubach import DATA_END_DATE, DATA_START_DATE
from wheel_backtest.engine import WheelBacktest
from wheel_backtest.ui.components import display_results_tabs
from wheel_backtest.ui.utils import get_cache_dir, get_history, get_output_dir

st.set_page_config(
    page_title="Run Backtest",
    page_icon="🚀",
    layout="wide",
)


def _get_last_config_path() -> Path:
    """Get path to last config file."""
    return get_cache_dir() / ".last_backtest_config.json"


def _load_last_config() -> dict | None:
    """Load the last backtest configuration."""
    config_path = _get_last_config_path()
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                data = json.load(f)
                # Convert date strings back to date objects
                if "start_date" in data and data["start_date"]:
                    data["start_date"] = date.fromisoformat(data["start_date"])
                if "end_date" in data and data["end_date"]:
                    data["end_date"] = date.fromisoformat(data["end_date"])
                return data
        except Exception:
            return None
    return None


def _save_last_config(
    ticker: str,
    date_range_preset: str,
    start_date: date,
    end_date: date,
    initial_capital: float,
    dte_target: int,
    dte_min: int,
    put_delta: float,
    call_delta: float,
    commission: float,
    enable_call_entry_protection: bool,
    call_entry_protection_dollars: float,
) -> None:
    """Save the last backtest configuration."""
    config_path = _get_last_config_path()
    config_data = {
        "ticker": ticker,
        "date_range_preset": date_range_preset,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "initial_capital": initial_capital,
        "dte_target": dte_target,
        "dte_min": dte_min,
        "put_delta": put_delta,
        "call_delta": call_delta,
        "commission": commission,
        "enable_call_entry_protection": enable_call_entry_protection,
        "call_entry_protection_dollars": call_entry_protection_dollars,
    }
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=2)
    except Exception:
        pass  # Silently fail if we can't save


def main():
    """Run backtest page."""
    st.title("🚀 Run New Backtest")
    st.markdown("Configure and execute a wheel strategy backtest")
    st.markdown("---")

    # Load last configuration
    last_config = _load_last_config()

    # Set defaults from last config or use hardcoded defaults
    default_ticker = last_config.get("ticker", "SPY") if last_config else "SPY"
    default_initial_capital = last_config.get("initial_capital", 100_000.0) if last_config else 100_000.0
    default_date_range = last_config.get("date_range_preset", "Last 1 Year") if last_config else "Last 1 Year"
    default_start = last_config.get("start_date", date(2023, 1, 1)) if last_config else date(2023, 1, 1)
    default_end = last_config.get("end_date", date(2023, 12, 31)) if last_config else date(2023, 12, 31)
    default_dte_target = last_config.get("dte_target", 30) if last_config else 30
    default_dte_min = last_config.get("dte_min", 7) if last_config else 7
    default_put_delta = last_config.get("put_delta", 0.30) if last_config else 0.30
    default_call_delta = last_config.get("call_delta", 0.30) if last_config else 0.30
    default_commission = last_config.get("commission", 0.0) if last_config else 0.0
    default_enable_protection = last_config.get("enable_call_entry_protection", False) if last_config else False
    default_protection_dollars = last_config.get("call_entry_protection_dollars", 0.0) if last_config else 0.0

    # Build help text with data availability info
    help_text = "Select a preset date range or choose Custom Range to specify exact dates"
    if date.today() > DATA_END_DATE:
        help_text += f" (Data available: {DATA_START_DATE.strftime('%Y-%m-%d')} to {DATA_END_DATE.strftime('%Y-%m-%d')})"

    # Configuration form
    with st.form("backtest_config"):
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Basic Settings")

            ticker = st.text_input(
                "Ticker Symbol",
                value=default_ticker,
                help="Stock symbol to backtest (e.g., SPY, QQQ, AAPL)",
            ).upper()

            initial_capital = st.number_input(
                "Initial Capital ($)",
                min_value=10_000.0,
                max_value=10_000_000.0,
                value=default_initial_capital,
                step=10_000.0,
                help="Starting capital for the backtest",
            )

            date_range_preset = st.selectbox(
                "Date Range",
                options=["Last 1 Year", "Last 2 Years", "Last 3 Years", "Last 5 Years", "Last 10 Years", "Custom Range"],
                index=0 if default_date_range == "Last 1 Year" else
                      1 if default_date_range == "Last 2 Years" else
                      2 if default_date_range == "Last 3 Years" else
                      3 if default_date_range == "Last 5 Years" else
                      4 if default_date_range == "Last 10 Years" else 5,
                help=help_text,
            )

            start_date = st.date_input(
                "Start Date",
                value=default_start,
                help="Backtest start date",
            )

            end_date = st.date_input(
                "End Date",
                value=default_end,
                max_value=DATA_END_DATE,
                help=f"Backtest end date (data available through {DATA_END_DATE.strftime('%Y-%m-%d')})",
            )

        with col2:
            st.subheader("Strategy Parameters")

            dte_target = st.slider(
                "Target Days to Expiration (DTE)",
                min_value=7,
                max_value=90,
                value=default_dte_target,
                help="Preferred days until option expiration",
            )

            dte_min = st.slider(
                "Minimum DTE",
                min_value=1,
                max_value=30,
                value=default_dte_min,
                help="Minimum DTE before rolling or closing",
            )

            put_delta = st.slider(
                "Put Delta",
                min_value=0.05,
                max_value=0.50,
                value=default_put_delta,
                step=0.05,
                help="Target delta for short puts (lower = further OTM)",
            )

            call_delta = st.slider(
                "Call Delta",
                min_value=0.05,
                max_value=0.50,
                value=default_call_delta,
                step=0.05,
                help="Target delta for short calls (lower = further OTM)",
            )

            commission = st.number_input(
                "Commission per Contract ($)",
                min_value=0.0,
                max_value=10.0,
                value=default_commission,
                step=0.10,
                help="Commission charged per option contract",
            )

            st.subheader("Risk Management")

            enable_call_entry_protection = st.checkbox(
                "Don't write covered calls when underlying is below assignment price",
                value=default_enable_protection,
                help="Provides two protections: (1) Only sells calls when underlying is within the $ threshold below cost basis, "
                     "(2) Ensures call strikes are always at or above the assignment price to avoid locking in losses.",
            )

            call_entry_protection_dollars = st.number_input(
                "Maximum $ below assignment price (only applies if checkbox is enabled)",
                min_value=0.0,
                max_value=100.0,
                value=default_protection_dollars,
                step=0.50,
                help="Wait until underlying is within this $ amount of assignment price before selling calls. "
                     "Strikes will always be at or above assignment price. "
                     "Example: Assigned at $300 with $50 threshold → sells calls when underlying ≥ $250, but only at strikes ≥ $300.",
            )

        st.markdown("---")

        # Submit button
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            submit = st.form_submit_button(
                "🚀 Run Backtest",
                use_container_width=True,
                type="primary",
            )

    # Run backtest when submitted
    if submit:
        # Calculate actual dates based on preset selection
        today = min(date.today(), DATA_END_DATE)
        if date_range_preset == "Last 1 Year":
            start_date = today - timedelta(days=365)
            end_date = today
        elif date_range_preset == "Last 2 Years":
            start_date = today - timedelta(days=730)
            end_date = today
        elif date_range_preset == "Last 3 Years":
            start_date = today - timedelta(days=1095)
            end_date = today
        elif date_range_preset == "Last 5 Years":
            start_date = today - timedelta(days=1825)
            end_date = today
        elif date_range_preset == "Last 10 Years":
            start_date = today - timedelta(days=3650)
            end_date = today
        # else: Custom Range - use the dates from form inputs

        # Validation
        if start_date >= end_date:
            st.error("❌ Start date must be before end date")
            return

        if not ticker:
            st.error("❌ Please enter a ticker symbol")
            return

        # Show progress
        try:
            # Create config
            with st.spinner("⚙️ Configuring backtest..."):
                config = BacktestConfig(
                    ticker=ticker,
                    start_date=start_date,
                    end_date=end_date,
                    initial_capital=initial_capital,
                    dte_target=dte_target,
                    dte_min=dte_min,
                    put_delta=put_delta,
                    call_delta=call_delta,
                    commission_per_contract=commission,
                    enable_call_entry_protection=enable_call_entry_protection,
                    call_entry_protection_dollars=call_entry_protection_dollars,
                    data_provider="philippdubach",
                    cache_dir=get_cache_dir(),
                    output_dir=get_output_dir(),
                )

            # Create progress display containers
            progress_bar = st.progress(0)
            status_text = st.empty()
            stats_container = st.empty()

            def update_progress(current, total, current_date, stats):
                """Update progress display."""
                progress = current / total
                progress_bar.progress(progress)
                status_text.text(f"Processing {current_date} (Day {current}/{total})")

                with stats_container.container():
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Progress", f"{progress * 100:.0f}%")
                    with col2:
                        st.metric("Trades", stats.get("total_trades", 0))
                    with col3:
                        st.metric("Current Equity", f"${stats.get('current_equity', 0):,.0f}")
                    with col4:
                        return_pct = stats.get("return_pct", 0)
                        st.metric("Return", f"{return_pct:+.2f}%", delta=f"{return_pct:+.2f}%")

            # Initialize backtest and load data with spinner
            with st.spinner("📊 Loading options data and preparing backtest..."):
                backtest = WheelBacktest(config)

            # Run the backtest with progress tracking
            result = backtest.run(progress_callback=update_progress)

            # Clear progress display
            progress_bar.empty()
            status_text.empty()
            stats_container.empty()

            # Show completion message
            st.success(f"✅ Backtest completed successfully!")

            # Save this configuration for next time
            _save_last_config(
                ticker=ticker,
                date_range_preset=date_range_preset,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                dte_target=dte_target,
                dte_min=dte_min,
                put_delta=put_delta,
                call_delta=call_delta,
                commission=commission,
                enable_call_entry_protection=enable_call_entry_protection,
                call_entry_protection_dollars=call_entry_protection_dollars,
            )

            # Save to history
            history = get_history()
            config.output_dir.mkdir(parents=True, exist_ok=True)

            equity_csv_path = config.output_dir / f"{ticker}_backtest_equity.csv"
            transactions_csv_path = config.output_dir / f"{ticker}_transactions.csv"

            # Save equity curve
            equity_df = result.equity_curve.to_dataframe()
            equity_df.to_csv(equity_csv_path)

            # Save transactions
            transactions_df = backtest.get_transactions_df()
            if not transactions_df.empty:
                transactions_df.to_csv(transactions_csv_path, index=False)

            # Save to history
            record_id = history.save_backtest(
                config=config,
                metrics=result.metrics,
                start_date=str(result.start_date),
                end_date=str(result.end_date),
                final_equity=result.final_equity,
                total_trades=len(result.events),
                equity_csv_path=equity_csv_path,
                transactions_csv_path=transactions_csv_path if not transactions_df.empty else None,
            )

            # Display results
            st.markdown("---")

            # Display results in tabs (tastytrade-style)
            display_results_tabs(result, transactions_df)

            # Performance Timing (optional, at the bottom)
            if result.timings:
                with st.expander("⏱️ Performance Timing"):
                    timing_data = []
                    for phase, label in [
                        ('data_loading', 'Data Loading'),
                        ('options_fetch', 'Options Chain Fetch'),
                        ('execution', 'Strategy Execution'),
                        ('metrics', 'Metrics Calculation'),
                        ('other', 'Other'),
                    ]:
                        if phase in result.timings:
                            t = result.timings[phase]
                            pct = (t / result.timings['total']) * 100 if 'total' in result.timings else 0
                            timing_data.append({
                                "Phase": label,
                                "Time (s)": f"{t:.2f}",
                                "Percentage": f"{pct:.1f}%"
                            })

                    if 'total' in result.timings:
                        timing_data.append({
                            "Phase": "**Total Time**",
                            "Time (s)": f"**{result.timings['total']:.2f}**",
                            "Percentage": "**100%**"
                        })

                    st.dataframe(timing_data, use_container_width=True, hide_index=True)

                    # Highlight if options fetch is slow
                    if 'options_fetch' in result.timings and result.timings['options_fetch'] > 10:
                        st.warning(
                            f"⚠️ Options data loading took {result.timings['options_fetch']:.1f}s "
                            f"({(result.timings['options_fetch']/result.timings['total'])*100:.0f}% of total time). "
                            "This is the main bottleneck."
                        )

        except Exception as e:
                st.error(f"❌ Error running backtest: {e}")
                st.exception(e)


if __name__ == "__main__":
    main()
