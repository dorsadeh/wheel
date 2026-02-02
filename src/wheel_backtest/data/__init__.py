"""Data providers and caching layer.

This module provides access to historical options and underlying price data.

Primary data sources:
- PhilippdubachProvider: Free options data (2008-2025, 104 tickers, full Greeks)
- YFinanceProvider: Underlying prices (free, all tickers)

Usage:
    from wheel_backtest.data import DataCache, PhilippdubachProvider, YFinanceProvider

    cache = DataCache(Path("./cache"))
    options_provider = PhilippdubachProvider(cache)
    underlying_provider = YFinanceProvider(cache)

    # Get options chain for a specific date
    chain = options_provider.get_options_chain("SPY", date(2024, 1, 2))

    # Get underlying prices
    prices = underlying_provider.get_prices("SPY", date(2024, 1, 1), date(2024, 12, 31))
"""

from wheel_backtest.data.cache import DataCache
from wheel_backtest.data.philippdubach import PhilippdubachProvider
from wheel_backtest.data.provider import (
    OptionContract,
    OptionsDataProvider,
    UnderlyingDataProvider,
    UnderlyingPrice,
)
from wheel_backtest.data.yfinance_provider import YFinanceProvider

__all__ = [
    "DataCache",
    "OptionContract",
    "OptionsDataProvider",
    "PhilippdubachProvider",
    "UnderlyingDataProvider",
    "UnderlyingPrice",
    "YFinanceProvider",
]
