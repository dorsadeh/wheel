"""Tests for chart generation."""

from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for testing
import matplotlib.pyplot as plt
import pytest

from wheel_backtest.analytics.equity import EquityCurve
from wheel_backtest.reports.charts import (
    create_benchmark_report,
    plot_drawdown,
    plot_equity_comparison,
    plot_equity_curve,
    plot_returns_comparison,
)


@pytest.fixture
def sample_curve() -> EquityCurve:
    """Create a sample equity curve for testing."""
    curve = EquityCurve()
    curve.add_point(date(2024, 1, 2), 100_000.0, 0.0)
    curve.add_point(date(2024, 1, 3), 101_000.0, 0.0)
    curve.add_point(date(2024, 1, 4), 99_000.0, 0.0)
    curve.add_point(date(2024, 1, 5), 102_000.0, 0.0)
    curve.add_point(date(2024, 1, 8), 103_000.0, 0.0)
    return curve


class TestPlotEquityCurve:
    """Tests for plot_equity_curve function."""

    def test_creates_figure(self, sample_curve: EquityCurve) -> None:
        """Test that function returns a figure."""
        fig = plot_equity_curve(sample_curve)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_saves_to_file(self, sample_curve: EquityCurve, temp_dir: Path) -> None:
        """Test saving chart to file."""
        output_path = temp_dir / "equity.png"
        fig = plot_equity_curve(sample_curve, output_path=output_path)

        assert output_path.exists()
        assert output_path.stat().st_size > 0
        plt.close(fig)

    def test_custom_title(self, sample_curve: EquityCurve) -> None:
        """Test custom title."""
        fig = plot_equity_curve(sample_curve, title="My Custom Title")
        ax = fig.axes[0]
        assert ax.get_title() == "My Custom Title"
        plt.close(fig)


class TestPlotEquityComparison:
    """Tests for plot_equity_comparison function."""

    def test_multiple_curves(self, sample_curve: EquityCurve) -> None:
        """Test plotting multiple curves."""
        # Create second curve
        curve2 = EquityCurve()
        curve2.add_point(date(2024, 1, 2), 100_000.0, 0.0)
        curve2.add_point(date(2024, 1, 3), 100_500.0, 0.0)
        curve2.add_point(date(2024, 1, 4), 101_000.0, 0.0)
        curve2.add_point(date(2024, 1, 5), 101_500.0, 0.0)
        curve2.add_point(date(2024, 1, 8), 102_000.0, 0.0)

        curves = {
            "Strategy A": sample_curve,
            "Strategy B": curve2,
        }

        fig = plot_equity_comparison(curves)
        ax = fig.axes[0]

        # Should have 2 lines
        assert len(ax.lines) == 2
        plt.close(fig)

    def test_saves_to_file(self, sample_curve: EquityCurve, temp_dir: Path) -> None:
        """Test saving comparison chart."""
        curves = {"Test": sample_curve}
        output_path = temp_dir / "comparison.png"

        fig = plot_equity_comparison(curves, output_path=output_path)

        assert output_path.exists()
        plt.close(fig)


class TestPlotReturnsComparison:
    """Tests for plot_returns_comparison function."""

    def test_returns_as_percentage(self, sample_curve: EquityCurve) -> None:
        """Test that returns are shown as percentages."""
        curves = {"Test": sample_curve}
        fig = plot_returns_comparison(curves)
        ax = fig.axes[0]

        assert "%" in ax.get_ylabel()
        plt.close(fig)


class TestPlotDrawdown:
    """Tests for plot_drawdown function."""

    def test_creates_drawdown_chart(self, sample_curve: EquityCurve) -> None:
        """Test drawdown chart creation."""
        fig = plot_drawdown(sample_curve)
        ax = fig.axes[0]

        assert "Drawdown" in ax.get_ylabel()
        plt.close(fig)

    def test_saves_to_file(self, sample_curve: EquityCurve, temp_dir: Path) -> None:
        """Test saving drawdown chart."""
        output_path = temp_dir / "drawdown.png"
        fig = plot_drawdown(sample_curve, output_path=output_path)

        assert output_path.exists()
        plt.close(fig)


class TestCreateBenchmarkReport:
    """Tests for create_benchmark_report function."""

    def test_creates_all_files(self, sample_curve: EquityCurve, temp_dir: Path) -> None:
        """Test that report creates all expected files."""
        output_dir = temp_dir / "output"

        charts = create_benchmark_report(
            benchmark_curve=sample_curve,
            ticker="SPY",
            initial_capital=100_000.0,
            output_dir=output_dir,
        )

        assert "equity" in charts
        assert "drawdown" in charts
        assert "data" in charts

        assert charts["equity"].exists()
        assert charts["drawdown"].exists()
        assert charts["data"].exists()

        # Check data CSV
        assert charts["data"].suffix == ".csv"

    def test_creates_output_directory(self, sample_curve: EquityCurve, temp_dir: Path) -> None:
        """Test that output directory is created if missing."""
        output_dir = temp_dir / "nonexistent" / "output"
        assert not output_dir.exists()

        create_benchmark_report(
            benchmark_curve=sample_curve,
            ticker="SPY",
            initial_capital=100_000.0,
            output_dir=output_dir,
        )

        assert output_dir.exists()
