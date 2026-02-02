"""Tests for portfolio management."""

from datetime import date

import pytest

from wheel_backtest.engine.portfolio import (
    OptionPosition,
    OptionType,
    Portfolio,
    PositionSide,
)


class TestOptionPosition:
    """Tests for OptionPosition."""

    def test_is_short(self) -> None:
        """Test is_short property."""
        short_put = OptionPosition(
            option_type=OptionType.PUT,
            side=PositionSide.SHORT,
            strike=100.0,
            expiration=date(2024, 1, 19),
            quantity=1,
            entry_price=2.50,
            entry_date=date(2024, 1, 2),
            underlying_price_at_entry=105.0,
        )
        assert short_put.is_short is True

        long_call = OptionPosition(
            option_type=OptionType.CALL,
            side=PositionSide.LONG,
            strike=110.0,
            expiration=date(2024, 1, 19),
            quantity=1,
            entry_price=1.50,
            entry_date=date(2024, 1, 2),
            underlying_price_at_entry=105.0,
        )
        assert long_call.is_short is False

    def test_is_itm_put(self) -> None:
        """Test ITM check for puts."""
        put = OptionPosition(
            option_type=OptionType.PUT,
            side=PositionSide.SHORT,
            strike=100.0,
            expiration=date(2024, 1, 19),
            quantity=1,
            entry_price=2.50,
            entry_date=date(2024, 1, 2),
            underlying_price_at_entry=105.0,
        )

        assert put.is_itm(95.0) is True  # Below strike - ITM
        assert put.is_itm(100.0) is False  # At strike - ATM
        assert put.is_itm(105.0) is False  # Above strike - OTM

    def test_is_itm_call(self) -> None:
        """Test ITM check for calls."""
        call = OptionPosition(
            option_type=OptionType.CALL,
            side=PositionSide.SHORT,
            strike=110.0,
            expiration=date(2024, 1, 19),
            quantity=1,
            entry_price=1.50,
            entry_date=date(2024, 1, 2),
            underlying_price_at_entry=105.0,
        )

        assert call.is_itm(115.0) is True  # Above strike - ITM
        assert call.is_itm(110.0) is False  # At strike - ATM
        assert call.is_itm(105.0) is False  # Below strike - OTM

    def test_intrinsic_value(self) -> None:
        """Test intrinsic value calculation."""
        put = OptionPosition(
            option_type=OptionType.PUT,
            side=PositionSide.SHORT,
            strike=100.0,
            expiration=date(2024, 1, 19),
            quantity=1,
            entry_price=2.50,
            entry_date=date(2024, 1, 2),
            underlying_price_at_entry=105.0,
        )

        assert put.intrinsic_value(95.0) == 5.0  # ITM by $5
        assert put.intrinsic_value(100.0) == 0.0  # ATM
        assert put.intrinsic_value(105.0) == 0.0  # OTM

        call = OptionPosition(
            option_type=OptionType.CALL,
            side=PositionSide.SHORT,
            strike=100.0,
            expiration=date(2024, 1, 19),
            quantity=1,
            entry_price=3.00,
            entry_date=date(2024, 1, 2),
            underlying_price_at_entry=102.0,
        )

        assert call.intrinsic_value(105.0) == 5.0  # ITM by $5
        assert call.intrinsic_value(100.0) == 0.0  # ATM
        assert call.intrinsic_value(95.0) == 0.0  # OTM

    def test_is_expired(self) -> None:
        """Test expiration check."""
        position = OptionPosition(
            option_type=OptionType.PUT,
            side=PositionSide.SHORT,
            strike=100.0,
            expiration=date(2024, 1, 19),
            quantity=1,
            entry_price=2.50,
            entry_date=date(2024, 1, 2),
            underlying_price_at_entry=105.0,
        )

        assert position.is_expired(date(2024, 1, 18)) is False
        assert position.is_expired(date(2024, 1, 19)) is True
        assert position.is_expired(date(2024, 1, 20)) is True


class TestPortfolio:
    """Tests for Portfolio."""

    def test_initial_state(self) -> None:
        """Test initial portfolio state."""
        portfolio = Portfolio()
        assert portfolio.cash == 0.0
        assert portfolio.shares == 0
        assert len(portfolio.option_positions) == 0

    def test_deposit(self) -> None:
        """Test depositing cash."""
        portfolio = Portfolio()
        portfolio.deposit(100_000.0)
        assert portfolio.cash == 100_000.0

    def test_deposit_negative_raises(self) -> None:
        """Test that negative deposit raises error."""
        portfolio = Portfolio()
        with pytest.raises(ValueError, match="positive"):
            portfolio.deposit(-1000.0)

    def test_withdraw(self) -> None:
        """Test withdrawing cash."""
        portfolio = Portfolio(cash=100_000.0)
        portfolio.withdraw(25_000.0)
        assert portfolio.cash == 75_000.0

    def test_withdraw_insufficient_raises(self) -> None:
        """Test that insufficient cash raises error."""
        portfolio = Portfolio(cash=1_000.0)
        with pytest.raises(ValueError, match="Insufficient cash"):
            portfolio.withdraw(5_000.0)

    def test_buy_shares(self) -> None:
        """Test buying shares."""
        portfolio = Portfolio(cash=100_000.0)
        cost = portfolio.buy_shares(100, 450.0)

        assert cost == 45_000.0
        assert portfolio.shares == 100
        assert portfolio.cash == 55_000.0

    def test_buy_shares_with_commission(self) -> None:
        """Test buying shares with commission."""
        portfolio = Portfolio(cash=100_000.0)
        cost = portfolio.buy_shares(100, 450.0, commission=10.0)

        assert cost == 45_010.0
        assert portfolio.shares == 100
        assert portfolio.cash == 54_990.0

    def test_buy_shares_insufficient_cash(self) -> None:
        """Test buying shares with insufficient cash."""
        portfolio = Portfolio(cash=1_000.0)
        with pytest.raises(ValueError, match="Insufficient cash"):
            portfolio.buy_shares(100, 450.0)

    def test_sell_shares(self) -> None:
        """Test selling shares."""
        portfolio = Portfolio(cash=10_000.0, shares=100)
        proceeds = portfolio.sell_shares(50, 460.0)

        assert proceeds == 23_000.0
        assert portfolio.shares == 50
        assert portfolio.cash == 33_000.0

    def test_sell_shares_insufficient(self) -> None:
        """Test selling more shares than owned."""
        portfolio = Portfolio(cash=10_000.0, shares=50)
        with pytest.raises(ValueError, match="Insufficient shares"):
            portfolio.sell_shares(100, 460.0)

    def test_open_short_put(self) -> None:
        """Test opening a short put position."""
        portfolio = Portfolio(cash=100_000.0)

        position = portfolio.open_short_option(
            option_type=OptionType.PUT,
            strike=450.0,
            expiration=date(2024, 1, 19),
            quantity=1,
            premium_per_share=5.00,
            trade_date=date(2024, 1, 2),
            underlying_price=472.0,
            delta=-0.20,
        )

        # Received $500 premium (5.00 * 100)
        assert portfolio.cash == 100_500.0
        assert len(portfolio.option_positions) == 1
        assert position.is_short
        assert position.is_put
        assert position.strike == 450.0

    def test_open_short_call(self) -> None:
        """Test opening a short call position."""
        portfolio = Portfolio(cash=10_000.0, shares=100)

        position = portfolio.open_short_option(
            option_type=OptionType.CALL,
            strike=480.0,
            expiration=date(2024, 1, 19),
            quantity=1,
            premium_per_share=3.50,
            trade_date=date(2024, 1, 2),
            underlying_price=472.0,
            delta=0.30,
        )

        # Received $350 premium
        assert portfolio.cash == 10_350.0
        assert len(portfolio.option_positions) == 1
        assert position.is_call

    def test_expire_option_worthless(self) -> None:
        """Test option expiring worthless."""
        portfolio = Portfolio(cash=100_000.0)

        # Open short put
        position = portfolio.open_short_option(
            option_type=OptionType.PUT,
            strike=450.0,
            expiration=date(2024, 1, 19),
            quantity=1,
            premium_per_share=5.00,
            trade_date=date(2024, 1, 2),
            underlying_price=472.0,
        )

        initial_cash = portfolio.cash  # 100,500 after premium

        # Expire worthless
        pnl = portfolio.expire_option_worthless(position)

        # P&L is the premium kept
        assert pnl == 500.0
        assert portfolio.cash == initial_cash  # Cash unchanged (already received)
        assert len(portfolio.option_positions) == 0

    def test_put_assignment(self) -> None:
        """Test put assignment (buying shares at strike)."""
        portfolio = Portfolio(cash=100_000.0)

        # Open short put at 450 strike
        position = portfolio.open_short_option(
            option_type=OptionType.PUT,
            strike=450.0,
            expiration=date(2024, 1, 19),
            quantity=1,
            premium_per_share=5.00,
            trade_date=date(2024, 1, 2),
            underlying_price=472.0,
        )

        # Cash now 100,500
        # Assignment - buy 100 shares at $450 = $45,000
        pnl = portfolio.exercise_put_assignment(position, underlying_price=440.0)

        assert portfolio.shares == 100
        assert portfolio.cash == pytest.approx(55_500.0)  # 100,500 - 45,000
        assert len(portfolio.option_positions) == 0

    def test_call_assignment(self) -> None:
        """Test call assignment (selling shares at strike)."""
        portfolio = Portfolio(cash=10_000.0, shares=100)

        # Open short call at 480 strike
        position = portfolio.open_short_option(
            option_type=OptionType.CALL,
            strike=480.0,
            expiration=date(2024, 1, 19),
            quantity=1,
            premium_per_share=3.50,
            trade_date=date(2024, 1, 2),
            underlying_price=472.0,
        )

        # Cash now 10,350
        # Assignment - sell 100 shares at $480 = $48,000
        pnl = portfolio.exercise_call_assignment(position, underlying_price=490.0)

        assert portfolio.shares == 0
        assert portfolio.cash == pytest.approx(58_350.0)  # 10,350 + 48,000
        assert len(portfolio.option_positions) == 0
        # P&L is just the premium (we "lose" upside above strike)
        assert pnl == 350.0

    def test_get_equity(self) -> None:
        """Test equity calculation."""
        portfolio = Portfolio(cash=50_000.0, shares=100)

        equity = portfolio.get_equity(underlying_price=450.0)

        assert equity == 95_000.0  # 50,000 + 100*450

    def test_get_buying_power_with_short_puts(self) -> None:
        """Test buying power calculation with short puts."""
        portfolio = Portfolio(cash=100_000.0)

        # Open short put at 450 strike
        portfolio.open_short_option(
            option_type=OptionType.PUT,
            strike=450.0,
            expiration=date(2024, 1, 19),
            quantity=1,
            premium_per_share=5.00,
            trade_date=date(2024, 1, 2),
            underlying_price=472.0,
        )

        # Cash is 100,500, but 45,000 is reserved for the put
        buying_power = portfolio.get_buying_power()
        assert buying_power == pytest.approx(55_500.0)

    def test_get_short_puts_and_calls(self) -> None:
        """Test filtering positions by type."""
        portfolio = Portfolio(cash=100_000.0, shares=100)

        # Open a short put
        portfolio.open_short_option(
            option_type=OptionType.PUT,
            strike=450.0,
            expiration=date(2024, 1, 19),
            quantity=1,
            premium_per_share=5.00,
            trade_date=date(2024, 1, 2),
            underlying_price=472.0,
        )

        # Open a short call
        portfolio.open_short_option(
            option_type=OptionType.CALL,
            strike=490.0,
            expiration=date(2024, 1, 19),
            quantity=1,
            premium_per_share=3.00,
            trade_date=date(2024, 1, 2),
            underlying_price=472.0,
        )

        assert len(portfolio.get_short_puts()) == 1
        assert len(portfolio.get_short_calls()) == 1
        assert portfolio.get_short_puts()[0].strike == 450.0
        assert portfolio.get_short_calls()[0].strike == 490.0
