"""Backtesting engine components.

This module provides the core engine for running wheel strategy backtests.

Usage:
    from wheel_backtest.engine import WheelBacktest
    from wheel_backtest.config import BacktestConfig

    config = BacktestConfig(ticker="SPY", initial_capital=100_000)
    backtest = WheelBacktest(config)
    result = backtest.run()
"""

from wheel_backtest.engine.backtest import (
    BacktestResult,
    Transaction,
    WheelBacktest,
)
from wheel_backtest.engine.options import (
    Fill,
    OptionOrder,
    OptionSelector,
    OrderAction,
)
from wheel_backtest.engine.portfolio import (
    OptionPosition,
    OptionType,
    Portfolio,
    PositionSide,
)
from wheel_backtest.engine.wheel import (
    WheelEvent,
    WheelState,
    WheelStrategy,
)

__all__ = [
    "BacktestResult",
    "Fill",
    "OptionOrder",
    "OptionPosition",
    "OptionSelector",
    "OptionType",
    "OrderAction",
    "Portfolio",
    "PositionSide",
    "Transaction",
    "WheelBacktest",
    "WheelEvent",
    "WheelState",
    "WheelStrategy",
]
