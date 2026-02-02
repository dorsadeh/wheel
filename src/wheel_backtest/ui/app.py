"""Streamlit web UI for Wheel Strategy Backtester.

Main dashboard showing overview of recent backtests and quick access to features.
"""

from datetime import date, datetime
from pathlib import Path

import streamlit as st
from wheel_backtest.ui.utils import get_history

# Page configuration
st.set_page_config(
    page_title="Wheel Strategy Backtester",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS - removed .stMetric styling to support dark mode
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)


def main():
    """Main dashboard page."""
    # Header
    st.title("🎯 Wheel Strategy Backtester")
    st.markdown("---")

    # Sidebar
    with st.sidebar:
        st.header("Navigation")
        st.markdown("""
        Use the pages on the left to:
        - 🚀 **Run Backtest** - Configure and execute new backtests
        - 📊 **History** - View and compare past results
        - 🔍 **Analysis** - Deep dive into specific backtests
        - 📈 **Benchmark** - Compare with buy-and-hold
        """)

        st.markdown("---")
        st.header("About")
        st.markdown("""
        The **Wheel Strategy** is an options trading strategy:
        1. Sell cash-secured puts
        2. Get assigned on ITM options
        3. Sell covered calls on shares
        4. Repeat when called away

        This backtester uses historical options data to simulate
        the strategy and calculate performance metrics.
        """)

    # Main content
    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("📋 Recent Backtests")

        try:
            history = get_history()
            records = history.list_backtests(limit=10)

            if records:
                # Create summary table
                data = []
                for record in records:
                    data.append({
                        "ID": record.id,
                        "Date": record.run_date.strftime("%Y-%m-%d %H:%M"),
                        "Ticker": record.ticker,
                        "Period": f"{record.start_date} to {record.end_date}",
                        "Return": f"{record.total_return_pct:.2f}%",
                        "CAGR": f"{record.cagr:.2f}%",
                        "Sharpe": f"{record.sharpe_ratio:.2f}",
                        "Max DD": f"{record.max_drawdown:.2f}%",
                    })

                st.dataframe(
                    data,
                    use_container_width=True,
                    hide_index=True,
                )

                st.markdown(f"*Showing {len(records)} most recent backtests*")
            else:
                st.info("No backtests found. Run your first backtest to get started!")

        except Exception as e:
            st.error(f"Error loading backtest history: {e}")

    with col2:
        st.header("📈 Quick Stats")

        try:
            history = get_history()
            all_records = history.list_backtests(limit=1000)

            if all_records:
                # Calculate aggregate stats
                avg_return = sum(r.total_return_pct for r in all_records) / len(all_records)
                avg_sharpe = sum(r.sharpe_ratio for r in all_records) / len(all_records)
                best_return = max(r.total_return_pct for r in all_records)

                # Count tickers
                tickers = set(r.ticker for r in all_records)

                st.metric("Total Backtests", len(all_records))
                st.metric("Tickers Tested", len(tickers))
                st.metric("Avg Return", f"{avg_return:.2f}%")
                st.metric("Avg Sharpe Ratio", f"{avg_sharpe:.2f}")
                st.metric("Best Return", f"{best_return:.2f}%")

            else:
                st.info("Run backtests to see statistics")

        except Exception as e:
            st.error(f"Error calculating stats: {e}")

    # Key Features
    st.markdown("---")
    st.header("✨ Key Features")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        with st.container():
            st.subheader("🎯 Delta-Based Selection")
            st.write("Select strikes using actual option Greeks for precise positioning.")

    with col2:
        with st.container():
            st.subheader("📊 Comprehensive Metrics")
            st.write("CAGR, Sharpe, Sortino, drawdown, win rate, and more.")

    with col3:
        with st.container():
            st.subheader("💾 Persistent History")
            st.write("All backtests saved to SQLite for easy comparison.")

    with col4:
        with st.container():
            st.subheader("📈 Visual Analysis")
            st.write("Equity curves, drawdown charts, and strategy comparisons.")

    # Data Source Info
    st.markdown("---")
    st.header("📦 Data Source")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Historical Options Data:** Philippe Dubach Dataset")
        st.write("• 24.6M options records (2008-2025)")
        st.write("• 104 tickers with full Greeks")
        st.write("• End-of-day prices and implied volatility")

    with col2:
        st.markdown("**Underlying Prices:** Yahoo Finance")
        st.write("• Adjusted daily OHLCV data")
        st.write("• Dividend information")

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
    <p>Wheel Strategy Backtester | Built with Streamlit</p>
    <p>⚠️ For educational purposes only. Not financial advice.</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
