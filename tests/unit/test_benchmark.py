"""Tests for buy-and-hold benchmark calculator."""

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from wheel_backtest.analytics.benchmark import BuyAndHoldBenchmark
from wheel_backtest.analytics.equity import EquityCurve
from wheel_backtest.data import DataCache, YFinanceProvider


class TestBuyAndHoldBenchmark:
    """Tests for BuyAndHoldBenchmark."""

    def test_calculate_with_cached_data(self, temp_dir: Path) -> None:
        """Test benchmark calculation with cached price data."""
        cache = DataCache(temp_dir / "cache")
        provider = YFinanceProvider(cache)

        # Pre-populate cache with mock price data
        mock_df = pd.DataFrame({
            "open": [100.0, 101.0, 102.0],
            "high": [102.0, 103.0, 104.0],
            "low": [99.0, 100.0, 101.0],
            "close": [101.0, 102.0, 103.0],
            "adjusted_close": [100.0, 101.0, 102.0],  # 1% daily gain
            "volume": [1000000, 1100000, 1200000],
            "dividend": [0.0, 0.0, 0.0],
        }, index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]))
        mock_df.index.name = "date"
        cache.put("yfinance", "SPY", "underlying", mock_df)

        # Calculate benchmark
        benchmark = BuyAndHoldBenchmark(provider)
        curve = benchmark.calculate(
            ticker="SPY",
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 4),
            initial_capital=10_000.0,
        )

        assert len(curve) == 3
        # Initial: $10,000 buys 100 shares at $100 adjusted
        # Day 1: 100 shares * $100 = $10,000
        # Day 2: 100 shares * $101 = $10,100
        # Day 3: 100 shares * $102 = $10,200
        assert curve[0].total == 10_000.0
        assert curve[1].total == 10_100.0
        assert curve[2].total == 10_200.0

    def test_calculate_fractional_shares(self, temp_dir: Path) -> None:
        """Test that fractional shares are used for adjusted returns."""
        cache = DataCache(temp_dir / "cache")
        provider = YFinanceProvider(cache)

        # Price that doesn't divide evenly into capital
        mock_df = pd.DataFrame({
            "open": [33.0],
            "high": [34.0],
            "low": [32.0],
            "close": [33.33],
            "adjusted_close": [33.33],
            "volume": [1000000],
            "dividend": [0.0],
        }, index=pd.to_datetime(["2024-01-02"]))
        mock_df.index.name = "date"
        cache.put("yfinance", "TEST", "underlying", mock_df)

        benchmark = BuyAndHoldBenchmark(provider)
        curve = benchmark.calculate(
            ticker="TEST",
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 2),
            initial_capital=100.0,
        )

        # Should invest all capital (fractional shares)
        assert len(curve) == 1
        assert abs(curve[0].total - 100.0) < 0.01

    def test_calculate_empty_result(self, temp_dir: Path) -> None:
        """Test calculation with no price data."""
        cache = DataCache(temp_dir / "cache")
        provider = YFinanceProvider(cache)

        # Empty cache - will return empty DataFrame
        benchmark = BuyAndHoldBenchmark(provider)

        # Mock the provider to return empty
        empty_df = pd.DataFrame()
        cache.put("yfinance", "EMPTY", "underlying", empty_df)

        curve = benchmark.calculate(
            ticker="EMPTY",
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 4),
            initial_capital=10_000.0,
        )

        assert len(curve) == 0

    def test_get_summary(self, temp_dir: Path) -> None:
        """Test summary statistics calculation."""
        cache = DataCache(temp_dir / "cache")
        provider = YFinanceProvider(cache)

        # Create data for 1 year (365 days approximation)
        dates = pd.date_range("2023-01-02", "2024-01-02", freq="B")  # Business days
        prices = [100.0 * (1.001 ** i) for i in range(len(dates))]  # ~0.1% daily gain

        mock_df = pd.DataFrame({
            "open": prices,
            "high": prices,
            "low": prices,
            "close": prices,
            "adjusted_close": prices,
            "volume": [1000000] * len(dates),
            "dividend": [0.0] * len(dates),
        }, index=dates)
        mock_df.index.name = "date"
        cache.put("yfinance", "SPY", "underlying", mock_df)

        benchmark = BuyAndHoldBenchmark(provider)
        curve = benchmark.calculate(
            ticker="SPY",
            start_date=date(2023, 1, 2),
            end_date=date(2024, 1, 2),
            initial_capital=100_000.0,
        )

        summary = benchmark.get_summary(curve, 100_000.0)

        assert summary["start_date"] == date(2023, 1, 2)
        assert summary["end_date"] == date(2024, 1, 2)
        assert summary["initial_capital"] == 100_000.0
        assert summary["final_value"] > 100_000.0
        assert summary["total_return"] > 0
        assert summary["total_return_pct"] > 0
        assert summary["cagr_pct"] is not None
        assert summary["trading_days"] > 200  # Should have many business days

    def test_get_summary_empty_curve(self, temp_dir: Path) -> None:
        """Test summary with empty curve."""
        cache = DataCache(temp_dir / "cache")
        provider = YFinanceProvider(cache)
        benchmark = BuyAndHoldBenchmark(provider)

        empty_curve = EquityCurve()
        summary = benchmark.get_summary(empty_curve, 100_000.0)

        assert summary["start_date"] is None
        assert summary["final_value"] is None
        assert summary["cagr_pct"] is None

    def test_calculate_with_dividends(self, temp_dir: Path) -> None:
        """Test calculation with dividend tracking."""
        cache = DataCache(temp_dir / "cache")
        provider = YFinanceProvider(cache)

        # Create data with a dividend
        mock_df = pd.DataFrame({
            "open": [100.0, 100.0, 100.0],
            "high": [101.0, 101.0, 101.0],
            "low": [99.0, 99.0, 99.0],
            "close": [100.0, 100.0, 100.0],
            "adjusted_close": [100.0, 100.0, 100.0],
            "volume": [1000000, 1100000, 1200000],
            "dividend": [0.0, 1.50, 0.0],  # $1.50 dividend on day 2
        }, index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]))
        mock_df.index.name = "date"
        cache.put("yfinance", "DIV", "underlying", mock_df)

        benchmark = BuyAndHoldBenchmark(provider)
        curve, dividends = benchmark.calculate_with_dividends(
            ticker="DIV",
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 4),
            initial_capital=10_000.0,
        )

        # $10,000 / $100 = 100 whole shares
        # Dividend: 100 shares * $1.50 = $150
        assert len(curve) == 3
        assert len(dividends) == 1
        assert dividends["total_dividend"].iloc[0] == 150.0

        # Final value should be 100 shares * $100 + $150 cash
        assert curve[2].stock_value == 10_000.0
        assert curve[2].cash == 150.0
        assert curve[2].total == 10_150.0
