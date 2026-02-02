"""Performance metrics calculations.

Provides standard financial metrics for backtest evaluation.
"""

import math
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from wheel_backtest.analytics.equity import EquityCurve


@dataclass
class PerformanceMetrics:
    """Collection of performance metrics for a backtest.

    Attributes:
        total_return: Total return in dollars
        total_return_pct: Total return as percentage
        cagr: Compound Annual Growth Rate (%)
        sharpe_ratio: Risk-adjusted return (annualized)
        sortino_ratio: Downside risk-adjusted return (annualized)
        max_drawdown: Maximum peak-to-trough decline (%)
        max_drawdown_duration: Days from peak to recovery
        volatility: Annualized volatility (%)
        win_rate: Percentage of profitable trades/days
        profit_factor: Gross profit / gross loss
        calmar_ratio: CAGR / max drawdown
    """

    total_return: float
    total_return_pct: float
    cagr: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_duration: int
    volatility: float
    win_rate: float
    profit_factor: float
    calmar_ratio: float


class MetricsCalculator:
    """Calculate performance metrics from equity curve."""

    def __init__(self, risk_free_rate: float = 0.0):
        """Initialize calculator.

        Args:
            risk_free_rate: Annual risk-free rate for Sharpe/Sortino (e.g., 0.04 for 4%)
        """
        self.risk_free_rate = risk_free_rate

    def calculate(
        self,
        equity_curve: EquityCurve,
        start_date: date,
        end_date: date,
        initial_capital: float,
    ) -> PerformanceMetrics:
        """Calculate all performance metrics.

        Args:
            equity_curve: Daily equity values
            start_date: Backtest start date
            end_date: Backtest end date
            initial_capital: Starting capital

        Returns:
            PerformanceMetrics with all calculated values
        """
        df = equity_curve.to_dataframe()

        if df.empty or len(df) < 2:
            return self._empty_metrics()

        # Calculate returns
        daily_returns = df["total"].pct_change().dropna()
        total_return = df["total"].iloc[-1] - df["total"].iloc[0]
        total_return_pct = (df["total"].iloc[-1] / df["total"].iloc[0] - 1) * 100

        # Calculate time period
        days = (end_date - start_date).days
        years = days / 365.25

        # CAGR
        if years > 0:
            cagr = (pow(df["total"].iloc[-1] / df["total"].iloc[0], 1 / years) - 1) * 100
        else:
            cagr = 0.0

        # Volatility (annualized)
        if len(daily_returns) > 1:
            volatility = daily_returns.std() * math.sqrt(252) * 100
        else:
            volatility = 0.0

        # Sharpe Ratio
        sharpe_ratio = self._calculate_sharpe_ratio(daily_returns)

        # Sortino Ratio
        sortino_ratio = self._calculate_sortino_ratio(daily_returns)

        # Maximum Drawdown
        max_dd, max_dd_duration = self._calculate_max_drawdown(df["total"])

        # Win Rate
        win_rate = self._calculate_win_rate(daily_returns)

        # Profit Factor
        profit_factor = self._calculate_profit_factor(daily_returns)

        # Calmar Ratio
        calmar_ratio = cagr / abs(max_dd) if max_dd != 0 else 0.0

        return PerformanceMetrics(
            total_return=total_return,
            total_return_pct=total_return_pct,
            cagr=cagr,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_dd,
            max_drawdown_duration=max_dd_duration,
            volatility=volatility,
            win_rate=win_rate,
            profit_factor=profit_factor,
            calmar_ratio=calmar_ratio,
        )

    def _calculate_sharpe_ratio(self, returns: pd.Series) -> float:
        """Calculate annualized Sharpe ratio.

        Args:
            returns: Daily returns series

        Returns:
            Sharpe ratio
        """
        if len(returns) < 2:
            return 0.0

        excess_returns = returns - (self.risk_free_rate / 252)
        mean_excess = excess_returns.mean()
        std_excess = excess_returns.std()

        if std_excess == 0:
            return 0.0

        return (mean_excess / std_excess) * math.sqrt(252)

    def _calculate_sortino_ratio(self, returns: pd.Series) -> float:
        """Calculate annualized Sortino ratio.

        Uses only downside volatility (negative returns).

        Args:
            returns: Daily returns series

        Returns:
            Sortino ratio
        """
        if len(returns) < 2:
            return 0.0

        excess_returns = returns - (self.risk_free_rate / 252)
        mean_excess = excess_returns.mean()

        # Downside deviation (only negative returns)
        downside_returns = excess_returns[excess_returns < 0]
        if len(downside_returns) == 0:
            return 0.0

        downside_std = downside_returns.std()
        if downside_std == 0:
            return 0.0

        return (mean_excess / downside_std) * math.sqrt(252)

    def _calculate_max_drawdown(self, equity: pd.Series) -> tuple[float, int]:
        """Calculate maximum drawdown and its duration.

        Args:
            equity: Equity series

        Returns:
            Tuple of (max_drawdown_pct, duration_in_days)
        """
        if len(equity) < 2:
            return (0.0, 0)

        # Calculate running maximum
        running_max = equity.expanding().max()

        # Calculate drawdown
        drawdown = (equity - running_max) / running_max * 100

        # Maximum drawdown (most negative)
        max_dd = drawdown.min()

        # Calculate duration
        # Find longest period from peak to recovery
        max_duration = 0
        current_duration = 0
        at_peak = True

        for dd in drawdown:
            if dd < -0.01:  # In drawdown (threshold to avoid noise)
                current_duration += 1
                at_peak = False
            else:  # At or near peak
                if not at_peak:
                    max_duration = max(max_duration, current_duration)
                    current_duration = 0
                at_peak = True

        # Handle case where we end in drawdown
        max_duration = max(max_duration, current_duration)

        return (max_dd, max_duration)

    def _calculate_win_rate(self, returns: pd.Series) -> float:
        """Calculate win rate (% of profitable days).

        Args:
            returns: Daily returns series

        Returns:
            Win rate as percentage
        """
        if len(returns) == 0:
            return 0.0

        winning_days = (returns > 0).sum()
        return (winning_days / len(returns)) * 100

    def _calculate_profit_factor(self, returns: pd.Series) -> float:
        """Calculate profit factor (gross profit / gross loss).

        Args:
            returns: Daily returns series

        Returns:
            Profit factor
        """
        if len(returns) == 0:
            return 0.0

        gross_profit = returns[returns > 0].sum()
        gross_loss = abs(returns[returns < 0].sum())

        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0

        return gross_profit / gross_loss

    def _empty_metrics(self) -> PerformanceMetrics:
        """Return empty metrics when insufficient data."""
        return PerformanceMetrics(
            total_return=0.0,
            total_return_pct=0.0,
            cagr=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            max_drawdown=0.0,
            max_drawdown_duration=0,
            volatility=0.0,
            win_rate=0.0,
            profit_factor=0.0,
            calmar_ratio=0.0,
        )


def calculate_drawdown_series(equity: pd.Series) -> pd.Series:
    """Calculate drawdown series for plotting.

    Args:
        equity: Equity series

    Returns:
        Drawdown series (percentage from peak)
    """
    running_max = equity.expanding().max()
    drawdown = (equity - running_max) / running_max * 100
    return drawdown
