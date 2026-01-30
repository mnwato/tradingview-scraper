import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, cast

import numpy as np
import pandas as pd

sys.path.append(os.getcwd())
from tradingview_scraper.orchestration.registry import StageRegistry
from tradingview_scraper.portfolio_engines import build_engine
from tradingview_scraper.portfolio_engines.base import EngineRequest, ProfileName
from tradingview_scraper.regime import MarketRegimeDetector
from tradingview_scraper.settings import get_settings
from tradingview_scraper.utils.audit import AuditLedger, get_df_hash

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("clustered_optimizer_v2")

AUDIT_FILE = os.getenv("SELECTION_AUDIT", "")


def calculate_concentration_entropy(weights: List[float]) -> float:
    """Calculates the normalized Shannon entropy of a weight distribution."""
    w = np.array(weights)
    w = w[w > 0]
    if len(w) <= 1:
        return 0.0
    p = w / w.sum()
    entropy = -np.sum(p * np.log(p))
    return float(entropy / np.log(len(w)))


class ClusteredOptimizerV2:
    def __init__(self, returns_path: str, clusters_path: str, meta_path: str, stats_path: Optional[str] = None):
        self.settings = get_settings()
        self.run_dir = self.settings.prepare_summaries_run_dir()
        self.ledger = None
        if self.settings.features.feat_audit_ledger:
            self.ledger = AuditLedger(self.run_dir)

        # Explicitly cast to DataFrame to satisfy linter
        if str(returns_path).endswith(".parquet"):
            df = pd.read_parquet(returns_path)
        else:
            with open(returns_path, "rb") as f_in:
                df = cast(pd.DataFrame, pd.read_pickle(f_in))

        # Ultra-robust forcing of naive index
        try:
            new_idx = [pd.to_datetime(t).replace(tzinfo=None) for t in df.index]
            df.index = pd.DatetimeIndex(new_idx)
        except Exception as e_idx:
            logger.warning(f"Fallback indexing for returns: {e_idx}")
            df.index = pd.to_datetime(df.index, utc=True).tz_convert(None)

        self.returns = df

        with open(clusters_path, "r") as f:
            self.clusters = cast(Dict[str, List[str]], json.load(f))
        with open(meta_path, "r") as f:
            self.meta = cast(Dict[str, Any], json.load(f))
        self.stats = None
        if stats_path and os.path.exists(stats_path):
            with open(stats_path, "r") as f:
                self.stats = cast(pd.DataFrame, pd.read_json(f))

    def run_profile(self, profile: ProfileName, engine_name: str = "custom", cluster_cap: float = 0.25) -> pd.DataFrame:
        """Entry point for standard risk profiles using the engine factory."""
        if self.ledger:
            self.ledger.record_intent(step=f"optimize_{profile}", params={"engine": engine_name, "cap": cluster_cap}, input_hashes={"returns": get_df_hash(self.returns)})

        try:
            engine = build_engine(engine_name)

            # Inject advanced parameters via bayesian_params bucket
            b_params = {}
            if engine_name == "pyportfolioopt":
                # Allow overriding linkage method via env var (default to single for backward compatibility)
                b_params["hrp_linkage"] = os.getenv("TV_HRP_LINKAGE", "single")

            request = EngineRequest(profile=profile, cluster_cap=cluster_cap, bayesian_params=b_params)
            response = engine.optimize(returns=self.returns, clusters=self.clusters, meta=self.meta, stats=self.stats, request=request)
            weights_df = response.weights
        except Exception as e:
            logger.error(f"Optimization failed for {profile}: {e}")
            return pd.DataFrame()

        if self.ledger:
            # Calculate concentration entropy for the ledger
            weights_list = weights_df["Weight"].tolist() if not weights_df.empty else []
            entropy = calculate_concentration_entropy(weights_list)
            self.ledger.record_outcome(
                step=f"optimize_{profile}", status="success", output_hashes={"weights": get_df_hash(weights_df)}, metrics={"n_assets": len(weights_df), "concentration_entropy": entropy}
            )
        return weights_df

    def run_barbell(self, cluster_cap: float = 0.25, regime: str = "NORMAL") -> pd.DataFrame:
        """Entry point for the Antifragile Barbell profile using the custom engine."""
        return self.run_profile(cast(ProfileName, "barbell"), "custom", cluster_cap)


@StageRegistry.register(id="risk.optimize", name="Clustered Optimization", description="Convex optimization with regime-aware constraints", category="risk")
def optimize_clustered_portfolio(run_id: Optional[str] = None, risk_profiles: Optional[List[str]] = None):
    settings = get_settings()
    if run_id:
        os.environ["TV_RUN_ID"] = run_id
        # Reload settings
        get_settings.cache_clear()
        settings = get_settings()

    run_dir = settings.prepare_summaries_run_dir()

    # CR-831: Workspace Isolation
    # Prioritize run-specific artifacts
    # Phase 173: Prioritize Synthetic Matrix if available (Strategy Synthesis)
    default_returns = str(run_dir / "data" / "synthetic_returns.parquet")
    if not os.path.exists(default_returns):
        default_returns = str(run_dir / "data" / "returns_matrix.parquet")

    if not os.path.exists(default_returns):
        default_returns = str(settings.lakehouse_dir / "portfolio_returns.pkl")

    default_clusters = str(run_dir / "data" / "portfolio_clusters.json")
    if not os.path.exists(default_clusters):
        default_clusters = str(settings.lakehouse_dir / "portfolio_clusters.json")

    default_meta = str(run_dir / "data" / "portfolio_meta.json")
    if not os.path.exists(default_meta):
        default_meta = str(settings.lakehouse_dir / "portfolio_meta.json")

    returns_path = os.getenv("RETURNS_MATRIX", default_returns)
    clusters_path = os.getenv("CLUSTERS_FILE", default_clusters)
    meta_path = os.getenv("PORTFOLIO_META", default_meta)
    stats_path = os.getenv("ANTIFRAGILITY_STATS", str(run_dir / "data" / "antifragility_stats.json"))

    optimizer = ClusteredOptimizerV2(
        returns_path=returns_path,
        clusters_path=clusters_path,
        meta_path=meta_path,
        stats_path=stats_path,
    )

    detector = MarketRegimeDetector()
    regime, score, quadrant = detector.detect_regime(optimizer.returns)
    logger.info(f"Regime Detected for Optimization: {regime} (Score: {score:.2f}) | Quadrant: {quadrant}")

    # Load enhanced regime analysis if available (Phase 60 Update)
    regime_analysis_path = str(settings.lakehouse_dir / "regime_analysis_v3.json")
    regime_metrics = {}
    recommended_window = 20
    if os.path.exists(regime_analysis_path):
        with open(regime_analysis_path, "r") as f:
            regime_data = json.load(f)
            regime_metrics = regime_data.get("tail_risk", {})
            recommended_window = regime_data.get("persistence", {}).get("recommended_window", 20)
            logger.info(f"Loaded enhanced regime metrics: MaxDD={regime_metrics.get('max_drawdown', 'N/A')}")
            logger.info(f"Recommended Rebalance Window from Persistence: {recommended_window} days")

    # Dynamic Cluster Cap Adjustment based on Regime
    base_cap = float(os.getenv("CLUSTER_CAP", "0.25"))
    cap = base_cap

    if regime == "CRISIS":
        # Tighten concentration limits in crisis
        cap = min(base_cap, 0.15)
        logger.info(f"Crisis Regime detected: Tightening cluster cap to {cap} (Tail-Risk Mitigation)")
    elif regime == "TURBULENT":
        cap = min(base_cap, 0.20)
        logger.info(f"Turbulent Regime detected: Tightening cluster cap to {cap} (Regime Alignment)")

    # Generate results for each profile
    target_profiles = risk_profiles or ["min_variance", "hrp", "max_sharpe", "equal_weight"]
    profiles = {}
    for p_name in target_profiles:
        method = cast(ProfileName, p_name)
        logger.info(f"Optimizing profile: {p_name}")
        weights_df = optimizer.run_profile(method, "custom", cap)

        if weights_df.empty:
            logger.warning(f"Optimization returned empty weights for {p_name}")
            profiles[p_name] = {"assets": [], "clusters": []}
            continue
        cluster_summary = []
        for c_id in optimizer.clusters.keys():
            sub = weights_df[weights_df["Cluster_ID"] == str(c_id)]
            if sub.empty:
                continue
            gross = sub["Weight"].sum()
            net = sub["Net_Weight"].sum()

            # Fix type errors for unique
            sectors_list = list(pd.unique(sub["Sector"])) if "Sector" in sub.columns else ["N/A"]

            cluster_summary.append(
                {
                    "Cluster_Label": f"Cluster {c_id}",
                    "Gross_Weight": float(gross),
                    "Net_Weight": float(net),
                    "Lead_Asset": sub.iloc[0]["Symbol"],
                    "Asset_Count": len(sub),
                    "Type": "CORE",  # Placeholder
                    "Sectors": sectors_list,
                }
            )

        profiles[p_name] = {
            "assets": weights_df.to_dict(orient="records"),
            "clusters": cluster_summary,
        }

    # Add Antifragile Barbell
    if "barbell" in target_profiles or risk_profiles is None:
        logger.info("Optimizing profile: barbell")
        barbell_df = optimizer.run_barbell(cap, regime)
        if not barbell_df.empty:
            barbell_summary = []
            for c_id in optimizer.clusters.keys():
                sub = barbell_df[barbell_df["Cluster_ID"] == str(c_id)]
                if sub.empty:
                    continue
                gross = sub["Weight"].sum()
                net = sub["Net_Weight"].sum()

                sectors_list = list(pd.unique(sub["Sector"])) if "Sector" in sub.columns else ["N/A"]

                barbell_summary.append(
                    {
                        "Cluster_Label": f"Cluster {c_id}",
                        "Gross_Weight": float(gross),
                        "Net_Weight": float(net),
                        "Lead_Asset": sub.iloc[0]["Symbol"],
                        "Asset_Count": len(sub),
                        "Type": sub.iloc[0]["Type"],
                        "Sectors": sectors_list,
                    }
                )
            profiles["barbell"] = {
                "assets": barbell_df.to_dict(orient="records"),
                "clusters": barbell_summary,
            }
        else:
            reason = "missing antifragility stats" if optimizer.stats is None else "barbell unavailable"
            profiles["barbell"] = {
                "assets": [],
                "clusters": [],
                "meta": {"skipped": True, "reason": reason},
            }

    # Build cluster registry
    registry = {}
    for c_id, symbols in optimizer.clusters.items():
        # Find primary sector from meta
        sectors = [optimizer.meta.get(s, {}).get("sector", "N/A") for s in symbols]
        primary = max(set(sectors), key=sectors.count) if sectors else "N/A"
        registry[c_id] = {"symbols": symbols, "primary_sector": primary}

    output = {
        "profiles": profiles,
        "cluster_registry": registry,
        "optimization": {"regime": {"name": regime, "score": float(score), "quadrant": quadrant}, "metrics": regime_metrics},
        "metadata": {"generated_at": datetime.now().isoformat(), "cluster_cap": cap},
    }

    # CR-831: Workspace Isolation
    os.makedirs(run_dir / "data", exist_ok=True)
    default_output = run_dir / "data" / "portfolio_optimized_v2.json"
    final_output_path = os.getenv("OPTIMIZED_FILE", str(default_output))

    with open(final_output_path, "w") as f:
        json.dump(output, f, indent=2)

    logger.info(f"✅ Clustered Optimization V2 Complete. Saved to: {final_output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id")
    parser.add_argument("--profiles")
    args = parser.parse_args()

    risk_profs = args.profiles.split(",") if args.profiles else None
    optimize_clustered_portfolio(run_id=args.run_id, risk_profiles=risk_profs)
