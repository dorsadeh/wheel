"""Tests for backtest history storage."""

import json
from datetime import date, datetime
from pathlib import Path

import pytest

from wheel_backtest.analytics.metrics import PerformanceMetrics
from wheel_backtest.config import BacktestConfig
from wheel_backtest.storage import BacktestHistory, BacktestRecord


class TestBacktestHistory:
    """Tests for BacktestHistory storage."""

    @pytest.fixture
    def temp_db(self, tmp_path: Path) -> Path:
        """Create temporary database path."""
        return tmp_path / "test_history.db"

    @pytest.fixture
    def history(self, temp_db: Path) -> BacktestHistory:
        """Create BacktestHistory instance."""
        return BacktestHistory(temp_db)

    @pytest.fixture
    def sample_config(self) -> BacktestConfig:
        """Create sample backtest configuration."""
        return BacktestConfig(
            ticker="SPY",
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            initial_capital=100_000,
            dte_target=30,
            dte_min=7,
            delta_target=0.20,
            commission_per_contract=0.50,
            data_provider="philippdubach",
            cache_dir=Path("./cache"),
            output_dir=Path("./output"),
        )

    @pytest.fixture
    def sample_metrics(self) -> PerformanceMetrics:
        """Create sample performance metrics."""
        return PerformanceMetrics(
            total_return=25_100.0,
            total_return_pct=25.1,
            cagr=25.1,
            sharpe_ratio=1.85,
            sortino_ratio=2.45,
            max_drawdown=-8.5,
            max_drawdown_duration=45,
            volatility=15.2,
            win_rate=65.5,
            profit_factor=2.15,
            calmar_ratio=2.95,
        )

    def test_database_initialization(self, temp_db: Path, history: BacktestHistory) -> None:
        """Test database is created with proper schema."""
        assert temp_db.exists()
        assert history.db_path == temp_db

    def test_save_backtest(
        self,
        history: BacktestHistory,
        sample_config: BacktestConfig,
        sample_metrics: PerformanceMetrics,
    ) -> None:
        """Test saving a backtest record."""
        record_id = history.save_backtest(
            config=sample_config,
            metrics=sample_metrics,
            start_date="2023-01-01",
            end_date="2023-12-31",
            final_equity=125_100.0,
            total_trades=50,
        )

        assert record_id > 0

    def test_get_backtest(
        self,
        history: BacktestHistory,
        sample_config: BacktestConfig,
        sample_metrics: PerformanceMetrics,
    ) -> None:
        """Test retrieving a backtest record."""
        record_id = history.save_backtest(
            config=sample_config,
            metrics=sample_metrics,
            start_date="2023-01-01",
            end_date="2023-12-31",
            final_equity=125_100.0,
            total_trades=50,
        )

        record = history.get_backtest(record_id)

        assert record is not None
        assert record.id == record_id
        assert record.ticker == "SPY"
        assert record.start_date == "2023-01-01"
        assert record.end_date == "2023-12-31"
        assert record.initial_capital == 100_000
        assert record.final_equity == 125_100.0
        assert record.total_return == 25_100.0
        assert record.total_return_pct == 25.1
        assert record.cagr == 25.1
        assert record.sharpe_ratio == 1.85
        assert record.sortino_ratio == 2.45
        assert record.max_drawdown == -8.5
        assert record.volatility == 15.2
        assert record.win_rate == 65.5
        assert record.profit_factor == 2.15
        assert record.dte_target == 30
        assert record.delta_target == 0.20
        assert record.commission == 0.50
        assert record.total_trades == 50

    def test_get_nonexistent_backtest(self, history: BacktestHistory) -> None:
        """Test retrieving a record that doesn't exist."""
        record = history.get_backtest(999)
        assert record is None

    def test_list_backtests(
        self,
        history: BacktestHistory,
        sample_config: BacktestConfig,
        sample_metrics: PerformanceMetrics,
    ) -> None:
        """Test listing backtest records."""
        # Save multiple records
        for i in range(5):
            history.save_backtest(
                config=sample_config,
                metrics=sample_metrics,
                start_date="2023-01-01",
                end_date="2023-12-31",
                final_equity=125_100.0 + i * 1000,
                total_trades=50 + i,
            )

        records = history.list_backtests(limit=10)

        assert len(records) == 5
        # Should be ordered by run_date descending (most recent first)
        for i in range(len(records) - 1):
            assert records[i].run_date >= records[i + 1].run_date

    def test_list_backtests_with_ticker_filter(
        self,
        history: BacktestHistory,
        sample_config: BacktestConfig,
        sample_metrics: PerformanceMetrics,
    ) -> None:
        """Test listing backtests filtered by ticker."""
        # Save SPY records
        for _ in range(3):
            history.save_backtest(
                config=sample_config,
                metrics=sample_metrics,
                start_date="2023-01-01",
                end_date="2023-12-31",
                final_equity=125_100.0,
                total_trades=50,
            )

        # Save QQQ records
        qqq_config = BacktestConfig(
            ticker="QQQ",
            initial_capital=100_000,
            dte_target=30,
            delta_target=0.20,
            cache_dir=Path("./cache"),
            output_dir=Path("./output"),
        )
        for _ in range(2):
            history.save_backtest(
                config=qqq_config,
                metrics=sample_metrics,
                start_date="2023-01-01",
                end_date="2023-12-31",
                final_equity=125_100.0,
                total_trades=50,
            )

        spy_records = history.list_backtests(ticker="SPY")
        qqq_records = history.list_backtests(ticker="QQQ")

        assert len(spy_records) == 3
        assert len(qqq_records) == 2
        assert all(r.ticker == "SPY" for r in spy_records)
        assert all(r.ticker == "QQQ" for r in qqq_records)

    def test_list_backtests_with_limit(
        self,
        history: BacktestHistory,
        sample_config: BacktestConfig,
        sample_metrics: PerformanceMetrics,
    ) -> None:
        """Test listing backtests with limit."""
        # Save 10 records
        for i in range(10):
            history.save_backtest(
                config=sample_config,
                metrics=sample_metrics,
                start_date="2023-01-01",
                end_date="2023-12-31",
                final_equity=125_100.0,
                total_trades=50,
            )

        records = history.list_backtests(limit=5)
        assert len(records) == 5

    def test_get_best_by_metric(
        self,
        history: BacktestHistory,
        sample_config: BacktestConfig,
    ) -> None:
        """Test getting best backtests by metric."""
        # Save records with different CAGRs
        cagrs = [15.0, 25.0, 18.0, 30.0, 22.0]
        for cagr in cagrs:
            metrics = PerformanceMetrics(
                total_return=cagr * 1000,
                total_return_pct=cagr,
                cagr=cagr,
                sharpe_ratio=1.5,
                sortino_ratio=2.0,
                max_drawdown=-10.0,
                max_drawdown_duration=30,
                volatility=15.0,
                win_rate=60.0,
                profit_factor=2.0,
                calmar_ratio=2.0,
            )
            history.save_backtest(
                config=sample_config,
                metrics=metrics,
                start_date="2023-01-01",
                end_date="2023-12-31",
                final_equity=100_000 + cagr * 1000,
                total_trades=50,
            )

        best = history.get_best_by_metric(metric="cagr", limit=3)

        assert len(best) == 3
        assert best[0].cagr == 30.0
        assert best[1].cagr == 25.0
        assert best[2].cagr == 22.0

    def test_get_best_by_sharpe_ratio(
        self,
        history: BacktestHistory,
        sample_config: BacktestConfig,
    ) -> None:
        """Test getting best backtests by Sharpe ratio."""
        # Save records with different Sharpe ratios
        sharpes = [1.2, 1.8, 1.5, 2.1, 1.6]
        for sharpe in sharpes:
            metrics = PerformanceMetrics(
                total_return=20_000,
                total_return_pct=20.0,
                cagr=20.0,
                sharpe_ratio=sharpe,
                sortino_ratio=2.0,
                max_drawdown=-10.0,
                max_drawdown_duration=30,
                volatility=15.0,
                win_rate=60.0,
                profit_factor=2.0,
                calmar_ratio=2.0,
            )
            history.save_backtest(
                config=sample_config,
                metrics=metrics,
                start_date="2023-01-01",
                end_date="2023-12-31",
                final_equity=120_000,
                total_trades=50,
            )

        best = history.get_best_by_metric(metric="sharpe_ratio", limit=2)

        assert len(best) == 2
        assert best[0].sharpe_ratio == 2.1
        assert best[1].sharpe_ratio == 1.8

    def test_get_best_invalid_metric(self, history: BacktestHistory) -> None:
        """Test that invalid metric raises ValueError."""
        with pytest.raises(ValueError, match="Invalid metric"):
            history.get_best_by_metric(metric="invalid_metric", limit=10)

    def test_delete_backtest(
        self,
        history: BacktestHistory,
        sample_config: BacktestConfig,
        sample_metrics: PerformanceMetrics,
    ) -> None:
        """Test deleting a backtest record."""
        record_id = history.save_backtest(
            config=sample_config,
            metrics=sample_metrics,
            start_date="2023-01-01",
            end_date="2023-12-31",
            final_equity=125_100.0,
            total_trades=50,
        )

        # Verify it exists
        assert history.get_backtest(record_id) is not None

        # Delete it
        deleted = history.delete_backtest(record_id)
        assert deleted is True

        # Verify it's gone
        assert history.get_backtest(record_id) is None

    def test_delete_nonexistent_backtest(self, history: BacktestHistory) -> None:
        """Test deleting a record that doesn't exist."""
        deleted = history.delete_backtest(999)
        assert deleted is False

    def test_config_json_storage(
        self,
        history: BacktestHistory,
        sample_config: BacktestConfig,
        sample_metrics: PerformanceMetrics,
    ) -> None:
        """Test that configuration is stored as JSON."""
        record_id = history.save_backtest(
            config=sample_config,
            metrics=sample_metrics,
            start_date="2023-01-01",
            end_date="2023-12-31",
            final_equity=125_100.0,
            total_trades=50,
        )

        record = history.get_backtest(record_id)
        assert record is not None

        # Parse config JSON
        config_dict = json.loads(record.config_json)
        assert config_dict["ticker"] == "SPY"
        assert config_dict["initial_capital"] == 100_000
        assert config_dict["dte_target"] == 30
        assert config_dict["delta_target"] == 0.20
        assert config_dict["commission_per_contract"] == 0.50

    def test_csv_paths_storage(
        self,
        history: BacktestHistory,
        sample_config: BacktestConfig,
        sample_metrics: PerformanceMetrics,
        tmp_path: Path,
    ) -> None:
        """Test storing CSV file paths."""
        equity_path = tmp_path / "equity.csv"
        transactions_path = tmp_path / "transactions.csv"

        record_id = history.save_backtest(
            config=sample_config,
            metrics=sample_metrics,
            start_date="2023-01-01",
            end_date="2023-12-31",
            final_equity=125_100.0,
            total_trades=50,
            equity_csv_path=equity_path,
            transactions_csv_path=transactions_path,
        )

        record = history.get_backtest(record_id)
        assert record is not None
        assert record.equity_csv_path == str(equity_path)
        assert record.transactions_csv_path == str(transactions_path)

    def test_run_date_tracking(
        self,
        history: BacktestHistory,
        sample_config: BacktestConfig,
        sample_metrics: PerformanceMetrics,
    ) -> None:
        """Test that run_date is automatically tracked."""
        before = datetime.now()

        record_id = history.save_backtest(
            config=sample_config,
            metrics=sample_metrics,
            start_date="2023-01-01",
            end_date="2023-12-31",
            final_equity=125_100.0,
            total_trades=50,
        )

        after = datetime.now()

        record = history.get_backtest(record_id)
        assert record is not None
        assert before <= record.run_date <= after

    def test_empty_database(self, history: BacktestHistory) -> None:
        """Test operations on empty database."""
        records = history.list_backtests()
        assert len(records) == 0

        best = history.get_best_by_metric(metric="cagr")
        assert len(best) == 0
