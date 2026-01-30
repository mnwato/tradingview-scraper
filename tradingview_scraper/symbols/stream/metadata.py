import logging
import os
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, cast

import exchange_calendars as xcals
import pandas as pd

logger = logging.getLogger(__name__)


class DataProfile(Enum):
    CRYPTO = "CRYPTO"
    EQUITY = "EQUITY"
    FUTURES = "FUTURES"
    FOREX = "FOREX"
    UNKNOWN = "UNKNOWN"


# Canonical metadata for common exchanges
# Mapping TradingView exchange codes to exchange_calendars canonical names
DEFAULT_EXCHANGE_METADATA = {
    "BINANCE": {"timezone": "UTC", "is_crypto": True, "country": "Global", "profile": DataProfile.CRYPTO, "calendar": "XCRY"},
    "OKX": {"timezone": "UTC", "is_crypto": True, "country": "Global", "profile": DataProfile.CRYPTO, "calendar": "XCRY"},
    "BYBIT": {"timezone": "UTC", "is_crypto": True, "country": "Global", "profile": DataProfile.CRYPTO, "calendar": "XCRY"},
    "BITGET": {"timezone": "UTC", "is_crypto": True, "country": "Global", "profile": DataProfile.CRYPTO, "calendar": "XCRY"},
    "THINKMARKETS": {"timezone": "UTC", "is_crypto": False, "country": "Global", "profile": DataProfile.FOREX, "calendar": "24/5"},
    "NASDAQ": {"timezone": "America/New_York", "is_crypto": False, "country": "United States", "profile": DataProfile.EQUITY, "calendar": "XNYS"},
    "NYSE": {"timezone": "America/New_York", "is_crypto": False, "country": "United States", "profile": DataProfile.EQUITY, "calendar": "XNYS"},
    "AMEX": {"timezone": "America/New_York", "is_crypto": False, "country": "United States", "profile": DataProfile.EQUITY, "calendar": "XNYS"},
    "CME": {"timezone": "America/Chicago", "is_crypto": False, "country": "United States", "profile": DataProfile.FUTURES, "calendar": "CMES"},
    "CME_MINI": {"timezone": "America/Chicago", "is_crypto": False, "country": "United States", "profile": DataProfile.FUTURES, "calendar": "CMES"},
    "CBOT": {"timezone": "America/Chicago", "is_crypto": False, "country": "United States", "profile": DataProfile.FUTURES, "calendar": "CMES"},
    "COMEX": {"timezone": "America/Chicago", "is_crypto": False, "country": "United States", "profile": DataProfile.FUTURES, "calendar": "CMES"},
    "NYMEX": {"timezone": "America/Chicago", "is_crypto": False, "country": "United States", "profile": DataProfile.FUTURES, "calendar": "CMES"},
    "ICE": {"timezone": "America/New_York", "is_crypto": False, "country": "United States", "profile": DataProfile.FUTURES, "calendar": "ICEUS"},
    "ICEUS": {"timezone": "America/New_York", "is_crypto": False, "country": "United States", "profile": DataProfile.FUTURES, "calendar": "ICEUS"},
    "EUREX": {"timezone": "Europe/Berlin", "is_crypto": False, "country": "Germany", "profile": DataProfile.FUTURES, "calendar": "XFRA"},
    "OANDA": {"timezone": "America/New_York", "is_crypto": False, "country": "United States", "profile": DataProfile.FOREX, "calendar": "24/5"},
    "FX_IDC": {"timezone": "UTC", "is_crypto": False, "country": "Global", "profile": DataProfile.FOREX, "calendar": "24/5"},
    "FOREX": {"timezone": "America/New_York", "is_crypto": False, "country": "Global", "profile": DataProfile.FOREX, "calendar": "24/5"},
}


def get_exchange_calendar(symbol: str, profile: DataProfile = DataProfile.UNKNOWN) -> xcals.ExchangeCalendar:
    """Returns an exchange_calendars instance for the given symbol/profile."""
    exchange = symbol.split(":")[0].upper() if ":" in symbol else "UNKNOWN"

    cal_name: str = "XNYS"  # Default
    if exchange in DEFAULT_EXCHANGE_METADATA:
        # Cast to str to satisfy type checker
        val = DEFAULT_EXCHANGE_METADATA[exchange].get("calendar")
        if isinstance(val, str):
            cal_name = val
    elif profile == DataProfile.CRYPTO:
        cal_name = "XCRY"
    elif profile == DataProfile.FOREX:
        cal_name = "24/5"

    try:
        return xcals.get_calendar(cal_name)
    except Exception:
        return xcals.get_calendar("XNYS")


def get_us_holidays(year: int) -> Set[str]:
    """Returns a set of major US market holiday dates (YYYY-MM-DD)."""
    # Use XNYS as proxy for US holidays
    cal = xcals.get_calendar("XNYS")
    start = pd.Timestamp(f"{year}-01-01")
    end = pd.Timestamp(f"{year}-12-31")

    # xcals defines 'holidays' as actual closure days
    all_days = pd.date_range(start, end)

    # Cast to ensure these are valid Timestamps for exchange_calendars
    business_days = cal.sessions_in_range(cast(pd.Timestamp, start), cast(pd.Timestamp, end))
    holidays = all_days[~all_days.isin(business_days)]

    # Filter for weekdays only to get literal holidays (not weekends)
    weekday_holidays = [d for d in holidays if d.dayofweek < 5]

    return {d.strftime("%Y-%m-%d") for d in weekday_holidays}


def get_symbol_profile(symbol: str, meta: Optional[Dict] = None) -> DataProfile:
    """Determines the data profile for a symbol."""
    if not symbol:
        return DataProfile.UNKNOWN

    exchange = symbol.split(":")[0]

    # 1. Check metadata override
    if meta:
        if meta.get("is_crypto"):
            return DataProfile.CRYPTO
        stype = str(meta.get("type", "")).lower()
        if stype in ["spot", "swap", "crypto"]:
            return DataProfile.CRYPTO
        if stype in ["stock", "fund", "dr", "index"]:
            return DataProfile.EQUITY
        if stype in ["futures", "commodity"]:
            return DataProfile.FUTURES
        if stype in ["forex", "fx"]:
            return DataProfile.FOREX

    # 2. Check exchange defaults
    if exchange in DEFAULT_EXCHANGE_METADATA:
        profile = DEFAULT_EXCHANGE_METADATA[exchange].get("profile")
        if isinstance(profile, DataProfile):
            return profile

    # 3. Last resort heuristics
    if ".P" in symbol or "USDT" in symbol:
        return DataProfile.CRYPTO

    return DataProfile.UNKNOWN


class MetadataCatalog:
    """
    Manages the symbol metadata catalog for the Data Lakehouse.

    Acts as the single source of truth for instrument definitions,
    providing lookup and search capabilities.
    """

    def __init__(self, base_path: str | Path | None = None):
        from tradingview_scraper.settings import get_settings

        settings = get_settings()
        self.base_path = Path(base_path) if base_path else settings.lakehouse_dir
        self.catalog_path = self.base_path / "symbols.parquet"
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._df = self._load_catalog()

    def _load_catalog(self) -> pd.DataFrame:
        """Loads the catalog from disk or returns an empty DataFrame."""
        # Standard schema including PIT and enriched fields.
        # New columns may be added over time; missing columns are backfilled as null.
        required_cols: List[str] = [
            "symbol",
            "exchange",
            "base",
            "quote",
            "type",
            "subtype",
            "profile",
            "description",
            "sector",
            "industry",
            "country",
            "pricescale",
            "minmov",
            "tick_size",
            "lot_size",
            "contract_size",
            "timezone",
            "session",
            "active",
            "updated_at",
            "valid_from",
            "valid_until",
        ]

        if os.path.exists(self.catalog_path):
            try:
                df = pd.read_parquet(self.catalog_path)
                for col in required_cols:
                    if col not in df.columns:
                        df[col] = None
                return df
            except Exception as e:
                logger.error(f"Failed to load metadata catalog: {e}")

        return pd.DataFrame(data=None, columns=pd.Index(required_cols))

    def upsert_symbols(self, symbols_data: List[Dict]):
        """Inserts or updates multiple symbol definitions using SCD Type 2."""
        if not symbols_data:
            return

        def _is_missing(value) -> bool:
            if value is None:
                return True
            if isinstance(value, str) and value.strip() == "":
                return True
            try:
                return bool(pd.isna(value))
            except Exception:
                return False

        def _normalize_profile(value) -> Optional[str]:
            if isinstance(value, DataProfile):
                return value.value
            if _is_missing(value):
                return None
            return str(value)

        def _ensure_symbol_record(record: Dict) -> Dict:
            sym = str(record.get("symbol") or "").strip()
            if not sym:
                return record

            record["symbol"] = sym

            if _is_missing(record.get("exchange")) and ":" in sym:
                record["exchange"] = sym.split(":", 1)[0]

            # Normalize numeric fields
            for numeric_field in ["pricescale", "minmov"]:
                val = record.get(numeric_field)
                if not _is_missing(val):
                    try:
                        record[numeric_field] = int(float(str(val)))
                    except Exception:
                        pass

            if _is_missing(record.get("tick_size")):
                ps_val = record.get("pricescale")
                mm_val = record.get("minmov")
                if not _is_missing(ps_val) and not _is_missing(mm_val):
                    try:
                        ps = float(str(ps_val))
                        mm = float(str(mm_val))
                        record["tick_size"] = (mm / ps) if ps else None
                    except Exception:
                        pass

            # Persist profile (required)
            profile_val = _normalize_profile(record.get("profile"))
            if profile_val is None:
                record["profile"] = get_symbol_profile(sym, record).value
            else:
                record["profile"] = profile_val

            # Resolve timezone/session/country only if missing
            exchange = record.get("exchange")
            ex_defaults = DEFAULT_EXCHANGE_METADATA.get(str(exchange), {}) if exchange else {}

            if _is_missing(record.get("timezone")):
                record["timezone"] = ex_defaults.get("timezone") or "UTC"

            if _is_missing(record.get("session")):
                record["session"] = "24x7" if record.get("profile") == DataProfile.CRYPTO.value else "Unknown"

            if _is_missing(record.get("country")) and ex_defaults.get("country") is not None:
                record["country"] = ex_defaults.get("country")

            if "active" not in record or _is_missing(record.get("active")):
                record["active"] = True

            return record

        def _values_equal(left, right) -> bool:
            if _is_missing(left) and _is_missing(right):
                return True

            if isinstance(left, DataProfile):
                left = left.value
            if isinstance(right, DataProfile):
                right = right.value

            # Numeric tolerance
            if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                try:
                    return abs(float(left) - float(right)) <= 1e-12
                except Exception:
                    return left == right

            return left == right

        meaningful_fields = [
            "exchange",
            "base",
            "quote",
            "type",
            "subtype",
            "profile",
            "description",
            "sector",
            "industry",
            "country",
            "pricescale",
            "minmov",
            "tick_size",
            "lot_size",
            "contract_size",
            "timezone",
            "session",
            "active",
        ]

        def _has_meaningful_changes(old: Dict, new: Dict) -> bool:
            for field in meaningful_fields:
                if not _values_equal(old.get(field), new.get(field)):
                    return True
            return False

        now_ts = pd.Timestamp.now()
        new_records = []

        incoming_map: Dict[str, Dict] = {}
        for item in symbols_data:
            sym = item.get("symbol")
            if sym:
                incoming_map[str(sym)] = item

        # 1. Process existing active symbols
        active_mask = self._df["valid_until"].isna()
        for idx, row in self._df[active_mask].iterrows():
            sym = str(row["symbol"])
            if sym not in incoming_map:
                continue

            incoming = incoming_map[sym]

            merged = row.to_dict()
            for key, value in incoming.items():
                if not _is_missing(value):
                    merged[key] = value

            merged = _ensure_symbol_record(merged)

            if not _has_meaningful_changes(row.to_dict(), merged):
                del incoming_map[sym]
                continue

            # Retire old record
            self._df.at[idx, "valid_until"] = now_ts

            # Prepare new record
            merged["valid_from"] = now_ts
            merged["valid_until"] = None
            merged["updated_at"] = now_ts
            new_records.append(merged)

            del incoming_map[sym]

        # 2. Process completely new symbols
        for sym, data in incoming_map.items():
            record = _ensure_symbol_record(data.copy())
            record["valid_from"] = now_ts
            record["valid_until"] = None
            record["updated_at"] = now_ts
            new_records.append(record)

        # 3. Append new records
        if new_records:
            new_df = pd.DataFrame(new_records)
            if self._df.empty:
                self._df = new_df.reset_index(drop=True)
            else:
                self._df = pd.concat([self._df, new_df], ignore_index=True)

        self.save()

    def retire_symbols(self, symbols: List[str]):
        """
        Marks symbols as inactive and ends their validity window using SCD Type 2.
        """
        if not symbols:
            return

        now_ts = pd.Timestamp.now()
        new_records = []

        # Find active records for these symbols
        mask = (self._df["symbol"].isin(symbols)) & (self._df["valid_until"].isna())

        for idx, row in self._df[mask].iterrows():
            # 1. Expire the old record
            self._df.at[idx, "valid_until"] = now_ts

            # 2. Create a new "Inactive" record for the future
            record = row.to_dict()
            record["active"] = False
            record["valid_from"] = now_ts
            record["valid_until"] = None
            record["updated_at"] = now_ts
            new_records.append(record)

        if new_records:
            new_df = pd.DataFrame(new_records)
            if self._df.empty:
                self._df = new_df.reset_index(drop=True)
            else:
                self._df = pd.concat([self._df, new_df], ignore_index=True)
            self.save()
            logger.info(f"Retired {len(new_records)} symbols. New inactive versions created.")

    def get_instrument(self, symbol: str, as_of: Optional[float] = None) -> Optional[Dict]:
        """
        Retrieves metadata for a specific symbol.

        Args:
            symbol: The symbol to look up.
            as_of: Optional timestamp (float or datetime) for Point-in-Time lookup.
                   If None, returns the current active record.
        """
        if self._df.empty:
            return None

        # Base filter by symbol
        mask = self._df["symbol"] == symbol

        if as_of is None:
            # Get currently active
            mask &= self._df["valid_until"].isna()
        else:
            # PIT lookup
            ts = pd.Timestamp(as_of)
            mask &= (self._df["valid_from"] <= ts) & ((self._df["valid_until"].isna()) | (self._df["valid_until"] > ts))

        match = self._df[mask]
        if match.empty:
            return None

        return match.iloc[0].to_dict()

    def list_active_symbols(self, exchange: Optional[str] = None) -> List[str]:
        """Returns a list of active symbols, optionally filtered by exchange."""
        if self._df.empty:
            return []

        query = self._df[(self._df["active"] == True) & (self._df["valid_until"].isna())]
        if exchange:
            query = query[query["exchange"] == exchange]

        return query["symbol"].tolist()

    def save(self):
        """Persists the catalog to disk."""
        self._df.to_parquet(self.catalog_path, index=False)
        logger.info(f"Metadata catalog saved with {len(self._df)} entries.")


class ExchangeCatalog:
    """
    Manages the exchange metadata catalog for the Data Lakehouse.
    """

    def __init__(self, base_path: str | Path | None = None):
        from tradingview_scraper.settings import get_settings

        settings = get_settings()
        self.base_path = Path(base_path) if base_path else settings.lakehouse_dir
        self.catalog_path = self.base_path / "exchanges.parquet"
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._df = self._load_catalog()

    def _load_catalog(self) -> pd.DataFrame:
        """Loads the catalog from disk or returns an empty DataFrame."""
        if os.path.exists(self.catalog_path):
            try:
                return pd.read_parquet(self.catalog_path)
            except Exception as e:
                logger.error(f"Failed to load exchange catalog: {e}")

        cols: List[str] = ["exchange", "country", "timezone", "is_crypto", "description", "updated_at"]
        return pd.DataFrame(data=None, columns=pd.Index(cols))

    def upsert_exchange(self, exchange_data: Dict):
        """Inserts or updates an exchange definition."""
        name = exchange_data.get("exchange")
        if not name:
            return

        new_row = exchange_data.copy()
        new_row["updated_at"] = pd.Timestamp.now()
        new_df = pd.DataFrame([new_row])

        if self._df.empty:
            self._df = new_df
        else:
            self._df = pd.concat([self._df, new_df]).drop_duplicates(subset=["exchange"], keep="last")

        self.save()

    def get_exchange(self, exchange: str) -> Optional[Dict]:
        """Retrieves metadata for a specific exchange."""
        if self._df.empty:
            return None
        match = self._df[self._df["exchange"] == exchange]
        return match.iloc[0].to_dict() if not match.empty else None

    def save(self):
        """Persists the catalog to disk."""
        self._df.to_parquet(self.catalog_path, index=False)
        logger.info(f"Exchange catalog saved with {len(self._df)} entries.")


class MetadataService:
    """
    Higher-level service for interacting with the Metadata Catalog.
    Will eventually handle hybrid sourcing (TV + CCXT).
    """

    def __init__(self, catalog: Optional[MetadataCatalog] = None):
        self.catalog = catalog or MetadataCatalog()

    def resolve_symbol(self, symbol: str) -> Dict:
        """
        Attempts to find metadata for a symbol.
        If missing, this would be where 'Discovery' is triggered.
        """
        meta = self.catalog.get_instrument(symbol)
        if meta:
            return meta

        # TODO: Trigger discovery/enrichment if symbol is unknown
        return {"symbol": symbol, "error": "Not in catalog"}
