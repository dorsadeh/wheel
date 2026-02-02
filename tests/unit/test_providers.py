"""Tests for data providers."""

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from wheel_backtest.data import (
    DataCache,
    PhilippdubachProvider,
    YFinanceProvider,
)


class TestPhilippdubachProvider:
    """Tests for PhilippdubachProvider."""

    def test_provider_name(self, temp_dir: Path) -> None:
        """Test provider name property."""
        cache = DataCache(temp_dir / "cache")
        provider = PhilippdubachProvider(cache)
        assert provider.name == "philippdubach"

    def test_available_tickers(self, temp_dir: Path) -> None:
        """Test getting available tickers."""
        cache = DataCache(temp_dir / "cache")
        provider = PhilippdubachProvider(cache)

        tickers = provider.get_available_tickers()

        assert "SPY" in tickers
        assert "AAPL" in tickers
        assert "QQQ" in tickers
        assert len(tickers) == 104

    def test_invalid_ticker_raises(self, temp_dir: Path) -> None:
        """Test that invalid ticker raises error."""
        cache = DataCache(temp_dir / "cache")
        provider = PhilippdubachProvider(cache)

        with pytest.raises(ValueError, match="not available"):
            provider.get_options_chain("INVALID_TICKER", date(2024, 1, 2))

    def test_uses_cache(self, temp_dir: Path) -> None:
        """Test that provider uses cache."""
        cache = DataCache(temp_dir / "cache")
        provider = PhilippdubachProvider(cache)

        # Pre-populate cache with mock data
        mock_df = pd.DataFrame({
            "trade_date": pd.to_datetime(["2024-01-02", "2024-01-02"]),
            "expiration": pd.to_datetime(["2024-01-05", "2024-01-05"]),
            "strike": [470.0, 475.0],
            "option_type": ["call", "put"],
            "bid": [5.0, 3.0],
            "ask": [5.5, 3.5],
            "delta": [0.6, -0.4],
        })
        cache.put("philippdubach", "SPY", "options", mock_df)

        # Should use cached data without downloading
        chain = provider.get_options_chain("SPY", date(2024, 1, 2))

        assert len(chain) == 2
        assert list(chain["strike"]) == [470.0, 475.0]

    def test_underlying_not_implemented(self, temp_dir: Path) -> None:
        """Test that underlying prices raise NotImplementedError."""
        cache = DataCache(temp_dir / "cache")
        provider = PhilippdubachProvider(cache)

        with pytest.raises(NotImplementedError, match="YFinanceProvider"):
            provider.get_underlying_prices("SPY", date(2024, 1, 1), date(2024, 1, 31))


class TestYFinanceProvider:
    """Tests for YFinanceProvider."""

    def test_provider_name(self, temp_dir: Path) -> None:
        """Test provider name property."""
        cache = DataCache(temp_dir / "cache")
        provider = YFinanceProvider(cache)
        assert provider.name == "yfinance"

    def test_uses_cache(self, temp_dir: Path) -> None:
        """Test that provider uses cache."""
        cache = DataCache(temp_dir / "cache")
        provider = YFinanceProvider(cache)

        # Pre-populate cache with mock data
        mock_df = pd.DataFrame({
            "open": [470.0, 471.0],
            "high": [475.0, 476.0],
            "low": [468.0, 469.0],
            "close": [472.0, 473.0],
            "adjusted_close": [472.0, 473.0],
            "volume": [1000000, 1100000],
            "dividend": [0.0, 0.0],
        }, index=pd.to_datetime(["2024-01-02", "2024-01-03"]))
        mock_df.index.name = "date"

        cache.put("yfinance", "SPY", "underlying", mock_df)

        # Should use cached data
        prices = provider.get_prices("SPY", date(2024, 1, 2), date(2024, 1, 3))

        assert len(prices) == 2
        assert prices["close"].iloc[0] == 472.0

    def test_get_price_single_date(self, temp_dir: Path) -> None:
        """Test getting price for single date."""
        cache = DataCache(temp_dir / "cache")
        provider = YFinanceProvider(cache)

        # Pre-populate cache
        mock_df = pd.DataFrame({
            "open": [470.0],
            "high": [475.0],
            "low": [468.0],
            "close": [472.65],
            "adjusted_close": [461.25],
            "volume": [1000000],
            "dividend": [0.0],
        }, index=pd.to_datetime(["2024-01-02"]))
        mock_df.index.name = "date"

        cache.put("yfinance", "SPY", "underlying", mock_df)

        price = provider.get_price("SPY", date(2024, 1, 2))
        assert price == 472.65

    def test_get_adjusted_price(self, temp_dir: Path) -> None:
        """Test getting adjusted price."""
        cache = DataCache(temp_dir / "cache")
        provider = YFinanceProvider(cache)

        # Pre-populate cache
        mock_df = pd.DataFrame({
            "open": [470.0],
            "high": [475.0],
            "low": [468.0],
            "close": [472.65],
            "adjusted_close": [461.25],
            "volume": [1000000],
            "dividend": [0.0],
        }, index=pd.to_datetime(["2024-01-02"]))
        mock_df.index.name = "date"

        cache.put("yfinance", "SPY", "underlying", mock_df)

        adj_price = provider.get_adjusted_price("SPY", date(2024, 1, 2))
        assert adj_price == 461.25

    def test_get_dividends(self, temp_dir: Path) -> None:
        """Test getting dividend payments."""
        cache = DataCache(temp_dir / "cache")
        provider = YFinanceProvider(cache)

        # Pre-populate cache with dividend
        mock_df = pd.DataFrame({
            "open": [470.0, 471.0, 472.0],
            "high": [475.0, 476.0, 477.0],
            "low": [468.0, 469.0, 470.0],
            "close": [472.0, 473.0, 474.0],
            "adjusted_close": [472.0, 473.0, 474.0],
            "volume": [1000000, 1100000, 1200000],
            "dividend": [0.0, 1.50, 0.0],  # Dividend on day 2
        }, index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]))
        mock_df.index.name = "date"

        cache.put("yfinance", "SPY", "underlying", mock_df)

        divs = provider.get_dividends("SPY", date(2024, 1, 2), date(2024, 1, 4))

        assert len(divs) == 1
        assert divs["dividend"].iloc[0] == 1.50

    def test_missing_date_raises(self, temp_dir: Path) -> None:
        """Test that missing date raises error when date not in result."""
        cache = DataCache(temp_dir / "cache")
        provider = YFinanceProvider(cache)

        # Cache with data covering the requested range, but not the specific date
        # (simulating a market holiday)
        mock_df = pd.DataFrame({
            "open": [470.0, 471.0],
            "high": [475.0, 476.0],
            "low": [468.0, 469.0],
            "close": [472.0, 473.0],
            "adjusted_close": [461.0, 462.0],
            "volume": [1000000, 1100000],
            "dividend": [0.0, 0.0],
        }, index=pd.to_datetime(["2024-01-02", "2024-01-04"]))  # Skip Jan 3
        mock_df.index.name = "date"
        cache.put("yfinance", "SPY", "underlying", mock_df)

        # Request Jan 3 which is in the range but not in the data (holiday)
        with pytest.raises(ValueError, match="No price data"):
            provider.get_price("SPY", date(2024, 1, 3))

    def test_get_trading_days(self, temp_dir: Path) -> None:
        """Test getting list of trading days."""
        cache = DataCache(temp_dir / "cache")
        provider = YFinanceProvider(cache)

        # Pre-populate cache (skip weekend)
        mock_df = pd.DataFrame({
            "open": [470.0, 471.0, 472.0],
            "high": [475.0, 476.0, 477.0],
            "low": [468.0, 469.0, 470.0],
            "close": [472.0, 473.0, 474.0],
            "adjusted_close": [472.0, 473.0, 474.0],
            "volume": [1000000, 1100000, 1200000],
            "dividend": [0.0, 0.0, 0.0],
        }, index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]))
        mock_df.index.name = "date"

        cache.put("yfinance", "SPY", "underlying", mock_df)

        days = provider.get_trading_days("SPY", date(2024, 1, 2), date(2024, 1, 4))

        assert len(days) == 3
        assert days[0] == date(2024, 1, 2)
        assert days[2] == date(2024, 1, 4)
