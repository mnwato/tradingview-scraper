import logging
from typing import Any, Dict, List

from tradingview_scraper.futures_universe_selector import (
    FuturesUniverseSelector,
    load_config,
)
from tradingview_scraper.pipelines.discovery.base import (
    BaseDiscoveryScanner,
    CandidateMetadata,
)
from tradingview_scraper.pipelines.selection.base import (
    AdvancedToxicityValidator,
    FoundationHealthRegistry,
)
from tradingview_scraper.settings import get_settings

logger = logging.getLogger(__name__)


class TradingViewDiscoveryScanner(BaseDiscoveryScanner):
    """
    Discovery scanner that leverages the TradingView Screener API
    via FuturesUniverseSelector.
    """

    def __init__(self):
        self.settings = get_settings()
        self.registry = FoundationHealthRegistry(path=self.settings.lakehouse_dir / "foundation_health.json")

    @property
    def name(self) -> str:
        return "tradingview"

    def discover(self, params: Dict[str, Any]) -> List[CandidateMetadata]:
        """
        Executes a TradingView screen and maps results to CandidateMetadata.
        """
        # 1. Load config (handles inheritance if base_preset is in params)
        try:
            config_source: Any = params
            if isinstance(params, dict) and params.get("config_path"):
                config_source = str(params["config_path"])

            cfg = load_config(config_source)
            selector = FuturesUniverseSelector(cfg)

            # 2. Run the selector
            result = selector.run()

            if result.get("status") not in ["success", "partial_success"]:
                logger.error(f"TradingView screen failed: {result.get('errors')}")
                return []

            # 3. Map to CandidateMetadata with Sanity Gate
            candidates = []
            for row in result.get("data", []):
                raw_symbol = row.get("symbol")
                if not raw_symbol:
                    continue

                # Registry-Aware Veto (Phase 520)
                if not self.registry.is_healthy(raw_symbol) and raw_symbol in self.registry.data:
                    reg_entry = self.registry.data[raw_symbol]
                    if reg_entry.get("status") == "toxic":
                        logger.info(f"Discovery Gate: Vetoing known TOXIC asset: {raw_symbol} (Reason: {reg_entry.get('reason')})")
                        continue

                # Microstructure Veto (Fail-fast in discovery)
                # Note: Scanners often return single OHLCV snapshot.
                # If they return a list (historical), we can use AdvancedToxicityValidator.
                # FuturesUniverseSelector rows contain 'volume' and 'close'.

                # Heuristic: if selector didn't already filter it, we do a basic check here
                vol = row.get("volume", 0)
                if vol == 0:
                    logger.info(f"Discovery Gate: Vetoing zero-volume asset: {raw_symbol}")
                    continue

                # Extract exchange from symbol if not present in row
                exchange = row.get("exchange")
                if not exchange and ":" in raw_symbol:
                    exchange = raw_symbol.split(":")[0]
                exchange = exchange or "UNKNOWN"

                # Determine asset type
                # (This is a bit heuristic, could be improved)
                asset_type = row.get("type", "spot")
                if str(raw_symbol).endswith(".P"):
                    asset_type = "perp"

                # Normalize identity: downstream expects `EXCHANGE:SYMBOL` in the `symbol` field.
                if ":" in str(raw_symbol):
                    symbol = str(raw_symbol)
                    if exchange == "UNKNOWN":
                        exchange = symbol.split(":")[0]
                else:
                    symbol = f"{exchange}:{raw_symbol}"

                cand = CandidateMetadata(
                    symbol=symbol,
                    exchange=exchange,
                    asset_type=asset_type,
                    market_cap_rank=row.get("market_cap_rank"),
                    volume_24h=row.get("volume"),
                    sector=row.get("sector"),
                    industry=row.get("industry"),
                    metadata=row,
                )
                candidates.append(cand)

            return candidates

        except Exception as e:
            logger.error(f"TradingView discovery failed: {e}", exc_info=True)
            return []
