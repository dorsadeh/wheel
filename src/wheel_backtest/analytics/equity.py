"""Equity curve data structures and calculations.

Provides daily tracking of portfolio value for backtesting.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Iterator

import pandas as pd


@dataclass
class EquityPoint:
    """Single point in an equity curve."""

    date: date
    cash: float
    stock_value: float
    options_value: float = 0.0

    @property
    def total(self) -> float:
        """Total portfolio value."""
        return self.cash + self.stock_value + self.options_value


@dataclass
class EquityCurve:
    """Time series of portfolio equity values.

    Tracks daily portfolio value broken down by:
    - Cash holdings
    - Stock positions (marked to market)
    - Options positions (marked to market)
    """

    points: list[EquityPoint] = field(default_factory=list)

    def add_point(
        self,
        trade_date: date,
        cash: float,
        stock_value: float,
        options_value: float = 0.0,
    ) -> None:
        """Add a new equity point.

        Args:
            trade_date: Date of the equity snapshot
            cash: Cash balance
            stock_value: Value of stock holdings
            options_value: Mark-to-market value of options positions
        """
        self.points.append(
            EquityPoint(
                date=trade_date,
                cash=cash,
                stock_value=stock_value,
                options_value=options_value,
            )
        )

    def __len__(self) -> int:
        return len(self.points)

    def __iter__(self) -> Iterator[EquityPoint]:
        return iter(self.points)

    def __getitem__(self, index: int) -> EquityPoint:
        return self.points[index]

    @property
    def start_date(self) -> date | None:
        """First date in curve."""
        return self.points[0].date if self.points else None

    @property
    def end_date(self) -> date | None:
        """Last date in curve."""
        return self.points[-1].date if self.points else None

    @property
    def start_value(self) -> float | None:
        """Initial portfolio value."""
        return self.points[0].total if self.points else None

    @property
    def end_value(self) -> float | None:
        """Final portfolio value."""
        return self.points[-1].total if self.points else None

    def to_dataframe(self) -> pd.DataFrame:
        """Convert to pandas DataFrame.

        Returns:
            DataFrame with columns: date, cash, stock_value, options_value, total
        """
        if not self.points:
            return pd.DataFrame(
                columns=["date", "cash", "stock_value", "options_value", "total"]
            )

        data = [
            {
                "date": p.date,
                "cash": p.cash,
                "stock_value": p.stock_value,
                "options_value": p.options_value,
                "total": p.total,
            }
            for p in self.points
        ]
        df = pd.DataFrame(data)
        df = df.set_index("date")
        return df

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> "EquityCurve":
        """Create EquityCurve from DataFrame.

        Args:
            df: DataFrame with date index and columns:
                cash, stock_value, options_value (optional)

        Returns:
            EquityCurve instance
        """
        curve = cls()
        for idx, row in df.iterrows():
            trade_date = idx.date() if hasattr(idx, "date") else idx
            curve.add_point(
                trade_date=trade_date,
                cash=row.get("cash", 0.0),
                stock_value=row.get("stock_value", 0.0),
                options_value=row.get("options_value", 0.0),
            )
        return curve

    def get_returns(self) -> pd.Series:
        """Calculate daily returns.

        Returns:
            Series of daily percentage returns
        """
        df = self.to_dataframe()
        if df.empty:
            return pd.Series(dtype=float)
        return df["total"].pct_change().dropna()

    def get_cumulative_returns(self) -> pd.Series:
        """Calculate cumulative returns from start.

        Returns:
            Series of cumulative returns (1.0 = 100% gain)
        """
        df = self.to_dataframe()
        if df.empty or self.start_value is None or self.start_value == 0:
            return pd.Series(dtype=float)
        return (df["total"] / self.start_value) - 1
