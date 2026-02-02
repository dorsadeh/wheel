"""Tests for equity curve data structures."""

from datetime import date

import pandas as pd
import pytest

from wheel_backtest.analytics.equity import EquityCurve, EquityPoint


class TestEquityPoint:
    """Tests for EquityPoint."""

    def test_total_calculation(self) -> None:
        """Test total property calculation."""
        point = EquityPoint(
            date=date(2024, 1, 2),
            cash=50_000.0,
            stock_value=45_000.0,
            options_value=5_000.0,
        )
        assert point.total == 100_000.0

    def test_total_with_zero_options(self) -> None:
        """Test total with no options value."""
        point = EquityPoint(
            date=date(2024, 1, 2),
            cash=30_000.0,
            stock_value=70_000.0,
        )
        assert point.total == 100_000.0


class TestEquityCurve:
    """Tests for EquityCurve."""

    def test_empty_curve(self) -> None:
        """Test empty equity curve."""
        curve = EquityCurve()
        assert len(curve) == 0
        assert curve.start_date is None
        assert curve.end_date is None
        assert curve.start_value is None
        assert curve.end_value is None

    def test_add_point(self) -> None:
        """Test adding points to curve."""
        curve = EquityCurve()
        curve.add_point(
            trade_date=date(2024, 1, 2),
            cash=100_000.0,
            stock_value=0.0,
        )
        curve.add_point(
            trade_date=date(2024, 1, 3),
            cash=50_000.0,
            stock_value=52_000.0,
        )

        assert len(curve) == 2
        assert curve.start_date == date(2024, 1, 2)
        assert curve.end_date == date(2024, 1, 3)
        assert curve.start_value == 100_000.0
        assert curve.end_value == 102_000.0

    def test_iteration(self) -> None:
        """Test iterating over curve."""
        curve = EquityCurve()
        curve.add_point(date(2024, 1, 2), 100_000.0, 0.0)
        curve.add_point(date(2024, 1, 3), 100_500.0, 0.0)

        dates = [p.date for p in curve]
        assert dates == [date(2024, 1, 2), date(2024, 1, 3)]

    def test_indexing(self) -> None:
        """Test index access."""
        curve = EquityCurve()
        curve.add_point(date(2024, 1, 2), 100_000.0, 0.0)
        curve.add_point(date(2024, 1, 3), 101_000.0, 0.0)

        assert curve[0].total == 100_000.0
        assert curve[1].total == 101_000.0

    def test_to_dataframe(self) -> None:
        """Test conversion to DataFrame."""
        curve = EquityCurve()
        curve.add_point(date(2024, 1, 2), 50_000.0, 50_000.0, 1_000.0)
        curve.add_point(date(2024, 1, 3), 49_000.0, 52_000.0, 500.0)

        df = curve.to_dataframe()

        assert len(df) == 2
        assert list(df.columns) == ["cash", "stock_value", "options_value", "total"]
        assert df.index.name == "date"
        assert df["total"].iloc[0] == 101_000.0
        assert df["total"].iloc[1] == 101_500.0

    def test_to_dataframe_empty(self) -> None:
        """Test DataFrame conversion with empty curve."""
        curve = EquityCurve()
        df = curve.to_dataframe()

        assert df.empty
        assert "total" in df.columns

    def test_from_dataframe(self) -> None:
        """Test creating curve from DataFrame."""
        df = pd.DataFrame({
            "cash": [50_000.0, 48_000.0],
            "stock_value": [50_000.0, 53_000.0],
            "options_value": [0.0, 0.0],
        }, index=pd.to_datetime(["2024-01-02", "2024-01-03"]))

        curve = EquityCurve.from_dataframe(df)

        assert len(curve) == 2
        assert curve[0].cash == 50_000.0
        assert curve[1].stock_value == 53_000.0

    def test_get_returns(self) -> None:
        """Test daily returns calculation."""
        curve = EquityCurve()
        curve.add_point(date(2024, 1, 2), 100_000.0, 0.0)
        curve.add_point(date(2024, 1, 3), 101_000.0, 0.0)  # +1%
        curve.add_point(date(2024, 1, 4), 99_990.0, 0.0)  # -1%

        returns = curve.get_returns()

        assert len(returns) == 2
        assert abs(returns.iloc[0] - 0.01) < 0.0001
        assert abs(returns.iloc[1] - (-0.01)) < 0.001

    def test_get_cumulative_returns(self) -> None:
        """Test cumulative returns calculation."""
        curve = EquityCurve()
        curve.add_point(date(2024, 1, 2), 100_000.0, 0.0)
        curve.add_point(date(2024, 1, 3), 110_000.0, 0.0)  # +10%
        curve.add_point(date(2024, 1, 4), 120_000.0, 0.0)  # +20%

        cum_returns = curve.get_cumulative_returns()

        assert len(cum_returns) == 3
        assert cum_returns.iloc[0] == pytest.approx(0.0)
        assert cum_returns.iloc[1] == pytest.approx(0.1)
        assert cum_returns.iloc[2] == pytest.approx(0.2)
