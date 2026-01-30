import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional, cast

import numpy as np
import pandas as pd

sys.path.append(os.getcwd())
from tradingview_scraper.orchestration.registry import StageRegistry
from tradingview_scraper.portfolio_engines import build_engine
from tradingview_scraper.portfolio_engines.base import EngineRequest, ProfileName
from tradingview_scraper.settings import get_settings
from tradingview_scraper.utils.audit import AuditLedger, get_df_hash

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("optimize_meta_portfolio")


def _project_bounded_simplex(weights: np.ndarray, *, min_weight: float, max_weight: float) -> np.ndarray:
    """Project weights onto the bounded simplex.

    Constraints:
    - sum(w) == 1
    - min_weight <= w_i <= max_weight for all i
    """
    w = np.asarray(weights, dtype=float).copy()
    n = int(w.size)
    if n <= 0:
        return w

    min_w = float(min_weight)
    max_w = float(max_weight)
    if min_w < 0 or max_w <= 0 or min_w > max_w:
        raise ValueError(f"invalid bounds min={min_w} max={max_w}")
    if n * min_w > 1.0 + 1e-12:
        raise ValueError(f"infeasible bounds: n*min_weight={n * min_w} > 1")
    if n * max_w < 1.0 - 1e-12:
        raise ValueError(f"infeasible bounds: n*max_weight={n * max_w} < 1")

    w = np.nan_to_num(w, nan=0.0, posinf=0.0, neginf=0.0)
    w[w < 0] = 0.0
    w = np.clip(w, min_w, max_w)

    for _ in range(200):
        s = float(w.sum())
        if abs(s - 1.0) <= 1e-10:
            break

        if s > 1.0:
            delta = s - 1.0
            room = w - min_w
            mask = room > 1e-12
            total_room = float(room[mask].sum())
            if total_room <= 1e-18:
                break
            w[mask] -= delta * (room[mask] / total_room)
            w = np.maximum(w, min_w)
        else:
            delta = 1.0 - s
            room = max_w - w
            mask = room > 1e-12
            total_room = float(room[mask].sum())
            if total_room <= 1e-18:
                break
            w[mask] += delta * (room[mask] / total_room)
            w = np.minimum(w, max_w)

    s = float(w.sum())
    if s <= 0:
        w = np.array([1.0 / n] * n, dtype=float)
        w = np.clip(w, min_w, max_w)
        w = w / float(w.sum())
    elif abs(s - 1.0) > 1e-8:
        diff = 1.0 - s
        if diff > 0:
            idx = int(np.argmax(max_w - w))
            w[idx] = min(max_w, w[idx] + diff)
        else:
            idx = int(np.argmax(w - min_w))
            w[idx] = max(min_w, w[idx] + diff)

    return w


def _load_meta_allocation_bounds(manifest_path: Path, meta_profile: str) -> tuple[Optional[float], Optional[float]]:
    if not manifest_path.exists():
        return None, None
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None, None

    cfg = (data.get("profiles") or {}).get(meta_profile) or {}
    alloc = cfg.get("meta_allocation") or {}
    min_w = alloc.get("min_weight")
    max_w = alloc.get("max_weight")
    try:
        return (float(min_w) if min_w is not None else None), (float(max_w) if max_w is not None else None)
    except Exception:
        return None, None


@StageRegistry.register(
    id="risk.optimize_meta",
    name="Meta Optimization",
    description="Solves for optimal sleeve allocations in a meta-portfolio.",
    category="risk",
    tags=["meta", "risk"],
)
def optimize_meta(returns_path: str, output_path: str, profile: Optional[str] = None, meta_profile: Optional[str] = None):
    settings = get_settings()
    run_dir = settings.prepare_summaries_run_dir()
    ledger = AuditLedger(run_dir) if settings.features.feat_audit_ledger else None
    lakehouse_dir = settings.lakehouse_dir

    # Resolve Meta Profile from settings if not passed
    m_prof = meta_profile or os.getenv("PROFILE") or "meta_production"

    # Handle Profile Matrix
    if profile is None:
        # CR-831: Workspace Isolation - Infer base directory from returns_path
        input_path = Path(returns_path)
        # If input_path is a directory, use it. If it's a file (or dummy file path), use parent.
        if input_path.is_dir():
            base_dir = input_path
        else:
            base_dir = input_path.parent

        base_dir = base_dir.resolve()

        logger.info(f"Searching for returns in: {base_dir}")
        # Search for all meta_returns_{meta_profile}_*.pkl in the resolved directory
        files = list(base_dir.glob(f"meta_returns_{m_prof}_*.pkl"))
        logger.info(f"Found {len(files)} files matching meta_returns_{m_prof}_*.pkl")

        # If none found in run dir, try lakehouse (Legacy fallback)
        if not files:
            files = list(lakehouse_dir.glob(f"meta_returns_{m_prof}_*.pkl"))

        # Global fallback to old pattern if no profile-specific ones found
        if not files:
            files = list(base_dir.glob("meta_returns_*.pkl"))
            if not files:
                files = list(lakehouse_dir.glob("meta_returns_*.pkl"))

        if not files and input_path.exists() and input_path.is_file():
            files = [input_path]
    else:
        # Try run_dir first, then lakehouse
        input_path = Path(returns_path)
        if input_path.is_dir():
            base_dir = input_path
        else:
            base_dir = input_path.parent

        candidates = [
            base_dir / f"meta_returns_{m_prof}_{profile}.pkl",
            lakehouse_dir / f"meta_returns_{m_prof}_{profile}.pkl",
            base_dir / f"meta_returns_{profile}.pkl",
            lakehouse_dir / f"meta_returns_{profile}.pkl",
        ]
        files = [c for c in candidates if c.exists()]

    for p_path in files:
        if not p_path.exists():
            continue

        # Extract profile from filename: meta_returns_{m_prof}_<prof>.pkl or meta_returns_<prof>.pkl
        stem = p_path.stem
        if f"meta_returns_{m_prof}_" in stem:
            prof_name = stem.replace(f"meta_returns_{m_prof}_", "")
        else:
            prof_name = stem.replace("meta_returns_", "")

        if prof_name == "meta_returns":
            prof_name = "hrp"  # Default legacy

        # Map profile to valid ProfileName
        target_profile: ProfileName = "hrp"
        try:
            target_profile = cast(ProfileName, prof_name)
        except Exception:
            pass

        logger.info(f"🔨 Fractal Meta-Optimization ({m_prof}): {target_profile}")

        meta_rets = pd.read_pickle(p_path)
        if not isinstance(meta_rets, pd.DataFrame):
            meta_rets = pd.DataFrame(meta_rets)

        if meta_rets.empty:
            continue

        clusters = {str(col): [str(col)] for col in meta_rets.columns}

        if ledger:
            ledger.record_intent(
                step=f"meta_optimize_{target_profile}",
                params={"engine": "custom", "profile": str(target_profile), "n_sleeves": len(meta_rets.columns)},
                input_hashes={"meta_returns": get_df_hash(meta_rets)},
                context={"meta_profile": m_prof},
            )

        engine = build_engine("custom")
        request = EngineRequest(profile=target_profile, engine="custom", cluster_cap=1.0)

        try:
            # Explicitly cast to satisfy static analyzer
            rets_df = cast(pd.DataFrame, meta_rets)

            # If barbell is requested, we need antifragility stats for the sleeves
            current_stats = pd.DataFrame()
            if target_profile == "barbell":
                from tradingview_scraper.risk import AntifragilityAuditor

                auditor = AntifragilityAuditor()
                af_df = auditor.audit(rets_df)
                current_stats = af_df

            response = engine.optimize(returns=rets_df, clusters=clusters, meta={}, stats=current_stats, request=request)
            weights_df = response.weights
            if weights_df.empty:
                continue

            # Enforce meta-layer sleeve bounds from the manifest (min/max sleeve weights).
            # This is a meta-portfolio requirement to prevent over-concentration in a single sleeve.
            min_w, max_w = _load_meta_allocation_bounds(settings.manifest_path, m_prof)
            if min_w is not None and max_w is not None and "Weight" in weights_df.columns:
                try:
                    w_raw = np.asarray(weights_df["Weight"], dtype=float)
                    w_proj = _project_bounded_simplex(w_raw, min_weight=float(min_w), max_weight=float(max_w))
                    weights_df = weights_df.copy()
                    weights_df["Weight"] = w_proj
                    if "Net_Weight" in weights_df.columns:
                        weights_df["Net_Weight"] = w_proj
                except Exception as exc:
                    logger.warning(f"Failed to apply meta_allocation bounds for {m_prof}/{target_profile}: {exc}")

            # Save specific matrix result
            p_output_path = Path(output_path).parent / f"meta_optimized_{m_prof}_{target_profile}.json"

            # CR-838: Preserve Hierarchical Cluster Metadata for Audit
            # This captures the 'Fractal Tree' before it is flattened into physical assets
            cluster_tree_path = Path(output_path).parent / f"meta_cluster_tree_{m_prof}_{target_profile}.json"

            artifact = {
                "metadata": {
                    "source": str(p_path),
                    "meta_profile": m_prof,
                    "engine": "custom",
                    "profile": target_profile,
                    "n_sleeves": len(meta_rets.columns),
                    "run_id": settings.run_id,
                    "generated_at": str(pd.Timestamp.now()),
                },
                "weights": weights_df.to_dict(orient="records"),
            }

            os.makedirs(os.path.dirname(p_output_path), exist_ok=True)
            with open(p_output_path, "w") as f:
                json.dump(artifact, f, indent=2)

            # Also save the hierarchical tree (unflattened logic weights)
            with open(cluster_tree_path, "w") as f:
                json.dump(artifact, f, indent=2)

            if ledger:
                ledger.record_outcome(
                    step=f"meta_optimize_{target_profile}",
                    status="success",
                    output_hashes={"weights": get_df_hash(weights_df)},
                    metrics={"n_assets": len(weights_df), "total_weight": weights_df["Weight"].sum()},
                    data={"weights": weights_df.to_dict(orient="records")},
                    context={"meta_profile": m_prof, "profile": str(target_profile)},
                )

            logger.info(f"✅ Meta-optimized weights ({m_prof}/{target_profile}) saved to {p_output_path}")
            logger.info(f"🌳 Meta-cluster tree preserved at {cluster_tree_path}")

        except Exception as e:
            if ledger:
                ledger.record_outcome(
                    step=f"meta_optimize_{target_profile}",
                    status="error",
                    output_hashes={},
                    metrics={"error": str(e)},
                    context={"meta_profile": m_prof},
                )
            logger.error(f"Meta-optimization failed for {target_profile}: {e}")


if __name__ == "__main__":
    settings = get_settings()
    default_returns = str(settings.prepare_summaries_run_dir() / "data")
    default_output = str(settings.prepare_summaries_run_dir() / "data" / "meta_optimized.json")

    parser = argparse.ArgumentParser()
    parser.add_argument("--returns", default=default_returns)
    parser.add_argument("--output", default=default_output)
    parser.add_argument("--profile", help="Specific risk profile to optimize (e.g. hrp)")
    parser.add_argument("--meta-profile", help="Meta profile name (e.g. meta_super_benchmark)")
    args = parser.parse_args()

    optimize_meta(args.returns, args.output, args.profile, args.meta_profile)
