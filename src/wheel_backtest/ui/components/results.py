"""Result display components for Streamlit UI.

Inspired by tastytrade's interface design for options backtesting.
"""

from datetime import date
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from wheel_backtest.analytics.benchmark import BuyAndHoldBenchmark
from wheel_backtest.analytics.equity import EquityCurve
from wheel_backtest.analytics.metrics import MetricsCalculator, PerformanceMetrics
from wheel_backtest.config import BacktestConfig
from wheel_backtest.data import DataCache, YFinanceProvider
from wheel_backtest.engine.backtest import BacktestResult


def display_results_tabs(result: BacktestResult, transactions_df: pd.DataFrame):
    """Display backtest results in tabs like tastytrade's UI.

    Args:
        result: Backtest result with metrics and equity curve
        transactions_df: DataFrame with all transactions
    """
    # Calculate buy-and-hold benchmark
    cache = DataCache(result.config.cache_dir)
    yf_provider = YFinanceProvider(cache)
    benchmark_calc = BuyAndHoldBenchmark(yf_provider)

    benchmark_curve = benchmark_calc.calculate(
        ticker=result.ticker,
        start_date=result.start_date,
        end_date=result.end_date,
        initial_capital=result.initial_capital,
    )

    # Calculate benchmark metrics
    benchmark_df = benchmark_curve.to_dataframe()
    if not benchmark_df.empty:
        metrics_calc = MetricsCalculator()
        benchmark_metrics = metrics_calc.calculate(
            equity_curve=benchmark_curve,
            start_date=result.start_date,
            end_date=result.end_date,
            initial_capital=result.initial_capital,
        )
    else:
        benchmark_metrics = None

    # Create tabs
    tab1, tab2, tab3 = st.tabs(["📊 Summary", "📈 Details", "📋 Logs"])

    with tab1:
        _display_summary_tab(result, benchmark_curve, benchmark_metrics)

    with tab2:
        _display_details_tab(result, transactions_df)

    with tab3:
        _display_logs_tab(result, transactions_df)


def _display_summary_tab(
    result: BacktestResult,
    benchmark_curve: EquityCurve,
    benchmark_metrics: Optional[PerformanceMetrics],
):
    """Display summary tab with config, chart, and metrics comparison."""
    # Configuration panel
    st.subheader("Configuration")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**UNDERLYING**")
        st.text(result.ticker)

        st.markdown("**LEGS**")
        st.markdown("🔴 sell &nbsp;&nbsp; 1 put &nbsp;&nbsp; 30 Δ &nbsp;&nbsp; 45 DTE")

    with col2:
        st.markdown("**DATES**")
        st.text(f"From: {result.start_date}")
        st.text(f"To: {result.end_date}")

    with col3:
        st.markdown("**ENTRY CONDITIONS**")
        st.text(f"Enter: On every Monday")
        st.text(f"Maximum active trades: 1")

        st.markdown("**EXIT CONDITIONS**")
        st.text(f"Take profit: at 50% of premium")

    st.markdown("---")

    # Dual-axis chart: Strategy equity vs Underlying price
    st.subheader("Performance Comparison")
    _display_dual_axis_chart(result, benchmark_curve)

    st.markdown("---")

    # Metrics comparison
    st.subheader("Strategy Comparison")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Your Strategy")
        _display_metric_card(
            "Total profit/loss",
            f"${result.metrics.total_return:,.0f}",
            "green" if result.metrics.total_return >= 0 else "red",
        )
        _display_metric_row("Max drawdown", f"{result.metrics.max_drawdown:.2f}%",
                           f"${result.metrics.max_drawdown * result.initial_capital / 100:,.0f} on {result.start_date}")
        _display_metric_row("Return on used capital", f"{result.metrics.total_return_pct:.2f}%",
                           f"${result.initial_capital:,.0f} used capital")
        _display_metric_row("MAR ratio", f"{result.metrics.calmar_ratio:.2f}", "")

    with col2:
        st.markdown("### Buy and Hold")
        if benchmark_metrics:
            _display_metric_card(
                "Total profit/loss",
                f"${benchmark_metrics.total_return:,.0f}",
                "green" if benchmark_metrics.total_return >= 0 else "red",
            )
            _display_metric_row("Max drawdown", f"{benchmark_metrics.max_drawdown:.2f}%",
                               f"${benchmark_metrics.max_drawdown * result.initial_capital / 100:,.0f} on {result.start_date}")
            _display_metric_row("Return on used capital", f"{benchmark_metrics.total_return_pct:.2f}%",
                               f"${result.initial_capital:,.0f} used capital")
            _display_metric_row("MAR ratio", f"{benchmark_metrics.calmar_ratio:.2f}", "")
        else:
            st.info("Benchmark metrics not available")


def _display_details_tab(result: BacktestResult, transactions_df: pd.DataFrame):
    """Display details tab with trade-by-trade profit/loss and detailed stats."""
    # Trade-by-trade profit/loss chart
    st.subheader("Profit/Loss for All Trades")
    _display_trade_pnl_chart(transactions_df)

    st.markdown("---")

    # Detailed statistics grid
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Number of trades", result.summary.get("total_puts_sold", 0) + result.summary.get("total_calls_sold", 0))
        st.metric("Trades with profits", _count_profitable_trades(transactions_df))
        st.metric("Profit rate", f"{result.metrics.win_rate:.2f}%")
        st.metric("Largest individual profit", f"${_get_largest_profit(transactions_df):,.2f}")
        st.metric("Trades with losses", _count_losing_trades(transactions_df))
        st.metric("Loss rate", f"{100 - result.metrics.win_rate:.2f}%")
        st.metric("Largest individual loss", f"${_get_largest_loss(transactions_df):,.2f}")

    with col2:
        premium_collected = result.summary.get("total_premium_collected", 0)
        num_trades = result.summary.get("total_puts_sold", 0) + result.summary.get("total_calls_sold", 0)
        avg_premium = premium_collected / num_trades if num_trades > 0 else 0

        st.metric("Avg. return per trade", f"{result.metrics.total_return_pct / num_trades if num_trades > 0 else 0:.2f}%")
        st.metric("Avg. days in trade", "N/A")  # TODO: Calculate from transactions
        st.metric("Avg. BPR per trade", "N/A")  # TODO: Calculate buying power reduction
        st.metric("Avg. premium", f"${avg_premium:,.2f}")
        st.metric("Avg. profit/loss per trade", f"${result.metrics.total_return / num_trades if num_trades > 0 else 0:,.2f}")
        st.metric("Avg. win size", f"${_get_avg_win(transactions_df):,.2f}")
        st.metric("Avg. loss size", f"${_get_avg_loss(transactions_df):,.2f}")

    with col3:
        st.metric("Total profit/loss", f"${result.metrics.total_return:,.2f}")
        st.metric("Used capital", f"${result.initial_capital:,.0f}")
        st.metric("Return on used capital", f"{result.metrics.total_return_pct:.2f}%")
        st.metric("CAGR", f"{result.metrics.cagr:.2f}%")
        st.metric("Total premium", f"${premium_collected:,.2f}")
        st.metric("Total fees", f"${result.summary.get('total_commissions', 0):,.2f}")
        st.metric("Max drawdown", f"{result.metrics.max_drawdown:.2f}%")


def _display_logs_tab(result: BacktestResult, transactions_df: pd.DataFrame):
    """Display logs tab with transaction table."""
    st.subheader("Trades")

    # Add download button
    if not transactions_df.empty:
        csv = transactions_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download trades",
            csv,
            f"{result.ticker}_transactions.csv",
            "text/csv",
            key='download-trades'
        )

    # Prepare transactions for display
    if not transactions_df.empty:
        display_df = _prepare_transactions_for_display(transactions_df)

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Number of trades", len(display_df))

        with col2:
            st.metric("Avg. return per trade", f"{result.metrics.total_return_pct / len(display_df) if len(display_df) > 0 else 0:.2f}%")

        with col3:
            st.metric("Total profit/loss", f"${result.metrics.total_return:,.2f}")

        with col4:
            st.metric("Used capital", f"${result.initial_capital:,.0f}")

        st.markdown("---")

        # Display table
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No transactions recorded")


def _display_dual_axis_chart(result: BacktestResult, benchmark_curve: EquityCurve):
    """Display dual-axis chart with strategy equity and underlying price."""
    # Prepare data
    equity_df = result.equity_curve.to_dataframe()
    benchmark_df = benchmark_curve.to_dataframe()

    if equity_df.empty or benchmark_df.empty:
        st.warning("Insufficient data for chart")
        return

    # Ensure 'date' is a column, not index
    if equity_df.index.name == "date" or "date" not in equity_df.columns:
        equity_df = equity_df.reset_index()

    if benchmark_df.index.name == "date" or "date" not in benchmark_df.columns:
        benchmark_df = benchmark_df.reset_index()

    # Verify required columns exist
    if "date" not in equity_df.columns or "total" not in equity_df.columns:
        st.error("Equity data missing required columns")
        return

    if "date" not in benchmark_df.columns or "total" not in benchmark_df.columns:
        st.error("Benchmark data missing required columns")
        return

    # Create figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add strategy equity (left axis)
    fig.add_trace(
        go.Scatter(
            x=equity_df["date"],
            y=equity_df["total"],
            name="Strategy profit / loss",
            line=dict(color="#FF6B35", width=2),
            mode="lines",
        ),
        secondary_y=False,
    )

    # Add underlying price (right axis)
    fig.add_trace(
        go.Scatter(
            x=benchmark_df["date"],
            y=benchmark_df["total"],
            name=f"{result.ticker} end of day price",
            line=dict(color="#666666", width=2),
            mode="lines",
        ),
        secondary_y=True,
    )

    # Update layout
    fig.update_layout(
        height=500,
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=0, r=0, t=40, b=0),
    )

    # Update axes
    fig.update_xaxes(title_text="Date", showgrid=True, gridcolor="#f0f0f0")
    fig.update_yaxes(title_text="Strategy ($)", secondary_y=False, showgrid=True, gridcolor="#f0f0f0")
    fig.update_yaxes(title_text=f"{result.ticker} Price ($)", secondary_y=True, showgrid=False)

    st.plotly_chart(fig, use_container_width=True)


def _display_trade_pnl_chart(transactions_df: pd.DataFrame):
    """Display bar chart of trade-by-trade profit/loss."""
    if transactions_df.empty:
        st.info("No trade data available")
        return

    # Verify required columns exist
    if "action" not in transactions_df.columns or "value" not in transactions_df.columns or "date" not in transactions_df.columns:
        st.info("Transaction data missing required columns for P&L chart")
        return

    # Extract profit/loss per trade
    # For simplicity, we'll use the 'value' column when action contains 'expired' or 'assigned'
    pnl_data = []

    for idx, row in transactions_df.iterrows():
        if "expired" in row["action"].lower() or "assigned" in row["action"].lower():
            pnl = row["value"]
            pnl_data.append({
                "date": row["date"],
                "pnl": pnl,
                "action": row["action"],
            })

    if not pnl_data:
        st.info("No completed trades to display")
        return

    pnl_df = pd.DataFrame(pnl_data)

    # Create bar chart
    colors = ["#00C853" if pnl >= 0 else "#FF1744" for pnl in pnl_df["pnl"]]

    fig = go.Figure(data=[
        go.Bar(
            x=pnl_df["date"],
            y=pnl_df["pnl"],
            marker_color=colors,
            hovertemplate="<b>%{x}</b><br>P&L: $%{y:,.2f}<extra></extra>",
        )
    ])

    fig.update_layout(
        height=400,
        xaxis_title="Trade Date",
        yaxis_title="Profit / Loss ($)",
        showlegend=False,
        hovermode="x",
        margin=dict(l=0, r=0, t=20, b=0),
    )

    fig.update_xaxes(showgrid=True, gridcolor="#f0f0f0")
    fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0", zeroline=True, zerolinecolor="#666")

    st.plotly_chart(fig, use_container_width=True)


def _display_metric_card(label: str, value: str, color: str = "black"):
    """Display a metric card with styling."""
    color_map = {
        "green": "#00C853",
        "red": "#FF1744",
        "black": "#000000",
    }

    st.markdown(f"""
    <div style="padding: 10px; margin: 10px 0;">
        <p style="margin: 0; font-size: 14px; color: #666;">{label}</p>
        <p style="margin: 5px 0 0 0; font-size: 28px; font-weight: bold; color: {color_map.get(color, color)};">{value}</p>
    </div>
    """, unsafe_allow_html=True)


def _display_metric_row(label: str, value: str, subtext: str = ""):
    """Display a metric row."""
    st.markdown(f"""
    <div style="padding: 8px 10px; margin: 5px 0; background-color: #f8f9fa; border-radius: 5px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 14px; color: #666;">{label}</span>
            <span style="font-size: 16px; font-weight: bold;">{value}</span>
        </div>
        {f'<p style="margin: 5px 0 0 0; font-size: 12px; color: #999;">{subtext}</p>' if subtext else ''}
    </div>
    """, unsafe_allow_html=True)


def _prepare_transactions_for_display(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare transactions dataframe for display."""
    display_df = transactions_df.copy()

    # Format columns
    if "date" in display_df.columns:
        display_df["date"] = pd.to_datetime(display_df["date"]).dt.strftime("%Y-%m-%d")

    if "price" in display_df.columns:
        display_df["price"] = display_df["price"].apply(lambda x: f"${x:.2f}")

    if "value" in display_df.columns:
        display_df["value"] = display_df["value"].apply(lambda x: f"${x:,.2f}")

    if "commission" in display_df.columns:
        display_df["commission"] = display_df["commission"].apply(lambda x: f"${x:.2f}")

    if "cash_after" in display_df.columns:
        display_df["cash_after"] = display_df["cash_after"].apply(lambda x: f"${x:,.0f}")

    if "equity_after" in display_df.columns:
        display_df["equity_after"] = display_df["equity_after"].apply(lambda x: f"${x:,.0f}")

    # Add visual indicator for assignments
    if "action" in display_df.columns:
        display_df["action"] = display_df["action"].apply(_format_action_with_indicator)

    # Rename columns
    column_map = {
        "date": "Date",
        "action": "Action",
        "instrument": "Instrument",
        "quantity": "Qty",
        "price": "Price",
        "value": "Value",
        "commission": "Fee",
        "cash_after": "Cash",
        "equity_after": "Equity",
        "notes": "Notes",
    }

    display_df = display_df.rename(columns=column_map)

    return display_df


def _format_action_with_indicator(action: str) -> str:
    """Format action with visual indicator for assignments."""
    if "assigned" in action.lower():
        return f"⚠️ {action}"
    elif "expired" in action.lower():
        return f"✓ {action}"
    else:
        return action


def _count_profitable_trades(transactions_df: pd.DataFrame) -> int:
    """Count number of profitable trades."""
    if transactions_df.empty or "value" not in transactions_df.columns:
        return 0

    # Count trades where value is positive (profit)
    return len(transactions_df[transactions_df["value"] > 0])


def _count_losing_trades(transactions_df: pd.DataFrame) -> int:
    """Count number of losing trades."""
    if transactions_df.empty or "value" not in transactions_df.columns:
        return 0

    # Count trades where value is negative (loss)
    return len(transactions_df[transactions_df["value"] < 0])


def _get_largest_profit(transactions_df: pd.DataFrame) -> float:
    """Get largest individual profit."""
    if transactions_df.empty or "value" not in transactions_df.columns:
        return 0.0

    profitable = transactions_df[transactions_df["value"] > 0]
    if profitable.empty:
        return 0.0

    return profitable["value"].max()


def _get_largest_loss(transactions_df: pd.DataFrame) -> float:
    """Get largest individual loss."""
    if transactions_df.empty or "value" not in transactions_df.columns:
        return 0.0

    losing = transactions_df[transactions_df["value"] < 0]
    if losing.empty:
        return 0.0

    return abs(losing["value"].min())


def _get_avg_win(transactions_df: pd.DataFrame) -> float:
    """Get average win size."""
    if transactions_df.empty or "value" not in transactions_df.columns:
        return 0.0

    profitable = transactions_df[transactions_df["value"] > 0]
    if profitable.empty:
        return 0.0

    return profitable["value"].mean()


def _get_avg_loss(transactions_df: pd.DataFrame) -> float:
    """Get average loss size."""
    if transactions_df.empty or "value" not in transactions_df.columns:
        return 0.0

    losing = transactions_df[transactions_df["value"] < 0]
    if losing.empty:
        return 0.0

    return abs(losing["value"].mean())
