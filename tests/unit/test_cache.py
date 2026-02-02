"""Tests for the data caching layer."""

from pathlib import Path

import pandas as pd
import pytest

from wheel_backtest.data.cache import DataCache


class TestDataCache:
    """Tests for DataCache."""

    def test_cache_initialization(self, temp_dir: Path) -> None:
        """Test cache initializes correctly."""
        cache_dir = temp_dir / "cache"
        cache = DataCache(cache_dir)

        assert cache.cache_dir.exists()
        # Metadata file is created lazily on first put()
        assert cache.metadata_path.parent.exists()

    def test_cache_put_and_get(self, temp_dir: Path) -> None:
        """Test storing and retrieving data."""
        cache = DataCache(temp_dir / "cache")

        # Create sample data
        df = pd.DataFrame({
            "strike": [100, 105, 110],
            "delta": [0.5, 0.4, 0.3],
        })

        # Store data
        cache.put("test_provider", "SPY", "options", df)

        # Retrieve data
        result = cache.get("test_provider", "SPY", "options")

        assert result is not None
        assert len(result) == 3
        assert list(result.columns) == ["strike", "delta"]

    def test_cache_has(self, temp_dir: Path) -> None:
        """Test checking if data exists."""
        cache = DataCache(temp_dir / "cache")

        assert not cache.has("test", "SPY", "options")

        df = pd.DataFrame({"x": [1, 2, 3]})
        cache.put("test", "SPY", "options", df)

        assert cache.has("test", "SPY", "options")
        assert not cache.has("test", "SPY", "underlying")

    def test_cache_miss_returns_none(self, temp_dir: Path) -> None:
        """Test that cache miss returns None."""
        cache = DataCache(temp_dir / "cache")

        result = cache.get("nonexistent", "SPY", "options")
        assert result is None

    def test_cache_invalidate(self, temp_dir: Path) -> None:
        """Test invalidating cached data."""
        cache = DataCache(temp_dir / "cache")

        df = pd.DataFrame({"x": [1, 2, 3]})
        cache.put("test", "SPY", "options", df)

        assert cache.has("test", "SPY", "options")

        # Invalidate
        result = cache.invalidate("test", "SPY", "options")
        assert result is True
        assert not cache.has("test", "SPY", "options")

        # Invalidate non-existent
        result = cache.invalidate("test", "SPY", "options")
        assert result is False

    def test_cache_clear(self, temp_dir: Path) -> None:
        """Test clearing all cached data."""
        cache = DataCache(temp_dir / "cache")

        # Add multiple items
        df = pd.DataFrame({"x": [1, 2, 3]})
        cache.put("provider1", "SPY", "options", df)
        cache.put("provider1", "AAPL", "options", df)
        cache.put("provider2", "SPY", "underlying", df)

        assert cache.has("provider1", "SPY", "options")
        assert cache.has("provider1", "AAPL", "options")
        assert cache.has("provider2", "SPY", "underlying")

        # Clear all
        cache.clear()

        assert not cache.has("provider1", "SPY", "options")
        assert not cache.has("provider1", "AAPL", "options")
        assert not cache.has("provider2", "SPY", "underlying")

    def test_cache_stats(self, temp_dir: Path) -> None:
        """Test getting cache statistics."""
        cache = DataCache(temp_dir / "cache")

        stats = cache.get_stats()
        assert stats["entries"] == 0
        assert stats["files"] == 0

        # Add data
        df = pd.DataFrame({"x": list(range(1000))})
        cache.put("test", "SPY", "options", df)

        stats = cache.get_stats()
        assert stats["entries"] == 1
        assert stats["files"] == 1
        assert stats["total_size_mb"] > 0

    def test_cache_preserves_datatypes(self, temp_dir: Path) -> None:
        """Test that data types are preserved through cache."""
        cache = DataCache(temp_dir / "cache")

        df = pd.DataFrame({
            "int_col": [1, 2, 3],
            "float_col": [1.5, 2.5, 3.5],
            "str_col": ["a", "b", "c"],
            "date_col": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
        })

        cache.put("test", "SPY", "data", df)
        result = cache.get("test", "SPY", "data")

        assert result["int_col"].dtype == df["int_col"].dtype
        assert result["float_col"].dtype == df["float_col"].dtype
        assert result["str_col"].dtype == df["str_col"].dtype
        # Parquet preserves datetime64[ns]
        assert pd.api.types.is_datetime64_any_dtype(result["date_col"])
