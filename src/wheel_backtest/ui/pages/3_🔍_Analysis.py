"""Page for detailed analysis of specific backtests."""

from pathlib import Path

import pandas as pd
import streamlit as st
from wheel_backtest.ui.utils import get_history

st.set_page_config(
    page_title="Backtest Analysis",
    page_icon="🔍",
    layout="wide",
)


def main():
    """Analysis page."""
    st.title("🔍 Backtest Analysis")
    st.markdown("Deep dive into specific backtest results with charts and transactions")
    st.markdown("---")

    try:
        history = get_history()
        records = history.list_backtests(limit=50)

        if not records:
            st.info("No backtests found. Run a backtest first!")
            return

        # Record selection
        record_options = [f"#{r.id} - {r.ticker} ({r.start_date} to {r.end_date})" for r in records]
        selected_option = st.selectbox(
            "Select Backtest",
            options=record_options,
        )

        # Extract ID from selection
        record_id = int(selected_option.split("#")[1].split(" ")[0])
        record = history.get_backtest(record_id)

        if not record:
            st.error(f"Record #{record_id} not found")
            return

        st.markdown("---")

        # Summary cards
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric(
                "Final Equity",
                f"${record.final_equity:,.0f}",
                f"{record.total_return_pct:.2f}%",
            )

        with col2:
            st.metric("CAGR", f"{record.cagr:.2f}%")

        with col3:
            st.metric("Sharpe Ratio", f"{record.sharpe_ratio:.2f}")

        with col4:
            st.metric("Max Drawdown", f"{record.max_drawdown:.2f}%")

        with col5:
            st.metric("Total Trades", record.total_trades)

        st.markdown("---")

        # Tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs(["📈 Equity Curve", "📊 Metrics", "💰 Transactions", "⚙️ Configuration"])

        with tab1:
            st.subheader("Equity Curve")

            # Try to load equity CSV if available
            if record.equity_csv_path:
                try:
                    equity_df = pd.read_csv(record.equity_csv_path)
                    equity_df["date"] = pd.to_datetime(equity_df["date"])

                    # Plot equity curve
                    st.line_chart(
                        equity_df.set_index("date")["total"],
                        use_container_width=True,
                    )

                    # Calculate drawdown
                    equity_df["running_max"] = equity_df["total"].cummax()
                    equity_df["drawdown"] = ((equity_df["total"] - equity_df["running_max"]) / equity_df["running_max"]) * 100

                    st.subheader("Drawdown Chart")
                    st.area_chart(
                        equity_df.set_index("date")["drawdown"],
                        use_container_width=True,
                        color="#ff4b4b",
                    )

                    # Show data table
                    with st.expander("📋 View Equity Data"):
                        st.dataframe(equity_df, use_container_width=True)

                except Exception as e:
                    st.error(f"Error loading equity data: {e}")
                    st.info("Equity CSV path exists but file could not be loaded")
            else:
                st.info("No equity curve data available for this backtest")

        with tab2:
            st.subheader("Performance Metrics")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Returns**")
                st.text(f"Total Return: ${record.total_return:,.2f}")
                st.text(f"Total Return %: {record.total_return_pct:.2f}%")
                st.text(f"CAGR: {record.cagr:.2f}%")
                st.text(f"Initial Capital: ${record.initial_capital:,.2f}")
                st.text(f"Final Equity: ${record.final_equity:,.2f}")

                st.markdown("**Risk Metrics**")
                st.text(f"Volatility (Ann.): {record.volatility:.2f}%")
                st.text(f"Max Drawdown: {record.max_drawdown:.2f}%")
                st.text(f"Sharpe Ratio: {record.sharpe_ratio:.2f}")
                st.text(f"Sortino Ratio: {record.sortino_ratio:.2f}")

            with col2:
                st.markdown("**Trading Statistics**")
                st.text(f"Total Trades: {record.total_trades}")
                st.text(f"Win Rate: {record.win_rate:.2f}%")
                st.text(f"Profit Factor: {record.profit_factor:.2f}")

                st.markdown("**Strategy Parameters**")
                st.text(f"Ticker: {record.ticker}")
                st.text(f"Period: {record.start_date} to {record.end_date}")
                st.text(f"DTE Target: {record.dte_target} days")
                st.text(f"Delta Target: {record.delta_target:.2f}")
                st.text(f"Commission: ${record.commission:.2f}/contract")

            # Visualize metrics
            st.markdown("---")
            st.subheader("Metrics Comparison")

            metrics_df = pd.DataFrame({
                "Metric": ["CAGR", "Sharpe", "Sortino", "Win Rate", "Profit Factor"],
                "Value": [
                    record.cagr,
                    record.sharpe_ratio * 10,  # Scale for visibility
                    record.sortino_ratio * 10,  # Scale for visibility
                    record.win_rate,
                    record.profit_factor * 10,  # Scale for visibility
                ],
            })

            st.bar_chart(metrics_df.set_index("Metric"), use_container_width=True)
            st.caption("Note: Sharpe, Sortino, and Profit Factor scaled by 10x for visibility")

        with tab3:
            st.subheader("Transaction Log")

            if record.transactions_csv_path:
                try:
                    transactions_df = pd.read_csv(record.transactions_csv_path)

                    # Display summary
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric("Total Transactions", len(transactions_df))

                    with col2:
                        total_commissions = transactions_df["commission"].sum() if "commission" in transactions_df.columns else 0
                        st.metric("Total Commissions", f"${total_commissions:.2f}")

                    with col3:
                        unique_actions = transactions_df["action"].nunique() if "action" in transactions_df.columns else 0
                        st.metric("Action Types", unique_actions)

                    with col4:
                        if "value" in transactions_df.columns:
                            total_value = abs(transactions_df["value"]).sum()
                            st.metric("Total Value", f"${total_value:,.0f}")

                    # Filter options
                    st.markdown("---")
                    if "action" in transactions_df.columns:
                        action_filter = st.multiselect(
                            "Filter by Action",
                            options=transactions_df["action"].unique(),
                            default=None,
                        )

                        if action_filter:
                            transactions_df = transactions_df[transactions_df["action"].isin(action_filter)]

                    # Display table
                    st.dataframe(
                        transactions_df,
                        use_container_width=True,
                        hide_index=True,
                    )

                    # Download button
                    csv = transactions_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "📥 Download Transactions CSV",
                        csv,
                        f"backtest_{record_id}_transactions.csv",
                        "text/csv",
                        key='download-csv'
                    )

                except Exception as e:
                    st.error(f"Error loading transactions: {e}")
                    st.info("Transactions CSV path exists but file could not be loaded")
            else:
                st.info("No transaction data available for this backtest")

        with tab4:
            st.subheader("Configuration Details")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Backtest Settings**")
                st.text(f"Record ID: {record.id}")
                st.text(f"Run Date: {record.run_date.strftime('%Y-%m-%d %H:%M:%S')}")
                st.text(f"Ticker: {record.ticker}")
                st.text(f"Start Date: {record.start_date}")
                st.text(f"End Date: {record.end_date}")
                st.text(f"Initial Capital: ${record.initial_capital:,.2f}")

                if record.git_commit:
                    st.text(f"Git Commit: {record.git_commit}")

            with col2:
                st.markdown("**Strategy Parameters**")
                st.text(f"DTE Target: {record.dte_target} days")
                st.text(f"Delta Target: {record.delta_target:.2f}")
                st.text(f"Commission: ${record.commission:.2f} per contract")

                st.markdown("**Output Files**")
                if record.equity_csv_path:
                    st.text(f"Equity CSV: {record.equity_csv_path}")
                if record.transactions_csv_path:
                    st.text(f"Transactions CSV: {record.transactions_csv_path}")

            # Full configuration JSON
            st.markdown("---")
            with st.expander("📋 View Full Configuration JSON"):
                st.json(record.config_json)

    except Exception as e:
        st.error(f"Error loading analysis: {e}")
        st.exception(e)


if __name__ == "__main__":
    main()
