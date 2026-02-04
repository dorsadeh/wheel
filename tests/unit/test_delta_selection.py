"""Tests for delta-based strike selection."""

from datetime import date

import pandas as pd
import pytest

from wheel_backtest.engine.options import OptionSelector
from wheel_backtest.engine.portfolio import OptionType


class TestDeltaBasedSelection:
    """Tests for delta-based strike selection."""

    @pytest.fixture
    def options_with_delta(self) -> pd.DataFrame:
        """Create mock options chain with delta values."""
        return pd.DataFrame({
            "expiration": [pd.Timestamp("2024-02-01")] * 10,
            "strike": [440.0, 445.0, 450.0, 455.0, 460.0, 465.0, 470.0, 475.0, 480.0, 485.0],
            "option_type": ["put"] * 5 + ["call"] * 5,
            "bid": [8.0, 6.0, 4.5, 3.0, 2.0, 2.0, 3.0, 4.0, 5.5, 7.0],
            "ask": [8.5, 6.5, 5.0, 3.5, 2.5, 2.5, 3.5, 4.5, 6.0, 7.5],
            "delta": [-0.35, -0.28, -0.20, -0.14, -0.08, 0.08, 0.14, 0.20, 0.28, 0.35],
        })

    @pytest.fixture
    def options_without_delta(self) -> pd.DataFrame:
        """Create mock options chain without delta values."""
        return pd.DataFrame({
            "expiration": [pd.Timestamp("2024-02-01")] * 6,
            "strike": [440.0, 445.0, 450.0, 470.0, 475.0, 480.0],
            "option_type": ["put"] * 3 + ["call"] * 3,
            "bid": [8.0, 6.0, 4.5, 3.0, 4.0, 5.5],
            "ask": [8.5, 6.5, 5.0, 3.5, 4.5, 6.0],
        })

    def test_delta_selector_initialization(self) -> None:
        """Test OptionSelector initialization with delta."""
        selector = OptionSelector(
            dte_target=30,
            dte_min=7,
            delta_target=0.20,
        )

        assert selector.delta_target == 0.20
        assert selector.dte_target == 30
        # OTM pct should be auto-calculated from delta
        assert selector.otm_pct == pytest.approx(0.05)

    def test_selector_with_separate_deltas(self) -> None:
        """Test OptionSelector initialization with separate put and call deltas."""
        selector = OptionSelector(
            dte_target=30,
            dte_min=7,
            put_delta=0.30,
            call_delta=0.15,
        )

        assert selector.put_delta == 0.30
        assert selector.call_delta == 0.15

    def test_selector_separate_deltas_override_target(self) -> None:
        """Test that separate deltas override delta_target."""
        selector = OptionSelector(
            delta_target=0.20,
            put_delta=0.30,
            call_delta=0.15,
        )

        assert selector.put_delta == 0.30
        assert selector.call_delta == 0.15

    def test_selector_fallback_to_delta_target(self) -> None:
        """Test that separate deltas fall back to delta_target when not set."""
        selector = OptionSelector(delta_target=0.25)

        assert selector.put_delta == 0.25
        assert selector.call_delta == 0.25

    def test_select_put_by_delta(self, options_with_delta: pd.DataFrame) -> None:
        """Test selecting put strike by delta."""
        selector = OptionSelector(delta_target=0.20)

        put_chain = options_with_delta[options_with_delta["option_type"] == "put"]

        strike = selector.select_strike_by_delta(
            options_df=put_chain,
            option_type=OptionType.PUT,
            target_delta=0.20,
            underlying_price=460.0,
        )

        # Should select strike with delta closest to -0.20
        assert strike == 450.0

    def test_select_call_by_delta(self, options_with_delta: pd.DataFrame) -> None:
        """Test selecting call strike by delta."""
        selector = OptionSelector(delta_target=0.20)

        call_chain = options_with_delta[options_with_delta["option_type"] == "call"]

        strike = selector.select_strike_by_delta(
            options_df=call_chain,
            option_type=OptionType.CALL,
            target_delta=0.20,
            underlying_price=460.0,
        )

        # Should select strike with delta closest to +0.20
        assert strike == 475.0

    def test_select_put_with_higher_delta(self, options_with_delta: pd.DataFrame) -> None:
        """Test selecting put with higher delta (closer to ATM)."""
        selector = OptionSelector(delta_target=0.30)

        put_chain = options_with_delta[options_with_delta["option_type"] == "put"]

        strike = selector.select_strike_by_delta(
            options_df=put_chain,
            option_type=OptionType.PUT,
            target_delta=0.30,
            underlying_price=460.0,
        )

        # Should select strike with delta closest to -0.30
        assert strike == 445.0  # Delta = -0.28

    def test_select_call_with_cost_basis(self, options_with_delta: pd.DataFrame) -> None:
        """Test that cost basis is respected for covered calls."""
        selector = OptionSelector(delta_target=0.20)

        call_chain = options_with_delta[options_with_delta["option_type"] == "call"]

        # Cost basis at 478, should not select strikes below it
        strike = selector.select_strike_by_delta(
            options_df=call_chain,
            option_type=OptionType.CALL,
            target_delta=0.20,
            underlying_price=460.0,
            cost_basis=478.0,
        )

        # Should select 480 (delta=0.28) instead of 475 (delta=0.20)
        # because cost basis constraint filters out 475
        assert strike == 480.0

    def test_fallback_to_otm_when_no_delta(self, options_without_delta: pd.DataFrame) -> None:
        """Test fallback to OTM selection when delta unavailable."""
        selector = OptionSelector(
            delta_target=0.20,
            dte_target=30,
            dte_min=7,
        )

        # Try to select using delta (should fail and fall back)
        put_chain = options_without_delta[options_without_delta["option_type"] == "put"]

        strike = selector.select_strike_by_delta(
            options_df=put_chain,
            option_type=OptionType.PUT,
            target_delta=0.20,
            underlying_price=460.0,
        )

        # Should return None when delta not available
        assert strike is None

    def test_select_option_from_chain_with_delta(self, options_with_delta: pd.DataFrame) -> None:
        """Test full option selection from chain using delta."""
        selector = OptionSelector(
            dte_target=30,
            dte_min=7,
            delta_target=0.20,
        )

        result = selector.select_option_from_chain(
            chain=options_with_delta,
            option_type=OptionType.PUT,
            underlying_price=460.0,
            trade_date=date(2024, 1, 2),
        )

        assert result is not None
        assert result["strike"] == 450.0  # Delta = -0.20
        assert result["option_type"] == OptionType.PUT
        assert result["delta"] == -0.20

    def test_select_option_from_chain_fallback(self, options_without_delta: pd.DataFrame) -> None:
        """Test that selection falls back to OTM when delta unavailable."""
        selector = OptionSelector(
            dte_target=30,
            dte_min=7,
            delta_target=0.20,
            otm_pct=0.05,  # 5% OTM
        )

        result = selector.select_option_from_chain(
            chain=options_without_delta,
            option_type=OptionType.PUT,
            underlying_price=460.0,
            trade_date=date(2024, 1, 2),
        )

        assert result is not None
        # Should use OTM selection: 5% below 460 = 437, closest is 450
        assert result["strike"] in [440.0, 445.0, 450.0]
        assert result["delta"] is None  # No delta in data

    def test_empty_chain_returns_none(self) -> None:
        """Test that empty chain returns None."""
        selector = OptionSelector(delta_target=0.20)

        empty_chain = pd.DataFrame()

        strike = selector.select_strike_by_delta(
            options_df=empty_chain,
            option_type=OptionType.PUT,
            target_delta=0.20,
            underlying_price=460.0,
        )

        assert strike is None

    def test_no_otm_options_returns_none(self, options_with_delta: pd.DataFrame) -> None:
        """Test that no valid OTM options returns None."""
        selector = OptionSelector(delta_target=0.20)

        call_chain = options_with_delta[options_with_delta["option_type"] == "call"]

        # Underlying way above all strikes - no OTM calls available
        strike = selector.select_strike_by_delta(
            options_df=call_chain,
            option_type=OptionType.CALL,
            target_delta=0.20,
            underlying_price=500.0,
        )

        assert strike is None

    def test_different_delta_targets(self, options_with_delta: pd.DataFrame) -> None:
        """Test selection with various delta targets."""
        put_chain = options_with_delta[options_with_delta["option_type"] == "put"]

        # Test 0.10 delta (further OTM)
        selector_10 = OptionSelector(delta_target=0.10)
        strike_10 = selector_10.select_strike_by_delta(
            put_chain, OptionType.PUT, 0.10, 460.0
        )
        assert strike_10 == 460.0  # Delta = -0.08, closest to -0.10

        # Test 0.30 delta (closer to ATM)
        selector_30 = OptionSelector(delta_target=0.30)
        strike_30 = selector_30.select_strike_by_delta(
            put_chain, OptionType.PUT, 0.30, 460.0
        )
        assert strike_30 == 445.0  # Delta = -0.28, closest to -0.30

    def test_otm_pct_defaults_from_delta(self) -> None:
        """Test that OTM percentage is calculated from delta when not provided."""
        selector = OptionSelector(delta_target=0.20)
        assert selector.otm_pct == pytest.approx(0.05)

        selector = OptionSelector(delta_target=0.30)
        assert selector.otm_pct == pytest.approx(0.075)

    def test_explicit_otm_pct_overrides_default(self) -> None:
        """Test that explicit OTM pct overrides delta-based default."""
        selector = OptionSelector(delta_target=0.20, otm_pct=0.10)
        assert selector.otm_pct == 0.10  # Explicit value used

    def test_separate_deltas_for_puts_and_calls(self, options_with_delta: pd.DataFrame) -> None:
        """Test that different deltas are used for puts vs calls."""
        selector = OptionSelector(
            dte_target=30,
            dte_min=7,
            put_delta=0.30,  # Higher delta for puts (closer to ATM)
            call_delta=0.15,  # Lower delta for calls (further OTM)
        )

        # Test put selection with 0.30 delta
        put_result = selector.select_option_from_chain(
            chain=options_with_delta,
            option_type=OptionType.PUT,
            underlying_price=460.0,
            trade_date=date(2024, 1, 2),
        )
        assert put_result is not None
        assert put_result["strike"] == 445.0  # Delta = -0.28, closest to -0.30

        # Test call selection with 0.15 delta
        call_result = selector.select_option_from_chain(
            chain=options_with_delta,
            option_type=OptionType.CALL,
            underlying_price=460.0,
            trade_date=date(2024, 1, 2),
        )
        assert call_result is not None
        assert call_result["strike"] == 470.0  # Delta = 0.14, closest to 0.15
