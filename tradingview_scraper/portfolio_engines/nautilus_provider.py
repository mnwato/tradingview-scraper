import logging
import math
from typing import Any, Dict, Optional

import pandas as pd

try:
    import nautilus_trader.model.currencies as currencies_mod
    from nautilus_trader.model.currencies import USD, register_currency
    from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
    from nautilus_trader.model.instruments import CurrencyPair, Equity
    from nautilus_trader.model.objects import Price, Quantity

    HAS_NAUTILUS = True
except ImportError:
    HAS_NAUTILUS = False

from tradingview_scraper.execution.metadata import ExecutionLimits, ExecutionMetadataCatalog

logger = logging.getLogger(__name__)


class NautilusInstrumentProvider:
    """
    Bridges ExecutionMetadataCatalog and NautilusTrader Instruments.
    """

    def __init__(self, catalog: Optional[ExecutionMetadataCatalog] = None):
        self.catalog = catalog or ExecutionMetadataCatalog()

    def get_instruments(self, venue: str) -> Dict[str, Any]:
        """
        Returns a mapping of unified symbols to Nautilus Instrument objects.
        """
        df = self.catalog._df
        venue_df = df[df["venue"] == venue]

        instruments = {}
        # Use an old timestamp to ensure instruments exist before data
        past_ns = 0

        for _, row in venue_df.iterrows():
            unified_symbol = str(row["symbol"])
            inst = self._create_nautilus_instrument(unified_symbol, venue, row, past_ns)
            if inst:
                instruments[unified_symbol] = inst

        return instruments

    def get_instrument_for_symbol(self, unified_symbol: str) -> Optional[Any]:
        """
        Creates a single instrument object.
        """
        if ":" not in unified_symbol:
            return None

        venue = unified_symbol.split(":")[0]
        limits = self.catalog.get_limits(unified_symbol, venue)
        past_ns = 0

        if limits is None:
            limits = ExecutionLimits(
                symbol=unified_symbol,
                venue=venue,
                tick_size=0.00000001,
                step_size=0.00000001,
                lot_size=1.0,
                min_notional=0.0,
                maker_fee=0.0,
                taker_fee=0.0,
                contract_size=1.0,
                updated_at=pd.Timestamp.now(),
            )

        return self._create_nautilus_instrument(unified_symbol, venue, limits, past_ns)

    def _create_nautilus_instrument(self, unified_symbol: str, venue: str, limits: Any, ts_ns: int) -> Optional[Any]:
        if not HAS_NAUTILUS:
            return None

        symbol_part = unified_symbol.split(":")[-1]

        if isinstance(limits, ExecutionLimits):
            tick_size = limits.tick_size
            step_size = limits.step_size
            lot_size_val = limits.lot_size or step_size
        else:
            tick_size = float(limits["tick_size"]) if not pd.isna(limits["tick_size"]) else 0.00000001
            step_size = float(limits["step_size"]) if not pd.isna(limits["step_size"]) else 0.00000001
            lot_size_val = float(limits["lot_size"]) if not pd.isna(limits.get("lot_size", step_size)) else step_size

        price_precision = self._size_to_precision(tick_size)
        size_precision = self._size_to_precision(step_size)

        is_crypto = any(x in venue.upper() for x in ["BINANCE", "BITGET", "OKX", "BYBIT"])
        inst_id = InstrumentId(Symbol(symbol_part), Venue(venue))
        raw_symbol = Symbol(symbol_part)

        try:
            if is_crypto and len(symbol_part) > 5:
                base_code = symbol_part[:3]
                quote_code = symbol_part[3:]
                inst = CurrencyPair(
                    inst_id,
                    raw_symbol,
                    self._get_currency(base_code),
                    self._get_currency(quote_code),
                    price_precision,
                    size_precision,
                    Price(tick_size, price_precision),
                    Quantity(step_size, size_precision),
                    ts_ns,
                    ts_ns,
                )
            else:
                inst = Equity(inst_id, raw_symbol, USD, price_precision, Price(tick_size, price_precision), Quantity(lot_size_val, size_precision), ts_ns, ts_ns)
            return inst
        except Exception as e:
            logger.error(f"Failed to create Nautilus instrument for {unified_symbol}: {e}")
            return None

    def _get_currency(self, code: str) -> Any:
        if hasattr(currencies_mod, code):
            return getattr(currencies_mod, code)
        try:
            return register_currency(code, code, code, 0, 8)
        except Exception:
            return USD

    def _size_to_precision(self, size: float) -> int:
        if size <= 0:
            return 8
        return max(0, int(-math.log10(size)))
