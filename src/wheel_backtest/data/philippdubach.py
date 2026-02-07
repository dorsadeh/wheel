"""Philippdubach options data provider.

Free historical options data from https://github.com/philippdubach/options-data
Coverage: 104 tickers, 2008-2025, full Greeks included.
"""

import io
import logging
import urllib.request
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd
import pyarrow.parquet as pq

from wheel_backtest.data.cache import DataCache
from wheel_backtest.data.provider import OptionsDataProvider

logger = logging.getLogger(__name__)

BASE_URL = "https://static.philippdubach.com/data/options"

# Data coverage dates (update when data source is refreshed)
DATA_START_DATE = date(2008, 1, 2)
DATA_END_DATE = date(2025, 12, 16)  # Last available data date

# All available tickers in the philippdubach dataset
AVAILABLE_TICKERS = [
    "AAPL", "ABBV", "ABT", "ACN", "ADBE", "AIG", "AMD", "AMGN", "AMT", "AMZN",
    "AVGO", "AXP", "BA", "BAC", "BK", "BKNG", "BLK", "BMY", "BRK.B", "C",
    "CAT", "CL", "CMCSA", "COF", "COP", "COST", "CRM", "CSCO", "CVS", "CVX",
    "DE", "DHR", "DIS", "DUK", "EMR", "FDX", "GD", "GE", "GILD", "GM",
    "GOOG", "GOOGL", "GS", "HD", "HON", "IBM", "INTU", "ISRG", "IWM", "JNJ",
    "JPM", "KO", "LIN", "LLY", "LMT", "LOW", "MA", "MCD", "MDLZ", "MDT",
    "MET", "META", "MMM", "MO", "MRK", "MS", "MSFT", "NEE", "NFLX", "NKE",
    "NOW", "NVDA", "ORCL", "PEP", "PFE", "PG", "PLTR", "PM", "PYPL", "QCOM",
    "QQQ", "RTX", "SBUX", "SCHW", "SO", "SPG", "SPY", "T", "TGT", "TMO",
    "TMUS", "TSLA", "TXN", "UBER", "UNH", "UNP", "UPS", "USB", "V", "VIX",
    "VZ", "WFC", "WMT", "XOM",
]

# Ticker categorization by asset class/sector
TICKER_CATEGORIES = {
    "ETFs": ["SPY", "QQQ", "IWM", "VIX"],
    "Technology": [
        "AAPL", "ADBE", "AMD", "AMZN", "AVGO", "CRM", "CSCO", "GOOG", "GOOGL",
        "IBM", "INTU", "META", "MSFT", "NFLX", "NOW", "NVDA", "ORCL", "PLTR",
        "PYPL", "QCOM", "TSLA", "TXN", "UBER",
    ],
    "Financials": [
        "AIG", "AXP", "BAC", "BK", "BLK", "BRK.B", "C", "COF", "GS", "JPM",
        "MA", "MET", "MS", "SCHW", "USB", "V", "WFC",
    ],
    "Healthcare": [
        "ABBV", "ABT", "AMGN", "BMY", "CVS", "GILD", "ISRG", "JNJ", "LLY",
        "MDT", "MRK", "PFE", "TMO", "UNH",
    ],
    "Consumer": [
        "CL", "COST", "DIS", "HD", "KO", "LOW", "MCD", "MDLZ", "MO", "NKE",
        "PEP", "PG", "PM", "SBUX", "TGT", "WMT",
    ],
    "Industrials": [
        "BA", "CAT", "DE", "DHR", "EMR", "FDX", "GD", "GE", "HON", "LMT",
        "MMM", "RTX", "UNP", "UPS",
    ],
    "Energy": ["COP", "CVX", "XOM"],
    "Communication": ["CMCSA", "T", "TMUS", "VZ"],
    "Utilities": ["DUK", "NEE", "SO"],
    "Real Estate": ["AMT", "SPG"],
    "Materials": ["LIN"],
    "Business Services": ["ACN"],
    "Automotive": ["GM"],
    "Hospitality": ["BKNG"],
}

# Reverse mapping: ticker -> category
TICKER_TO_CATEGORY = {}
for category, tickers in TICKER_CATEGORIES.items():
    for ticker in tickers:
        TICKER_TO_CATEGORY[ticker] = category

# Standard column mapping from philippdubach format
COLUMN_MAPPING = {
    "type": "option_type",
    "expiration": "expiration",
    "strike": "strike",
    "bid": "bid",
    "ask": "ask",
    "last": "last",
    "volume": "volume",
    "open_interest": "open_interest",
    "implied_volatility": "implied_volatility",
    "delta": "delta",
    "gamma": "gamma",
    "theta": "theta",
    "vega": "vega",
    "rho": "rho",
    "date": "trade_date",
}


class PhilippdubachProvider(OptionsDataProvider):
    """Options data provider using philippdubach/options-data.

    This provider downloads parquet files from the static hosting and caches
    them locally for fast repeated access.
    """

    def __init__(self, cache: DataCache):
        """Initialize provider.

        Args:
            cache: DataCache instance for storing downloaded data
        """
        self._cache = cache
        self._data: dict[str, pd.DataFrame] = {}  # In-memory cache for session

    @property
    def name(self) -> str:
        return "philippdubach"

    def _download_parquet(self, url: str) -> pd.DataFrame:
        """Download parquet file from URL.

        Args:
            url: URL to download from

        Returns:
            DataFrame from parquet file
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        request = urllib.request.Request(url, headers=headers)

        logger.info(f"Downloading: {url}")
        with urllib.request.urlopen(request, timeout=300) as response:
            data = response.read()

        return pd.read_parquet(io.BytesIO(data))

    def _ensure_data_loaded(self, ticker: str) -> pd.DataFrame:
        """Ensure options data is loaded for ticker.

        Checks cache first, downloads if needed.

        Args:
            ticker: Stock symbol

        Returns:
            DataFrame with all options data for ticker
        """
        ticker = ticker.upper()

        # Check in-memory cache first
        if ticker in self._data:
            return self._data[ticker]

        # Check disk cache
        cached = self._cache.get(self.name, ticker, "options")
        if cached is not None:
            self._data[ticker] = cached
            return cached

        # Download from source
        if ticker not in AVAILABLE_TICKERS:
            raise ValueError(
                f"Ticker {ticker} not available. "
                f"Available: {', '.join(AVAILABLE_TICKERS[:10])}..."
            )

        url = f"{BASE_URL}/{ticker.lower()}/options.parquet"
        df = self._download_parquet(url)

        # Normalize column names
        df = df.rename(columns=COLUMN_MAPPING)

        # Ensure date columns are proper datetime
        if "trade_date" in df.columns:
            df["trade_date"] = pd.to_datetime(df["trade_date"])
        if "expiration" in df.columns:
            df["expiration"] = pd.to_datetime(df["expiration"])

        # Normalize option_type to lowercase
        if "option_type" in df.columns:
            df["option_type"] = df["option_type"].str.lower()

        # Cache to disk
        self._cache.put(self.name, ticker, "options", df)

        # Store in memory
        self._data[ticker] = df

        return df

    def get_filtered_options(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """Get options data filtered to a date range using PyArrow predicate pushdown.

        This is much faster than loading all data and filtering in pandas,
        especially for large datasets.

        Args:
            ticker: Stock symbol
            start_date: Start date for filter
            end_date: End date for filter

        Returns:
            DataFrame with options data in the date range
        """
        ticker = ticker.upper()

        # Create cache suffix for this date range
        cache_suffix = f"{start_date}_{end_date}"

        # Check cache first
        cached = self._cache.get(self.name, ticker, "options_filtered", suffix=cache_suffix)
        if cached is not None:
            logger.info(f"Using cached filtered data: {ticker} {start_date} to {end_date}")
            return cached

        # Check if we have the full data file cached
        cache_path = self._cache._get_cache_path(self.name, ticker, "options")

        if cache_path.exists():
            # Use PyArrow to filter while reading
            logger.info(f"Filtering cached data with PyArrow: {ticker} {start_date} to {end_date}")

            # Read parquet with PyArrow filters
            table = pq.read_table(
                cache_path,
                filters=[
                    ("trade_date", ">=", pd.Timestamp(start_date)),
                    ("trade_date", "<=", pd.Timestamp(end_date)),
                ],
            )
            df = table.to_pandas()

            # Normalize column names (already done in cache, but be safe)
            if "date" in df.columns:
                df = df.rename(columns=COLUMN_MAPPING)

            # Ensure datetime types
            if "trade_date" in df.columns:
                df["trade_date"] = pd.to_datetime(df["trade_date"])
            if "expiration" in df.columns:
                df["expiration"] = pd.to_datetime(df["expiration"])

            # Normalize option_type
            if "option_type" in df.columns:
                df["option_type"] = df["option_type"].str.lower()
        else:
            # Download and filter in one go
            logger.info(f"Downloading and filtering: {ticker} {start_date} to {end_date}")

            # Download full data first (will be cached)
            full_df = self._ensure_data_loaded(ticker)

            # Filter to date range
            start_ts = pd.Timestamp(start_date).normalize()
            end_ts = pd.Timestamp(end_date).normalize()
            mask = (full_df["trade_date"].dt.normalize() >= start_ts) & (full_df["trade_date"].dt.normalize() <= end_ts)
            df = full_df[mask].copy()

        # Cache the filtered result
        self._cache.put(self.name, ticker, "options_filtered", df, suffix=cache_suffix)
        logger.info(f"Cached filtered data: {len(df):,} rows for {ticker} {start_date} to {end_date}")

        return df

    def get_options_chain(self, ticker: str, trade_date: date) -> pd.DataFrame:
        """Get options chain for a specific trading date.

        Args:
            ticker: Stock symbol
            trade_date: Date to get options for

        Returns:
            DataFrame with options chain for that date
        """
        df = self._ensure_data_loaded(ticker)

        # Filter to specific date using pandas Timestamp comparison (much faster than .dt.date)
        trade_date_ts = pd.Timestamp(trade_date).normalize()
        mask = df["trade_date"].dt.normalize() == trade_date_ts

        chain = df[mask].copy()

        if chain.empty:
            logger.warning(f"No options data for {ticker} on {trade_date}")

        return chain

    def get_underlying_prices(
        self, ticker: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """Get underlying prices - NOT AVAILABLE from philippdubach.

        The underlying.parquet files are empty in this dataset.
        Use YFinanceProvider for underlying prices instead.

        Raises:
            NotImplementedError: Always, use YFinanceProvider instead
        """
        raise NotImplementedError(
            "Philippdubach underlying data is empty. Use YFinanceProvider instead."
        )

    def get_available_tickers(self) -> list[str]:
        """Get list of available tickers."""
        return AVAILABLE_TICKERS.copy()

    def get_date_range(self, ticker: str) -> tuple[date, date]:
        """Get available date range for a ticker."""
        df = self._ensure_data_loaded(ticker)

        min_date = df["trade_date"].min().date()
        max_date = df["trade_date"].max().date()

        return (min_date, max_date)

    def get_expirations(self, ticker: str, trade_date: date) -> list[date]:
        """Get available expiration dates for a trading date.

        Args:
            ticker: Stock symbol
            trade_date: Trading date

        Returns:
            List of available expiration dates, sorted ascending
        """
        chain = self.get_options_chain(ticker, trade_date)
        if chain.empty:
            return []

        expirations = chain["expiration"].dt.date.unique()
        return sorted(expirations)

    def get_strikes(
        self, ticker: str, trade_date: date, expiration: date
    ) -> list[float]:
        """Get available strikes for a specific expiration.

        Args:
            ticker: Stock symbol
            trade_date: Trading date
            expiration: Expiration date

        Returns:
            List of available strikes, sorted ascending
        """
        chain = self.get_options_chain(ticker, trade_date)
        if chain.empty:
            return []

        exp_ts = pd.Timestamp(expiration)
        mask = chain["expiration"] == exp_ts
        strikes = chain[mask]["strike"].unique()

        return sorted(strikes)

    def validate_data(self, ticker: str) -> dict[str, any]:
        """Validate data quality for a ticker.

        Returns:
            Dict with validation results
        """
        df = self._ensure_data_loaded(ticker)

        results = {
            "ticker": ticker,
            "total_rows": len(df),
            "date_range": self.get_date_range(ticker),
            "null_counts": {},
            "delta_range": None,
            "issues": [],
        }

        # Check null counts
        critical_cols = ["strike", "expiration", "bid", "ask"]
        for col in critical_cols:
            if col in df.columns:
                null_count = df[col].isna().sum()
                results["null_counts"][col] = null_count
                if null_count > 0:
                    results["issues"].append(f"{col} has {null_count} nulls")

        # Check delta range
        if "delta" in df.columns:
            delta_min = df["delta"].min()
            delta_max = df["delta"].max()
            results["delta_range"] = (delta_min, delta_max)

            if delta_min < -1.01 or delta_max > 1.01:
                results["issues"].append(
                    f"Delta outside valid range: [{delta_min}, {delta_max}]"
                )

        return results
