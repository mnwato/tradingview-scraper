import logging
from typing import Any, Dict, List, Optional, cast

import pandas as pd

# Define types for linter
Bar: Any = cast(Any, None)
BarType: Any = cast(Any, None)
BarSpecification: Any = cast(Any, None)
InstrumentId: Any = cast(Any, None)
BarAggregation: Any = cast(Any, None)
PriceType: Any = cast(Any, None)
Price: Any = cast(Any, None)
Quantity: Any = cast(Any, None)

try:
    from nautilus_trader.model.data import Bar as _Bar
    from nautilus_trader.model.data import BarSpecification as _BarSpecification
    from nautilus_trader.model.data import BarType as _BarType
    from nautilus_trader.model.enums import BarAggregation as _BarAggregation
    from nautilus_trader.model.enums import PriceType as _PriceType
    from nautilus_trader.model.identifiers import InstrumentId as _InstrumentId
    from nautilus_trader.model.objects import Price as _Price
    from nautilus_trader.model.objects import Quantity as _Quantity

    Bar = _Bar
    BarType = _BarType
    BarSpecification = _BarSpecification
    InstrumentId = _InstrumentId
    BarAggregation = _BarAggregation
    PriceType = _PriceType
    Price = _Price
    Quantity = _Quantity

    HAS_NAUTILUS = True
except ImportError:
    HAS_NAUTILUS = False

logger = logging.getLogger(__name__)


class NautilusDataConverter:
    """
    Converts return DataFrames to synthesized Nautilus Bars.
    """

    def _to_nautilus_id_str(self, symbol: str) -> str:
        """Converts VENUE:SYMBOL to SYMBOL.VENUE for Nautilus."""
        if ":" in symbol:
            parts = symbol.split(":")
            return f"{parts[1]}.{parts[0]}"
        return symbol

    def to_nautilus_bars(self, returns: pd.DataFrame, base_price: float = 100.0, instrument_map: Optional[Dict[str, Any]] = None) -> Dict[str, List[Any]]:
        """
        Synthesizes OHLC bars from daily returns.
        """
        bars_dict = {}

        for symbol in returns.columns:
            symbol_str = str(symbol)
            symbol_returns = returns[symbol]

            curr_price = base_price
            symbol_bars = []

            p_prec = 8
            s_prec = 8
            target_id = None

            if instrument_map and symbol_str in instrument_map:
                inst = instrument_map[symbol_str]
                if hasattr(inst, "id"):
                    target_id = inst.id
                    p_prec = inst.price_precision
                    s_prec = inst.size_precision
                elif isinstance(inst, dict):
                    p_prec = inst.get("price_precision", 8)
                    s_prec = inst.get("size_precision", 8)

            if target_id is None:
                id_str = self._to_nautilus_id_str(symbol_str)
                target_id = InstrumentId.from_str(id_str)

            # print(f"DEBUG: to_nautilus_bars symbol={symbol_str} target_id={target_id}")

            for ts, ret in symbol_returns.items():
                val = float(ret)
                if pd.isna(val):
                    val = 0.0
                curr_price *= 1.0 + val

                if HAS_NAUTILUS and Bar is not None:
                    ts_pd = pd.Timestamp(ts)
                    ts_ns = int(ts_pd.value)

                    bar_spec = BarSpecification(1, BarAggregation.DAY, PriceType.LAST)
                    bar_type = BarType(target_id, bar_spec)

                    bar = Bar(
                        bar_type,
                        Price(float(curr_price), p_prec),
                        Price(float(curr_price), p_prec),
                        Price(float(curr_price), p_prec),
                        Price(float(curr_price), p_prec),
                        Quantity(0.0, s_prec),
                        ts_ns,
                        ts_ns,
                    )
                    symbol_bars.append(bar)
                else:
                    symbol_bars.append({"ts": ts, "open": float(curr_price), "high": float(curr_price), "low": float(curr_price), "close": float(curr_price), "volume": 0.0})

            bars_dict[symbol_str] = symbol_bars

        return bars_dict

    def write_parquet_catalog(self, returns: pd.DataFrame, path: str):
        pass
