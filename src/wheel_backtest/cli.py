"""Command-line interface for the wheel backtester."""

from datetime import date
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from wheel_backtest import __version__
from wheel_backtest.config import BacktestConfig, load_config

console = Console()


def parse_date(ctx: click.Context, param: click.Parameter, value: str | None) -> date | None:
    """Parse date string in YYYY-MM-DD format."""
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise click.BadParameter(f"Invalid date format: {value}. Use YYYY-MM-DD.")


@click.group()
@click.version_option(version=__version__, prog_name="wheel-backtest")
@click.option(
    "--cache-dir",
    type=click.Path(path_type=Path),
    envvar="WHEEL_CACHE_DIR",
    default="./cache",
    help="Directory for cached data",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    envvar="WHEEL_OUTPUT_DIR",
    default="./output",
    help="Directory for output files",
)
@click.pass_context
def main(ctx: click.Context, cache_dir: Path, output_dir: Path) -> None:
    """Wheel Strategy Options Backtesting Simulator.

    A test-driven backtester for the wheel options strategy (sell puts,
    get assigned, sell calls, repeat).
    """
    ctx.ensure_object(dict)
    ctx.obj["cache_dir"] = cache_dir
    ctx.obj["output_dir"] = output_dir


@main.command()
@click.argument("ticker", default="SPY")
@click.option(
    "--start",
    "start_date",
    callback=parse_date,
    help="Start date (YYYY-MM-DD)",
)
@click.option(
    "--end",
    "end_date",
    callback=parse_date,
    help="End date (YYYY-MM-DD)",
)
@click.option(
    "--capital",
    "initial_capital",
    type=float,
    default=100_000,
    help="Initial capital in USD",
)
@click.option(
    "--dte",
    "dte_target",
    type=int,
    default=30,
    help="Target days to expiration",
)
@click.option(
    "--delta",
    "delta_target",
    type=float,
    default=0.20,
    help="Target delta for short options (fallback if put/call deltas not specified)",
)
@click.option(
    "--put-delta",
    "put_delta",
    type=float,
    default=None,
    help="Target delta for short puts (overrides --delta)",
)
@click.option(
    "--call-delta",
    "call_delta",
    type=float,
    default=None,
    help="Target delta for short calls (overrides --delta)",
)
@click.option(
    "--commission",
    "commission_per_contract",
    type=float,
    default=0.0,
    help="Commission per contract in USD",
)
@click.option(
    "--charts/--no-charts",
    default=True,
    help="Generate charts",
)
@click.option(
    "--benchmark/--no-benchmark",
    default=False,
    help="Include buy-and-hold benchmark comparison",
)
@click.pass_context
def run(
    ctx: click.Context,
    ticker: str,
    start_date: Optional[date],
    end_date: Optional[date],
    initial_capital: float,
    dte_target: int,
    delta_target: float,
    put_delta: Optional[float],
    call_delta: Optional[float],
    commission_per_contract: float,
    charts: bool,
    benchmark: bool,
) -> None:
    """Run a wheel strategy backtest.

    TICKER: Stock symbol to backtest (default: SPY)
    """
    config = load_config(
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        dte_target=dte_target,
        delta_target=delta_target,
        put_delta=put_delta,
        call_delta=call_delta,
        commission_per_contract=commission_per_contract,
        cache_dir=ctx.obj["cache_dir"],
        output_dir=ctx.obj["output_dir"],
    )

    _display_config(config)

    # Run the backtest
    from wheel_backtest.engine import WheelBacktest

    try:
        backtest = WheelBacktest(config)
        result = backtest.run()

        # Display summary
        _display_backtest_summary(result)

        # Save to history database
        from wheel_backtest.storage import BacktestHistory

        history_db_path = config.cache_dir / "backtest_history.db"
        history = BacktestHistory(history_db_path)

        # Save transactions to CSV
        transactions_df = backtest.get_transactions_df()
        transactions_path = None
        if not transactions_df.empty:
            config.output_dir.mkdir(parents=True, exist_ok=True)
            transactions_path = config.output_dir / f"{config.ticker}_transactions.csv"
            transactions_df.to_csv(transactions_path, index=False)
            console.print(f"\n[dim]Transactions saved to: {transactions_path}[/dim]")

        # Generate charts
        if charts:
            from wheel_backtest.analytics import BuyAndHoldBenchmark
            from wheel_backtest.data import DataCache, YFinanceProvider
            from wheel_backtest.reports.charts import create_backtest_report

            console.print("\n[dim]Generating charts...[/dim]")

            # Optionally calculate benchmark for comparison
            benchmark_curve = None
            if benchmark:
                cache = DataCache(config.cache_dir)
                yf_provider = YFinanceProvider(cache)
                benchmark_calc = BuyAndHoldBenchmark(yf_provider)

                console.print("[dim]Calculating buy-and-hold benchmark...[/dim]")
                benchmark_curve = benchmark_calc.calculate(
                    ticker=config.ticker,
                    start_date=result.start_date,
                    end_date=result.end_date,
                    initial_capital=config.initial_capital,
                )

            # Generate charts
            chart_files = create_backtest_report(
                backtest_curve=result.equity_curve,
                benchmark_curve=benchmark_curve,
                ticker=config.ticker,
                output_dir=config.output_dir,
            )

            console.print("\n[bold]Generated Charts:[/bold]")
            for name, path in chart_files.items():
                if name != "data":  # Don't list CSV
                    console.print(f"  • {name}: {path}")

        # Save to history database
        equity_csv_path = chart_files.get("data") if charts else None
        record_id = history.save_backtest(
            config=config,
            metrics=result.metrics,
            start_date=str(result.start_date),
            end_date=str(result.end_date),
            final_equity=result.final_equity,
            total_trades=len(result.events),
            equity_csv_path=equity_csv_path,
            transactions_csv_path=transactions_path,
        )
        console.print(f"\n[dim]Saved to history database (ID: {record_id})[/dim]")

    except Exception as e:
        console.print(f"\n[red]Error running backtest: {e}[/red]")
        raise


@main.command()
@click.argument("ticker", default="SPY")
@click.option(
    "--start",
    "start_date",
    callback=parse_date,
    help="Start date (YYYY-MM-DD)",
)
@click.option(
    "--end",
    "end_date",
    callback=parse_date,
    help="End date (YYYY-MM-DD)",
)
@click.option(
    "--capital",
    "initial_capital",
    type=float,
    default=100_000,
    help="Initial capital in USD",
)
@click.option(
    "--chart/--no-chart",
    default=True,
    help="Generate charts",
)
@click.pass_context
def benchmark(
    ctx: click.Context,
    ticker: str,
    start_date: Optional[date],
    end_date: Optional[date],
    initial_capital: float,
    chart: bool,
) -> None:
    """Calculate buy-and-hold benchmark for comparison.

    TICKER: Stock symbol to benchmark (default: SPY)
    """
    from wheel_backtest.analytics import BuyAndHoldBenchmark
    from wheel_backtest.data import DataCache, YFinanceProvider
    from wheel_backtest.reports import create_benchmark_report

    config = load_config(
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        cache_dir=ctx.obj["cache_dir"],
        output_dir=ctx.obj["output_dir"],
    )

    console.print(f"\n[bold]Buy-and-Hold Benchmark: {config.ticker}[/bold]")

    # Set default dates if not provided
    effective_start = config.start_date or date(2020, 1, 1)
    effective_end = config.end_date or date.today()

    console.print(f"Period: {effective_start} to {effective_end}")
    console.print(f"Initial Capital: ${config.initial_capital:,.2f}")

    # Initialize data provider
    cache = DataCache(config.cache_dir)
    provider = YFinanceProvider(cache)
    benchmark_calc = BuyAndHoldBenchmark(provider)

    console.print("\n[dim]Fetching price data...[/dim]")

    # Calculate benchmark
    curve = benchmark_calc.calculate(
        ticker=config.ticker,
        start_date=effective_start,
        end_date=effective_end,
        initial_capital=config.initial_capital,
    )

    if not curve.points:
        console.print("[red]Error: No price data available for the specified period.[/red]")
        return

    # Get summary statistics
    summary = benchmark_calc.get_summary(curve, config.initial_capital)

    # Display results
    table = Table(title="Buy-and-Hold Results", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Ticker", config.ticker)
    table.add_row("Start Date", str(summary["start_date"]))
    table.add_row("End Date", str(summary["end_date"]))
    table.add_row("Trading Days", str(summary["trading_days"]))
    table.add_row("Years", str(summary["years"]))
    table.add_row("Initial Capital", f"${summary['initial_capital']:,.2f}")
    table.add_row("Final Value", f"${summary['final_value']:,.2f}")
    table.add_row("Total Return", f"${summary['total_return']:,.2f}")
    table.add_row("Total Return %", f"{summary['total_return_pct']:.2f}%")
    table.add_row("CAGR", f"{summary['cagr_pct']:.2f}%")

    console.print(table)

    # Generate charts
    if chart:
        config.output_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"\n[dim]Generating charts in {config.output_dir}...[/dim]")

        charts = create_benchmark_report(
            benchmark_curve=curve,
            ticker=config.ticker,
            initial_capital=config.initial_capital,
            output_dir=config.output_dir,
        )

        console.print("\n[bold]Generated Files:[/bold]")
        for name, path in charts.items():
            console.print(f"  • {name}: {path}")


@main.command()
@click.pass_context
def config(ctx: click.Context) -> None:
    """Show current configuration."""
    cfg = load_config(
        cache_dir=ctx.obj["cache_dir"],
        output_dir=ctx.obj["output_dir"],
    )
    _display_config(cfg)


@main.group()
@click.pass_context
def history(ctx: click.Context) -> None:
    """Manage backtest history."""
    pass


@history.command(name="list")
@click.option(
    "--ticker",
    help="Filter by ticker symbol",
)
@click.option(
    "--limit",
    type=int,
    default=20,
    help="Maximum number of records to display",
)
@click.pass_context
def history_list(ctx: click.Context, ticker: Optional[str], limit: int) -> None:
    """List backtest history records."""
    from wheel_backtest.storage import BacktestHistory

    history_db_path = ctx.obj["cache_dir"] / "backtest_history.db"
    history = BacktestHistory(history_db_path)

    records = history.list_backtests(ticker=ticker, limit=limit)

    if not records:
        console.print("[yellow]No backtest history found.[/yellow]")
        return

    table = Table(title="Backtest History", show_header=True)
    table.add_column("ID", style="cyan")
    table.add_column("Date", style="dim")
    table.add_column("Ticker", style="green")
    table.add_column("Period", style="dim")
    table.add_column("Return %", style="green")
    table.add_column("CAGR", style="green")
    table.add_column("Sharpe", style="yellow")
    table.add_column("Max DD", style="red")

    for record in records:
        table.add_row(
            str(record.id),
            record.run_date.strftime("%Y-%m-%d %H:%M"),
            record.ticker,
            f"{record.start_date} to {record.end_date}",
            f"{record.total_return_pct:.2f}%",
            f"{record.cagr:.2f}%",
            f"{record.sharpe_ratio:.2f}",
            f"{record.max_drawdown:.2f}%",
        )

    console.print(table)


@history.command(name="show")
@click.argument("record_id", type=int)
@click.pass_context
def history_show(ctx: click.Context, record_id: int) -> None:
    """Show detailed backtest record."""
    from wheel_backtest.storage import BacktestHistory

    history_db_path = ctx.obj["cache_dir"] / "backtest_history.db"
    history = BacktestHistory(history_db_path)

    record = history.get_backtest(record_id)

    if not record:
        console.print(f"[red]Record ID {record_id} not found.[/red]")
        return

    # Display record details
    table = Table(title=f"Backtest Record #{record.id}", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Run Date", record.run_date.strftime("%Y-%m-%d %H:%M:%S"))
    table.add_row("Ticker", record.ticker)
    table.add_row("Period", f"{record.start_date} to {record.end_date}")
    table.add_row("Initial Capital", f"${record.initial_capital:,.2f}")
    table.add_row("Final Equity", f"${record.final_equity:,.2f}")
    table.add_row("Total Return", f"${record.total_return:,.2f}")
    table.add_row("Total Return %", f"{record.total_return_pct:.2f}%")
    table.add_row("CAGR", f"{record.cagr:.2f}%")
    table.add_row("Volatility", f"{record.volatility:.2f}%")
    table.add_row("Sharpe Ratio", f"{record.sharpe_ratio:.2f}")
    table.add_row("Sortino Ratio", f"{record.sortino_ratio:.2f}")
    table.add_row("Max Drawdown", f"{record.max_drawdown:.2f}%")
    table.add_row("Win Rate", f"{record.win_rate:.2f}%")
    table.add_row("Profit Factor", f"{record.profit_factor:.2f}")
    table.add_row("DTE Target", str(record.dte_target))
    table.add_row("Delta Target", f"{record.delta_target:.2f}")
    table.add_row("Commission", f"${record.commission:.2f}")
    table.add_row("Total Trades", str(record.total_trades))
    if record.git_commit:
        table.add_row("Git Commit", record.git_commit[:8])
    if record.equity_csv_path:
        table.add_row("Equity CSV", record.equity_csv_path)
    if record.transactions_csv_path:
        table.add_row("Transactions CSV", record.transactions_csv_path)

    console.print(table)


@history.command(name="best")
@click.option(
    "--metric",
    type=click.Choice([
        "cagr", "sharpe_ratio", "sortino_ratio", "total_return_pct",
        "win_rate", "profit_factor", "volatility", "max_drawdown"
    ]),
    default="cagr",
    help="Metric to rank by",
)
@click.option(
    "--ticker",
    help="Filter by ticker symbol",
)
@click.option(
    "--limit",
    type=int,
    default=10,
    help="Number of top results to display",
)
@click.pass_context
def history_best(ctx: click.Context, metric: str, ticker: Optional[str], limit: int) -> None:
    """Show best backtests by metric."""
    from wheel_backtest.storage import BacktestHistory

    history_db_path = ctx.obj["cache_dir"] / "backtest_history.db"
    history = BacktestHistory(history_db_path)

    records = history.get_best_by_metric(metric=metric, ticker=ticker, limit=limit)

    if not records:
        console.print("[yellow]No backtest history found.[/yellow]")
        return

    metric_display = metric.replace("_", " ").title()
    table = Table(title=f"Best Backtests by {metric_display}", show_header=True)
    table.add_column("ID", style="cyan")
    table.add_column("Ticker", style="green")
    table.add_column("Period", style="dim")
    table.add_column(metric_display, style="bold green")
    table.add_column("Sharpe", style="yellow")
    table.add_column("Max DD", style="red")

    for record in records:
        metric_value = getattr(record, metric)
        if metric in ["max_drawdown", "volatility", "win_rate", "total_return_pct", "cagr"]:
            metric_str = f"{metric_value:.2f}%"
        else:
            metric_str = f"{metric_value:.2f}"

        table.add_row(
            str(record.id),
            record.ticker,
            f"{record.start_date} to {record.end_date}",
            metric_str,
            f"{record.sharpe_ratio:.2f}",
            f"{record.max_drawdown:.2f}%",
        )

    console.print(table)


@history.command(name="delete")
@click.argument("record_id", type=int)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@click.pass_context
def history_delete(ctx: click.Context, record_id: int, yes: bool) -> None:
    """Delete a backtest record."""
    from wheel_backtest.storage import BacktestHistory

    history_db_path = ctx.obj["cache_dir"] / "backtest_history.db"
    history = BacktestHistory(history_db_path)

    record = history.get_backtest(record_id)
    if not record:
        console.print(f"[red]Record ID {record_id} not found.[/red]")
        return

    if not yes:
        console.print(f"\n[yellow]About to delete:[/yellow]")
        console.print(f"  ID: {record.id}")
        console.print(f"  Ticker: {record.ticker}")
        console.print(f"  Date: {record.run_date.strftime('%Y-%m-%d %H:%M')}")
        console.print(f"  Period: {record.start_date} to {record.end_date}")

        if not click.confirm("\nAre you sure?"):
            console.print("[dim]Cancelled.[/dim]")
            return

    if history.delete_backtest(record_id):
        console.print(f"[green]Deleted record #{record_id}[/green]")
    else:
        console.print(f"[red]Failed to delete record #{record_id}[/red]")


def _display_config(config: BacktestConfig) -> None:
    """Display configuration in a formatted table."""
    table = Table(title="Backtest Configuration", show_header=True)
    table.add_column("Parameter", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Ticker", config.ticker)
    table.add_row("Start Date", str(config.start_date) if config.start_date else "Earliest")
    table.add_row("End Date", str(config.end_date) if config.end_date else "Latest")
    table.add_row("Initial Capital", f"${config.initial_capital:,.2f}")
    table.add_row("DTE Target", str(config.dte_target))
    table.add_row("DTE Minimum", str(config.dte_min))

    # Show separate deltas if specified, otherwise show legacy delta_target
    if config.put_delta is not None or config.call_delta is not None:
        table.add_row("Put Delta", f"{config.effective_put_delta:.2f}")
        table.add_row("Call Delta", f"{config.effective_call_delta:.2f}")
    else:
        table.add_row("Delta Target", f"{config.delta_target:.2f}")

    table.add_row("Contract Multiplier", str(config.contract_multiplier))
    table.add_row("Commission", f"${config.commission_per_contract:.2f}")
    table.add_row("Data Provider", config.data_provider)
    table.add_row("Cache Directory", str(config.cache_dir))
    table.add_row("Output Directory", str(config.output_dir))

    console.print(table)


def _display_backtest_summary(result) -> None:
    """Display backtest results summary."""
    from wheel_backtest.engine import BacktestResult

    summary = result.summary
    metrics = result.metrics

    # Strategy summary table
    table = Table(title="Wheel Strategy Summary", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Puts Sold", str(summary["total_puts_sold"]))
    table.add_row("Calls Sold", str(summary["total_calls_sold"]))
    table.add_row("Put Assignments", str(summary["put_assignments"]))
    table.add_row("Call Assignments", str(summary["call_assignments"]))
    table.add_row("Puts Expired OTM", str(summary["puts_expired_otm"]))
    table.add_row("Calls Expired OTM", str(summary["calls_expired_otm"]))
    table.add_row("Total Premium Collected", f"${summary['total_premium_collected']:,.2f}")
    table.add_row("Current State", summary["current_state"])

    console.print("\n")
    console.print(table)

    # Performance metrics table
    days = (result.end_date - result.start_date).days
    years = days / 365.25

    perf_table = Table(title="Performance Metrics", show_header=True)
    perf_table.add_column("Metric", style="cyan")
    perf_table.add_column("Value", style="green")

    perf_table.add_row("Start Date", str(result.start_date))
    perf_table.add_row("End Date", str(result.end_date))
    perf_table.add_row("Trading Days", str(days))
    perf_table.add_row("Years", f"{years:.2f}")
    perf_table.add_row("Initial Capital", f"${result.initial_capital:,.2f}")
    perf_table.add_row("Final Equity", f"${result.final_equity:,.2f}")
    perf_table.add_row("Total Return", f"${metrics.total_return:,.2f}")
    perf_table.add_row("Total Return %", f"{metrics.total_return_pct:.2f}%")
    perf_table.add_row("CAGR", f"{metrics.cagr:.2f}%")
    perf_table.add_row("Volatility (Ann.)", f"{metrics.volatility:.2f}%")
    perf_table.add_row("Sharpe Ratio", f"{metrics.sharpe_ratio:.2f}")
    perf_table.add_row("Sortino Ratio", f"{metrics.sortino_ratio:.2f}")
    perf_table.add_row("Max Drawdown", f"{metrics.max_drawdown:.2f}%")
    perf_table.add_row("Max DD Duration", f"{metrics.max_drawdown_duration} days")
    perf_table.add_row("Calmar Ratio", f"{metrics.calmar_ratio:.2f}")
    perf_table.add_row("Win Rate", f"{metrics.win_rate:.2f}%")
    perf_table.add_row("Profit Factor", f"{metrics.profit_factor:.2f}")

    console.print(perf_table)


if __name__ == "__main__":
    main()
