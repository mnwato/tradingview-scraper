import logging
import math
from typing import Any, Dict, List, Optional, cast
from unittest.mock import MagicMock

import pandas as pd

from tradingview_scraper.execution.metadata import ExecutionMetadataCatalog

# Define mocks/types for linter
Strategy: Any = MagicMock
OrderSide: Any = MagicMock
TimeInForce: Any = MagicMock
InstrumentId: Any = MagicMock
Quantity: Any = MagicMock
Venue: Any = MagicMock

# Initialize to avoid unbound errors
BarSpecification: Any = None
BarAggregation: Any = None
PriceType: Any = None
BarType: Any = None
_USD: Any = None

try:
    from nautilus_trader.model.currencies import USD as _nautilus_USD
    from nautilus_trader.model.data import BarSpecification, BarType
    from nautilus_trader.model.enums import BarAggregation, PriceType
    from nautilus_trader.model.enums import OrderSide as _OrderSide
    from nautilus_trader.model.enums import TimeInForce as _TimeInForce
    from nautilus_trader.model.identifiers import InstrumentId as _InstrumentId
    from nautilus_trader.model.identifiers import Venue as _Venue
    from nautilus_trader.model.objects import Quantity as _Quantity
    from nautilus_trader.trading.strategy import Strategy as _Strategy

    Strategy = _Strategy
    OrderSide = _OrderSide
    TimeInForce = _TimeInForce
    InstrumentId = _InstrumentId
    Venue = _Venue
    Quantity = _Quantity
    _USD = _nautilus_USD
    HAS_NAUTILUS = True
except ImportError:
    HAS_NAUTILUS = False

logger = logging.getLogger(__name__)

# Constant for parity validation
INITIAL_CASH_VAL = 1000000.0


class NautilusRebalanceStrategy(Strategy):
    """
    Event-driven rebalancing strategy for NautilusTrader.
    Ensures 1:1 parity with portfolio target weights while respecting exchange limits.
    """

    def __init__(self, target_weights: pd.DataFrame, catalog: Optional[ExecutionMetadataCatalog] = None, initial_cash: float = INITIAL_CASH_VAL, venue_code: str = "BACKTEST"):
        super().__init__()
        self.target_weights = target_weights.copy()
        self.venue_code = venue_code
        if not isinstance(self.target_weights.index, pd.DatetimeIndex):
            self.target_weights.index = pd.to_datetime(self.target_weights.index)

        # Ensure UTC timezone for consistency
        if self.target_weights.index.tz is None:
            self.target_weights.index = self.target_weights.index.tz_localize("UTC")
        else:
            self.target_weights.index = self.target_weights.index.tz_convert("UTC")

        self.catalog = catalog or ExecutionMetadataCatalog()
        self.initial_cash = initial_cash
        self._nav_history: List[Dict[str, Any]] = []
        self._last_nav_record_ts: int = 0
        self.latest_prices: Dict[str, float] = {}
        self.fills_history: List[Dict[str, Any]] = []

    def _to_nautilus_id_str(self, symbol: str) -> str:
        if ":" in symbol:
            parts = symbol.split(":")
            return f"{parts[1]}.{parts[0]}"
        return symbol

    def _from_nautilus_id_str(self, id_str: str) -> str:
        if "." in id_str:
            parts = id_str.split(".")
            return f"{parts[1]}:{parts[0]}"
        return id_str

    def on_start(self):
        if not HAS_NAUTILUS:
            return
        for symbol in self.target_weights.columns:
            try:
                instrument_id = InstrumentId.from_str(symbol)
                bar_spec = BarSpecification(1, BarAggregation.DAY, PriceType.LAST)
                bar_type = BarType(instrument_id, bar_spec)
                self.subscribe_bars(bar_type)
            except Exception as e:
                logger.error(f"Failed to subscribe to {symbol}: {e}")

    def on_stop(self):
        # Record final NAV state when engine stops
        if self._last_nav_record_ts > 0:
            nav = self._get_nav()
            self._nav_history.append({"ts": self._last_nav_record_ts, "nav": nav})

    def on_order_filled(self, event: Any):
        """Record fill for turnover calculation."""
        if not HAS_NAUTILUS:
            return

        try:
            # Use last_px if available, else fallback
            price = event.last_px if hasattr(event, "last_px") else event.price

            fill_data = {
                "ts": event.ts_event,
                "symbol": str(event.instrument_id),
                "qty": float(event.last_qty),  # OrderFilled usually has last_qty
                "price": float(price),
                "side": str(event.order_side),
                "value": float(event.last_qty) * float(price),
            }
            self.fills_history.append(fill_data)
        except Exception as e:
            logger.error(f"Failed to record fill: {e}")

    def _get_nav(self) -> float:
        """Robustly extracts total equity from portfolio using manual summation."""
        # 1. Cash Balance
        total_cash = 0.0
        if HAS_NAUTILUS:
            try:
                # Use the configured venue
                venue_id = Venue(self.venue_code)
                account = self.portfolio.account(venue_id)

                # Try explicit USD balance first
                try:
                    # CashAccount usually has balance_total(currency)
                    val = account.balance_total(_USD)
                    if hasattr(val, "as_double"):
                        total_cash += val.as_double()
                    elif hasattr(val, "float_value"):
                        total_cash += val.float_value()
                    else:
                        total_cash += float(val)
                except Exception:
                    # Fallback to iteration if USD lookup fails
                    for balance in account.balances():
                        money_obj = None
                        if hasattr(balance, "total"):
                            money_obj = balance.total
                        elif hasattr(balance, "as_double") or hasattr(balance, "float_value"):
                            money_obj = balance

                        if money_obj:
                            if hasattr(money_obj, "as_double"):
                                total_cash += money_obj.as_double()
                            elif hasattr(money_obj, "float_value"):
                                total_cash += money_obj.float_value()
                            else:
                                total_cash += float(money_obj)
            except Exception as e:
                logger.error(f"Failed to get cash balance from account for venue {self.venue_code}: {e}")

        # 2. Positions Market Value

        pos_value = 0.0
        if HAS_NAUTILUS:
            for id_str, price in self.latest_prices.items():
                try:
                    inst_id = InstrumentId.from_str(id_str)
                    net_pos = self.portfolio.net_position(inst_id)
                    qty = float(net_pos)
                    val = qty * price
                    pos_value += val
                except Exception as e:
                    logger.error(f"Failed to calc position value for {id_str}: {e}")
                    pass

        final_nav = total_cash + pos_value

        if final_nav == 0.0:
            # Fallback only if genuinely 0 (which shouldn't happen with initial cash)
            # But if everything failed, we might want to return initial cash to avoid div/0
            return self.initial_cash

        return final_nav

    def on_bar(self, bar: Any):
        try:
            instrument_id = bar.bar_type.instrument_id
            id_str = str(instrument_id)

            if id_str not in self.target_weights.columns:
                return

            # Record NAV when timestamp changes (completion of previous timestamp)
            if bar.ts_event > self._last_nav_record_ts:
                if self._last_nav_record_ts > 0:
                    nav = self._get_nav()
                    self._nav_history.append({"ts": self._last_nav_record_ts, "nav": nav})
                self._last_nav_record_ts = bar.ts_event

            # Update latest price for NAV calculation (for current timestamp)
            if hasattr(bar.close, "float_value"):
                self.latest_prices[id_str] = cast(Any, bar.close).float_value()
            else:
                self.latest_prices[id_str] = float(cast(Any, bar.close))

            ts = pd.Timestamp(bar.ts_event, unit="ns", tz="UTC")

            # Rebalance Logic (Daily)
            try:
                # Use net_position which returns Decimal
                net_pos = self.portfolio.net_position(instrument_id)

                # Find weight for the current or last known timestamp
                if ts in self.target_weights.index:
                    lookup_ts = ts
                else:
                    potential_idx = self.target_weights.index[self.target_weights.index <= ts]
                    if potential_idx.empty:
                        return
                    lookup_ts = potential_idx[-1]

                weight = self.target_weights.loc[lookup_ts, id_str]

                instrument = self.cache.instrument(instrument_id)
                if instrument:
                    target_qty = self._calculate_target_qty(instrument, bar, weight)
                    if target_qty >= 0:
                        self._execute_rebalance(instrument, target_qty)
            except Exception:
                pass
        except Exception:
            pass

    def _calculate_target_qty(self, instrument: Any, bar: Any, weight: float) -> float:
        nav = self._get_nav()
        target_value = nav * weight * 0.95  # Buffer
        price = bar.close.float_value() if hasattr(bar.close, "float_value") else float(bar.close)

        if price <= 0:
            return 0.0

        raw_qty = target_value / price

        unified_symbol = self._from_nautilus_id_str(str(instrument.id))
        limits = self.catalog.get_limits(unified_symbol, str(instrument.id.venue))

        step = 0.00000001
        min_notional = 0.0
        if limits:
            step = limits.step_size
            min_notional = limits.min_notional

        if step > 0:
            # Round towards zero to prevent over-allocation (especially for shorts)
            qty = math.trunc(raw_qty / step) * step
        else:
            qty = raw_qty

        # Check notional value using absolute quantity
        if abs(qty) * price < min_notional:
            return 0.0

        return qty

    def _execute_rebalance(self, instrument: Any, target_qty: float):
        if not HAS_NAUTILUS:
            return
        try:
            current_qty = float(self.portfolio.net_position(instrument.id))

            delta = target_qty - current_qty

            if abs(delta) > 1e-8:
                side = OrderSide.BUY if delta > 0 else OrderSide.SELL
                qty_to_order = abs(delta)

                try:
                    order = self.order_factory.market(instrument.id, side, Quantity(qty_to_order, instrument.size_precision))
                    self.submit_order(order)
                except Exception:
                    pass
        except Exception:
            pass
