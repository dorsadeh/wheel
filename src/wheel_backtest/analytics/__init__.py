"""Analytics and performance metrics.

This module provides equity curve tracking, performance metrics, and benchmark calculations.

Usage:
    from wheel_backtest.analytics import (
        BuyAndHoldBenchmark,
        EquityCurve,
        MetricsCalculator,
        PerformanceMetrics,
    )

    # Calculate backtest metrics
    calculator = MetricsCalculator(risk_free_rate=0.04)
    metrics = calculator.calculate(equity_curve, start_date, end_date, initial_capital)

    # Calculate benchmark
    benchmark = BuyAndHoldBenchmark(yfinance_provider)
    curve = benchmark.calculate("SPY", start_date, end_date, 100_000)
"""

from wheel_backtest.analytics.benchmark import BuyAndHoldBenchmark
from wheel_backtest.analytics.equity import EquityCurve, EquityPoint
from wheel_backtest.analytics.metrics import (
    MetricsCalculator,
    PerformanceMetrics,
    calculate_drawdown_series,
)

__all__ = [
    "BuyAndHoldBenchmark",
    "EquityCurve",
    "EquityPoint",
    "MetricsCalculator",
    "PerformanceMetrics",
    "calculate_drawdown_series",
]
