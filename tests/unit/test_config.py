"""Tests for configuration management."""

from datetime import date
from pathlib import Path

import pytest

from wheel_backtest.config import BacktestConfig, load_config


class TestBacktestConfig:
    """Tests for BacktestConfig."""

    def test_default_values(self, temp_dir: Path) -> None:
        """Test that default values are set correctly."""
        config = BacktestConfig(
            cache_dir=temp_dir / "cache",
            output_dir=temp_dir / "output",
        )

        assert config.ticker == "SPY"
        assert config.start_date is None
        assert config.end_date is None
        assert config.initial_capital == 100_000.0
        assert config.dte_target == 30
        assert config.dte_min == 7
        assert config.delta_target == 0.20
        assert config.contract_multiplier == 100
        assert config.commission_per_contract == 0.0
        assert config.data_provider == "philippdubach"

    def test_ticker_normalization(self, temp_dir: Path) -> None:
        """Test that ticker is normalized to uppercase."""
        config = BacktestConfig(
            ticker="spy",
            cache_dir=temp_dir / "cache",
            output_dir=temp_dir / "output",
        )
        assert config.ticker == "SPY"

        config = BacktestConfig(
            ticker="  aapl  ",
            cache_dir=temp_dir / "cache",
            output_dir=temp_dir / "output",
        )
        assert config.ticker == "AAPL"

    def test_date_validation(self, temp_dir: Path) -> None:
        """Test date order validation."""
        # Valid: end after start
        config = BacktestConfig(
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
            cache_dir=temp_dir / "cache",
            output_dir=temp_dir / "output",
        )
        assert config.start_date == date(2020, 1, 1)
        assert config.end_date == date(2020, 12, 31)

        # Invalid: end before start
        with pytest.raises(ValueError, match="end_date must be after start_date"):
            BacktestConfig(
                start_date=date(2020, 12, 31),
                end_date=date(2020, 1, 1),
                cache_dir=temp_dir / "cache",
                output_dir=temp_dir / "output",
            )

    def test_capital_validation(self, temp_dir: Path) -> None:
        """Test that capital must be positive."""
        with pytest.raises(ValueError):
            BacktestConfig(
                initial_capital=0,
                cache_dir=temp_dir / "cache",
                output_dir=temp_dir / "output",
            )

        with pytest.raises(ValueError):
            BacktestConfig(
                initial_capital=-1000,
                cache_dir=temp_dir / "cache",
                output_dir=temp_dir / "output",
            )

    def test_delta_validation(self, temp_dir: Path) -> None:
        """Test that delta must be between 0 and 1."""
        with pytest.raises(ValueError):
            BacktestConfig(
                delta_target=0,
                cache_dir=temp_dir / "cache",
                output_dir=temp_dir / "output",
            )

        with pytest.raises(ValueError):
            BacktestConfig(
                delta_target=1,
                cache_dir=temp_dir / "cache",
                output_dir=temp_dir / "output",
            )

        # Valid delta
        config = BacktestConfig(
            delta_target=0.15,
            cache_dir=temp_dir / "cache",
            output_dir=temp_dir / "output",
        )
        assert config.delta_target == 0.15

    def test_separate_put_call_deltas(self, temp_dir: Path) -> None:
        """Test separate put and call delta configuration."""
        config = BacktestConfig(
            put_delta=0.25,
            call_delta=0.15,
            cache_dir=temp_dir / "cache",
            output_dir=temp_dir / "output",
        )
        assert config.put_delta == 0.25
        assert config.call_delta == 0.15

    def test_effective_delta_with_separate_values(self, temp_dir: Path) -> None:
        """Test effective delta properties when separate deltas are set."""
        config = BacktestConfig(
            delta_target=0.20,
            put_delta=0.30,
            call_delta=0.15,
            cache_dir=temp_dir / "cache",
            output_dir=temp_dir / "output",
        )
        assert config.effective_put_delta == 0.30
        assert config.effective_call_delta == 0.15

    def test_effective_delta_fallback_to_target(self, temp_dir: Path) -> None:
        """Test effective delta falls back to delta_target when not set."""
        config = BacktestConfig(
            delta_target=0.20,
            cache_dir=temp_dir / "cache",
            output_dir=temp_dir / "output",
        )
        assert config.effective_put_delta == 0.20
        assert config.effective_call_delta == 0.20

    def test_put_delta_validation(self, temp_dir: Path) -> None:
        """Test that put_delta must be between 0 and 1."""
        with pytest.raises(ValueError):
            BacktestConfig(
                put_delta=0,
                cache_dir=temp_dir / "cache",
                output_dir=temp_dir / "output",
            )

        with pytest.raises(ValueError):
            BacktestConfig(
                put_delta=1.5,
                cache_dir=temp_dir / "cache",
                output_dir=temp_dir / "output",
            )

    def test_call_delta_validation(self, temp_dir: Path) -> None:
        """Test that call_delta must be between 0 and 1."""
        with pytest.raises(ValueError):
            BacktestConfig(
                call_delta=0,
                cache_dir=temp_dir / "cache",
                output_dir=temp_dir / "output",
            )

        with pytest.raises(ValueError):
            BacktestConfig(
                call_delta=1.5,
                cache_dir=temp_dir / "cache",
                output_dir=temp_dir / "output",
            )

    def test_call_entry_protection_defaults(self, temp_dir: Path) -> None:
        """Test that call entry protection defaults to disabled."""
        config = BacktestConfig(
            cache_dir=temp_dir / "cache",
            output_dir=temp_dir / "output",
        )
        assert config.enable_call_entry_protection is False
        assert config.call_entry_protection_dollars == 0.0

    def test_call_entry_protection_can_be_enabled(self, temp_dir: Path) -> None:
        """Test that call entry protection can be enabled and configured."""
        config = BacktestConfig(
            enable_call_entry_protection=True,
            call_entry_protection_dollars=2.0,
            cache_dir=temp_dir / "cache",
            output_dir=temp_dir / "output",
        )
        assert config.enable_call_entry_protection is True
        assert config.call_entry_protection_dollars == 2.0

    def test_directory_creation(self, temp_dir: Path) -> None:
        """Test that directories are created if they don't exist."""
        cache_path = temp_dir / "new_cache"
        output_path = temp_dir / "new_output"

        assert not cache_path.exists()
        assert not output_path.exists()

        config = BacktestConfig(
            cache_dir=cache_path,
            output_dir=output_path,
        )

        assert cache_path.exists()
        assert output_path.exists()
        assert config.cache_dir == cache_path
        assert config.output_dir == output_path


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_with_defaults(self, temp_dir: Path) -> None:
        """Test loading config with default values."""
        config = load_config(
            cache_dir=temp_dir / "cache",
            output_dir=temp_dir / "output",
        )
        assert config.ticker == "SPY"
        assert config.initial_capital == 100_000.0

    def test_load_with_overrides(self, temp_dir: Path) -> None:
        """Test loading config with overrides."""
        config = load_config(
            ticker="AAPL",
            initial_capital=50_000,
            dte_target=45,
            cache_dir=temp_dir / "cache",
            output_dir=temp_dir / "output",
        )
        assert config.ticker == "AAPL"
        assert config.initial_capital == 50_000
        assert config.dte_target == 45
