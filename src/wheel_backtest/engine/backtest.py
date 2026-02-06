"""Main backtesting orchestrator.

Coordinates the wheel strategy execution across historical data.
"""

import time
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import pandas as pd
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.table import Table

from wheel_backtest.analytics.equity import EquityCurve, EquityPoint
from wheel_backtest.analytics.metrics import MetricsCalculator, PerformanceMetrics
from wheel_backtest.config import BacktestConfig
from wheel_backtest.data import DataCache, PhilippdubachProvider, YFinanceProvider
from wheel_backtest.engine.options import OptionSelector
from wheel_backtest.engine.portfolio import Portfolio
from wheel_backtest.engine.wheel import WheelEvent, WheelStrategy

console = Console()


@dataclass
class BacktestResult:
    """Results from a completed backtest.

    Attributes:
        ticker: Stock symbol backtested
        start_date: First trading date
        end_date: Last trading date
        initial_capital: Starting capital
        final_equity: Ending equity
        equity_curve: Daily equity values
        events: All wheel strategy events
        summary: Strategy execution summary
        metrics: Performance metrics
        config: Backtest configuration
        timings: Performance timing breakdown by phase
    """

    ticker: str
    start_date: date
    end_date: date
    initial_capital: float
    final_equity: float
    equity_curve: EquityCurve
    events: list[WheelEvent]
    summary: dict
    metrics: PerformanceMetrics
    config: BacktestConfig
    timings: dict[str, float] = field(default_factory=dict)


@dataclass
class Transaction:
    """A transaction record for logging.

    Attributes:
        date: Transaction date
        action: Action type (e.g., 'sell_put', 'put_assigned')
        instrument: Instrument description
        quantity: Number of contracts/shares
        price: Price per unit
        value: Total value
        commission: Commission paid
        cash_after: Cash balance after transaction
        shares_after: Share balance after transaction
        equity_after: Total equity after transaction
        delta: Option delta at time of trade (None for non-option transactions)
        notes: Additional notes
    """

    date: date
    action: str
    instrument: str
    quantity: int
    price: float
    value: float
    commission: float
    cash_after: float
    shares_after: int
    equity_after: float
    delta: Optional[float] = None
    notes: str = ""


class WheelBacktest:
    """Main backtest orchestrator for the wheel strategy.

    Coordinates data providers, portfolio, and strategy to run
    a complete historical backtest.
    """

    def __init__(self, config: BacktestConfig):
        """Initialize backtest with configuration.

        Args:
            config: Backtest configuration
        """
        self.config = config

        # Initialize data providers
        cache = DataCache(config.cache_dir)
        self.options_provider = PhilippdubachProvider(cache)
        self.underlying_provider = YFinanceProvider(cache)

        # Initialize strategy components
        self.portfolio = Portfolio(cash=config.initial_capital)
        self.selector = OptionSelector(
            dte_target=config.dte_target,
            dte_min=config.dte_min,
            delta_target=config.delta_target,  # Legacy fallback
            put_delta=config.effective_put_delta,
            call_delta=config.effective_call_delta,
        )
        self.strategy = WheelStrategy(
            portfolio=self.portfolio,
            selector=self.selector,
            contracts_per_trade=1,
            commission_per_contract=config.commission_per_contract,
            enable_call_entry_protection=config.enable_call_entry_protection,
            call_entry_protection_dollars=config.call_entry_protection_dollars,
        )

        # Results tracking
        self.equity_curve = EquityCurve(points=[])
        self.transactions: list[Transaction] = []

        # Pre-filtered options data (for performance)
        self._options_data_filtered: Optional[pd.DataFrame] = None

    def run(self) -> BacktestResult:
        """Execute the backtest.

        Returns:
            BacktestResult with all performance data
        """
        # Time tracking
        timings = {}
        start_time = time.time()

        console.print(f"\n[bold]Running Wheel Strategy Backtest: {self.config.ticker}[/bold]")

        # Get underlying price data to determine date range
        console.print("[dim]Loading underlying price data...[/dim]")
        t0 = time.time()
        prices = self._get_price_data()
        timings['data_loading'] = time.time() - t0
        console.print(f"[dim]Loaded {len(prices)} days in {timings['data_loading']:.2f}s[/dim]")

        if prices.empty:
            raise ValueError(f"No price data available for {self.config.ticker}")

        # Determine actual date range
        start_date = prices.index[0].date()
        end_date = prices.index[-1].date()

        console.print(f"Period: {start_date} to {end_date}")
        console.print(f"Trading Days: {len(prices)}")
        console.print(f"Initial Capital: ${self.config.initial_capital:,.2f}\n")

        # Pre-filter options data to backtest date range for performance
        console.print("[dim]Pre-filtering options data to date range...[/dim]")
        t0 = time.time()
        self._prefilter_options_data(start_date, end_date)
        t_prefilter = time.time() - t0
        console.print(f"[dim]Pre-filtered options data in {t_prefilter:.2f}s[/dim]")
        timings['prefilter'] = t_prefilter

        # Record initial equity point (all cash, no stock/options)
        self.equity_curve.add_point(
            trade_date=start_date,
            cash=self.config.initial_capital,
            stock_value=0.0,
            options_value=0.0,
        )

        # Run backtest day by day
        t_execution = time.time()
        t_options_fetch = 0.0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"Processing {len(prices)} days", total=len(prices)
            )

            for idx, (trade_date, price_row) in enumerate(prices.iterrows(), 1):
                trade_date_obj = trade_date.date()
                underlying_price = float(price_row["close"])

                # Update progress with current date
                progress.update(
                    task,
                    description=f"Processing {trade_date_obj} (Day {idx}/{len(prices)})",
                )

                # Get options chain for this date (track time)
                t0 = time.time()
                options_chain = self._get_options_chain(trade_date_obj)
                t_options_fetch += time.time() - t0

                if not options_chain.empty:
                    # Process this day with the strategy
                    events = self.strategy.process_day(
                        trade_date=trade_date_obj,
                        underlying_price=underlying_price,
                        options_chain=options_chain,
                    )

                    # Log transactions from events
                    for event in events:
                        self._log_event(event, underlying_price)

                # Record equity for this day
                stock_value = self.portfolio.shares * underlying_price
                # TODO: mark options to market properly
                options_value = 0.0  # Simplified for now
                self.equity_curve.add_point(
                    trade_date=trade_date_obj,
                    cash=self.portfolio.cash,
                    stock_value=stock_value,
                    options_value=options_value,
                )

                progress.advance(task)

        # Get final results
        timings['execution'] = time.time() - t_execution
        timings['options_fetch'] = t_options_fetch
        final_equity = self.equity_curve.points[-1].total

        console.print(f"\n[bold green]Backtest Complete![/bold green]")
        console.print(f"Final Equity: ${final_equity:,.2f}")
        console.print(
            f"Total Return: ${final_equity - self.config.initial_capital:,.2f} "
            f"({(final_equity / self.config.initial_capital - 1) * 100:.2f}%)"
        )

        # Calculate performance metrics
        t0 = time.time()
        metrics_calc = MetricsCalculator(risk_free_rate=0.04)  # 4% risk-free rate
        metrics = metrics_calc.calculate(
            equity_curve=self.equity_curve,
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.config.initial_capital,
        )
        timings['metrics'] = time.time() - t0

        # Calculate total time and display summary
        timings['total'] = time.time() - start_time
        timings['other'] = timings['total'] - sum([
            timings.get('data_loading', 0),
            timings.get('prefilter', 0),
            timings.get('execution', 0),
            timings.get('metrics', 0)
        ])

        # Display timing summary
        console.print("\n")
        table = Table(title="⏱️  Performance Timing Summary", show_header=True, header_style="bold")
        table.add_column("Phase", style="cyan")
        table.add_column("Time", justify="right", style="green")
        table.add_column("Percentage", justify="right", style="yellow")

        for phase, label in [
            ('data_loading', 'Data Loading'),
            ('prefilter', 'Options Data Pre-filter'),
            ('options_fetch', 'Options Chain Fetch'),
            ('execution', 'Strategy Execution'),
            ('metrics', 'Metrics Calculation'),
            ('other', 'Other'),
        ]:
            if phase in timings:
                t = timings[phase]
                pct = (t / timings['total']) * 100
                table.add_row(label, f"{t:.2f}s", f"{pct:.1f}%")

        table.add_section()
        table.add_row("[bold]Total Time[/bold]", f"[bold]{timings['total']:.2f}s[/bold]", "[bold]100%[/bold]")

        console.print(table)

        return BacktestResult(
            ticker=self.config.ticker,
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.config.initial_capital,
            final_equity=final_equity,
            equity_curve=self.equity_curve,
            events=self.strategy.events,
            summary=self.strategy.get_summary(),
            metrics=metrics,
            config=self.config,
            timings=timings,
        )

    def _get_price_data(self) -> pd.DataFrame:
        """Get underlying price data for the backtest period.

        Returns:
            DataFrame with OHLCV data indexed by date
        """
        # Determine date range
        if self.config.start_date and self.config.end_date:
            start = self.config.start_date
            end = self.config.end_date
        else:
            # Use default range if not specified
            start = self.config.start_date or date(2020, 1, 1)
            end = self.config.end_date or date.today()

        prices = self.underlying_provider.get_prices(
            ticker=self.config.ticker,
            start_date=start,
            end_date=end,
        )

        # Filter to configured range if provided
        if self.config.start_date:
            prices = prices[prices.index >= pd.Timestamp(self.config.start_date)]
        if self.config.end_date:
            prices = prices[prices.index <= pd.Timestamp(self.config.end_date)]

        return prices

    def _prefilter_options_data(self, start_date: date, end_date: date) -> None:
        """Pre-filter options data to backtest date range for performance.

        This uses PyArrow predicate pushdown to filter while reading the parquet file,
        and caches the filtered result for reuse.

        Args:
            start_date: Backtest start date
            end_date: Backtest end date
        """
        # Use the provider's optimized filtered method (with PyArrow + caching)
        self._options_data_filtered = self.options_provider.get_filtered_options(
            ticker=self.config.ticker,
            start_date=start_date,
            end_date=end_date,
        )

        # Log result
        filtered_size = len(self._options_data_filtered)
        console.print(
            f"[dim]Loaded {filtered_size:,} rows for date range "
            f"{start_date} to {end_date}[/dim]"
        )

    def _get_options_chain(self, trade_date: date) -> pd.DataFrame:
        """Get options chain for a specific date.

        Args:
            trade_date: Date to fetch options for

        Returns:
            DataFrame with options chain data
        """
        # Use pre-filtered data if available (much faster)
        if self._options_data_filtered is not None:
            trade_date_ts = pd.Timestamp(trade_date).normalize()
            mask = self._options_data_filtered["trade_date"].dt.normalize() == trade_date_ts
            return self._options_data_filtered[mask].copy()

        # Fallback to provider if pre-filtering not done
        try:
            return self.options_provider.get_options_chain(
                ticker=self.config.ticker,
                trade_date=trade_date,
            )
        except Exception:
            # If no options data available for this date, return empty DataFrame
            return pd.DataFrame()

    def _log_event(self, event: WheelEvent, underlying_price: float) -> None:
        """Log a wheel event as a transaction.

        Args:
            event: Wheel strategy event
            underlying_price: Current underlying price
        """
        details = event.details
        action = event.event_type

        # Determine instrument description
        if "strike" in details:
            option_type = "PUT" if "put" in action else "CALL"
            expiry = details.get("expiration", "")
            instrument = f"{option_type} ${details['strike']:.0f} {expiry}"
        else:
            instrument = self.config.ticker

        # Calculate values
        if "premium" in details:
            price = details["premium"]
            quantity = details.get("contracts", 1)
            value = price * quantity * 100
        elif "shares_acquired" in details:
            quantity = details["shares_acquired"]
            price = details["strike"]
            value = quantity * price
        elif "shares_sold" in details:
            quantity = details["shares_sold"]
            price = details["strike"]
            value = quantity * price
        else:
            price = 0.0
            quantity = 0
            value = 0.0

        commission = details.get("commission", 0.0)
        delta = details.get("delta")  # Will be None for non-option transactions

        # Create transaction record
        transaction = Transaction(
            date=event.date,
            action=action,
            instrument=instrument,
            quantity=quantity,
            price=price,
            value=value,
            commission=commission,
            cash_after=self.portfolio.cash,
            shares_after=self.portfolio.shares,
            equity_after=self.portfolio.get_equity(underlying_price),
            delta=delta,
            notes=f"State: {event.state_after.value}",
        )

        self.transactions.append(transaction)

    def get_transactions_df(self) -> pd.DataFrame:
        """Get transactions as a DataFrame.

        Returns:
            DataFrame with all transaction records
        """
        if not self.transactions:
            return pd.DataFrame()

        return pd.DataFrame([vars(t) for t in self.transactions])
