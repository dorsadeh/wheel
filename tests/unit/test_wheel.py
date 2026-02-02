"""Tests for wheel strategy state machine."""

from datetime import date

import pandas as pd
import pytest

from wheel_backtest.engine.options import OptionSelector
from wheel_backtest.engine.portfolio import OptionType, Portfolio
from wheel_backtest.engine.wheel import WheelState, WheelStrategy


def create_mock_chain(
    trade_date: date,
    underlying_price: float,
    put_strikes: list[float] = None,
    call_strikes: list[float] = None,
    dte: int = 30,
) -> pd.DataFrame:
    """Create a mock options chain for testing."""
    if put_strikes is None:
        put_strikes = [underlying_price * 0.95, underlying_price * 0.90]
    if call_strikes is None:
        call_strikes = [underlying_price * 1.05, underlying_price * 1.10]

    expiration = pd.Timestamp(trade_date) + pd.Timedelta(days=dte)

    rows = []
    for strike in put_strikes:
        rows.append({
            "expiration": expiration,
            "strike": strike,
            "option_type": "put",
            "bid": 4.50,
            "ask": 5.00,
            "delta": -0.25,
        })
    for strike in call_strikes:
        rows.append({
            "expiration": expiration,
            "strike": strike,
            "option_type": "call",
            "bid": 3.00,
            "ask": 3.50,
            "delta": 0.25,
        })

    return pd.DataFrame(rows)


class TestWheelStrategy:
    """Tests for WheelStrategy."""

    def test_initial_state(self) -> None:
        """Test initial state is SELLING_PUTS."""
        portfolio = Portfolio(cash=100_000.0)
        selector = OptionSelector(dte_target=30, otm_pct=0.05)
        strategy = WheelStrategy(portfolio, selector)

        assert strategy.state == WheelState.SELLING_PUTS

    def test_sell_put_on_first_day(self) -> None:
        """Test selling a put on the first day."""
        portfolio = Portfolio(cash=100_000.0)
        selector = OptionSelector(dte_target=30, dte_min=7, otm_pct=0.05)
        strategy = WheelStrategy(portfolio, selector, contracts_per_trade=1)

        chain = create_mock_chain(date(2024, 1, 2), 472.0)

        events = strategy.process_day(date(2024, 1, 2), 472.0, chain)

        assert len(events) == 1
        assert events[0].event_type == "sell_put"
        assert strategy.state == WheelState.SELLING_PUTS
        assert len(portfolio.get_short_puts()) == 1

    def test_put_expires_worthless(self) -> None:
        """Test put expiring OTM (worthless)."""
        portfolio = Portfolio(cash=100_000.0)
        selector = OptionSelector(dte_target=30, dte_min=7, otm_pct=0.05)
        strategy = WheelStrategy(portfolio, selector)

        # Day 1: Sell put
        chain = create_mock_chain(date(2024, 1, 2), 472.0, dte=17)
        strategy.process_day(date(2024, 1, 2), 472.0, chain)

        initial_cash = portfolio.cash
        put_position = portfolio.get_short_puts()[0]

        # Expiration day: underlying still above strike (OTM)
        chain_exp = create_mock_chain(date(2024, 1, 19), 475.0)
        events = strategy.process_day(date(2024, 1, 19), 475.0, chain_exp)

        # Should have expiration event and new put sale
        expired_events = [e for e in events if e.event_type == "put_expired"]
        assert len(expired_events) == 1

        # No shares acquired
        assert portfolio.shares == 0
        assert strategy.state == WheelState.SELLING_PUTS

    def test_put_assigned(self) -> None:
        """Test put being assigned (ITM at expiration)."""
        portfolio = Portfolio(cash=100_000.0)
        selector = OptionSelector(dte_target=30, dte_min=7, otm_pct=0.05)
        strategy = WheelStrategy(portfolio, selector)

        # Day 1: Sell put at ~448 strike (5% OTM from 472)
        chain = create_mock_chain(
            date(2024, 1, 2), 472.0,
            put_strikes=[448.0, 440.0],
            dte=17,
        )
        strategy.process_day(date(2024, 1, 2), 472.0, chain)

        # Expiration day: underlying drops below strike (ITM)
        chain_exp = create_mock_chain(date(2024, 1, 19), 440.0)
        events = strategy.process_day(date(2024, 1, 19), 440.0, chain_exp)

        # Should have assignment
        assigned_events = [e for e in events if e.event_type == "put_assigned"]
        assert len(assigned_events) == 1

        # Should now hold shares and immediately sell a call
        assert portfolio.shares == 100
        # Strategy immediately sells call after assignment
        assert strategy.state == WheelState.SELLING_CALLS

    def test_sell_call_after_assignment(self) -> None:
        """Test selling call after put assignment."""
        portfolio = Portfolio(cash=100_000.0)
        selector = OptionSelector(dte_target=30, dte_min=7, otm_pct=0.05)
        strategy = WheelStrategy(portfolio, selector)

        # Set up: already holding stock
        portfolio.buy_shares(100, 450.0)
        strategy._state = WheelState.HOLDING_STOCK
        strategy._cost_basis = 450.0

        # Sell call
        chain = create_mock_chain(
            date(2024, 1, 22), 455.0,
            call_strikes=[475.0, 480.0],
        )
        events = strategy.process_day(date(2024, 1, 22), 455.0, chain)

        assert len(events) == 1
        assert events[0].event_type == "sell_call"
        assert strategy.state == WheelState.SELLING_CALLS
        assert len(portfolio.get_short_calls()) == 1

    def test_call_expires_worthless(self) -> None:
        """Test call expiring OTM (worthless)."""
        portfolio = Portfolio(cash=50_000.0, shares=100)
        selector = OptionSelector(dte_target=30, dte_min=7, otm_pct=0.05)
        strategy = WheelStrategy(portfolio, selector)
        strategy._state = WheelState.HOLDING_STOCK
        strategy._cost_basis = 450.0

        # Sell call at 475 strike
        chain = create_mock_chain(
            date(2024, 1, 22), 455.0,
            call_strikes=[475.0, 480.0],
            dte=17,
        )
        strategy.process_day(date(2024, 1, 22), 455.0, chain)

        # Expiration: underlying still below strike
        chain_exp = create_mock_chain(date(2024, 2, 9), 465.0)
        events = strategy.process_day(date(2024, 2, 9), 465.0, chain_exp)

        # Call expired worthless
        expired = [e for e in events if e.event_type == "call_expired"]
        assert len(expired) == 1

        # Still holding stock, immediately sells another call
        assert portfolio.shares == 100
        assert strategy.state == WheelState.SELLING_CALLS

    def test_call_assigned(self) -> None:
        """Test call being assigned (ITM at expiration)."""
        portfolio = Portfolio(cash=50_000.0, shares=100)
        selector = OptionSelector(dte_target=30, dte_min=7, otm_pct=0.05)
        strategy = WheelStrategy(portfolio, selector)
        strategy._state = WheelState.HOLDING_STOCK
        strategy._cost_basis = 450.0

        # Sell call at 475 strike
        chain = create_mock_chain(
            date(2024, 1, 22), 455.0,
            call_strikes=[475.0, 480.0],
            dte=17,
        )
        strategy.process_day(date(2024, 1, 22), 455.0, chain)

        # Expiration: underlying above strike
        chain_exp = create_mock_chain(date(2024, 2, 9), 485.0)
        events = strategy.process_day(date(2024, 2, 9), 485.0, chain_exp)

        # Call assigned
        assigned = [e for e in events if e.event_type == "call_assigned"]
        assert len(assigned) == 1

        # Shares sold, back to selling puts
        assert portfolio.shares == 0
        assert strategy.state == WheelState.SELLING_PUTS

    def test_full_wheel_cycle(self) -> None:
        """Test a complete wheel cycle."""
        portfolio = Portfolio(cash=100_000.0)
        selector = OptionSelector(dte_target=15, dte_min=7, otm_pct=0.05)
        strategy = WheelStrategy(portfolio, selector)

        # Day 1: Sell put
        chain1 = create_mock_chain(date(2024, 1, 2), 472.0, put_strikes=[448.0], dte=17)
        strategy.process_day(date(2024, 1, 2), 472.0, chain1)
        assert strategy.state == WheelState.SELLING_PUTS

        # Expiration: Put assigned, immediately sells call
        chain2 = create_mock_chain(date(2024, 1, 19), 440.0, call_strikes=[465.0], dte=21)
        events = strategy.process_day(date(2024, 1, 19), 440.0, chain2)
        assert strategy.state == WheelState.SELLING_CALLS  # Immediately sells call after assignment
        assert portfolio.shares == 100
        # Should have both assignment and call sale events
        assert any(e.event_type == "put_assigned" for e in events)
        assert any(e.event_type == "sell_call" for e in events)

        # Expiration: Call assigned
        chain4 = create_mock_chain(date(2024, 2, 9), 470.0)
        strategy.process_day(date(2024, 2, 9), 470.0, chain4)
        assert strategy.state == WheelState.SELLING_PUTS
        assert portfolio.shares == 0

    def test_get_summary(self) -> None:
        """Test summary generation."""
        portfolio = Portfolio(cash=100_000.0)
        selector = OptionSelector(dte_target=15, dte_min=7, otm_pct=0.05)
        strategy = WheelStrategy(portfolio, selector)

        # Sell a put
        chain = create_mock_chain(date(2024, 1, 2), 472.0, put_strikes=[448.0], dte=17)
        strategy.process_day(date(2024, 1, 2), 472.0, chain)

        summary = strategy.get_summary()

        assert summary["total_puts_sold"] == 1
        assert summary["total_calls_sold"] == 0
        assert summary["put_assignments"] == 0
        assert summary["current_state"] == "selling_puts"

    def test_insufficient_buying_power(self) -> None:
        """Test that put is not sold without enough buying power."""
        portfolio = Portfolio(cash=10_000.0)  # Not enough for a 448 strike put
        selector = OptionSelector(dte_target=30, dte_min=7, otm_pct=0.05)
        strategy = WheelStrategy(portfolio, selector)

        chain = create_mock_chain(date(2024, 1, 2), 472.0, put_strikes=[448.0])
        events = strategy.process_day(date(2024, 1, 2), 472.0, chain)

        # No put should be sold
        assert len(events) == 0
        assert len(portfolio.get_short_puts()) == 0
