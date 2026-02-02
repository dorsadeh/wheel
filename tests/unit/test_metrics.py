"""Tests for performance metrics calculations."""

from datetime import date, timedelta

import pytest

from wheel_backtest.analytics import (
    EquityCurve,
    MetricsCalculator,
    calculate_drawdown_series,
)


class TestMetricsCalculator:
    """Tests for MetricsCalculator."""

    @pytest.fixture
    def simple_equity_curve(self) -> EquityCurve:
        """Create a simple equity curve for testing."""
        curve = EquityCurve()
        start = date(2024, 1, 1)

        # Create a simple upward trending equity curve
        for i in range(252):  # One year of trading days
            trade_date = start + timedelta(days=i)
            equity = 100_000 + (i * 100)  # Grows by $100/day
            curve.add_point(trade_date, cash=equity, stock_value=0.0)

        return curve

    @pytest.fixture
    def volatile_equity_curve(self) -> EquityCurve:
        """Create a volatile equity curve with drawdowns."""
        curve = EquityCurve()
        start = date(2024, 1, 1)

        # Create curve with peaks and valleys
        values = [
            100000, 105000, 110000, 115000, 120000,  # Up
            118000, 115000, 110000, 108000,  # Drawdown
            112000, 118000, 125000, 130000,  # Recovery and new high
            128000, 125000, 120000,  # Another drawdown
            125000, 130000, 135000, 140000,  # Final rally
        ]

        for i, value in enumerate(values):
            trade_date = start + timedelta(days=i)
            curve.add_point(trade_date, cash=value, stock_value=0.0)

        return curve

    def test_calculator_initialization(self) -> None:
        """Test MetricsCalculator initialization."""
        calc = MetricsCalculator(risk_free_rate=0.04)
        assert calc.risk_free_rate == 0.04

        calc_default = MetricsCalculator()
        assert calc_default.risk_free_rate == 0.0

    def test_calculate_basic_metrics(self, simple_equity_curve: EquityCurve) -> None:
        """Test basic metrics calculation."""
        calc = MetricsCalculator()

        metrics = calc.calculate(
            equity_curve=simple_equity_curve,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            initial_capital=100_000,
        )

        # Total return should be positive
        assert metrics.total_return > 0
        assert metrics.total_return_pct > 0

        # CAGR should be calculated
        assert metrics.cagr > 0

        # Volatility should be low for steady growth
        assert metrics.volatility >= 0

    def test_total_return_calculation(self, simple_equity_curve: EquityCurve) -> None:
        """Test total return calculation."""
        calc = MetricsCalculator()

        metrics = calc.calculate(
            equity_curve=simple_equity_curve,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            initial_capital=100_000,
        )

        # Should be approximately 251 * 100 = 25,100
        assert metrics.total_return == pytest.approx(25_100, abs=200)

        # Percentage should match
        expected_pct = (125_100 / 100_000 - 1) * 100
        assert metrics.total_return_pct == pytest.approx(expected_pct, abs=0.5)

    def test_cagr_calculation(self, simple_equity_curve: EquityCurve) -> None:
        """Test CAGR calculation."""
        calc = MetricsCalculator()

        metrics = calc.calculate(
            equity_curve=simple_equity_curve,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            initial_capital=100_000,
        )

        # CAGR should be positive for growing equity
        assert metrics.cagr > 0

        # For one year, CAGR ≈ total return %
        assert metrics.cagr == pytest.approx(metrics.total_return_pct, abs=0.1)

    def test_sharpe_ratio_calculation(self, simple_equity_curve: EquityCurve) -> None:
        """Test Sharpe ratio calculation."""
        calc = MetricsCalculator(risk_free_rate=0.04)

        metrics = calc.calculate(
            equity_curve=simple_equity_curve,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            initial_capital=100_000,
        )

        # Sharpe ratio should be calculated
        # Steady growth should give good Sharpe ratio
        assert metrics.sharpe_ratio > 0

    def test_sortino_ratio_calculation(self, volatile_equity_curve: EquityCurve) -> None:
        """Test Sortino ratio calculation."""
        calc = MetricsCalculator(risk_free_rate=0.04)

        metrics = calc.calculate(
            equity_curve=volatile_equity_curve,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 20),
            initial_capital=100_000,
        )

        # Sortino should be higher than Sharpe (only penalizes downside)
        assert metrics.sortino_ratio >= 0

    def test_max_drawdown_calculation(self, volatile_equity_curve: EquityCurve) -> None:
        """Test maximum drawdown calculation."""
        calc = MetricsCalculator()

        metrics = calc.calculate(
            equity_curve=volatile_equity_curve,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 20),
            initial_capital=100_000,
        )

        # Max drawdown should be negative
        assert metrics.max_drawdown < 0

        # Drawdown from 120k to 108k = -10%
        assert metrics.max_drawdown <= -10

        # Duration should be positive
        assert metrics.max_drawdown_duration >= 0

    def test_volatility_calculation(self, volatile_equity_curve: EquityCurve) -> None:
        """Test volatility calculation."""
        calc = MetricsCalculator()

        metrics = calc.calculate(
            equity_curve=volatile_equity_curve,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 20),
            initial_capital=100_000,
        )

        # Volatile curve should have higher volatility
        assert metrics.volatility > 0

    def test_win_rate_calculation(self, volatile_equity_curve: EquityCurve) -> None:
        """Test win rate calculation."""
        calc = MetricsCalculator()

        metrics = calc.calculate(
            equity_curve=volatile_equity_curve,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 20),
            initial_capital=100_000,
        )

        # Win rate should be between 0 and 100
        assert 0 <= metrics.win_rate <= 100

    def test_profit_factor_calculation(self, volatile_equity_curve: EquityCurve) -> None:
        """Test profit factor calculation."""
        calc = MetricsCalculator()

        metrics = calc.calculate(
            equity_curve=volatile_equity_curve,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 20),
            initial_capital=100_000,
        )

        # Profit factor should be positive for profitable strategy
        assert metrics.profit_factor > 0

    def test_calmar_ratio_calculation(self, volatile_equity_curve: EquityCurve) -> None:
        """Test Calmar ratio calculation."""
        calc = MetricsCalculator()

        metrics = calc.calculate(
            equity_curve=volatile_equity_curve,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 20),
            initial_capital=100_000,
        )

        # Calmar ratio = CAGR / |Max Drawdown|
        if metrics.max_drawdown != 0:
            expected_calmar = metrics.cagr / abs(metrics.max_drawdown)
            assert metrics.calmar_ratio == pytest.approx(expected_calmar, abs=0.01)

    def test_empty_equity_curve(self) -> None:
        """Test metrics with empty equity curve."""
        calc = MetricsCalculator()
        empty_curve = EquityCurve()

        metrics = calc.calculate(
            equity_curve=empty_curve,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            initial_capital=100_000,
        )

        # Should return zeros for empty data
        assert metrics.total_return == 0.0
        assert metrics.cagr == 0.0
        assert metrics.sharpe_ratio == 0.0

    def test_single_point_equity_curve(self) -> None:
        """Test metrics with only one data point."""
        calc = MetricsCalculator()
        curve = EquityCurve()
        curve.add_point(date(2024, 1, 1), cash=100_000, stock_value=0.0)

        metrics = calc.calculate(
            equity_curve=curve,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 1),
            initial_capital=100_000,
        )

        # Should handle gracefully
        assert metrics.total_return == 0.0
        assert metrics.volatility == 0.0


class TestDrawdownCalculation:
    """Tests for drawdown series calculation."""

    def test_calculate_drawdown_series(self) -> None:
        """Test drawdown series calculation."""
        import pandas as pd

        equity = pd.Series([100, 110, 105, 115, 108, 120])

        drawdown = calculate_drawdown_series(equity)

        # At peak (index 1, 3, 5), drawdown should be 0
        assert drawdown.iloc[1] == 0.0
        assert drawdown.iloc[3] == 0.0
        assert drawdown.iloc[5] == 0.0

        # At index 2: down from 110 to 105 = -4.5%
        assert drawdown.iloc[2] == pytest.approx(-4.545, abs=0.01)

        # At index 4: down from 115 to 108 = -6.1%
        assert drawdown.iloc[4] == pytest.approx(-6.087, abs=0.01)

    def test_drawdown_always_negative_or_zero(self) -> None:
        """Test that drawdown is never positive."""
        import pandas as pd

        equity = pd.Series([100, 95, 90, 85, 95, 100, 105])

        drawdown = calculate_drawdown_series(equity)

        # All drawdown values should be <= 0
        assert all(drawdown <= 0)
