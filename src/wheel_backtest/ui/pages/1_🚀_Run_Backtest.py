"""Page for configuring and running new backtests."""

from datetime import date, timedelta
from pathlib import Path

import streamlit as st
from wheel_backtest.config import BacktestConfig
from wheel_backtest.engine import WheelBacktest
from wheel_backtest.ui.components import display_results_tabs
from wheel_backtest.ui.utils import get_cache_dir, get_history, get_output_dir

st.set_page_config(
    page_title="Run Backtest",
    page_icon="🚀",
    layout="wide",
)


def main():
    """Run backtest page."""
    st.title("🚀 Run New Backtest")
    st.markdown("Configure and execute a wheel strategy backtest")
    st.markdown("---")

    # Configuration form
    with st.form("backtest_config"):
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Basic Settings")

            ticker = st.text_input(
                "Ticker Symbol",
                value="SPY",
                help="Stock symbol to backtest (e.g., SPY, QQQ, AAPL)",
            ).upper()

            initial_capital = st.number_input(
                "Initial Capital ($)",
                min_value=10_000.0,
                max_value=10_000_000.0,
                value=100_000.0,
                step=10_000.0,
                help="Starting capital for the backtest",
            )

            st.subheader("Date Range")

            default_start = date(2023, 1, 1)
            default_end = date(2023, 12, 31)

            start_date = st.date_input(
                "Start Date",
                value=default_start,
                help="Backtest start date (YYYY-MM-DD)",
            )

            end_date = st.date_input(
                "End Date",
                value=default_end,
                help="Backtest end date (YYYY-MM-DD)",
            )

        with col2:
            st.subheader("Strategy Parameters")

            dte_target = st.slider(
                "Target Days to Expiration (DTE)",
                min_value=7,
                max_value=90,
                value=30,
                help="Preferred days until option expiration",
            )

            dte_min = st.slider(
                "Minimum DTE",
                min_value=1,
                max_value=30,
                value=7,
                help="Minimum DTE before rolling or closing",
            )

            put_delta = st.slider(
                "Put Delta",
                min_value=0.05,
                max_value=0.50,
                value=0.20,
                step=0.05,
                help="Target delta for short puts (lower = further OTM)",
            )

            call_delta = st.slider(
                "Call Delta",
                min_value=0.05,
                max_value=0.50,
                value=0.20,
                step=0.05,
                help="Target delta for short calls (lower = further OTM)",
            )

            commission = st.number_input(
                "Commission per Contract ($)",
                min_value=0.0,
                max_value=10.0,
                value=0.0,
                step=0.10,
                help="Commission charged per option contract",
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
        # Validation
        if start_date >= end_date:
            st.error("❌ Start date must be before end date")
            return

        if not ticker:
            st.error("❌ Please enter a ticker symbol")
            return

        # Show progress
        # TODO: Replace spinner with real-time progress tracking
        # - Add st.progress() bar showing percentage complete
        # - Add st.status() or st.container() showing:
        #   * Current phase: "Loading data..." / "Processing 2024-03-15..." / "Calculating metrics..."
        #   * Progress: "Day 180/252 (71%)"
        #   * Stats: "Contracts: 45 | Premium: $12,450 | P&L: +8.5%"
        #   * Timing: "Elapsed: 1m 23s | ETA: 25s"
        # - Use st.empty() to update progress in real-time
        # - Consider websocket or polling to get progress from backend
        with st.spinner(f"Running backtest for {ticker}..."):
            try:
                # Create config
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
                    data_provider="philippdubach",
                    cache_dir=get_cache_dir(),
                    output_dir=get_output_dir(),
                )

                # Run backtest
                backtest = WheelBacktest(config)
                result = backtest.run()

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
                st.success(f"✅ Backtest complete! Saved as record #{record_id}")
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
