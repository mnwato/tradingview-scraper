import json
import logging
import math
import os
import threading
import time
from typing import Any, Dict, List, Optional, cast
from unittest.mock import MagicMock

import pandas as pd

from tradingview_scraper.execution.metadata import ExecutionMetadataCatalog

# Global state for SHADOW mode position tracking
_SHADOW_POSITIONS: Dict[str, float] = {}

# Nautilus Types (using Any to handle conditional imports and mocking)
Strategy: Any = object
OrderSide: Any = object
InstrumentId: Any = object
Quantity: Any = object
Venue: Any = object
Symbol: Any = object
Currency: Any = object
CurrencyType: Any = object
Price: Any = object
CurrencyPair: Any = object
register_currency: Any = lambda c: None
BarType: Any = object
BarSpecification: Any = object
BarAggregation: Any = object
PriceType: Any = object

try:
    from nautilus_trader.model.currencies import register_currency as _register_currency
    from nautilus_trader.model.data import BarSpecification as _BarSpecification
    from nautilus_trader.model.data import BarType as _BarType
    from nautilus_trader.model.enums import BarAggregation as _BarAggregation
    from nautilus_trader.model.enums import CurrencyType as _CurrencyType
    from nautilus_trader.model.enums import OrderSide as _OrderSide
    from nautilus_trader.model.enums import PriceType as _PriceType
    from nautilus_trader.model.identifiers import InstrumentId as _InstrumentId
    from nautilus_trader.model.identifiers import Symbol as _Symbol
    from nautilus_trader.model.identifiers import Venue as _Venue
    from nautilus_trader.model.instruments import CurrencyPair as _CurrencyPair
    from nautilus_trader.model.objects import Currency as _Currency
    from nautilus_trader.model.objects import Price as _Price
    from nautilus_trader.model.objects import Quantity as _Quantity
    from nautilus_trader.trading.strategy import Strategy as _Strategy

    from tradingview_scraper.portfolio_engines.nautilus_strategy import INITIAL_CASH_VAL, NautilusRebalanceStrategy

    Strategy = _Strategy
    OrderSide = _OrderSide
    InstrumentId = _InstrumentId
    Symbol = _Symbol
    Venue = _Venue
    Currency = _Currency
    CurrencyType = _CurrencyType
    Price = _Price
    Quantity = _Quantity
    CurrencyPair = _CurrencyPair
    register_currency = _register_currency
    BarType = _BarType
    BarSpecification = _BarSpecification
    BarAggregation = _BarAggregation
    PriceType = _PriceType
    HAS_NAUTILUS = True
except ImportError:
    HAS_NAUTILUS = False
    INITIAL_CASH_VAL = 100_000.0

    class NautilusRebalanceStrategy(object):  # type: ignore
        def __init__(self, *args, **kwargs):
            self.cache: Any = MagicMock()
            self.portfolio: Any = MagicMock()
            self.target_weights = pd.DataFrame()

        def on_start(self):
            pass

        def on_stop(self):
            pass

        def _get_nav(self) -> float:
            return 0.0


logger = logging.getLogger(__name__)


class LiveRebalanceStrategy(NautilusRebalanceStrategy):  # type: ignore
    """
    Live execution strategy that watches a JSON file for target weight updates.
    """

    def __init__(self, weights_file: str, venue_str: str = "BINANCE", mode: str = "SHADOW", state_file: str = "data/lakehouse/portfolio_actual_state.json", catalog: Any = None, *args, **kwargs):
        super().__init__(pd.DataFrame(), *args, **kwargs)
        self.weights_file = weights_file
        self.venue_str = venue_str
        self.mode = mode.upper()
        self.state_file = state_file
        self.catalog = catalog or ExecutionMetadataCatalog()
        self.last_mtime = 0
        self.running = False

    def on_start(self):
        if HAS_NAUTILUS and not self.cache.instruments():
            logger.warning("Shadow Mode detected (Empty Instrument Cache). Injecting dummy instruments...")
            self._inject_dummy_instruments()

        super().on_start()
        self.running = True
        self.watcher_thread = threading.Thread(target=self._watch_file, daemon=True)
        self.watcher_thread.start()
        logger.info(f"Started LiveRebalanceStrategy watching {self.weights_file} [MODE={self.mode}]")

    def _inject_dummy_instruments(self):
        """Injects dummy CurrencyPair instruments for Shadow Mode."""
        try:
            if os.path.exists(self.weights_file):
                with open(self.weights_file, "r") as f:
                    data = json.load(f)
                if "winners" in data:
                    symbols = [a["Symbol"] for a in data["winners"][0].get("assets", [])]
                else:
                    weights_map = data.get("weights", data)
                    symbols = list(weights_map.keys())
            else:
                symbols = ["BTCUSDT", "ETHUSDT"]
        except Exception:
            symbols = ["BTCUSDT", "ETHUSDT"]

        venue = Venue(self.venue_str)
        quote_code = "USDT"
        try:
            quote_curr = Currency.from_str(quote_code)
        except Exception:
            quote_curr = Currency(quote_code, 8, 999, quote_code, CurrencyType.CRYPTO)
            register_currency(quote_curr)

        for full_symbol in symbols:
            raw_symbol = full_symbol.split(":")[-1] if ":" in full_symbol else full_symbol
            clean_symbol = raw_symbol.split(".")[0] if "." in raw_symbol else raw_symbol
            base_code = clean_symbol.replace(quote_code, "")
            try:
                base_curr = Currency.from_str(base_code)
            except Exception:
                base_curr = Currency(base_code, 8, 999, base_code, CurrencyType.CRYPTO)
                register_currency(base_curr)

            sym_obj = Symbol(clean_symbol)
            inst_id = InstrumentId(sym_obj, venue)

            inst = CurrencyPair(
                instrument_id=inst_id,
                raw_symbol=sym_obj,
                base_currency=base_curr,
                quote_currency=quote_curr,
                price_precision=2,
                size_precision=5,
                price_increment=Price.from_str("0.01"),
                size_increment=Quantity.from_str("0.00001"),
                lot_size=Quantity.from_str("0.00001"),
                max_quantity=Quantity.from_str("1000000"),
                min_quantity=Quantity.from_str("0.00001"),
                max_price=Price.from_str("1000000"),
                min_price=Price.from_str("0.01"),
                margin_init=0,
                margin_maint=0,
                maker_fee=0,
                taker_fee=0,
                ts_event=0,
                ts_init=0,
            )

            try:
                if hasattr(self.cache, "add_instrument"):
                    self.cache.add_instrument(inst)
                elif hasattr(self.cache, "_instruments"):
                    self.cache._instruments[inst_id] = inst
                logger.info(f"Injected dummy instrument: {inst_id}")
            except Exception as e:
                logger.error(f"Failed to inject {inst_id}: {e}")

    def _get_live_equity(self) -> float:
        nav = self._get_nav()
        if nav < 1.0:
            return 100_000.0
        return nav

    def _get_nav(self) -> float:
        """Robustly extracts total equity from portfolio."""
        if not HAS_NAUTILUS:
            return 0.0
        total_cash = 0.0

        try:
            accounts = []
            try:
                accounts = self.cache.accounts()
            except Exception:
                pass

            if not accounts and self.mode == "SHADOW":
                total_cash = 100000.0
            else:
                for acct in accounts:
                    if str(acct.venue) == self.venue_str:
                        for balance in acct.balances():
                            money_obj = getattr(balance, "total", balance)
                            if hasattr(money_obj, "as_double"):
                                total_cash += money_obj.as_double()
                            elif hasattr(money_obj, "float_value"):
                                total_cash += money_obj.float_value()
                            else:
                                total_cash += float(money_obj)
        except Exception as e:
            logger.debug(f"Could not get cash balance from cache: {e}")

        pos_value = 0.0
        positions = self._get_positions()
        for pos in positions:
            try:
                last_quote = self.cache.quote_tick(pos.instrument_id)
                if last_quote:
                    price = float(last_quote.bid_price if pos.quantity > 0 else last_quote.ask_price)
                else:
                    price = 1.0 if self.mode == "SHADOW" else 0.0
                pos_value += float(pos.quantity) * price
            except Exception as e:
                logger.debug(f"Failed to calc position value for {pos.instrument_id}: {e}")
        return total_cash + pos_value

    def on_stop(self):
        super().on_stop()
        self.running = False

    def _watch_file(self):
        while self.running:
            try:
                if os.path.exists(self.weights_file):
                    mtime = os.path.getmtime(self.weights_file)
                    if mtime > self.last_mtime:
                        self.last_mtime = mtime
                        self._load_weights()
            except Exception as e:
                logger.error(f"Error watching weights file: {e}")
            time.sleep(5)

    def _load_weights(self):
        try:
            with open(self.weights_file, "r") as f:
                data = json.load(f)

            if "winners" in data:
                winner = data["winners"][0]
                assets = winner.get("assets", [])
                weights_map = {a["Symbol"]: a["Weight"] for a in assets}
            elif "weights" in data:
                weights_map = data["weights"]
            else:
                weights_map = data

            df = pd.DataFrame([weights_map])
            df.index = pd.to_datetime([pd.Timestamp.now(tz="UTC")])
            self.target_weights = df
            logger.info(f"Loaded {len(weights_map)} target weights from {self.weights_file}")
            self._rebalance_portfolio()
        except Exception as e:
            logger.error(f"Failed to load weights: {e}")

    def _get_positions(self) -> List[Any]:
        """Robustly returns a list of current positions."""
        if hasattr(self.cache, "positions"):
            return self.cache.positions()
        elif hasattr(self.portfolio, "positions"):
            return self.portfolio.positions()
        return []

    def _rebalance_portfolio(self):
        if not HAS_NAUTILUS or self.target_weights.empty:
            return

        targets = self.target_weights.iloc[0]
        target_symbols = set(targets.index)
        positions = self._get_positions()
        current_holdings = {str(pos.instrument_id) for pos in positions}
        all_symbols = target_symbols | current_holdings

        logger.info(f"Rebalancing {len(all_symbols)} symbols...")

        for symbol_str in all_symbols:
            # Normalize symbol format
            if ":" in symbol_str:
                parts = symbol_str.split(":")
                nautilus_symbol = f"{parts[1]}.{parts[0]}"
            else:
                nautilus_symbol = symbol_str

            try:
                instrument_id = InstrumentId.from_str(nautilus_symbol)
                instrument = self.cache.instrument(instrument_id)
                if not instrument:
                    continue

                weight = float(targets.get(symbol_str, targets.get(nautilus_symbol, 0.0)))

                # Get current price
                last_quote = self.cache.quote_tick(instrument_id)
                if last_quote:
                    price = float(last_quote.bid_price if weight < 0 else last_quote.ask_price)
                else:
                    # Robust bar lookup
                    try:
                        b_spec = BarSpecification(1, BarAggregation.DAY, PriceType.LAST)
                        b_type = BarType(instrument_id, b_spec)
                        last_bar = self.cache.bar(b_type)
                        price = float(last_bar.close) if last_bar else 0.0
                    except Exception:
                        price = 0.0

                if price <= 0:
                    if self.mode == "SHADOW":
                        price = 1.0  # Simulation floor
                    else:
                        continue

                equity = self._get_live_equity()
                target_value = equity * weight * 0.98

                # Robust current quantity lookup
                current_qty = 0.0
                if self.mode == "SHADOW":
                    current_qty = _SHADOW_POSITIONS.get(nautilus_symbol, 0.0)
                else:
                    try:
                        current_qty = float(self.portfolio.net_position(instrument_id))
                    except Exception:
                        pass

                raw_qty = target_value / price

                # Apply Metadata Limits
                unified_symbol = self._from_nautilus_id_str(nautilus_symbol)
                limits = self.catalog.get_limits(unified_symbol, self.venue_str)

                step = float(getattr(instrument, "size_increment", 0.00001))
                min_notional = 0.0
                if limits:
                    step = limits.step_size
                    min_notional = limits.min_notional

                qty = math.floor(raw_qty / step) * step if step > 0 else raw_qty

                if abs(qty * price) < min_notional:
                    qty = 0.0

                delta = qty - current_qty

                if abs(delta * price) > max(10.0, equity * 0.001):
                    self._execute_rebalance_live(instrument, delta)
            except Exception as e:
                logger.error(f"Error rebalancing {symbol_str}: {e}")

        self._persist_state()

    def _execute_rebalance_live(self, instrument, delta):
        side = OrderSide.BUY if delta > 0 else OrderSide.SELL
        qty = abs(delta)
        nautilus_symbol = str(instrument.id)

        if self.mode == "SHADOW":
            logger.info(f"✨ [SHADOW ORDER] {side} {qty:.4f} {instrument.id}")
            old_qty = _SHADOW_POSITIONS.get(nautilus_symbol, 0.0)
            _SHADOW_POSITIONS[nautilus_symbol] = old_qty + delta
            return

        logger.info(f"🚀 [LIVE ORDER] Submitting {side} {qty:.4f} {instrument.id}")
        try:
            order = self.order_factory.market(instrument.id, side, Quantity.from_scalar(qty, instrument.size_precision))
            self.submit_order(order)
        except Exception as e:
            logger.error(f"Failed to submit order for {instrument.id}: {e}")

    def _persist_state(self):
        """Syncs Nautilus portfolio positions to the lakehouse state file."""
        if not HAS_NAUTILUS:
            return
        try:
            equity = self._get_live_equity()

            assets = []
            if self.mode == "SHADOW":
                for sym, qty in _SHADOW_POSITIONS.items():
                    if abs(qty) < 1e-8:
                        continue
                    last_quote = self.cache.quote_tick(InstrumentId.from_str(sym))
                    price = float(last_quote.bid_price if qty > 0 else last_quote.ask_price) if last_quote else 1.0
                    weight = (qty * price) / equity if equity > 0 else 0.0
                    assets.append({"Symbol": self._from_nautilus_id_str(sym), "Weight": weight, "Quantity": qty, "Price": price, "Venue": sym.split(".")[-1]})
            else:
                positions = self._get_positions()
                for pos in positions:
                    sym = self._from_nautilus_id_str(str(pos.instrument_id))
                    last_quote = self.cache.quote_tick(pos.instrument_id)
                    price = float(last_quote.bid_price if pos.quantity > 0 else last_quote.ask_price) if last_quote else 0.0
                    weight = (float(pos.quantity) * price) / equity if equity > 0 else 0.0
                    assets.append({"Symbol": sym, "Weight": weight, "Quantity": float(pos.quantity), "Price": price, "Venue": str(pos.instrument_id.venue)})

            state = {}
            if os.path.exists(self.state_file):
                with open(self.state_file, "r") as f:
                    state = json.load(f)

            profile_key = f"LIVE_{self.venue_str}_{self.mode}"
            state[profile_key] = {"assets": assets, "equity": equity, "updated_at": pd.Timestamp.now(tz="UTC").isoformat()}
            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=2)
            logger.info(f"Persisted live state to {self.state_file} [Profile: {profile_key}]")
        except Exception as e:
            logger.error(f"Failed to persist state: {e}")

    def _from_nautilus_id_str(self, id_str: str) -> str:
        if "." in id_str:
            parts = id_str.split(".")
            return f"{parts[1]}:{parts[0]}"
        return id_str
