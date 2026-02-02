"""Page for configuring and running new backtests."""

from datetime import date, timedelta
from pathlib import Path

import streamlit as st
from wheel_backtest.config import BacktestConfig
from wheel_backtest.engine import WheelBacktest
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

            delta_target = st.slider(
                "Target Delta",
                min_value=0.05,
                max_value=0.50,
                value=0.20,
                step=0.05,
                help="Target delta for strike selection (lower = further OTM)",
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
                    delta_target=delta_target,
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
                equity_csv_path = config.output_dir / f"{ticker}_backtest_equity.csv"
                transactions_csv_path = config.output_dir / f"{ticker}_transactions.csv"

                # Save transactions
                transactions_df = backtest.get_transactions_df()
                if not transactions_df.empty:
                    config.output_dir.mkdir(parents=True, exist_ok=True)
                    transactions_df.to_csv(transactions_csv_path, index=False)

                # Save to history
                record_id = history.save_backtest(
                    config=config,
                    metrics=result.metrics,
                    start_date=str(result.start_date),
                    end_date=str(result.end_date),
                    final_equity=result.final_equity,
                    total_trades=len(result.events),
                    transactions_csv_path=transactions_csv_path if not transactions_df.empty else None,
                )

                # Display results
                st.success(f"✅ Backtest complete! Saved as record #{record_id}")
                st.markdown("---")

                # Results summary
                st.header("📊 Results")

                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric(
                        "Final Equity",
                        f"${result.final_equity:,.2f}",
                        f"{result.metrics.total_return_pct:.2f}%",
                    )

                with col2:
                    st.metric(
                        "CAGR",
                        f"{result.metrics.cagr:.2f}%",
                    )

                with col3:
                    st.metric(
                        "Sharpe Ratio",
                        f"{result.metrics.sharpe_ratio:.2f}",
                    )

                with col4:
                    st.metric(
                        "Max Drawdown",
                        f"{result.metrics.max_drawdown:.2f}%",
                    )

                # Additional metrics
                st.markdown("---")
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("Performance Metrics")
                    metrics_data = {
                        "Total Return": f"${result.metrics.total_return:,.2f}",
                        "Return %": f"{result.metrics.total_return_pct:.2f}%",
                        "CAGR": f"{result.metrics.cagr:.2f}%",
                        "Volatility": f"{result.metrics.volatility:.2f}%",
                        "Sharpe Ratio": f"{result.metrics.sharpe_ratio:.2f}",
                        "Sortino Ratio": f"{result.metrics.sortino_ratio:.2f}",
                        "Max Drawdown": f"{result.metrics.max_drawdown:.2f}%",
                        "Max DD Duration": f"{result.metrics.max_drawdown_duration} days",
                        "Calmar Ratio": f"{result.metrics.calmar_ratio:.2f}",
                    }
                    for metric, value in metrics_data.items():
                        st.text(f"{metric}: {value}")

                with col2:
                    st.subheader("Trading Statistics")
                    summary = result.summary
                    trading_stats = {
                        "Total Puts Sold": summary["total_puts_sold"],
                        "Total Calls Sold": summary["total_calls_sold"],
                        "Put Assignments": summary["put_assignments"],
                        "Call Assignments": summary["call_assignments"],
                        "Puts Expired OTM": summary["puts_expired_otm"],
                        "Calls Expired OTM": summary["calls_expired_otm"],
                        "Premium Collected": f"${summary['total_premium_collected']:,.2f}",
                        "Win Rate": f"{result.metrics.win_rate:.2f}%",
                        "Profit Factor": f"{result.metrics.profit_factor:.2f}",
                    }
                    for stat, value in trading_stats.items():
                        st.text(f"{stat}: {value}")

                # Link to analysis
                st.markdown("---")
                st.info(f"💡 View detailed analysis on the **Analysis** page (Record #{record_id})")

            except Exception as e:
                st.error(f"❌ Error running backtest: {e}")
                st.exception(e)


if __name__ == "__main__":
    main()
