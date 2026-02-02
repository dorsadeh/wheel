"""Disk caching layer for data providers."""

import hashlib
import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


class DataCache:
    """Disk-based cache for options and underlying data.

    Cache structure:
        cache_dir/
        ├── {provider}/
        │   └── {ticker}/
        │       ├── options.parquet      # Full options history
        │       └── underlying.parquet   # Full underlying history
        └── metadata.json                # Cache metadata and timestamps
    """

    def __init__(self, cache_dir: Path):
        """Initialize cache.

        Args:
            cache_dir: Directory to store cached data
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_path = self.cache_dir / "metadata.json"
        self._metadata: dict[str, Any] = self._load_metadata()

    def _load_metadata(self) -> dict[str, Any]:
        """Load cache metadata from disk."""
        if self.metadata_path.exists():
            try:
                return json.loads(self.metadata_path.read_text())
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load cache metadata: {e}")
        return {"version": 1, "entries": {}}

    def _save_metadata(self) -> None:
        """Save cache metadata to disk."""
        self.metadata_path.write_text(json.dumps(self._metadata, indent=2, default=str))

    def _get_cache_key(self, provider: str, ticker: str, data_type: str) -> str:
        """Generate deterministic cache key."""
        return f"{provider}/{ticker.lower()}/{data_type}"

    def _get_cache_path(self, provider: str, ticker: str, data_type: str) -> Path:
        """Get file path for cached data."""
        return self.cache_dir / provider / ticker.lower() / f"{data_type}.parquet"

    def has(self, provider: str, ticker: str, data_type: str) -> bool:
        """Check if data is cached.

        Args:
            provider: Provider name (e.g., 'philippdubach')
            ticker: Stock symbol
            data_type: Type of data ('options' or 'underlying')

        Returns:
            True if cached data exists
        """
        path = self._get_cache_path(provider, ticker, data_type)
        return path.exists()

    def get(self, provider: str, ticker: str, data_type: str) -> pd.DataFrame | None:
        """Retrieve cached data.

        Args:
            provider: Provider name
            ticker: Stock symbol
            data_type: Type of data

        Returns:
            Cached DataFrame or None if not found
        """
        path = self._get_cache_path(provider, ticker, data_type)
        if not path.exists():
            logger.debug(f"Cache miss: {provider}/{ticker}/{data_type}")
            return None

        logger.debug(f"Cache hit: {provider}/{ticker}/{data_type}")
        try:
            return pd.read_parquet(path)
        except Exception as e:
            logger.warning(f"Failed to read cache file {path}: {e}")
            return None

    def put(
        self,
        provider: str,
        ticker: str,
        data_type: str,
        data: pd.DataFrame,
    ) -> None:
        """Store data in cache.

        Args:
            provider: Provider name
            ticker: Stock symbol
            data_type: Type of data
            data: DataFrame to cache
        """
        path = self._get_cache_path(provider, ticker, data_type)
        path.parent.mkdir(parents=True, exist_ok=True)

        data.to_parquet(path, index=True)

        # Update metadata
        cache_key = self._get_cache_key(provider, ticker, data_type)
        self._metadata["entries"][cache_key] = {
            "path": str(path),
            "rows": len(data),
            "cached_at": datetime.now().isoformat(),
        }
        self._save_metadata()

        logger.info(f"Cached {len(data)} rows: {provider}/{ticker}/{data_type}")

    def invalidate(self, provider: str, ticker: str, data_type: str) -> bool:
        """Remove cached data.

        Args:
            provider: Provider name
            ticker: Stock symbol
            data_type: Type of data

        Returns:
            True if data was removed, False if it didn't exist
        """
        path = self._get_cache_path(provider, ticker, data_type)
        cache_key = self._get_cache_key(provider, ticker, data_type)

        if path.exists():
            path.unlink()
            self._metadata["entries"].pop(cache_key, None)
            self._save_metadata()
            logger.info(f"Invalidated cache: {provider}/{ticker}/{data_type}")
            return True
        return False

    def clear(self) -> None:
        """Clear all cached data."""
        import shutil

        for item in self.cache_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            elif item.name != "metadata.json":
                item.unlink()

        self._metadata = {"version": 1, "entries": {}}
        self._save_metadata()
        logger.info("Cleared all cache data")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with cache statistics
        """
        total_size = 0
        file_count = 0

        for path in self.cache_dir.rglob("*.parquet"):
            total_size += path.stat().st_size
            file_count += 1

        return {
            "entries": len(self._metadata.get("entries", {})),
            "files": file_count,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
        }
