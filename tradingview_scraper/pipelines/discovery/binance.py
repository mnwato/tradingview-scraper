import logging
from typing import Any, Dict, List

import ccxt

from tradingview_scraper.pipelines.discovery.base import (
    BaseDiscoveryScanner,
    CandidateMetadata,
)
from tradingview_scraper.pipelines.selection.base import FoundationHealthRegistry
from tradingview_scraper.settings import get_settings

logger = logging.getLogger(__name__)


class BinanceDiscoveryScanner(BaseDiscoveryScanner):
    """
    Discovery scanner that sources assets from Binance (Spot/Perp) via CCXT.
    """

    def __init__(self):
        self.settings = get_settings()
        self.registry = FoundationHealthRegistry(path=self.settings.lakehouse_dir / "foundation_health.json")

    @property
    def name(self) -> str:
        return "binance"

    def discover(self, params: Dict[str, Any]) -> List[CandidateMetadata]:
        """
        Executes discovery on Binance and maps results to CandidateMetadata.
        """
        asset_type = params.get("asset_type", "spot")
        quote = params.get("quote", "USDT")
        min_volume = float(params.get("min_volume", 0))

        logger.info(f"Executing Binance discovery (type={asset_type}, quote={quote})...")

        try:
            exchange = ccxt.binance({"enableRateLimit": True, "options": {"defaultType": asset_type}})

            markets = exchange.load_markets()
            tickers = exchange.fetch_tickers()

            candidates = []
            for symbol, market in markets.items():
                # Filter by active status and quote currency
                if not market.get("active"):
                    continue
                if market.get("quote") != quote:
                    continue

                # 1. Registry-Aware Veto (Phase 520)
                base = market.get("base")
                quote_curr = market.get("quote")
                clean_symbol = f"{base}{quote_curr}"
                identity = f"BINANCE:{clean_symbol}"

                if not self.registry.is_healthy(identity) and identity in self.registry.data:
                    reg_entry = self.registry.data[identity]
                    if reg_entry.get("status") == "toxic":
                        logger.info(f"Discovery Gate: Vetoing known TOXIC asset: {identity}")
                        continue

                # 2. Filter by volume if ticker available
                ticker = tickers.get(symbol, {})
                volume_raw = ticker.get("quoteVolume", 0)
                volume = float(volume_raw) if volume_raw is not None else 0.0

                if volume < min_volume:
                    continue

                # Map to CandidateMetadata
                cand = CandidateMetadata(
                    symbol=identity,
                    exchange="BINANCE",
                    asset_type="spot" if asset_type == "spot" else "perp",
                    volume_24h=volume,
                    metadata={"ccxt_symbol": symbol, "market_type": market.get("type"), "last_price": ticker.get("last"), "change_24h": ticker.get("percentage")},
                )
                candidates.append(cand)

            logger.info(f"Discovered {len(candidates)} candidates on Binance.")
            return candidates

        except Exception as e:
            logger.error(f"Binance discovery failed: {e}", exc_info=True)
            return []
