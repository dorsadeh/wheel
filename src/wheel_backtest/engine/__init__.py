"""Backtesting engine components.

This module provides the core engine for running wheel strategy backtests.

Usage:
    from wheel_backtest.engine import Portfolio, WheelStrategy, OptionSelector

    portfolio = Portfolio(cash=100_000)
    selector = OptionSelector(dte_target=30, otm_pct=0.05)
    strategy = WheelStrategy(portfolio, selector)
"""

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
    "Fill",
    "OptionOrder",
    "OptionPosition",
    "OptionSelector",
    "OptionType",
    "OrderAction",
    "Portfolio",
    "PositionSide",
    "WheelEvent",
    "WheelState",
    "WheelStrategy",
]
