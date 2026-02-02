"""Utility functions for Streamlit UI."""

import os
from pathlib import Path

from wheel_backtest.storage import BacktestHistory


def get_cache_dir() -> Path:
    """Get cache directory from environment or use default."""
    cache_dir = os.environ.get("WHEEL_CACHE_DIR", "./cache")
    return Path(cache_dir)


def get_output_dir() -> Path:
    """Get output directory from environment or use default."""
    output_dir = os.environ.get("WHEEL_OUTPUT_DIR", "./output")
    return Path(output_dir)


def get_history() -> BacktestHistory:
    """Get BacktestHistory instance."""
    cache_dir = get_cache_dir()
    db_path = cache_dir / "backtest_history.db"
    return BacktestHistory(db_path)
