"""Tests for option selection and order management."""

from datetime import date

import pandas as pd
import pytest

from wheel_backtest.engine.options import (
    Fill,
    OptionOrder,
    OptionSelector,
    OrderAction,
)
from wheel_backtest.engine.portfolio import OptionType


class TestOptionSelector:
    """Tests for OptionSelector."""

    def test_select_expiration_closest_to_target(self) -> None:
        """Test expiration selection finds closest to target DTE."""
        selector = OptionSelector(dte_target=30, dte_min=7)

        expirations = [
            date(2024, 1, 12),  # 10 DTE
            date(2024, 1, 19),  # 17 DTE
            date(2024, 1, 26),  # 24 DTE
            date(2024, 2, 2),   # 31 DTE - closest to 30
            date(2024, 2, 16),  # 45 DTE
        ]

        selected = selector.select_expiration(expirations, date(2024, 1, 2))
        assert selected == date(2024, 2, 2)

    def test_select_expiration_respects_minimum(self) -> None:
        """Test that minimum DTE is respected."""
        selector = OptionSelector(dte_target=30, dte_min=14)

        expirations = [
            date(2024, 1, 5),   # 3 DTE - below minimum
            date(2024, 1, 12),  # 10 DTE - below minimum
            date(2024, 1, 19),  # 17 DTE - valid
        ]

        selected = selector.select_expiration(expirations, date(2024, 1, 2))
        assert selected == date(2024, 1, 19)

    def test_select_expiration_none_valid(self) -> None:
        """Test when no expirations meet minimum."""
        selector = OptionSelector(dte_target=30, dte_min=30)

        expirations = [
            date(2024, 1, 5),   # 3 DTE
            date(2024, 1, 12),  # 10 DTE
        ]

        selected = selector.select_expiration(expirations, date(2024, 1, 2))
        assert selected is None

    def test_select_put_strike(self) -> None:
        """Test put strike selection (OTM)."""
        selector = OptionSelector(otm_pct=0.05)  # 5% OTM

        # Underlying at 100, so target is 95 (5% below)
        strikes = [90.0, 95.0, 100.0, 105.0, 110.0]

        selected = selector.select_put_strike(100.0, strikes)
        assert selected == 95.0

    def test_select_put_strike_finds_closest(self) -> None:
        """Test put strike finds closest to target."""
        selector = OptionSelector(otm_pct=0.05)  # 5% OTM

        # Underlying at 472, target is ~448.4 (5% below)
        strikes = [445.0, 450.0, 455.0, 460.0, 465.0, 470.0, 475.0]

        selected = selector.select_put_strike(472.0, strikes)
        assert selected == 450.0  # Closest to 448.4

    def test_select_call_strike(self) -> None:
        """Test call strike selection (OTM)."""
        selector = OptionSelector(otm_pct=0.05)  # 5% OTM

        # Underlying at 100, so target is 105 (5% above)
        strikes = [90.0, 95.0, 100.0, 105.0, 110.0]

        selected = selector.select_call_strike(100.0, strikes)
        assert selected == 105.0

    def test_select_option_from_chain(self) -> None:
        """Test selecting option from full chain."""
        selector = OptionSelector(dte_target=30, dte_min=7, otm_pct=0.05)

        chain = pd.DataFrame({
            "expiration": pd.to_datetime([
                "2024-01-19", "2024-01-19",  # 17 DTE
                "2024-02-02", "2024-02-02",  # 31 DTE - closest to 30
            ]),
            "strike": [450.0, 470.0, 450.0, 470.0],
            "option_type": ["put", "put", "put", "put"],
            "bid": [4.50, 2.00, 6.00, 3.00],
            "ask": [5.00, 2.50, 6.50, 3.50],
            "delta": [-0.30, -0.15, -0.35, -0.20],
        })

        # Underlying at 472, target put strike is ~448.4
        result = selector.select_option_from_chain(
            chain=chain,
            option_type=OptionType.PUT,
            underlying_price=472.0,
            trade_date=date(2024, 1, 2),
        )

        assert result is not None
        assert result["expiration"] == date(2024, 2, 2)
        assert result["strike"] == 450.0
        assert result["mid_price"] == 6.25  # (6.00 + 6.50) / 2
        assert result["delta"] == -0.35

    def test_select_option_from_chain_empty(self) -> None:
        """Test selection from empty chain."""
        selector = OptionSelector()
        chain = pd.DataFrame()

        result = selector.select_option_from_chain(
            chain=chain,
            option_type=OptionType.PUT,
            underlying_price=472.0,
            trade_date=date(2024, 1, 2),
        )

        assert result is None

    def test_create_sell_order(self) -> None:
        """Test creating sell order from option info."""
        selector = OptionSelector()

        option_info = {
            "expiration": date(2024, 1, 19),
            "strike": 450.0,
            "option_type": OptionType.PUT,
            "bid": 4.50,
            "ask": 5.00,
            "mid_price": 4.75,
            "delta": -0.25,
            "dte": 17,
        }

        order = selector.create_sell_order(option_info, quantity=2)

        assert order.action == OrderAction.SELL_TO_OPEN
        assert order.option_type == OptionType.PUT
        assert order.strike == 450.0
        assert order.expiration == date(2024, 1, 19)
        assert order.quantity == 2
        assert order.limit_price == 4.75


class TestFill:
    """Tests for Fill dataclass."""

    def test_total_premium(self) -> None:
        """Test total premium calculation."""
        order = OptionOrder(
            action=OrderAction.SELL_TO_OPEN,
            option_type=OptionType.PUT,
            strike=450.0,
            expiration=date(2024, 1, 19),
            quantity=2,
        )

        fill = Fill(
            order=order,
            fill_price=5.00,
            fill_date=date(2024, 1, 2),
            underlying_price=472.0,
            commission=2.00,
        )

        assert fill.total_premium == 1000.0  # 5.00 * 2 * 100

    def test_net_premium_sell(self) -> None:
        """Test net premium for sell order."""
        order = OptionOrder(
            action=OrderAction.SELL_TO_OPEN,
            option_type=OptionType.PUT,
            strike=450.0,
            expiration=date(2024, 1, 19),
            quantity=1,
        )

        fill = Fill(
            order=order,
            fill_price=5.00,
            fill_date=date(2024, 1, 2),
            underlying_price=472.0,
            commission=1.00,
        )

        # Sell: receive premium minus commission
        assert fill.net_premium == 499.0  # 500 - 1

    def test_net_premium_buy(self) -> None:
        """Test net premium for buy order."""
        order = OptionOrder(
            action=OrderAction.BUY_TO_OPEN,
            option_type=OptionType.CALL,
            strike=480.0,
            expiration=date(2024, 1, 19),
            quantity=1,
        )

        fill = Fill(
            order=order,
            fill_price=3.00,
            fill_date=date(2024, 1, 2),
            underlying_price=472.0,
            commission=1.00,
        )

        # Buy: pay premium plus commission (negative)
        assert fill.net_premium == -301.0  # -(300 + 1)
