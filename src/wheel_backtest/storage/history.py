"""Backtest history storage using SQLite.

Provides persistent storage for backtest results to track and compare
different runs over time.
"""

import json
import sqlite3
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from wheel_backtest.analytics.metrics import PerformanceMetrics
from wheel_backtest.config import BacktestConfig


@dataclass
class BacktestRecord:
    """A stored backtest record.

    Attributes:
        id: Unique record ID (auto-generated)
        run_date: When the backtest was executed
        ticker: Stock symbol
        start_date: Backtest start date
        end_date: Backtest end date
        initial_capital: Starting capital
        final_equity: Ending equity
        total_return: Total return in dollars
        total_return_pct: Total return percentage
        cagr: Compound Annual Growth Rate
        sharpe_ratio: Sharpe ratio
        sortino_ratio: Sortino ratio
        max_drawdown: Maximum drawdown percentage
        volatility: Annualized volatility
        win_rate: Win rate percentage
        profit_factor: Profit factor
        dte_target: Target days to expiration
        delta_target: Target delta
        commission: Commission per contract
        total_trades: Total number of trades
        git_commit: Git commit hash (if available)
        config_json: Full configuration as JSON
        equity_csv_path: Path to equity curve CSV
        transactions_csv_path: Path to transactions CSV
    """

    id: Optional[int]
    run_date: datetime
    ticker: str
    start_date: str
    end_date: str
    initial_capital: float
    final_equity: float
    total_return: float
    total_return_pct: float
    cagr: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    volatility: float
    win_rate: float
    profit_factor: float
    dte_target: int
    delta_target: float
    commission: float
    total_trades: int
    git_commit: Optional[str]
    config_json: str
    equity_csv_path: Optional[str] = None
    transactions_csv_path: Optional[str] = None


class BacktestHistory:
    """Manage backtest history storage.

    Uses SQLite to store backtest results for tracking and comparison.
    """

    def __init__(self, db_path: Path):
        """Initialize history storage.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self) -> None:
        """Initialize database schema if not exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS backtest_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date TIMESTAMP NOT NULL,
                ticker TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                initial_capital REAL NOT NULL,
                final_equity REAL NOT NULL,
                total_return REAL NOT NULL,
                total_return_pct REAL NOT NULL,
                cagr REAL NOT NULL,
                sharpe_ratio REAL NOT NULL,
                sortino_ratio REAL NOT NULL,
                max_drawdown REAL NOT NULL,
                volatility REAL NOT NULL,
                win_rate REAL NOT NULL,
                profit_factor REAL NOT NULL,
                dte_target INTEGER NOT NULL,
                delta_target REAL NOT NULL,
                commission REAL NOT NULL,
                total_trades INTEGER NOT NULL,
                git_commit TEXT,
                config_json TEXT NOT NULL,
                equity_csv_path TEXT,
                transactions_csv_path TEXT
            )
        """)

        # Create indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ticker
            ON backtest_history(ticker)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_run_date
            ON backtest_history(run_date)
        """)

        conn.commit()
        conn.close()

    def save_backtest(
        self,
        config: BacktestConfig,
        metrics: PerformanceMetrics,
        start_date: str,
        end_date: str,
        final_equity: float,
        total_trades: int,
        equity_csv_path: Optional[Path] = None,
        transactions_csv_path: Optional[Path] = None,
    ) -> int:
        """Save a backtest result to history.

        Args:
            config: Backtest configuration
            metrics: Performance metrics
            start_date: Backtest start date (ISO format)
            end_date: Backtest end date (ISO format)
            final_equity: Final portfolio value
            total_trades: Total number of trades executed
            equity_csv_path: Path to equity curve CSV (optional)
            transactions_csv_path: Path to transactions CSV (optional)

        Returns:
            Record ID of saved backtest
        """
        git_commit = self._get_git_commit()

        # Convert config to JSON
        config_dict = {
            "ticker": config.ticker,
            "start_date": str(config.start_date) if config.start_date else None,
            "end_date": str(config.end_date) if config.end_date else None,
            "initial_capital": config.initial_capital,
            "dte_target": config.dte_target,
            "dte_min": config.dte_min,
            "delta_target": config.delta_target,
            "commission_per_contract": config.commission_per_contract,
            "data_provider": config.data_provider,
        }
        config_json = json.dumps(config_dict)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO backtest_history (
                run_date, ticker, start_date, end_date,
                initial_capital, final_equity, total_return, total_return_pct,
                cagr, sharpe_ratio, sortino_ratio, max_drawdown,
                volatility, win_rate, profit_factor,
                dte_target, delta_target, commission, total_trades,
                git_commit, config_json,
                equity_csv_path, transactions_csv_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now(),
            config.ticker,
            start_date,
            end_date,
            config.initial_capital,
            final_equity,
            metrics.total_return,
            metrics.total_return_pct,
            metrics.cagr,
            metrics.sharpe_ratio,
            metrics.sortino_ratio,
            metrics.max_drawdown,
            metrics.volatility,
            metrics.win_rate,
            metrics.profit_factor,
            config.dte_target,
            config.delta_target,
            config.commission_per_contract,
            total_trades,
            git_commit,
            config_json,
            str(equity_csv_path) if equity_csv_path else None,
            str(transactions_csv_path) if transactions_csv_path else None,
        ))

        record_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return record_id

    def get_backtest(self, record_id: int) -> Optional[BacktestRecord]:
        """Retrieve a specific backtest record.

        Args:
            record_id: Record ID to retrieve

        Returns:
            BacktestRecord if found, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM backtest_history WHERE id = ?
        """, (record_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_record(row)
        return None

    def list_backtests(
        self,
        ticker: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[BacktestRecord]:
        """List backtest records with optional filtering.

        Args:
            ticker: Filter by ticker (optional)
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of BacktestRecords, ordered by run_date descending
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if ticker:
            cursor.execute("""
                SELECT * FROM backtest_history
                WHERE ticker = ?
                ORDER BY run_date DESC
                LIMIT ? OFFSET ?
            """, (ticker, limit, offset))
        else:
            cursor.execute("""
                SELECT * FROM backtest_history
                ORDER BY run_date DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_record(row) for row in rows]

    def get_best_by_metric(
        self,
        metric: str,
        ticker: Optional[str] = None,
        limit: int = 10,
    ) -> list[BacktestRecord]:
        """Get top backtests by a specific metric.

        Args:
            metric: Metric name (e.g., 'cagr', 'sharpe_ratio', 'total_return_pct')
            ticker: Filter by ticker (optional)
            limit: Number of top results to return

        Returns:
            List of BacktestRecords, ordered by metric descending
        """
        # Validate metric name to prevent SQL injection
        valid_metrics = [
            'cagr', 'sharpe_ratio', 'sortino_ratio', 'total_return_pct',
            'win_rate', 'profit_factor', 'volatility', 'max_drawdown'
        ]

        if metric not in valid_metrics:
            raise ValueError(f"Invalid metric: {metric}. Must be one of {valid_metrics}")

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if ticker:
            query = f"""
                SELECT * FROM backtest_history
                WHERE ticker = ?
                ORDER BY {metric} DESC
                LIMIT ?
            """
            cursor.execute(query, (ticker, limit))
        else:
            query = f"""
                SELECT * FROM backtest_history
                ORDER BY {metric} DESC
                LIMIT ?
            """
            cursor.execute(query, (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_record(row) for row in rows]

    def delete_backtest(self, record_id: int) -> bool:
        """Delete a backtest record.

        Args:
            record_id: Record ID to delete

        Returns:
            True if deleted, False if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM backtest_history WHERE id = ?
        """, (record_id,))

        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return deleted

    def _row_to_record(self, row: sqlite3.Row) -> BacktestRecord:
        """Convert database row to BacktestRecord."""
        return BacktestRecord(
            id=row['id'],
            run_date=datetime.fromisoformat(row['run_date']),
            ticker=row['ticker'],
            start_date=row['start_date'],
            end_date=row['end_date'],
            initial_capital=row['initial_capital'],
            final_equity=row['final_equity'],
            total_return=row['total_return'],
            total_return_pct=row['total_return_pct'],
            cagr=row['cagr'],
            sharpe_ratio=row['sharpe_ratio'],
            sortino_ratio=row['sortino_ratio'],
            max_drawdown=row['max_drawdown'],
            volatility=row['volatility'],
            win_rate=row['win_rate'],
            profit_factor=row['profit_factor'],
            dte_target=row['dte_target'],
            delta_target=row['delta_target'],
            commission=row['commission'],
            total_trades=row['total_trades'],
            git_commit=row['git_commit'],
            config_json=row['config_json'],
            equity_csv_path=row['equity_csv_path'],
            transactions_csv_path=row['transactions_csv_path'],
        )

    def _get_git_commit(self) -> Optional[str]:
        """Get current git commit hash if available.

        Returns:
            Git commit hash or None
        """
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None
