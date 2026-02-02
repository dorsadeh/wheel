"""Abstract base class for options data providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Protocol

import pandas as pd


@dataclass(frozen=True)
class OptionContract:
    """Represents a single option contract."""

    symbol: str
    expiration: date
    strike: float
    option_type: str  # 'call' or 'put'
    bid: float
    ask: float
    last: float | None
    volume: int | None
    open_interest: int | None
    implied_volatility: float | None
    delta: float | None
    gamma: float | None
    theta: float | None
    vega: float | None
    rho: float | None

    @property
    def mid_price(self) -> float:
        """Calculate mid-price from bid/ask."""
        return (self.bid + self.ask) / 2


@dataclass(frozen=True)
class UnderlyingPrice:
    """Represents underlying price data for a single day."""

    date: date
    open: float
    high: float
    low: float
    close: float
    adjusted_close: float
    volume: int
    dividend: float = 0.0


class OptionsDataProvider(ABC):
    """Abstract base class for options data providers.

    Providers must implement methods to fetch options chains and underlying prices.
    All providers should use the caching layer for efficiency.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging and cache keys."""
        pass

    @abstractmethod
    def get_options_chain(self, ticker: str, trade_date: date) -> pd.DataFrame:
        """Get full options chain for a ticker on a given date.

        Args:
            ticker: Stock symbol (e.g., 'SPY')
            trade_date: The trading date to fetch options for

        Returns:
            DataFrame with columns:
                - expiration: date
                - strike: float
                - option_type: str ('call' or 'put')
                - bid: float
                - ask: float
                - last: float (nullable)
                - volume: int (nullable)
                - open_interest: int (nullable)
                - implied_volatility: float (nullable)
                - delta: float (nullable)
                - gamma: float (nullable)
                - theta: float (nullable)
                - vega: float (nullable)
                - rho: float (nullable)
        """
        pass

    @abstractmethod
    def get_underlying_prices(
        self, ticker: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """Get underlying price history.

        Args:
            ticker: Stock symbol
            start_date: Start of date range
            end_date: End of date range

        Returns:
            DataFrame indexed by date with columns:
                - open, high, low, close, adjusted_close, volume, dividend
        """
        pass

    @abstractmethod
    def get_available_tickers(self) -> list[str]:
        """List all available tickers from this provider."""
        pass

    @abstractmethod
    def get_date_range(self, ticker: str) -> tuple[date, date]:
        """Get available date range for a ticker.

        Returns:
            Tuple of (earliest_date, latest_date)
        """
        pass

    def get_underlying_price(self, ticker: str, trade_date: date) -> float:
        """Get closing price for a specific date.

        Args:
            ticker: Stock symbol
            trade_date: The date to get price for

        Returns:
            Closing price (unadjusted)
        """
        df = self.get_underlying_prices(ticker, trade_date, trade_date)
        if df.empty:
            raise ValueError(f"No price data for {ticker} on {trade_date}")
        return float(df["close"].iloc[0])


class UnderlyingDataProvider(ABC):
    """Abstract base class for underlying price data providers.

    Separate from options data since some providers only offer one or the other.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging and cache keys."""
        pass

    @abstractmethod
    def get_prices(
        self, ticker: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """Get price history for underlying.

        Returns:
            DataFrame indexed by date with OHLCV + adjusted_close + dividend
        """
        pass

    def get_price(self, ticker: str, trade_date: date) -> float:
        """Get closing price for a specific date."""
        df = self.get_prices(ticker, trade_date, trade_date)
        if df.empty:
            raise ValueError(f"No price data for {ticker} on {trade_date}")
        return float(df["close"].iloc[0])
