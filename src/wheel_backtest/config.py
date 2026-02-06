"""Configuration management for the wheel backtester."""

from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BacktestConfig(BaseSettings):
    """Configuration for a wheel strategy backtest run."""

    model_config = SettingsConfigDict(
        env_prefix="WHEEL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core parameters
    ticker: str = Field(default="SPY", description="Ticker symbol to backtest")
    start_date: date | None = Field(default=None, description="Start date (None = earliest)")
    end_date: date | None = Field(default=None, description="End date (None = latest)")
    initial_capital: float = Field(default=100_000.0, gt=0, description="Starting capital in USD")

    # Options parameters
    dte_target: int = Field(default=30, ge=1, description="Target days to expiration")
    dte_min: int = Field(default=7, ge=1, description="Minimum DTE to consider")
    delta_target: float = Field(
        default=0.20, gt=0, lt=1, description="Target delta for short options (legacy, use put_delta/call_delta)"
    )
    put_delta: float | None = Field(
        default=None, gt=0, lt=1, description="Target delta for short puts (overrides delta_target)"
    )
    call_delta: float | None = Field(
        default=None, gt=0, lt=1, description="Target delta for short calls (overrides delta_target)"
    )
    contract_multiplier: int = Field(default=100, gt=0, description="Shares per contract")

    # Cost parameters
    commission_per_contract: float = Field(
        default=0.0, ge=0, description="Commission per contract in USD"
    )

    # Risk management
    enable_call_entry_protection: bool = Field(
        default=False,
        description="Enable dual protection: (1) wait until underlying recovers, (2) ensure strikes never below cost basis",
    )
    call_entry_protection_dollars: float = Field(
        default=0.0,
        ge=0,
        description="Only sell calls when underlying is within this $ of cost basis. Strikes always at or above cost basis (e.g., $50 with $300 assignment: sell when underlying ≥ $250, strikes ≥ $300)",
    )

    # Data provider settings
    data_provider: Literal["philippdubach"] = Field(
        default="philippdubach", description="Options data provider"
    )
    cache_dir: Path = Field(default=Path("./cache"), description="Directory for cached data")

    # Output settings
    output_dir: Path = Field(default=Path("./output"), description="Directory for output files")

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        """Normalize ticker to uppercase."""
        return v.upper().strip()

    @field_validator("cache_dir", "output_dir")
    @classmethod
    def create_directories(cls, v: Path) -> Path:
        """Ensure directories exist."""
        v.mkdir(parents=True, exist_ok=True)
        return v

    @field_validator("end_date")
    @classmethod
    def validate_date_order(cls, v: date | None, info) -> date | None:
        """Ensure end_date is after start_date if both are provided."""
        start = info.data.get("start_date")
        if v is not None and start is not None and v < start:
            raise ValueError("end_date must be after start_date")
        return v

    @property
    def effective_put_delta(self) -> float:
        """Get the effective put delta (put_delta if set, else delta_target)."""
        return self.put_delta if self.put_delta is not None else self.delta_target

    @property
    def effective_call_delta(self) -> float:
        """Get the effective call delta (call_delta if set, else delta_target)."""
        return self.call_delta if self.call_delta is not None else self.delta_target


def load_config(**overrides) -> BacktestConfig:
    """Load configuration with optional overrides.

    Args:
        **overrides: Key-value pairs to override default/env settings.

    Returns:
        Configured BacktestConfig instance.
    """
    return BacktestConfig(**overrides)
