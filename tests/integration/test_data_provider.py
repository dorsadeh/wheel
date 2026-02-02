"""Integration tests for data providers.

These tests make real network calls and should be run sparingly.
Run with: pytest -m integration
"""

from datetime import date
from pathlib import Path

import pytest

from wheel_backtest.data import DataCache, PhilippdubachProvider, YFinanceProvider


@pytest.fixture
def integration_cache(tmp_path: Path) -> DataCache:
    """Create cache for integration tests."""
    return DataCache(tmp_path / "integration_cache")


@pytest.mark.integration
@pytest.mark.slow
class TestPhilippdubachIntegration:
    """Integration tests for PhilippdubachProvider."""

    def test_download_and_cache_spy(self, integration_cache: DataCache) -> None:
        """Test downloading SPY options data."""
        provider = PhilippdubachProvider(integration_cache)

        # Get options chain for a known date
        chain = provider.get_options_chain("SPY", date(2024, 1, 2))

        assert len(chain) > 0
        assert "strike" in chain.columns
        assert "delta" in chain.columns
        assert "expiration" in chain.columns

        # Verify cache was populated
        assert integration_cache.has("philippdubach", "SPY", "options")

    def test_date_range(self, integration_cache: DataCache) -> None:
        """Test getting date range."""
        provider = PhilippdubachProvider(integration_cache)

        start_date, end_date = provider.get_date_range("SPY")

        # Data should start from 2008
        assert start_date.year == 2008
        # Data should extend to at least 2024
        assert end_date.year >= 2024

    def test_get_expirations(self, integration_cache: DataCache) -> None:
        """Test getting available expirations."""
        provider = PhilippdubachProvider(integration_cache)

        expirations = provider.get_expirations("SPY", date(2024, 1, 2))

        assert len(expirations) > 0
        # Should have near-term expiration
        assert any(exp <= date(2024, 1, 12) for exp in expirations)

    def test_get_strikes(self, integration_cache: DataCache) -> None:
        """Test getting available strikes."""
        provider = PhilippdubachProvider(integration_cache)

        # Get first expiration
        expirations = provider.get_expirations("SPY", date(2024, 1, 2))
        strikes = provider.get_strikes("SPY", date(2024, 1, 2), expirations[0])

        assert len(strikes) > 0
        # Should have strikes around ATM (~472)
        assert any(470 <= s <= 475 for s in strikes)

    def test_validate_data(self, integration_cache: DataCache) -> None:
        """Test data validation."""
        provider = PhilippdubachProvider(integration_cache)

        results = provider.validate_data("SPY")

        assert results["ticker"] == "SPY"
        assert results["total_rows"] > 0
        assert len(results["issues"]) == 0  # No issues expected
        assert results["delta_range"][0] >= -1.0
        assert results["delta_range"][1] <= 1.0


@pytest.mark.integration
@pytest.mark.slow
class TestYFinanceIntegration:
    """Integration tests for YFinanceProvider."""

    def test_download_spy_prices(self, integration_cache: DataCache) -> None:
        """Test downloading SPY price data."""
        provider = YFinanceProvider(integration_cache)

        prices = provider.get_prices("SPY", date(2024, 1, 2), date(2024, 1, 5))

        assert len(prices) >= 3  # At least 3 trading days
        assert "close" in prices.columns
        assert "adjusted_close" in prices.columns
        assert "volume" in prices.columns

    def test_get_single_price(self, integration_cache: DataCache) -> None:
        """Test getting single day price."""
        provider = YFinanceProvider(integration_cache)

        # Jan 2, 2024 SPY close was ~$472.65
        price = provider.get_price("SPY", date(2024, 1, 2))

        assert 470 < price < 480  # Reasonable range

    def test_get_dividends(self, integration_cache: DataCache) -> None:
        """Test getting dividend data."""
        provider = YFinanceProvider(integration_cache)

        # SPY pays quarterly dividends
        divs = provider.get_dividends("SPY", date(2024, 1, 1), date(2024, 12, 31))

        # Should have at least 3 quarterly dividends
        assert len(divs) >= 3

    def test_cache_is_used_on_second_call(self, integration_cache: DataCache) -> None:
        """Test that second call uses cache."""
        provider = YFinanceProvider(integration_cache)

        # First call downloads
        provider.get_prices("SPY", date(2024, 1, 2), date(2024, 1, 5))
        assert integration_cache.has("yfinance", "SPY", "underlying")

        # Second call should use cache (no network)
        prices = provider.get_prices("SPY", date(2024, 1, 2), date(2024, 1, 5))
        assert len(prices) >= 3


@pytest.mark.integration
@pytest.mark.slow
class TestDataConsistency:
    """Test consistency between providers."""

    def test_options_underlying_date_alignment(
        self, integration_cache: DataCache
    ) -> None:
        """Test that options and underlying data align on dates."""
        options_provider = PhilippdubachProvider(integration_cache)
        underlying_provider = YFinanceProvider(integration_cache)

        trade_date = date(2024, 1, 2)

        # Get options chain
        chain = options_provider.get_options_chain("SPY", trade_date)
        assert len(chain) > 0

        # Get underlying price
        price = underlying_provider.get_price("SPY", trade_date)

        # ATM strikes should be near the underlying price
        atm_strikes = chain[
            (chain["strike"] >= price - 5) & (chain["strike"] <= price + 5)
        ]
        assert len(atm_strikes) > 0
