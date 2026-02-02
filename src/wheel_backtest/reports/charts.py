"""Matplotlib chart generation for backtesting results.

Provides visualization of equity curves and strategy comparison.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

from wheel_backtest.analytics.equity import EquityCurve


def plot_equity_curve(
    curve: EquityCurve,
    title: str = "Equity Curve",
    output_path: Path | None = None,
    show: bool = False,
) -> plt.Figure:
    """Plot a single equity curve.

    Args:
        curve: EquityCurve to plot
        title: Chart title
        output_path: If provided, save chart to this path
        show: If True, display chart interactively

    Returns:
        Matplotlib figure object
    """
    df = curve.to_dataframe()

    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(df.index, df["total"], label="Total Equity", linewidth=2)
    ax.fill_between(df.index, df["total"], alpha=0.3)

    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xlabel("Date")
    ax.set_ylabel("Portfolio Value ($)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Format x-axis dates
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.xticks(rotation=45)

    # Format y-axis with comma separators
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, p: f"${x:,.0f}")
    )

    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")

    if show:
        plt.show()

    return fig


def plot_equity_comparison(
    curves: dict[str, EquityCurve],
    title: str = "Strategy Comparison",
    output_path: Path | None = None,
    show: bool = False,
) -> plt.Figure:
    """Plot multiple equity curves for comparison.

    Args:
        curves: Dictionary mapping strategy name to EquityCurve
        title: Chart title
        output_path: If provided, save chart to this path
        show: If True, display chart interactively

    Returns:
        Matplotlib figure object
    """
    fig, ax = plt.subplots(figsize=(12, 6))

    colors = plt.cm.tab10.colors

    for i, (name, curve) in enumerate(curves.items()):
        df = curve.to_dataframe()
        color = colors[i % len(colors)]
        ax.plot(df.index, df["total"], label=name, linewidth=2, color=color)

    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xlabel("Date")
    ax.set_ylabel("Portfolio Value ($)")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)

    # Format x-axis dates
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.xticks(rotation=45)

    # Format y-axis with comma separators
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, p: f"${x:,.0f}")
    )

    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")

    if show:
        plt.show()

    return fig


def plot_returns_comparison(
    curves: dict[str, EquityCurve],
    title: str = "Cumulative Returns Comparison",
    output_path: Path | None = None,
    show: bool = False,
) -> plt.Figure:
    """Plot cumulative returns as percentages.

    Args:
        curves: Dictionary mapping strategy name to EquityCurve
        title: Chart title
        output_path: If provided, save chart to this path
        show: If True, display chart interactively

    Returns:
        Matplotlib figure object
    """
    fig, ax = plt.subplots(figsize=(12, 6))

    colors = plt.cm.tab10.colors

    for i, (name, curve) in enumerate(curves.items()):
        returns = curve.get_cumulative_returns() * 100  # Convert to percentage
        color = colors[i % len(colors)]
        ax.plot(returns.index, returns.values, label=name, linewidth=2, color=color)

    ax.axhline(y=0, color="gray", linestyle="--", linewidth=1)

    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative Return (%)")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)

    # Format x-axis dates
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.xticks(rotation=45)

    # Format y-axis as percentage
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, p: f"{x:.0f}%")
    )

    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")

    if show:
        plt.show()

    return fig


def plot_drawdown(
    curve: EquityCurve,
    title: str = "Drawdown",
    output_path: Path | None = None,
    show: bool = False,
) -> plt.Figure:
    """Plot drawdown chart showing decline from peak.

    Args:
        curve: EquityCurve to analyze
        title: Chart title
        output_path: If provided, save chart to this path
        show: If True, display chart interactively

    Returns:
        Matplotlib figure object
    """
    df = curve.to_dataframe()

    # Calculate running maximum and drawdown
    running_max = df["total"].cummax()
    drawdown = (df["total"] - running_max) / running_max * 100

    fig, ax = plt.subplots(figsize=(12, 4))

    ax.fill_between(df.index, drawdown, 0, alpha=0.5, color="red")
    ax.plot(df.index, drawdown, color="darkred", linewidth=1)

    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xlabel("Date")
    ax.set_ylabel("Drawdown (%)")
    ax.grid(True, alpha=0.3)

    # Format x-axis dates
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.xticks(rotation=45)

    # Format y-axis as percentage
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, p: f"{x:.1f}%")
    )

    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")

    if show:
        plt.show()

    return fig


def create_benchmark_report(
    benchmark_curve: EquityCurve,
    ticker: str,
    initial_capital: float,
    output_dir: Path,
) -> dict[str, Path]:
    """Create full benchmark report with multiple charts.

    Args:
        benchmark_curve: Buy-and-hold equity curve
        ticker: Stock symbol
        initial_capital: Starting capital
        output_dir: Directory to save charts

    Returns:
        Dictionary mapping chart name to file path
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    charts = {}

    # Main equity curve
    equity_path = output_dir / f"{ticker}_benchmark_equity.png"
    plot_equity_curve(
        benchmark_curve,
        title=f"{ticker} Buy-and-Hold Equity Curve",
        output_path=equity_path,
    )
    charts["equity"] = equity_path
    plt.close()

    # Drawdown
    drawdown_path = output_dir / f"{ticker}_benchmark_drawdown.png"
    plot_drawdown(
        benchmark_curve,
        title=f"{ticker} Buy-and-Hold Drawdown",
        output_path=drawdown_path,
    )
    charts["drawdown"] = drawdown_path
    plt.close()

    # Save equity data as CSV
    csv_path = output_dir / f"{ticker}_benchmark_equity.csv"
    df = benchmark_curve.to_dataframe()
    df.to_csv(csv_path)
    charts["data"] = csv_path

    return charts
