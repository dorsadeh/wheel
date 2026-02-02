"""Analytics and performance metrics.

This module provides equity curve tracking and benchmark calculations.

Usage:
    from wheel_backtest.analytics import BuyAndHoldBenchmark, EquityCurve

    benchmark = BuyAndHoldBenchmark(yfinance_provider)
    curve = benchmark.calculate("SPY", start_date, end_date, 100_000)
"""

from wheel_backtest.analytics.benchmark import BuyAndHoldBenchmark
from wheel_backtest.analytics.equity import EquityCurve, EquityPoint

__all__ = [
    "BuyAndHoldBenchmark",
    "EquityCurve",
    "EquityPoint",
]
