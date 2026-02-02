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
    help="Target delta for short options",
)
@click.option(
    "--commission",
    "commission_per_contract",
    type=float,
    default=0.0,
    help="Commission per contract in USD",
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
    commission_per_contract: float,
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

        # Save transactions to CSV
        transactions_df = backtest.get_transactions_df()
        if not transactions_df.empty:
            config.output_dir.mkdir(parents=True, exist_ok=True)
            transactions_path = config.output_dir / f"{config.ticker}_transactions.csv"
            transactions_df.to_csv(transactions_path, index=False)
            console.print(f"\n[dim]Transactions saved to: {transactions_path}[/dim]")

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

    # Performance table
    total_return = result.final_equity - result.initial_capital
    total_return_pct = (result.final_equity / result.initial_capital - 1) * 100
    days = (result.end_date - result.start_date).days
    years = days / 365.25

    perf_table = Table(title="Performance Summary", show_header=True)
    perf_table.add_column("Metric", style="cyan")
    perf_table.add_column("Value", style="green")

    perf_table.add_row("Start Date", str(result.start_date))
    perf_table.add_row("End Date", str(result.end_date))
    perf_table.add_row("Trading Days", str(days))
    perf_table.add_row("Years", f"{years:.2f}")
    perf_table.add_row("Initial Capital", f"${result.initial_capital:,.2f}")
    perf_table.add_row("Final Equity", f"${result.final_equity:,.2f}")
    perf_table.add_row("Total Return", f"${total_return:,.2f}")
    perf_table.add_row("Total Return %", f"{total_return_pct:.2f}%")

    if years > 0:
        cagr = (pow(result.final_equity / result.initial_capital, 1 / years) - 1) * 100
        perf_table.add_row("CAGR", f"{cagr:.2f}%")

    console.print(perf_table)


if __name__ == "__main__":
    main()
