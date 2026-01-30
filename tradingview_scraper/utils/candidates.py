from __future__ import annotations

from typing import Any, Dict, Optional

CANONICAL_KEYS = {
    "symbol",
    "exchange",
    "asset_type",
    "identity",
    "market_cap_rank",
    "volume_24h",
    "sector",
    "industry",
    "metadata",
}


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def normalize_candidate_record(raw: Dict[str, Any], *, strict: bool) -> Optional[Dict[str, Any]]:
    """
    Normalize heterogeneous candidate dicts into the canonical CandidateMetadata-as-dict schema.

    Canonical keys (minimum set):
      - symbol: "EXCHANGE:SYMBOL"
      - exchange: "EXCHANGE"
      - asset_type: "spot" | "perp" | "equity" | "etf" | ...
      - identity: "EXCHANGE:SYMBOL" (exactly)
      - metadata: dict (free-form)

    In strict mode, invalid/unrecoverable records raise ValueError.
    In non-strict mode, invalid records return None.
    """
    if not isinstance(raw, dict):
        if strict:
            raise ValueError("Candidate record must be a dict")
        return None

    symbol_raw = raw.get("symbol", raw.get("Symbol"))
    symbol = _as_str(symbol_raw)
    if not symbol:
        if strict:
            raise ValueError("Candidate record missing required field: symbol")
        return None

    exchange_raw = raw.get("exchange", raw.get("Exchange"))
    exchange = _as_str(exchange_raw)

    # Normalize symbol to EXCHANGE:SYMBOL.
    if ":" in symbol:
        sym_exchange = symbol.split(":", 1)[0]
        if not exchange:
            exchange = sym_exchange
        elif exchange != sym_exchange:
            if strict:
                raise ValueError(f"Candidate exchange mismatch: exchange={exchange} symbol_prefix={sym_exchange}")
            # Prefer symbol prefix for determinism; keep the original under metadata.
            raw = dict(raw)
            raw.setdefault("metadata", {})
            if isinstance(raw["metadata"], dict):
                raw["metadata"].setdefault("_exchange_original", exchange)
            exchange = sym_exchange
    else:
        if not exchange:
            if strict:
                raise ValueError("Candidate record missing exchange and symbol is not prefixed (expected EXCHANGE:SYMBOL)")
            exchange = "UNKNOWN"
        symbol = f"{exchange}:{symbol}"

    asset_type = _as_str(raw.get("asset_type", raw.get("type", "spot"))) or "spot"

    identity = _as_str(raw.get("identity")) or symbol
    # Identity is a canonical unique key; it must match symbol exactly.
    identity = symbol

    # Metadata should preserve any non-canonical keys to avoid silently dropping information.
    metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    for k, v in raw.items():
        if k in CANONICAL_KEYS:
            continue
        metadata.setdefault(k, v)

    return {
        "symbol": symbol,
        "exchange": exchange,
        "asset_type": asset_type,
        "identity": identity,
        "market_cap_rank": raw.get("market_cap_rank"),
        "volume_24h": raw.get("volume_24h", raw.get("volume")),
        "sector": raw.get("sector"),
        "industry": raw.get("industry"),
        "metadata": metadata,
    }
