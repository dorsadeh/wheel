"""Yahoo Finance data provider for underlying prices.

Uses yfinance library to fetch historical price data including
OHLCV, adjusted close, and dividends.
"""

import logging
from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from wheel_backtest.data.cache import DataCache
from wheel_backtest.data.provider import UnderlyingDataProvider

logger = logging.getLogger(__name__)


class YFinanceProvider(UnderlyingDataProvider):
    """Underlying price provider using Yahoo Finance.

    Provides:
    - OHLCV data
    - Adjusted close prices (dividend/split adjusted)
    - Dividend history

    Data is cached locally to minimize API calls.
    """

    def __init__(self, cache: DataCache):
        """Initialize provider.

        Args:
            cache: DataCache instance for storing downloaded data
        """
        self._cache = cache
        self._data: dict[str, pd.DataFrame] = {}  # In-memory cache

    @property
    def name(self) -> str:
        return "yfinance"

    def _fetch_from_yfinance(
        self, ticker: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """Fetch data from Yahoo Finance.

        Args:
            ticker: Stock symbol
            start_date: Start of date range
            end_date: End of date range

        Returns:
            DataFrame with OHLCV + adjusted close + dividends
        """
        logger.info(f"Fetching {ticker} from Yahoo Finance: {start_date} to {end_date}")

        # yfinance end_date is exclusive, add 1 day
        end_plus = end_date + timedelta(days=1)

        stock = yf.Ticker(ticker)

        # Fetch with auto_adjust=False to get both raw and adjusted prices
        hist = stock.history(
            start=start_date.isoformat(),
            end=end_plus.isoformat(),
            auto_adjust=False,
        )

        if hist.empty:
            logger.warning(f"No data returned from yfinance for {ticker}")
            return pd.DataFrame()

        # Rename columns to our standard format
        df = pd.DataFrame({
            "open": hist["Open"],
            "high": hist["High"],
            "low": hist["Low"],
            "close": hist["Close"],
            "adjusted_close": hist["Adj Close"],
            "volume": hist["Volume"].astype(int),
            "dividend": hist["Dividends"],
        })

        # Convert timezone-aware index to date
        df.index = pd.to_datetime(df.index).tz_localize(None)
        df.index.name = "date"

        return df

    def _ensure_data_loaded(
        self, ticker: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """Ensure price data is loaded, fetching if needed.

        Args:
            ticker: Stock symbol
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame with price data
        """
        ticker = ticker.upper()

        # Check disk cache first
        cached = self._cache.get(self.name, ticker, "underlying")

        if cached is not None and not cached.empty:
            # Check if cached data covers requested range
            cached_start = cached.index.min().date()
            cached_end = cached.index.max().date()

            if cached_start <= start_date and cached_end >= end_date:
                logger.debug(f"Using cached data for {ticker}")
                return cached

            # Need to extend cache - fetch full range
            fetch_start = min(start_date, cached_start)
            fetch_end = max(end_date, cached_end)
        else:
            fetch_start = start_date
            fetch_end = end_date

        # Fetch from yfinance
        df = self._fetch_from_yfinance(ticker, fetch_start, fetch_end)

        if not df.empty:
            # Cache the data
            self._cache.put(self.name, ticker, "underlying", df)

        return df

    def get_prices(
        self, ticker: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """Get price history for underlying.

        Args:
            ticker: Stock symbol
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame indexed by date with columns:
                open, high, low, close, adjusted_close, volume, dividend
        """
        df = self._ensure_data_loaded(ticker, start_date, end_date)

        if df.empty:
            return df

        # Filter to requested date range
        mask = (df.index.date >= start_date) & (df.index.date <= end_date)
        return df[mask].copy()

    def get_price(self, ticker: str, trade_date: date) -> float:
        """Get closing price for a specific date.

        Args:
            ticker: Stock symbol
            trade_date: Date to get price for

        Returns:
            Closing price (unadjusted)
        """
        df = self.get_prices(ticker, trade_date, trade_date)
        if df.empty:
            raise ValueError(f"No price data for {ticker} on {trade_date}")
        return float(df["close"].iloc[0])

    def get_adjusted_price(self, ticker: str, trade_date: date) -> float:
        """Get adjusted closing price for a specific date.

        Args:
            ticker: Stock symbol
            trade_date: Date to get price for

        Returns:
            Adjusted closing price (dividend/split adjusted)
        """
        df = self.get_prices(ticker, trade_date, trade_date)
        if df.empty:
            raise ValueError(f"No price data for {ticker} on {trade_date}")
        return float(df["adjusted_close"].iloc[0])

    def get_dividends(
        self, ticker: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """Get dividend payments in date range.

        Args:
            ticker: Stock symbol
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame with dividend dates and amounts
        """
        df = self.get_prices(ticker, start_date, end_date)

        if df.empty:
            return pd.DataFrame(columns=["date", "dividend"])

        # Filter to non-zero dividends
        divs = df[df["dividend"] > 0][["dividend"]].copy()
        divs = divs.reset_index()

        return divs

    def get_trading_days(
        self, ticker: str, start_date: date, end_date: date
    ) -> list[date]:
        """Get list of trading days in date range.

        Args:
            ticker: Stock symbol
            start_date: Start date
            end_date: End date

        Returns:
            List of trading dates
        """
        df = self.get_prices(ticker, start_date, end_date)
        return [d.date() for d in df.index]
