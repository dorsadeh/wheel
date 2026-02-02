"""Wheel strategy state machine.

Implements the wheel options strategy:
1. Sell cash-secured puts
2. If assigned, hold the stock and sell covered calls
3. If called away, return to selling puts
4. Repeat
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional

import pandas as pd

from wheel_backtest.engine.options import Fill, OptionOrder, OptionSelector, OrderAction
from wheel_backtest.engine.portfolio import OptionPosition, OptionType, Portfolio


class WheelState(Enum):
    """Current state of the wheel strategy."""

    SELLING_PUTS = "selling_puts"  # No stock, selling cash-secured puts
    HOLDING_STOCK = "holding_stock"  # Holding stock, ready to sell calls
    SELLING_CALLS = "selling_calls"  # Holding stock with open short calls


@dataclass
class WheelEvent:
    """An event in the wheel strategy execution.

    Tracks state transitions, trades, and key events.
    """

    date: date
    event_type: str  # e.g., "sell_put", "put_expired", "put_assigned", "sell_call", etc.
    state_before: WheelState
    state_after: WheelState
    details: dict = field(default_factory=dict)


class WheelStrategy:
    """Wheel strategy state machine.

    Manages the wheel strategy lifecycle:
    - Tracks current state (selling puts, holding stock, selling calls)
    - Handles option expirations and assignments
    - Decides when to open new positions
    """

    def __init__(
        self,
        portfolio: Portfolio,
        selector: OptionSelector,
        contracts_per_trade: int = 1,
        commission_per_contract: float = 0.0,
    ):
        """Initialize wheel strategy.

        Args:
            portfolio: Portfolio to manage
            selector: Option selector for strike/expiration selection
            contracts_per_trade: Number of contracts per trade
            commission_per_contract: Commission per contract
        """
        self.portfolio = portfolio
        self.selector = selector
        self.contracts_per_trade = contracts_per_trade
        self.commission = commission_per_contract
        self._state = WheelState.SELLING_PUTS
        self._events: list[WheelEvent] = []
        self._cost_basis: Optional[float] = None  # Per-share cost basis when holding stock

    @property
    def state(self) -> WheelState:
        """Current wheel state."""
        return self._state

    @property
    def events(self) -> list[WheelEvent]:
        """List of all wheel events."""
        return self._events.copy()

    def _log_event(
        self,
        trade_date: date,
        event_type: str,
        state_before: WheelState,
        state_after: WheelState,
        **details,
    ) -> WheelEvent:
        """Log a wheel event."""
        event = WheelEvent(
            date=trade_date,
            event_type=event_type,
            state_before=state_before,
            state_after=state_after,
            details=details,
        )
        self._events.append(event)
        return event

    def process_day(
        self,
        trade_date: date,
        underlying_price: float,
        options_chain: pd.DataFrame,
    ) -> list[WheelEvent]:
        """Process a single trading day.

        Handles expirations, assignments, and opens new positions as needed.

        Args:
            trade_date: Current trading date
            underlying_price: Current underlying price
            options_chain: Available options chain for this date

        Returns:
            List of events that occurred this day
        """
        day_events = []

        # Step 1: Handle any expirations
        expiration_events = self._handle_expirations(trade_date, underlying_price)
        day_events.extend(expiration_events)

        # Step 2: Update state based on holdings
        self._update_state()

        # Step 3: Open new positions if appropriate
        if self._should_open_position():
            open_events = self._open_position(trade_date, underlying_price, options_chain)
            day_events.extend(open_events)

        return day_events

    def _handle_expirations(
        self,
        trade_date: date,
        underlying_price: float,
    ) -> list[WheelEvent]:
        """Handle any option expirations.

        Args:
            trade_date: Current date
            underlying_price: Current underlying price

        Returns:
            List of expiration events
        """
        events = []

        # Process expired positions
        expired_positions = [
            pos for pos in self.portfolio.option_positions
            if pos.is_expired(trade_date)
        ]

        for position in expired_positions:
            state_before = self._state

            if position.is_itm(underlying_price):
                # ITM at expiration - assignment
                if position.is_put:
                    # Put assignment - buy shares at strike
                    pnl = self.portfolio.exercise_put_assignment(position, underlying_price)

                    # Calculate cost basis
                    shares_acquired = position.quantity * self.portfolio.contract_multiplier
                    self._cost_basis = position.strike - position.entry_price

                    self._state = WheelState.HOLDING_STOCK

                    events.append(self._log_event(
                        trade_date,
                        "put_assigned",
                        state_before,
                        self._state,
                        strike=position.strike,
                        underlying_price=underlying_price,
                        shares_acquired=shares_acquired,
                        cost_basis=self._cost_basis,
                        premium_received=position.entry_price,
                        pnl=pnl,
                    ))
                else:
                    # Call assignment - sell shares at strike
                    pnl = self.portfolio.exercise_call_assignment(position, underlying_price)

                    self._state = WheelState.SELLING_PUTS
                    self._cost_basis = None

                    events.append(self._log_event(
                        trade_date,
                        "call_assigned",
                        state_before,
                        self._state,
                        strike=position.strike,
                        underlying_price=underlying_price,
                        shares_sold=position.quantity * self.portfolio.contract_multiplier,
                        premium_received=position.entry_price,
                        pnl=pnl,
                    ))
            else:
                # OTM at expiration - expires worthless
                pnl = self.portfolio.expire_option_worthless(position)

                event_type = "put_expired" if position.is_put else "call_expired"
                state_after = self._state

                # If call expired, we still have stock - go back to selling calls
                if position.is_call:
                    state_after = WheelState.HOLDING_STOCK

                events.append(self._log_event(
                    trade_date,
                    event_type,
                    state_before,
                    state_after,
                    strike=position.strike,
                    underlying_price=underlying_price,
                    premium_kept=position.entry_price,
                    pnl=pnl,
                ))

                self._state = state_after

        return events

    def _update_state(self) -> None:
        """Update state based on current holdings."""
        has_shares = self.portfolio.shares > 0
        has_short_puts = len(self.portfolio.get_short_puts()) > 0
        has_short_calls = len(self.portfolio.get_short_calls()) > 0

        if has_shares:
            if has_short_calls:
                self._state = WheelState.SELLING_CALLS
            else:
                self._state = WheelState.HOLDING_STOCK
        else:
            self._state = WheelState.SELLING_PUTS

    def _should_open_position(self) -> bool:
        """Check if we should open a new position.

        Returns:
            True if we should open a position
        """
        if self._state == WheelState.SELLING_PUTS:
            # Open new put if no puts open
            return len(self.portfolio.get_short_puts()) == 0

        elif self._state == WheelState.HOLDING_STOCK:
            # Open new call if no calls open
            return len(self.portfolio.get_short_calls()) == 0

        elif self._state == WheelState.SELLING_CALLS:
            # Already have calls open
            return False

        return False

    def _open_position(
        self,
        trade_date: date,
        underlying_price: float,
        options_chain: pd.DataFrame,
    ) -> list[WheelEvent]:
        """Open a new position.

        Args:
            trade_date: Current date
            underlying_price: Current underlying price
            options_chain: Available options

        Returns:
            List of events from opening position
        """
        events = []

        if self._state == WheelState.SELLING_PUTS:
            events.extend(self._sell_put(trade_date, underlying_price, options_chain))

        elif self._state == WheelState.HOLDING_STOCK:
            events.extend(self._sell_call(trade_date, underlying_price, options_chain))

        return events

    def _sell_put(
        self,
        trade_date: date,
        underlying_price: float,
        options_chain: pd.DataFrame,
    ) -> list[WheelEvent]:
        """Sell a cash-secured put.

        Args:
            trade_date: Current date
            underlying_price: Current underlying price
            options_chain: Available options

        Returns:
            List of events
        """
        events = []
        state_before = self._state

        # Select best put to sell
        option_info = self.selector.select_option_from_chain(
            chain=options_chain,
            option_type=OptionType.PUT,
            underlying_price=underlying_price,
            trade_date=trade_date,
        )

        if option_info is None:
            return events

        # Check if we have enough buying power
        required_cash = option_info["strike"] * self.contracts_per_trade * 100
        if self.portfolio.cash < required_cash:
            return events

        # Open the position
        total_commission = self.commission * self.contracts_per_trade
        position = self.portfolio.open_short_option(
            option_type=OptionType.PUT,
            strike=option_info["strike"],
            expiration=option_info["expiration"],
            quantity=self.contracts_per_trade,
            premium_per_share=option_info["mid_price"],
            trade_date=trade_date,
            underlying_price=underlying_price,
            delta=option_info.get("delta"),
            commission=total_commission,
        )

        events.append(self._log_event(
            trade_date,
            "sell_put",
            state_before,
            WheelState.SELLING_PUTS,
            strike=option_info["strike"],
            expiration=option_info["expiration"],
            premium=option_info["mid_price"],
            delta=option_info.get("delta"),
            dte=option_info["dte"],
            underlying_price=underlying_price,
            contracts=self.contracts_per_trade,
            commission=total_commission,
        ))

        return events

    def _sell_call(
        self,
        trade_date: date,
        underlying_price: float,
        options_chain: pd.DataFrame,
    ) -> list[WheelEvent]:
        """Sell a covered call.

        Args:
            trade_date: Current date
            underlying_price: Current underlying price
            options_chain: Available options

        Returns:
            List of events
        """
        events = []
        state_before = self._state

        # Select best call to sell
        option_info = self.selector.select_option_from_chain(
            chain=options_chain,
            option_type=OptionType.CALL,
            underlying_price=underlying_price,
            trade_date=trade_date,
            cost_basis=self._cost_basis,
        )

        if option_info is None:
            return events

        # Check if we have enough shares
        shares_needed = self.contracts_per_trade * 100
        if self.portfolio.shares < shares_needed:
            return events

        # Open the position
        total_commission = self.commission * self.contracts_per_trade
        position = self.portfolio.open_short_option(
            option_type=OptionType.CALL,
            strike=option_info["strike"],
            expiration=option_info["expiration"],
            quantity=self.contracts_per_trade,
            premium_per_share=option_info["mid_price"],
            trade_date=trade_date,
            underlying_price=underlying_price,
            delta=option_info.get("delta"),
            commission=total_commission,
        )

        self._state = WheelState.SELLING_CALLS

        events.append(self._log_event(
            trade_date,
            "sell_call",
            state_before,
            WheelState.SELLING_CALLS,
            strike=option_info["strike"],
            expiration=option_info["expiration"],
            premium=option_info["mid_price"],
            delta=option_info.get("delta"),
            dte=option_info["dte"],
            underlying_price=underlying_price,
            cost_basis=self._cost_basis,
            contracts=self.contracts_per_trade,
            commission=total_commission,
        ))

        return events

    def get_summary(self) -> dict:
        """Get summary of wheel strategy execution.

        Returns:
            Summary statistics
        """
        total_puts_sold = sum(1 for e in self._events if e.event_type == "sell_put")
        total_calls_sold = sum(1 for e in self._events if e.event_type == "sell_call")
        put_assignments = sum(1 for e in self._events if e.event_type == "put_assigned")
        call_assignments = sum(1 for e in self._events if e.event_type == "call_assigned")
        puts_expired = sum(1 for e in self._events if e.event_type == "put_expired")
        calls_expired = sum(1 for e in self._events if e.event_type == "call_expired")

        # Calculate total premium collected
        premium_from_puts = sum(
            e.details.get("premium", 0) * e.details.get("contracts", 1) * 100
            for e in self._events if e.event_type == "sell_put"
        )
        premium_from_calls = sum(
            e.details.get("premium", 0) * e.details.get("contracts", 1) * 100
            for e in self._events if e.event_type == "sell_call"
        )

        return {
            "total_puts_sold": total_puts_sold,
            "total_calls_sold": total_calls_sold,
            "put_assignments": put_assignments,
            "call_assignments": call_assignments,
            "puts_expired_otm": puts_expired,
            "calls_expired_otm": calls_expired,
            "total_premium_from_puts": premium_from_puts,
            "total_premium_from_calls": premium_from_calls,
            "total_premium_collected": premium_from_puts + premium_from_calls,
            "current_state": self._state.value,
        }
