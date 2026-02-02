"""Pytest fixtures and configuration."""

import tempfile
from datetime import date
from pathlib import Path

import pytest

from wheel_backtest.config import BacktestConfig


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config(temp_dir: Path) -> BacktestConfig:
    """Create a sample configuration for testing."""
    return BacktestConfig(
        ticker="SPY",
        start_date=date(2020, 1, 1),
        end_date=date(2020, 12, 31),
        initial_capital=100_000,
        dte_target=30,
        delta_target=0.20,
        cache_dir=temp_dir / "cache",
        output_dir=temp_dir / "output",
    )


@pytest.fixture
def minimal_config(temp_dir: Path) -> BacktestConfig:
    """Create a minimal configuration with defaults."""
    return BacktestConfig(
        cache_dir=temp_dir / "cache",
        output_dir=temp_dir / "output",
    )
