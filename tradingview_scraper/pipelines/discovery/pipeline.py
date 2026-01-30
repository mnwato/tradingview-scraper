import logging
from pathlib import Path
from typing import Dict, List, Optional

from tradingview_scraper.orchestration.registry import StageRegistry
from tradingview_scraper.pipelines.discovery.base import (
    BaseDiscoveryScanner,
    CandidateMetadata,
)
from tradingview_scraper.pipelines.discovery.binance import BinanceDiscoveryScanner
from tradingview_scraper.pipelines.discovery.tradingview import (
    TradingViewDiscoveryScanner,
)
from tradingview_scraper.settings import get_settings

logger = logging.getLogger(__name__)


class DiscoveryPipeline:
    """
    Orchestrates multiple discovery scanners to source candidate assets.
    """

    def __init__(self, run_id: Optional[str] = None):
        self.settings = get_settings()
        self.run_id = run_id or self.settings.run_id
        self.scanners: Dict[str, BaseDiscoveryScanner] = {
            "tradingview": TradingViewDiscoveryScanner(),
            "binance": BinanceDiscoveryScanner(),
        }

    def register_scanner(self, scanner: BaseDiscoveryScanner):
        self.scanners[scanner.name] = scanner

    @StageRegistry.register(id="discovery.full", name="Discovery Pipeline", description="Runs all configured scanners for a profile", category="discovery")
    def run_profile(self, profile_name: str) -> List[CandidateMetadata]:
        """
        Runs all scanners configured for a specific profile in the manifest.
        """
        # 1. Resolve Profile from manifest
        # (Logic similar to scripts/compose_pipeline.py)
        import json

        manifest_path = self.settings.manifest_path
        if not manifest_path.exists():
            logger.error(f"Manifest not found at {manifest_path}")
            return []

        with open(manifest_path, "r") as f:
            manifest = json.load(f)

        profile = manifest.get("profiles", {}).get(profile_name)
        if not profile:
            logger.error(f"Profile {profile_name} not found in manifest")
            return []

        discovery_config = profile.get("discovery", {})
        pipelines = discovery_config.get("pipelines", {})
        strategies = discovery_config.get("strategies", {})

        all_candidates: List[CandidateMetadata] = []

        # 2. Execute Pipelines
        for p_name, p_config in pipelines.items():
            logger.info(f"Running discovery pipeline: {p_name}")
            scanner_type = p_config.get("scanner_type", "tradingview")
            scanner = self.scanners.get(scanner_type)

            if not scanner:
                logger.warning(f"Scanner type {scanner_type} not registered. Skipping.")
                continue

            # Run for each scanner path in the pipeline
            scanner_paths = p_config.get("scanners", [])
            for s_path in scanner_paths:
                # Handle path resolution (relative to configs/)
                full_path = self.settings.configs_dir / s_path
                if not full_path.exists() and not full_path.suffix:
                    full_path = full_path.with_suffix(".yaml")

                params = {"config_path": str(full_path), "interval": p_config.get("interval", "1d"), "pipeline": p_name}
                cands = scanner.discover(params)
                all_candidates.extend(cands)

        # 3. Execute Strategies
        for s_name, s_config in strategies.items():
            logger.info(f"Running discovery strategy: {s_name}")
            scanner_type = s_config.get("scanner_type", "tradingview")
            scanner = self.scanners.get(scanner_type)

            if not scanner:
                continue

            scanner_paths = s_config.get("scanners", [])
            for s_path in scanner_paths:
                full_path = self.settings.configs_dir / s_path
                if not full_path.exists() and not full_path.suffix:
                    full_path = full_path.with_suffix(".yaml")

                params = {"config_path": str(full_path), "interval": s_config.get("interval", "1d"), "strategy": s_name}
                cands = scanner.discover(params)
                # Inject logic metadata
                for c in cands:
                    if "logic" not in c.metadata:
                        c.metadata["logic"] = s_name
                all_candidates.extend(cands)

        return all_candidates

    def save_candidates(self, candidates: List[CandidateMetadata], output_dir: Optional[Path] = None):
        """
        Saves discovered candidates to the export directory.
        """
        import json
        from dataclasses import asdict

        if not output_dir:
            output_dir = self.settings.export_dir / self.run_id

        output_dir.mkdir(parents=True, exist_ok=True)

        # Group by scanner/logic for separate files or save unified?
        # Current system expects multiple JSON files in the run_id directory.

        # For now, let's just save a unified candidates.json
        output_path = output_dir / "candidates.json"

        with open(output_path, "w") as f:
            json.dump([asdict(c) for c in candidates], f, indent=2)

        logger.info(f"Saved {len(candidates)} candidates to {output_path}")
