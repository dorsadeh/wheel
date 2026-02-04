"""Option selection and order management.

Provides logic for selecting strikes and managing option orders.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from typing import Optional

import pandas as pd

from wheel_backtest.engine.portfolio import OptionType


class OrderAction(Enum):
    """Type of order action."""

    SELL_TO_OPEN = "sell_to_open"  # Open short position
    BUY_TO_CLOSE = "buy_to_close"  # Close short position
    BUY_TO_OPEN = "buy_to_open"  # Open long position
    SELL_TO_CLOSE = "sell_to_close"  # Close long position


@dataclass
class OptionOrder:
    """An option order to be filled.

    Attributes:
        action: Order action (sell_to_open, etc.)
        option_type: PUT or CALL
        strike: Strike price
        expiration: Expiration date
        quantity: Number of contracts
        limit_price: Limit price per share (optional)
    """

    action: OrderAction
    option_type: OptionType
    strike: float
    expiration: date
    quantity: int
    limit_price: Optional[float] = None


@dataclass
class Fill:
    """A filled order.

    Attributes:
        order: The original order
        fill_price: Price per share at which order was filled
        fill_date: Date the order was filled
        underlying_price: Underlying price at fill
        delta: Option delta at fill (optional)
        commission: Commission paid
    """

    order: OptionOrder
    fill_price: float
    fill_date: date
    underlying_price: float
    delta: Optional[float] = None
    commission: float = 0.0

    @property
    def total_premium(self) -> float:
        """Total premium for the fill (per share * contracts * 100)."""
        return self.fill_price * self.order.quantity * 100

    @property
    def net_premium(self) -> float:
        """Net premium after commission."""
        if self.order.action in (OrderAction.SELL_TO_OPEN, OrderAction.SELL_TO_CLOSE):
            return self.total_premium - self.commission
        else:
            return -(self.total_premium + self.commission)


class OptionSelector:
    """Selects options based on criteria.

    Supports selection by:
    - Delta (e.g., -0.20 for puts, +0.20 for calls)
    - Percentage OTM (e.g., 5% below current price for puts)
    - Target DTE (days to expiration)

    Selection method priority:
    1. Delta-based selection (if delta_target provided and delta data available)
    2. OTM percentage fallback (if delta unavailable)
    """

    def __init__(
        self,
        dte_target: int = 30,
        dte_min: int = 7,
        delta_target: Optional[float] = None,
        put_delta: Optional[float] = None,
        call_delta: Optional[float] = None,
        otm_pct: Optional[float] = None,
    ):
        """Initialize selector.

        Args:
            dte_target: Target days to expiration
            dte_min: Minimum DTE to consider
            delta_target: Target delta for both puts and calls (legacy, use put_delta/call_delta)
            put_delta: Target delta for puts (overrides delta_target)
            call_delta: Target delta for calls (overrides delta_target)
            otm_pct: Target OTM percentage (0.05 = 5%), used as fallback if delta unavailable
        """
        self.dte_target = dte_target
        self.dte_min = dte_min
        self.delta_target = delta_target

        # Set effective deltas for puts and calls
        self.put_delta = put_delta if put_delta is not None else delta_target
        self.call_delta = call_delta if call_delta is not None else delta_target

        # Set default OTM percentage based on delta if not provided
        effective_delta = delta_target if delta_target is not None else (put_delta or call_delta or 0.20)
        if otm_pct is None and effective_delta is not None:
            # Rough approximation: 0.20 delta ≈ 5% OTM
            self.otm_pct = effective_delta * 0.25
        else:
            self.otm_pct = otm_pct if otm_pct is not None else 0.05

    def select_expiration(
        self,
        available_expirations: list[date],
        trade_date: date,
    ) -> Optional[date]:
        """Select best expiration date.

        Finds expiration closest to target DTE that meets minimum.

        Args:
            available_expirations: List of available expiration dates
            trade_date: Current trade date

        Returns:
            Selected expiration date, or None if none available
        """
        if not available_expirations:
            return None

        # Filter to expirations meeting minimum DTE
        valid_exps = []
        for exp in available_expirations:
            dte = (exp - trade_date).days
            if dte >= self.dte_min:
                valid_exps.append((exp, dte))

        if not valid_exps:
            return None

        # Find closest to target DTE
        valid_exps.sort(key=lambda x: abs(x[1] - self.dte_target))
        return valid_exps[0][0]

    def select_put_strike(
        self,
        underlying_price: float,
        available_strikes: list[float],
    ) -> Optional[float]:
        """Select strike for a short put.

        Selects strike that is approximately otm_pct below current price.

        Args:
            underlying_price: Current underlying price
            available_strikes: List of available strikes

        Returns:
            Selected strike, or None if none available
        """
        if not available_strikes:
            return None

        # Target strike is otm_pct below current price
        target_strike = underlying_price * (1 - self.otm_pct)

        # Find closest strike at or below target
        valid_strikes = [s for s in available_strikes if s <= underlying_price]

        if not valid_strikes:
            return None

        # Find closest to target
        valid_strikes.sort(key=lambda x: abs(x - target_strike))
        return valid_strikes[0]

    def select_call_strike(
        self,
        underlying_price: float,
        available_strikes: list[float],
        cost_basis: Optional[float] = None,
    ) -> Optional[float]:
        """Select strike for a short call.

        Selects strike that is approximately otm_pct above current price,
        but at least at cost basis if provided.

        Args:
            underlying_price: Current underlying price
            available_strikes: List of available strikes
            cost_basis: Cost basis per share (optional, ensures profit if called)

        Returns:
            Selected strike, or None if none available
        """
        if not available_strikes:
            return None

        # Target strike is otm_pct above current price
        target_strike = underlying_price * (1 + self.otm_pct)

        # Ensure at least at cost basis
        if cost_basis is not None:
            target_strike = max(target_strike, cost_basis)

        # Find closest strike at or above target
        valid_strikes = [s for s in available_strikes if s >= underlying_price]

        if not valid_strikes:
            return None

        # Find closest to target
        valid_strikes.sort(key=lambda x: abs(x - target_strike))
        return valid_strikes[0]

    def select_strike_by_delta(
        self,
        options_df: pd.DataFrame,
        option_type: OptionType,
        target_delta: float,
        underlying_price: float,
        cost_basis: Optional[float] = None,
    ) -> Optional[float]:
        """Select strike based on target delta.

        Args:
            options_df: DataFrame with options for a specific expiration
            option_type: PUT or CALL
            target_delta: Target absolute delta value (e.g., 0.20 for 20 delta)
            underlying_price: Current underlying price
            cost_basis: For covered calls, ensures strike >= cost basis

        Returns:
            Selected strike, or None if no suitable option found
        """
        if options_df.empty or "delta" not in options_df.columns:
            return None

        # Filter to options with valid delta
        valid_options = options_df[options_df["delta"].notna()].copy()
        if valid_options.empty:
            return None

        # For puts: target negative delta (e.g., -0.20)
        # For calls: target positive delta (e.g., +0.20)
        if option_type == OptionType.PUT:
            target_signed_delta = -abs(target_delta)
            # Filter to OTM puts (strike < underlying)
            valid_options = valid_options[valid_options["strike"] <= underlying_price]
        else:  # CALL
            target_signed_delta = abs(target_delta)
            # Filter to OTM calls (strike > underlying)
            valid_options = valid_options[valid_options["strike"] >= underlying_price]

            # For covered calls, ensure strike >= cost basis
            if cost_basis is not None:
                valid_options = valid_options[valid_options["strike"] >= cost_basis]

        if valid_options.empty:
            return None

        # Find option with delta closest to target
        valid_options["delta_diff"] = abs(valid_options["delta"] - target_signed_delta)
        best_option = valid_options.loc[valid_options["delta_diff"].idxmin()]

        return float(best_option["strike"])

    def select_option_from_chain(
        self,
        chain: pd.DataFrame,
        option_type: OptionType,
        underlying_price: float,
        trade_date: date,
        cost_basis: Optional[float] = None,
    ) -> Optional[dict]:
        """Select best option from options chain.

        Args:
            chain: Options chain DataFrame with columns:
                   expiration, strike, option_type, bid, ask, delta
            option_type: PUT or CALL
            underlying_price: Current underlying price
            trade_date: Current trade date
            cost_basis: Cost basis for covered calls (optional)

        Returns:
            Dict with selected option details, or None if none found
        """
        if chain.empty:
            return None

        # Filter to correct option type
        type_str = option_type.value
        type_chain = chain[chain["option_type"] == type_str].copy()

        if type_chain.empty:
            return None

        # Get unique expirations
        expirations = sorted(type_chain["expiration"].dt.date.unique())
        selected_exp = self.select_expiration(expirations, trade_date)

        if selected_exp is None:
            return None

        # Filter to selected expiration
        exp_chain = type_chain[type_chain["expiration"].dt.date == selected_exp]

        # Select strike - try delta first, fall back to OTM percentage
        selected_strike = None

        # Determine which delta to use based on option type
        target_delta = self.put_delta if option_type == OptionType.PUT else self.call_delta

        # Try delta-based selection if configured and data available
        if target_delta is not None:
            selected_strike = self.select_strike_by_delta(
                options_df=exp_chain,
                option_type=option_type,
                target_delta=target_delta,
                underlying_price=underlying_price,
                cost_basis=cost_basis,
            )

        # Fall back to OTM percentage if delta selection failed
        if selected_strike is None:
            strikes = sorted(exp_chain["strike"].unique())
            if option_type == OptionType.PUT:
                selected_strike = self.select_put_strike(underlying_price, strikes)
            else:
                selected_strike = self.select_call_strike(
                    underlying_price, strikes, cost_basis
                )

        if selected_strike is None:
            return None

        # Get the specific option
        option = exp_chain[exp_chain["strike"] == selected_strike].iloc[0]

        # Calculate mid price
        bid = float(option["bid"])
        ask = float(option["ask"])
        mid_price = (bid + ask) / 2

        return {
            "expiration": selected_exp,
            "strike": selected_strike,
            "option_type": option_type,
            "bid": bid,
            "ask": ask,
            "mid_price": mid_price,
            "delta": float(option["delta"]) if "delta" in option else None,
            "dte": (selected_exp - trade_date).days,
        }

    def create_sell_order(
        self,
        option_info: dict,
        quantity: int = 1,
    ) -> OptionOrder:
        """Create a sell-to-open order from selected option.

        Args:
            option_info: Dict from select_option_from_chain
            quantity: Number of contracts

        Returns:
            OptionOrder for selling the option
        """
        return OptionOrder(
            action=OrderAction.SELL_TO_OPEN,
            option_type=option_info["option_type"],
            strike=option_info["strike"],
            expiration=option_info["expiration"],
            quantity=quantity,
            limit_price=option_info["mid_price"],
        )
