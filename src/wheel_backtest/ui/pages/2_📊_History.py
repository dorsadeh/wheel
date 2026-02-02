"""Page for viewing backtest history."""

from pathlib import Path

import streamlit as st
from wheel_backtest.ui.utils import get_history

st.set_page_config(
    page_title="Backtest History",
    page_icon="📊",
    layout="wide",
)


def main():
    """Backtest history page."""
    st.title("📊 Backtest History")
    st.markdown("View and compare past backtest results")
    st.markdown("---")

    try:
        history = get_history()

        # Filters
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

        with col1:
            # Get all tickers
            all_records = history.list_backtests(limit=1000)
            tickers = sorted(set(r.ticker for r in all_records))
            ticker_filter = st.selectbox(
                "Filter by Ticker",
                options=["All"] + tickers,
            )

        with col2:
            sort_by = st.selectbox(
                "Sort by Metric",
                options=[
                    "Run Date (newest)",
                    "CAGR",
                    "Sharpe Ratio",
                    "Total Return %",
                    "Max Drawdown",
                    "Sortino Ratio",
                    "Win Rate",
                    "Profit Factor",
                ],
            )

        with col3:
            limit = st.number_input(
                "Number of Results",
                min_value=10,
                max_value=100,
                value=20,
                step=10,
            )

        with col4:
            st.markdown("<br>", unsafe_allow_html=True)
            refresh = st.button("🔄 Refresh", use_container_width=True)

        st.markdown("---")

        # Get records based on filters
        ticker_param = None if ticker_filter == "All" else ticker_filter

        if sort_by == "Run Date (newest)":
            records = history.list_backtests(ticker=ticker_param, limit=limit)
        else:
            # Map display name to database column
            metric_map = {
                "CAGR": "cagr",
                "Sharpe Ratio": "sharpe_ratio",
                "Total Return %": "total_return_pct",
                "Max Drawdown": "max_drawdown",
                "Sortino Ratio": "sortino_ratio",
                "Win Rate": "win_rate",
                "Profit Factor": "profit_factor",
            }
            metric = metric_map.get(sort_by, "cagr")
            records = history.get_best_by_metric(
                metric=metric,
                ticker=ticker_param,
                limit=limit,
            )

        if records:
            st.success(f"Found {len(records)} backtest(s)")

            # Display as table
            data = []
            for record in records:
                data.append({
                    "ID": record.id,
                    "Date": record.run_date.strftime("%Y-%m-%d %H:%M"),
                    "Ticker": record.ticker,
                    "Start": record.start_date,
                    "End": record.end_date,
                    "Capital": f"${record.initial_capital:,.0f}",
                    "Final": f"${record.final_equity:,.0f}",
                    "Return %": f"{record.total_return_pct:.2f}%",
                    "CAGR": f"{record.cagr:.2f}%",
                    "Sharpe": f"{record.sharpe_ratio:.2f}",
                    "Sortino": f"{record.sortino_ratio:.2f}",
                    "Max DD": f"{record.max_drawdown:.2f}%",
                    "Volatility": f"{record.volatility:.2f}%",
                    "Win Rate": f"{record.win_rate:.2f}%",
                    "Profit Factor": f"{record.profit_factor:.2f}",
                    "Trades": record.total_trades,
                    "DTE": record.dte_target,
                    "Delta": f"{record.delta_target:.2f}",
                })

            st.dataframe(
                data,
                use_container_width=True,
                hide_index=True,
            )

            # Record selection for details
            st.markdown("---")
            st.subheader("📋 View Details")

            selected_id = st.number_input(
                "Enter Record ID",
                min_value=1,
                value=records[0].id if records else 1,
                step=1,
            )

            if st.button("View Record Details", type="primary"):
                record = history.get_backtest(selected_id)

                if record:
                    st.markdown("---")
                    st.subheader(f"Record #{record.id} - {record.ticker}")

                    # Display all details
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("**Backtest Information**")
                        st.text(f"Run Date: {record.run_date.strftime('%Y-%m-%d %H:%M:%S')}")
                        st.text(f"Ticker: {record.ticker}")
                        st.text(f"Period: {record.start_date} to {record.end_date}")
                        st.text(f"Initial Capital: ${record.initial_capital:,.2f}")
                        st.text(f"Final Equity: ${record.final_equity:,.2f}")
                        st.text(f"Total Trades: {record.total_trades}")

                        st.markdown("**Strategy Parameters**")
                        st.text(f"DTE Target: {record.dte_target}")
                        st.text(f"Delta Target: {record.delta_target:.2f}")
                        st.text(f"Commission: ${record.commission:.2f}")

                        if record.git_commit:
                            st.text(f"Git Commit: {record.git_commit[:8]}")

                    with col2:
                        st.markdown("**Performance Metrics**")
                        st.text(f"Total Return: ${record.total_return:,.2f}")
                        st.text(f"Total Return %: {record.total_return_pct:.2f}%")
                        st.text(f"CAGR: {record.cagr:.2f}%")
                        st.text(f"Volatility: {record.volatility:.2f}%")
                        st.text(f"Sharpe Ratio: {record.sharpe_ratio:.2f}")
                        st.text(f"Sortino Ratio: {record.sortino_ratio:.2f}")
                        st.text(f"Max Drawdown: {record.max_drawdown:.2f}%")
                        st.text(f"Win Rate: {record.win_rate:.2f}%")
                        st.text(f"Profit Factor: {record.profit_factor:.2f}")

                        st.markdown("**Files**")
                        if record.equity_csv_path:
                            st.text(f"Equity CSV: {record.equity_csv_path}")
                        if record.transactions_csv_path:
                            st.text(f"Transactions CSV: {record.transactions_csv_path}")

                    # Delete button
                    st.markdown("---")
                    if st.button(f"🗑️ Delete Record #{selected_id}", type="secondary"):
                        if history.delete_backtest(selected_id):
                            st.success(f"✅ Deleted record #{selected_id}")
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to delete record #{selected_id}")

                else:
                    st.error(f"❌ Record #{selected_id} not found")

        else:
            st.info("No backtests found matching the filters")

    except Exception as e:
        st.error(f"Error loading backtest history: {e}")
        st.exception(e)


if __name__ == "__main__":
    main()
