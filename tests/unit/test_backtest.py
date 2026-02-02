"""Tests for backtest orchestrator."""

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from wheel_backtest.config import BacktestConfig
from wheel_backtest.engine.backtest import Transaction, WheelBacktest


class TestWheelBacktest:
    """Tests for WheelBacktest orchestrator."""

    @pytest.fixture
    def config(self, tmp_path: Path) -> BacktestConfig:
        """Create a test configuration."""
        return BacktestConfig(
            ticker="SPY",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            initial_capital=100_000.0,
            dte_target=30,
            dte_min=7,
            delta_target=0.20,
            commission_per_contract=1.0,
            cache_dir=tmp_path / "cache",
            output_dir=tmp_path / "output",
        )

    @pytest.fixture
    def mock_price_data(self) -> pd.DataFrame:
        """Create mock price data."""
        dates = pd.date_range("2024-01-01", "2024-01-05", freq="D")
        return pd.DataFrame(
            {
                "Open": [470.0, 471.0, 472.0, 473.0, 474.0],
                "High": [472.0, 473.0, 474.0, 475.0, 476.0],
                "Low": [468.0, 469.0, 470.0, 471.0, 472.0],
                "Close": [471.0, 472.0, 473.0, 474.0, 475.0],
                "Adj Close": [471.0, 472.0, 473.0, 474.0, 475.0],
                "Volume": [1000000] * 5,
            },
            index=dates,
        )

    @pytest.fixture
    def mock_options_chain(self) -> pd.DataFrame:
        """Create mock options chain."""
        return pd.DataFrame(
            {
                "expiration": [pd.Timestamp("2024-02-01")] * 2,
                "strike": [450.0, 490.0],
                "option_type": ["put", "call"],
                "bid": [4.50, 3.00],
                "ask": [5.00, 3.50],
                "delta": [-0.25, 0.25],
            }
        )

    def test_initialization(self, config: BacktestConfig) -> None:
        """Test backtest initialization."""
        with patch("wheel_backtest.engine.backtest.DataCache"), \
             patch("wheel_backtest.engine.backtest.PhilippdubachProvider"), \
             patch("wheel_backtest.engine.backtest.YFinanceProvider"):
            backtest = WheelBacktest(config)

            assert backtest.config == config
            assert backtest.portfolio.cash == config.initial_capital
            assert backtest.selector.dte_target == config.dte_target
            assert len(backtest.transactions) == 0

    def test_get_price_data(
        self, config: BacktestConfig, mock_price_data: pd.DataFrame
    ) -> None:
        """Test getting price data."""
        with patch("wheel_backtest.engine.backtest.DataCache"), \
             patch("wheel_backtest.engine.backtest.PhilippdubachProvider"), \
             patch("wheel_backtest.engine.backtest.YFinanceProvider") as mock_yf:
            mock_provider = Mock()
            mock_provider.get_underlying_prices.return_value = mock_price_data
            mock_yf.return_value = mock_provider

            backtest = WheelBacktest(config)
            prices = backtest._get_price_data()

            assert not prices.empty
            assert len(prices) == 5
            mock_provider.get_underlying_prices.assert_called_once()

    def test_get_options_chain_success(
        self, config: BacktestConfig, mock_options_chain: pd.DataFrame
    ) -> None:
        """Test getting options chain successfully."""
        with patch("wheel_backtest.engine.backtest.DataCache"), \
             patch("wheel_backtest.engine.backtest.PhilippdubachProvider") as mock_pd, \
             patch("wheel_backtest.engine.backtest.YFinanceProvider"):
            mock_provider = Mock()
            mock_provider.get_options_chain.return_value = mock_options_chain
            mock_pd.return_value = mock_provider

            backtest = WheelBacktest(config)
            chain = backtest._get_options_chain(date(2024, 1, 2))

            assert not chain.empty
            assert len(chain) == 2

    def test_get_options_chain_error(self, config: BacktestConfig) -> None:
        """Test getting options chain with error."""
        with patch("wheel_backtest.engine.backtest.DataCache"), \
             patch("wheel_backtest.engine.backtest.PhilippdubachProvider") as mock_pd, \
             patch("wheel_backtest.engine.backtest.YFinanceProvider"):
            mock_provider = Mock()
            mock_provider.get_options_chain.side_effect = Exception("No data")
            mock_pd.return_value = mock_provider

            backtest = WheelBacktest(config)
            chain = backtest._get_options_chain(date(2024, 1, 2))

            # Should return empty DataFrame on error
            assert chain.empty

    def test_get_transactions_df_empty(self, config: BacktestConfig) -> None:
        """Test getting transactions DataFrame when empty."""
        with patch("wheel_backtest.engine.backtest.DataCache"), \
             patch("wheel_backtest.engine.backtest.PhilippdubachProvider"), \
             patch("wheel_backtest.engine.backtest.YFinanceProvider"):
            backtest = WheelBacktest(config)
            df = backtest.get_transactions_df()

            assert df.empty

    def test_get_transactions_df_with_data(self, config: BacktestConfig) -> None:
        """Test getting transactions DataFrame with data."""
        with patch("wheel_backtest.engine.backtest.DataCache"), \
             patch("wheel_backtest.engine.backtest.PhilippdubachProvider"), \
             patch("wheel_backtest.engine.backtest.YFinanceProvider"):
            backtest = WheelBacktest(config)

            # Add a mock transaction
            transaction = Transaction(
                date=date(2024, 1, 2),
                action="sell_put",
                instrument="PUT $450",
                quantity=1,
                price=5.0,
                value=500.0,
                commission=1.0,
                cash_after=100_499.0,
                shares_after=0,
                equity_after=100_499.0,
            )
            backtest.transactions.append(transaction)

            df = backtest.get_transactions_df()

            assert not df.empty
            assert len(df) == 1
            assert df.iloc[0]["action"] == "sell_put"


class TestTransaction:
    """Tests for Transaction dataclass."""

    def test_transaction_creation(self) -> None:
        """Test creating a transaction."""
        transaction = Transaction(
            date=date(2024, 1, 2),
            action="sell_put",
            instrument="PUT $450 2024-01-19",
            quantity=1,
            price=5.0,
            value=500.0,
            commission=1.0,
            cash_after=100_499.0,
            shares_after=0,
            equity_after=100_499.0,
            notes="Test transaction",
        )

        assert transaction.date == date(2024, 1, 2)
        assert transaction.action == "sell_put"
        assert transaction.instrument == "PUT $450 2024-01-19"
        assert transaction.quantity == 1
        assert transaction.price == 5.0
        assert transaction.value == 500.0
        assert transaction.commission == 1.0
        assert transaction.notes == "Test transaction"
