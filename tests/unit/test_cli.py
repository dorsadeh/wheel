"""Tests for the CLI interface."""

from click.testing import CliRunner

from wheel_backtest import __version__
from wheel_backtest.cli import main


class TestCLI:
    """Tests for CLI commands."""

    def test_version(self) -> None:
        """Test --version flag."""
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        assert __version__ in result.output

    def test_help(self) -> None:
        """Test --help flag."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "Wheel Strategy" in result.output
        assert "run" in result.output
        assert "benchmark" in result.output
        assert "config" in result.output

    def test_run_help(self) -> None:
        """Test run command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["run", "--help"])

        assert result.exit_code == 0
        assert "--start" in result.output
        assert "--end" in result.output
        assert "--capital" in result.output
        assert "--dte" in result.output
        assert "--delta" in result.output

    def test_benchmark_help(self) -> None:
        """Test benchmark command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["benchmark", "--help"])

        assert result.exit_code == 0
        assert "--start" in result.output
        assert "--end" in result.output
        assert "--capital" in result.output

    def test_config_command(self) -> None:
        """Test config command displays configuration."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["config"])

            assert result.exit_code == 0
            assert "SPY" in result.output
            assert "100,000" in result.output
            assert "philippdubach" in result.output

    def test_run_with_options(self) -> None:
        """Test run command with custom options."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main,
                [
                    "run",
                    "AAPL",
                    "--start", "2020-01-01",
                    "--end", "2020-12-31",
                    "--capital", "50000",
                    "--dte", "45",
                    "--delta", "0.15",
                ],
            )

            assert result.exit_code == 0
            assert "AAPL" in result.output
            assert "50,000" in result.output

    def test_run_invalid_date(self) -> None:
        """Test run command with invalid date format."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["run", "--start", "invalid-date"])

            assert result.exit_code != 0
            assert "Invalid date format" in result.output

    def test_benchmark_with_ticker(self) -> None:
        """Test benchmark command with custom ticker."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["benchmark", "QQQ"])

            assert result.exit_code == 0
            assert "QQQ" in result.output
