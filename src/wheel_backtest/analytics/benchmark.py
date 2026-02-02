"""Buy-and-hold benchmark calculator.

Calculates equity curve for a simple buy-and-hold strategy
to compare against the wheel strategy performance.
"""

from datetime import date

import pandas as pd

from wheel_backtest.analytics.equity import EquityCurve
from wheel_backtest.data.yfinance_provider import YFinanceProvider


class BuyAndHoldBenchmark:
    """Buy-and-hold benchmark calculator.

    Simulates buying stock on day 1 and holding through the entire period.
    Uses adjusted close prices to account for dividends and splits.
    """

    def __init__(self, provider: YFinanceProvider):
        """Initialize benchmark calculator.

        Args:
            provider: YFinanceProvider for price data
        """
        self._provider = provider

    def calculate(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
        initial_capital: float,
    ) -> EquityCurve:
        """Calculate buy-and-hold equity curve.

        Invests all capital in shares on the first trading day
        and holds through the end date. Uses adjusted close prices
        to reflect dividend reinvestment.

        Args:
            ticker: Stock symbol
            start_date: Start date (or first trading day after)
            end_date: End date (or last trading day before)
            initial_capital: Starting capital in dollars

        Returns:
            EquityCurve with daily equity values
        """
        # Get price data for the full period
        prices = self._provider.get_prices(ticker, start_date, end_date)

        if prices.empty:
            return EquityCurve()

        curve = EquityCurve()

        # Buy as many shares as possible on first day
        first_price = float(prices["adjusted_close"].iloc[0])
        shares = initial_capital / first_price  # Allow fractional shares

        # Track equity for each trading day
        for idx, row in prices.iterrows():
            trade_date = idx.date() if hasattr(idx, "date") else idx
            adjusted_price = float(row["adjusted_close"])

            # All value is in stock (no cash since we invest everything)
            stock_value = shares * adjusted_price

            curve.add_point(
                trade_date=trade_date,
                cash=0.0,
                stock_value=stock_value,
                options_value=0.0,
            )

        return curve

    def calculate_with_dividends(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
        initial_capital: float,
    ) -> tuple[EquityCurve, pd.DataFrame]:
        """Calculate buy-and-hold with detailed dividend tracking.

        Similar to calculate() but also returns dividend history.
        Uses unadjusted prices and accumulates dividends as cash.

        Args:
            ticker: Stock symbol
            start_date: Start date
            end_date: End date
            initial_capital: Starting capital

        Returns:
            Tuple of (EquityCurve, dividend_df)
        """
        prices = self._provider.get_prices(ticker, start_date, end_date)

        if prices.empty:
            return EquityCurve(), pd.DataFrame()

        curve = EquityCurve()

        # Buy shares at unadjusted price
        first_price = float(prices["close"].iloc[0])
        shares = int(initial_capital / first_price)  # Whole shares only
        cash = initial_capital - (shares * first_price)

        dividend_records = []

        for idx, row in prices.iterrows():
            trade_date = idx.date() if hasattr(idx, "date") else idx
            close_price = float(row["close"])
            dividend = float(row["dividend"])

            # Collect dividends
            if dividend > 0:
                dividend_amount = shares * dividend
                cash += dividend_amount
                dividend_records.append(
                    {
                        "date": trade_date,
                        "dividend_per_share": dividend,
                        "shares": shares,
                        "total_dividend": dividend_amount,
                    }
                )

            stock_value = shares * close_price

            curve.add_point(
                trade_date=trade_date,
                cash=cash,
                stock_value=stock_value,
                options_value=0.0,
            )

        dividend_df = pd.DataFrame(dividend_records)

        return curve, dividend_df

    def get_summary(
        self,
        curve: EquityCurve,
        initial_capital: float,
    ) -> dict:
        """Generate summary statistics for benchmark.

        Args:
            curve: Calculated equity curve
            initial_capital: Starting capital

        Returns:
            Dictionary with summary statistics
        """
        if not curve.points:
            return {
                "start_date": None,
                "end_date": None,
                "trading_days": 0,
                "years": None,
                "initial_capital": initial_capital,
                "final_value": None,
                "total_return": None,
                "total_return_pct": None,
                "cagr_pct": None,
            }

        final_value = curve.end_value
        total_return = final_value - initial_capital if final_value else None
        total_return_pct = (
            (total_return / initial_capital * 100) if total_return else None
        )

        # Calculate years for CAGR
        if curve.start_date and curve.end_date:
            days = (curve.end_date - curve.start_date).days
            years = days / 365.25

            if years > 0 and final_value and initial_capital > 0:
                cagr = ((final_value / initial_capital) ** (1 / years) - 1) * 100
            else:
                cagr = None
        else:
            years = None
            cagr = None

        return {
            "start_date": curve.start_date,
            "end_date": curve.end_date,
            "trading_days": len(curve),
            "years": round(years, 2) if years else None,
            "initial_capital": initial_capital,
            "final_value": round(final_value, 2) if final_value else None,
            "total_return": round(total_return, 2) if total_return else None,
            "total_return_pct": round(total_return_pct, 2) if total_return_pct else None,
            "cagr_pct": round(cagr, 2) if cagr else None,
        }
