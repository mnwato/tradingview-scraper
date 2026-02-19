"""Top-100 market-cap oversold screener based on RSI and volume trend."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from tradingview_scraper.symbols.screener import Screener

DEFAULT_COLUMNS_BASE = ["name", "market_cap_basic", "RSI", "volume"]
DEFAULT_ALLOWED_EXCHANGES = ("NASDAQ", "NYSE")
DEFAULT_VOLUME_AVERAGE_FIELD_CANDIDATES = [
    "average_volume_20d_calc",
    "average_volume_30d_calc",
    "average_volume_10d_calc",
]


def _extract_exchange(symbol: str) -> str:
    if not isinstance(symbol, str) or ":" not in symbol:
        return ""
    return symbol.split(":", 1)[0]


def _is_signal_match(row: Dict[str, Any], volume_average_field: str, rsi_threshold: float) -> bool:
    try:
        rsi = float(row.get("RSI"))
        volume = float(row.get("volume"))
        average_volume = float(row.get(volume_average_field))
    except (TypeError, ValueError):
        return False

    return rsi <= rsi_threshold and volume > average_volume


def screen_top100_oversold_with_rising_volume(
    screener: Optional[Screener] = None,
    market: str = "america",
    limit: int = 100,
    universe_scan_limit: int = 5000,
    rsi_threshold: float = 30,
    allowed_exchanges: Iterable[str] = DEFAULT_ALLOWED_EXCHANGES,
    include_universe: bool = False,
    volume_average_field_candidates: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """
    Screen top market-cap symbols where RSI is oversold and volume is above average.
    """
    screener_client = screener or Screener()
    attempts: List[Dict[str, str]] = []
    candidates = list(
        volume_average_field_candidates or DEFAULT_VOLUME_AVERAGE_FIELD_CANDIDATES
    )
    allowed_exchanges_set = {exchange.upper() for exchange in allowed_exchanges}

    for volume_average_field in candidates:
        columns = [*DEFAULT_COLUMNS_BASE, volume_average_field]
        try:
            result = screener_client.screen(
                market=market,
                columns=columns,
                sort_by="market_cap_basic",
                sort_order="desc",
                limit=universe_scan_limit,
            )
        except Exception as exc:  # pragma: no cover - defensive path
            attempts.append({"field": volume_average_field, "error": str(exc)})
            continue

        if result.get("status") == "success":
            source_rows = result.get("data", [])
            restricted_universe = [
                row
                for row in source_rows
                if _extract_exchange(row.get("symbol", "")) in allowed_exchanges_set
            ][:limit]
            filtered_rows = [
                row
                for row in restricted_universe
                if _is_signal_match(
                    row=row,
                    volume_average_field=volume_average_field,
                    rsi_threshold=rsi_threshold,
                )
            ]
            response = {
                **result,
                "data": filtered_rows,
                "total": len(filtered_rows),
                "volume_average_field": volume_average_field,
            }
            if include_universe:
                response["universe"] = restricted_universe
                response["universe_size"] = len(restricted_universe)
            return response

        attempts.append(
            {
                "field": volume_average_field,
                "error": result.get("error", "unknown error"),
            }
        )

    return {
        "status": "failed",
        "error": "screening failed for all volume average field candidates",
        "attempts": attempts,
    }
