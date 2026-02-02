"""Page for calculating and comparing buy-and-hold benchmark."""

from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
from wheel_backtest.analytics import BuyAndHoldBenchmark
from wheel_backtest.data import DataCache, YFinanceProvider
from wheel_backtest.ui.utils import get_cache_dir

st.set_page_config(
    page_title="Benchmark Comparison",
    page_icon="📈",
    layout="wide",
)


def main():
    """Benchmark comparison page."""
    st.title("📈 Buy-and-Hold Benchmark")
    st.markdown("Calculate and compare buy-and-hold strategy performance")
    st.markdown("---")

    # Configuration form
    with st.form("benchmark_config"):
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Settings")

            ticker = st.text_input(
                "Ticker Symbol",
                value="SPY",
                help="Stock symbol to benchmark (e.g., SPY, QQQ, AAPL)",
            ).upper()

            initial_capital = st.number_input(
                "Initial Capital ($)",
                min_value=10_000.0,
                max_value=10_000_000.0,
                value=100_000.0,
                step=10_000.0,
                help="Starting capital for the benchmark",
            )

        with col2:
            st.subheader("Date Range")

            default_start = date(2023, 1, 1)
            default_end = date(2023, 12, 31)

            start_date = st.date_input(
                "Start Date",
                value=default_start,
                help="Benchmark start date",
            )

            end_date = st.date_input(
                "End Date",
                value=default_end,
                help="Benchmark end date",
            )

        st.markdown("---")

        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            submit = st.form_submit_button(
                "📊 Calculate Benchmark",
                use_container_width=True,
                type="primary",
            )

    # Calculate benchmark when submitted
    if submit:
        # Validation
        if start_date >= end_date:
            st.error("❌ Start date must be before end date")
            return

        if not ticker:
            st.error("❌ Please enter a ticker symbol")
            return

        # Calculate benchmark
        with st.spinner(f"Calculating buy-and-hold for {ticker}..."):
            try:
                # Initialize data provider
                cache = DataCache(get_cache_dir())
                provider = YFinanceProvider(cache)
                benchmark_calc = BuyAndHoldBenchmark(provider)

                # Calculate
                curve = benchmark_calc.calculate(
                    ticker=ticker,
                    start_date=start_date,
                    end_date=end_date,
                    initial_capital=initial_capital,
                )

                if not curve.points:
                    st.error("❌ No price data available for the specified period")
                    return

                # Get summary
                summary = benchmark_calc.get_summary(curve, initial_capital)

                st.success(f"✅ Benchmark calculated successfully!")
                st.markdown("---")

                # Display results
                st.header("📊 Results")

                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric(
                        "Final Value",
                        f"${summary['final_value']:,.2f}",
                        f"{summary['total_return_pct']:.2f}%",
                    )

                with col2:
                    st.metric(
                        "CAGR",
                        f"{summary['cagr_pct']:.2f}%",
                    )

                with col3:
                    st.metric(
                        "Total Return",
                        f"${summary['total_return']:,.2f}",
                    )

                with col4:
                    st.metric(
                        "Trading Days",
                        summary["trading_days"],
                    )

                # Detailed metrics
                st.markdown("---")
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("Buy-and-Hold Summary")
                    st.text(f"Ticker: {ticker}")
                    st.text(f"Start Date: {summary['start_date']}")
                    st.text(f"End Date: {summary['end_date']}")
                    st.text(f"Trading Days: {summary['trading_days']}")
                    st.text(f"Years: {summary['years']:.2f}")

                with col2:
                    st.subheader("Performance")
                    st.text(f"Initial Capital: ${summary['initial_capital']:,.2f}")
                    st.text(f"Final Value: ${summary['final_value']:,.2f}")
                    st.text(f"Total Return: ${summary['total_return']:,.2f}")
                    st.text(f"Total Return %: {summary['total_return_pct']:.2f}%")
                    st.text(f"CAGR: {summary['cagr_pct']:.2f}%")

                # Equity curve
                st.markdown("---")
                st.subheader("📈 Equity Curve")

                df = curve.to_dataframe()
                df["date"] = pd.to_datetime(df.index)

                st.line_chart(
                    df.set_index("date")["total"],
                    use_container_width=True,
                )

                # Drawdown
                df["running_max"] = df["total"].cummax()
                df["drawdown"] = ((df["total"] - df["running_max"]) / df["running_max"]) * 100

                st.subheader("📉 Drawdown")
                st.area_chart(
                    df.set_index("date")["drawdown"],
                    use_container_width=True,
                    color="#ff4b4b",
                )

                max_dd = df["drawdown"].min()
                st.metric("Maximum Drawdown", f"{max_dd:.2f}%")

                # Cumulative returns
                st.markdown("---")
                st.subheader("📊 Cumulative Returns")

                df["cumulative_return"] = ((df["total"] / initial_capital) - 1) * 100

                st.line_chart(
                    df.set_index("date")["cumulative_return"],
                    use_container_width=True,
                )

                # Data table
                with st.expander("📋 View Equity Data"):
                    st.dataframe(df, use_container_width=True)

                # Download
                csv = df.to_csv().encode('utf-8')
                st.download_button(
                    "📥 Download Equity Data",
                    csv,
                    f"{ticker}_benchmark_{start_date}_{end_date}.csv",
                    "text/csv",
                    key='download-benchmark'
                )

            except Exception as e:
                st.error(f"❌ Error calculating benchmark: {e}")
                st.exception(e)

    else:
        # Show instructions
        st.info("""
        ### How to Use

        1. Enter a ticker symbol (e.g., SPY, QQQ, AAPL)
        2. Set your initial capital amount
        3. Choose start and end dates for the analysis
        4. Click **Calculate Benchmark** to see results

        ### What is Buy-and-Hold?

        Buy-and-hold is a passive investment strategy where you:
        - Buy shares at the start date
        - Hold them through the entire period
        - Never sell until the end date

        This provides a baseline to compare against the wheel strategy's performance.

        ### Comparison Tips

        - Use the same ticker, dates, and capital as your wheel backtests
        - Look at CAGR to compare risk-adjusted returns
        - Consider drawdowns to assess risk
        - Factor in the effort required for active vs. passive strategies
        """)


if __name__ == "__main__":
    main()
