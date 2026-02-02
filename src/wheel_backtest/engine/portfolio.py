"""Portfolio management for backtesting.

Tracks cash, stock positions, and option positions with full
accounting for the wheel strategy.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional


class OptionType(Enum):
    """Type of option contract."""

    PUT = "put"
    CALL = "call"


class PositionSide(Enum):
    """Side of option position."""

    LONG = "long"
    SHORT = "short"


@dataclass
class OptionPosition:
    """An open option position.

    Attributes:
        option_type: PUT or CALL
        side: LONG or SHORT
        strike: Strike price
        expiration: Expiration date
        quantity: Number of contracts (positive)
        entry_price: Premium per share at entry
        entry_date: Date position was opened
        underlying_price_at_entry: Underlying price when opened
        delta_at_entry: Delta when position was opened (optional)
    """

    option_type: OptionType
    side: PositionSide
    strike: float
    expiration: date
    quantity: int
    entry_price: float
    entry_date: date
    underlying_price_at_entry: float
    delta_at_entry: Optional[float] = None

    @property
    def is_short(self) -> bool:
        """True if this is a short position."""
        return self.side == PositionSide.SHORT

    @property
    def is_put(self) -> bool:
        """True if this is a put option."""
        return self.option_type == OptionType.PUT

    @property
    def is_call(self) -> bool:
        """True if this is a call option."""
        return self.option_type == OptionType.CALL

    @property
    def notional_value(self) -> float:
        """Notional value of position (strike * quantity * 100)."""
        return self.strike * self.quantity * 100

    def is_expired(self, current_date: date) -> bool:
        """Check if option has expired."""
        return current_date >= self.expiration

    def is_itm(self, underlying_price: float) -> bool:
        """Check if option is in-the-money.

        Args:
            underlying_price: Current underlying price

        Returns:
            True if ITM
        """
        if self.is_put:
            return underlying_price < self.strike
        else:  # CALL
            return underlying_price > self.strike

    def intrinsic_value(self, underlying_price: float) -> float:
        """Calculate intrinsic value per share.

        Args:
            underlying_price: Current underlying price

        Returns:
            Intrinsic value (0 if OTM)
        """
        if self.is_put:
            return max(0.0, self.strike - underlying_price)
        else:  # CALL
            return max(0.0, underlying_price - self.strike)


@dataclass
class Portfolio:
    """Portfolio state tracking cash, shares, and options.

    The portfolio tracks:
    - Cash balance
    - Stock shares held
    - Open option positions

    All values are tracked precisely for accurate P&L calculation.
    """

    cash: float = 0.0
    shares: int = 0
    option_positions: list[OptionPosition] = field(default_factory=list)
    contract_multiplier: int = 100

    def deposit(self, amount: float) -> None:
        """Add cash to portfolio.

        Args:
            amount: Cash amount to add
        """
        if amount < 0:
            raise ValueError("Deposit amount must be positive")
        self.cash += amount

    def withdraw(self, amount: float) -> None:
        """Remove cash from portfolio.

        Args:
            amount: Cash amount to remove

        Raises:
            ValueError: If insufficient cash
        """
        if amount < 0:
            raise ValueError("Withdrawal amount must be positive")
        if amount > self.cash:
            raise ValueError(f"Insufficient cash: have {self.cash}, need {amount}")
        self.cash -= amount

    def buy_shares(self, quantity: int, price: float, commission: float = 0.0) -> float:
        """Buy shares of the underlying.

        Args:
            quantity: Number of shares to buy
            price: Price per share
            commission: Commission for the trade

        Returns:
            Total cost of the trade

        Raises:
            ValueError: If insufficient cash
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        total_cost = quantity * price + commission

        if total_cost > self.cash:
            raise ValueError(f"Insufficient cash: have {self.cash}, need {total_cost}")

        self.cash -= total_cost
        self.shares += quantity

        return total_cost

    def sell_shares(self, quantity: int, price: float, commission: float = 0.0) -> float:
        """Sell shares of the underlying.

        Args:
            quantity: Number of shares to sell
            price: Price per share
            commission: Commission for the trade

        Returns:
            Net proceeds from the trade

        Raises:
            ValueError: If insufficient shares
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        if quantity > self.shares:
            raise ValueError(f"Insufficient shares: have {self.shares}, need {quantity}")

        proceeds = quantity * price - commission
        self.cash += proceeds
        self.shares -= quantity

        return proceeds

    def open_short_option(
        self,
        option_type: OptionType,
        strike: float,
        expiration: date,
        quantity: int,
        premium_per_share: float,
        trade_date: date,
        underlying_price: float,
        delta: Optional[float] = None,
        commission: float = 0.0,
    ) -> OptionPosition:
        """Open a short option position (sell to open).

        For the wheel strategy, this is used to:
        - Sell cash-secured puts
        - Sell covered calls

        Args:
            option_type: PUT or CALL
            strike: Strike price
            expiration: Expiration date
            quantity: Number of contracts
            premium_per_share: Premium received per share
            trade_date: Date of trade
            underlying_price: Current underlying price
            delta: Option delta at entry (optional)
            commission: Commission for the trade

        Returns:
            The opened OptionPosition
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        # Receive premium (credit)
        total_premium = premium_per_share * quantity * self.contract_multiplier
        net_credit = total_premium - commission
        self.cash += net_credit

        position = OptionPosition(
            option_type=option_type,
            side=PositionSide.SHORT,
            strike=strike,
            expiration=expiration,
            quantity=quantity,
            entry_price=premium_per_share,
            entry_date=trade_date,
            underlying_price_at_entry=underlying_price,
            delta_at_entry=delta,
        )

        self.option_positions.append(position)
        return position

    def close_option_position(
        self,
        position: OptionPosition,
        close_price: float,
        commission: float = 0.0,
    ) -> float:
        """Close an option position (buy to close for shorts).

        Args:
            position: Position to close
            close_price: Price per share to close
            commission: Commission for the trade

        Returns:
            P&L from closing the position
        """
        if position not in self.option_positions:
            raise ValueError("Position not found in portfolio")

        if position.is_short:
            # Buy to close - pay the premium
            total_cost = close_price * position.quantity * self.contract_multiplier
            self.cash -= (total_cost + commission)

            # P&L = entry premium - exit cost
            pnl = (position.entry_price - close_price) * position.quantity * self.contract_multiplier - commission
        else:
            # Sell to close (long position) - receive premium
            total_proceeds = close_price * position.quantity * self.contract_multiplier
            self.cash += (total_proceeds - commission)

            # P&L = exit proceeds - entry cost
            pnl = (close_price - position.entry_price) * position.quantity * self.contract_multiplier - commission

        self.option_positions.remove(position)
        return pnl

    def expire_option_worthless(self, position: OptionPosition) -> float:
        """Expire an option worthless (OTM at expiration).

        For short options, this is pure profit (keep the premium).

        Args:
            position: Position that expired worthless

        Returns:
            P&L from expiration (premium kept for shorts)
        """
        if position not in self.option_positions:
            raise ValueError("Position not found in portfolio")

        if position.is_short:
            # Keep full premium - already received at entry
            pnl = position.entry_price * position.quantity * self.contract_multiplier
        else:
            # Lose full premium paid
            pnl = -position.entry_price * position.quantity * self.contract_multiplier

        self.option_positions.remove(position)
        return pnl

    def exercise_put_assignment(
        self,
        position: OptionPosition,
        underlying_price: float,
    ) -> float:
        """Handle put assignment (forced to buy shares at strike).

        When a short put is ITM at expiration, we are assigned:
        - Buy 100 shares per contract at the strike price

        Args:
            position: The put position being assigned
            underlying_price: Current underlying price

        Returns:
            P&L from assignment (including premium already received)
        """
        if not position.is_put or not position.is_short:
            raise ValueError("Can only exercise assignment on short puts")

        if position not in self.option_positions:
            raise ValueError("Position not found in portfolio")

        shares_to_buy = position.quantity * self.contract_multiplier
        cost = position.strike * shares_to_buy

        if cost > self.cash:
            raise ValueError(f"Insufficient cash for assignment: need {cost}, have {self.cash}")

        # Buy shares at strike price
        self.cash -= cost
        self.shares += shares_to_buy

        # P&L includes premium received and any intrinsic loss
        # Premium was already added to cash when position opened
        intrinsic_loss = (position.strike - underlying_price) * shares_to_buy
        pnl = position.entry_price * shares_to_buy - intrinsic_loss

        self.option_positions.remove(position)
        return pnl

    def exercise_call_assignment(
        self,
        position: OptionPosition,
        underlying_price: float,
    ) -> float:
        """Handle call assignment (forced to sell shares at strike).

        When a short call is ITM at expiration, we are assigned:
        - Sell 100 shares per contract at the strike price

        Args:
            position: The call position being assigned
            underlying_price: Current underlying price

        Returns:
            P&L from assignment (including premium already received)
        """
        if not position.is_call or not position.is_short:
            raise ValueError("Can only exercise assignment on short calls")

        if position not in self.option_positions:
            raise ValueError("Position not found in portfolio")

        shares_to_sell = position.quantity * self.contract_multiplier

        if shares_to_sell > self.shares:
            raise ValueError(f"Insufficient shares for assignment: need {shares_to_sell}, have {self.shares}")

        # Sell shares at strike price
        proceeds = position.strike * shares_to_sell
        self.cash += proceeds
        self.shares -= shares_to_sell

        # P&L includes premium received
        # We "lose" the upside above strike but gained the premium
        pnl = position.entry_price * shares_to_sell

        self.option_positions.remove(position)
        return pnl

    def get_equity(self, underlying_price: float, option_mid_prices: Optional[dict] = None) -> float:
        """Calculate total portfolio equity.

        Args:
            underlying_price: Current underlying price
            option_mid_prices: Dict mapping position to mid price (optional)

        Returns:
            Total equity value
        """
        stock_value = self.shares * underlying_price

        # Mark options to market
        options_value = 0.0
        for pos in self.option_positions:
            if option_mid_prices and pos in option_mid_prices:
                mid_price = option_mid_prices[pos]
            else:
                # Use intrinsic value as approximation
                mid_price = pos.intrinsic_value(underlying_price)

            position_value = mid_price * pos.quantity * self.contract_multiplier

            if pos.is_short:
                # Short options: liability (negative value to us)
                options_value -= position_value
            else:
                # Long options: asset
                options_value += position_value

        return self.cash + stock_value + options_value

    def get_buying_power(self) -> float:
        """Get available buying power.

        For simplicity, this returns cash minus any reserved for
        cash-secured puts.

        Returns:
            Available buying power
        """
        # Reserve cash for short puts
        reserved = 0.0
        for pos in self.option_positions:
            if pos.is_put and pos.is_short:
                reserved += pos.strike * pos.quantity * self.contract_multiplier

        return max(0.0, self.cash - reserved)

    def has_open_positions(self) -> bool:
        """Check if there are any open option positions."""
        return len(self.option_positions) > 0

    def get_short_puts(self) -> list[OptionPosition]:
        """Get all open short put positions."""
        return [p for p in self.option_positions if p.is_put and p.is_short]

    def get_short_calls(self) -> list[OptionPosition]:
        """Get all open short call positions."""
        return [p for p in self.option_positions if p.is_call and p.is_short]
