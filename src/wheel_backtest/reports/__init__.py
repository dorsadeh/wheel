"""Report generation and visualization.

This module provides chart generation and report exports.

Usage:
    from wheel_backtest.reports import plot_equity_curve, create_benchmark_report

    plot_equity_curve(curve, output_path=Path("./output/equity.png"))
"""

from wheel_backtest.reports.charts import (
    create_benchmark_report,
    plot_drawdown,
    plot_equity_comparison,
    plot_equity_curve,
    plot_returns_comparison,
)

__all__ = [
    "create_benchmark_report",
    "plot_drawdown",
    "plot_equity_comparison",
    "plot_equity_curve",
    "plot_returns_comparison",
]
