import fcntl
import hashlib
import json
import logging
import os
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional, cast

import numpy as np
import pandas as pd

from tradingview_scraper.selection_engines import SelectionRequest, SelectionResponse, build_selection_engine
from tradingview_scraper.settings import get_settings
from tradingview_scraper.utils.audit import AuditLedger, get_df_hash

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("natural_selection")


def get_default_audit_file() -> str:
    settings = get_settings()
    if settings.run_id and settings.run_id != "default_run":
        return str(settings.summaries_runs_dir / settings.run_id / "data" / "selection_audit.json")
    return str(settings.logs_dir / "selection_audit.json")


AUDIT_FILE = get_default_audit_file()


def run_selection(
    returns: pd.DataFrame,
    raw_candidates: List[Dict[str, Any]],
    stats_df: Optional[pd.DataFrame] = None,
    top_n: int = 2,
    threshold: float = 0.5,
    max_clusters: int = 25,
    m_gate: float = 0.0,
    mode: Optional[str] = None,
) -> SelectionResponse:
    """Orchestrates selection using the modular engine system."""
    settings = get_settings()
    engine_name = mode or settings.features.selection_mode
    engine = build_selection_engine(engine_name)
    request = SelectionRequest(
        top_n=top_n,
        threshold=threshold,
        max_clusters=max_clusters,
        min_momentum_score=m_gate,
    )
    response = engine.select(returns, raw_candidates, stats_df, request)
    for warning in response.warnings:
        logger.warning(warning)
    return response


def natural_selection(
    returns_path: Optional[str] = None,
    meta_path: Optional[str] = None,
    stats_path: Optional[str] = None,
    output_path: Optional[str] = None,
    top_n_per_cluster: Optional[int] = None,
    dist_threshold: Optional[float] = None,
    max_clusters: int = 25,
    min_momentum_score: Optional[float] = None,
    mode: Optional[str] = None,
):
    settings = get_settings()
    run_dir = settings.prepare_summaries_run_dir()

    # CR-831: Workspace Isolation
    returns_path = returns_path or os.getenv("RETURNS_MATRIX", str(run_dir / "data" / "returns_matrix.parquet"))
    meta_path = meta_path or os.getenv("PORTFOLIO_META", str(run_dir / "data" / "portfolio_meta.json"))
    stats_path = stats_path or os.getenv("ANTIFRAGILITY_STATS", str(run_dir / "data" / "antifragility_stats.json"))
    output_path = output_path or os.getenv("CANDIDATES_SELECTED", str(run_dir / "data" / "portfolio_candidates.json"))

    # Audit File Isolation
    default_audit = str(run_dir / "data" / "selection_audit.json")
    run_audit_file = os.getenv("SELECTION_AUDIT", default_audit)

    # Global audit file is only used as a fallback or shared history
    # CR-831: Move shared history to logs
    shared_audit_file = str(settings.logs_dir / "selection_audit.json")

    # Handle multiple modes
    modes = [m.strip() for m in (mode or settings.features.selection_mode).split(",") if m.strip()]

    top_n = top_n_per_cluster if top_n_per_cluster is not None else settings.top_n
    threshold = dist_threshold if dist_threshold is not None else settings.threshold
    m_gate = min_momentum_score if min_momentum_score is not None else settings.min_momentum_score

    ledger = AuditLedger(run_dir) if settings.features.feat_audit_ledger else None

    # Base Context
    sel_context_base = {
        "run_id": settings.run_id,
        "profile_manifest": settings.profile,
        "top_n": top_n,
        "threshold": threshold,
        "min_momentum_score": m_gate,
        "selection_mode": mode or settings.features.selection_mode,
    }

    if not os.path.exists(returns_path) or not os.path.exists(meta_path):
        logger.error(f"Required data missing: {returns_path} or {meta_path}")
        return

    # Load returns (Parquet or Pickle)
    if returns_path.endswith(".parquet"):
        returns = pd.read_parquet(returns_path)
    else:
        returns = cast(pd.DataFrame, pd.read_pickle(returns_path))

    with open(meta_path, "r") as f_meta:
        meta_data = json.load(f_meta)

    # Handle both list (raw candidates) and dict (refined meta) formats
    if isinstance(meta_data, dict):
        raw_candidates = []
        for s, c in meta_data.items():
            if "symbol" not in c:
                c["symbol"] = s
            raw_candidates.append(c)
    else:
        raw_candidates = meta_data

    stats_df = pd.read_json(stats_path).set_index("Symbol") if os.path.exists(stats_path) else None

    meta_hash = hashlib.sha256(json.dumps(raw_candidates, sort_keys=True).encode()).hexdigest()

    if ledger and not ledger.last_hash:
        manifest_hash = hashlib.sha256(open(settings.manifest_path, "rb").read()).hexdigest() if settings.manifest_path.exists() else "unknown"
        ledger.record_genesis(settings.run_id, settings.profile, manifest_hash)

    # We will process each mode, but only the last one will be saved to output_path
    # This maintains compatibility with downstream steps.
    last_response = None

    for current_mode in modes:
        logger.info(f"Running Natural Selection Mode: {current_mode}")
        if ledger:
            ledger.record_intent(
                step="natural_selection",
                params={"top_n": top_n, "threshold": threshold, "mode": current_mode},
                input_hashes={"returns": get_df_hash(returns), "candidates_raw": meta_hash, "stats": get_df_hash(stats_df) if stats_df is not None else "none"},
                context={**sel_context_base, "selection_mode": current_mode},
            )

        logger.info(f"Selection Request: top_n={top_n}, threshold={threshold}, m_gate={m_gate}, mode={current_mode}")
        response = run_selection(returns, raw_candidates, stats_df, top_n, threshold, max_clusters, m_gate, mode=current_mode)
        last_response = response
        winners = response.winners
        audit_clusters = response.audit_clusters
        spec_version = response.spec_version
        vetoes = response.vetoes
        engine_metrics = response.metrics

        logger.info(f"Selection Result: {len(winners)} winners picked.")

        # Benchmark Isolation: Ensure the final winners list exclusively contains scanner-discovered signals.
        # Hardcoded benchmarks are isolated to baseline profiles.
        final_winners = [w for w in winners if not w.get("is_benchmark", False)]
        if len(final_winners) < len(winners):
            logger.info(f"Isolated {len(winners) - len(final_winners)} benchmark symbols from selected candidates.")

        # Atomic write for winners
        with tempfile.NamedTemporaryFile("w", dir=os.path.dirname(output_path), delete=False) as tf:
            json.dump(final_winners, tf, indent=2)
            temp_name = tf.name
        os.replace(temp_name, output_path)

        def _sanitize(obj: Any) -> Any:
            if isinstance(obj, dict):
                return {str(k): _sanitize(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_sanitize(x) for x in obj]
            if hasattr(obj, "to_dict"):
                return obj.to_dict()
            if isinstance(obj, (np.integer, np.floating)):
                return obj.item()
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj

        sanitized_metrics = cast(Dict[str, Any], _sanitize(engine_metrics))

        # Update Audit File with selection info (Atomic + Locked)
        # CR-831: Audit File Isolation
        # run_audit_file is already defined at function start
        lock_file = str(run_audit_file) + ".lock"
        try:
            with open(lock_file, "w") as lf:
                fcntl.flock(lf, fcntl.LOCK_EX)
                audit_data = {}
                # Try reading from shared audit if it exists and run-level doesn't
                # to maintain historical continuity
                search_files = [run_audit_file, shared_audit_file]
                for sf in search_files:
                    if os.path.exists(sf):
                        try:
                            with open(sf, "r") as f:
                                content = f.read().strip()
                                if content:
                                    audit_data = json.loads(content)
                                    break
                        except Exception:
                            pass

                current_selection_audit = {
                    "timestamp": datetime.now().isoformat(),
                    "selection_mode": current_mode,
                    "total_raw_symbols": len(raw_candidates),
                    "total_selected": len(winners),
                    "lookbacks_used": [60, 120, 200],
                    "clusters": {str(k): v for k, v in audit_clusters.items()},
                    "spec_version": spec_version,
                    "vetoes": vetoes,
                    "metrics": sanitized_metrics,
                    "relaxation_stage": response.relaxation_stage,
                    "active_thresholds": response.active_thresholds,
                }

                # Update main selection key
                audit_data["selection"] = current_selection_audit

                # Update selection history
                if "selection_history" not in audit_data:
                    audit_data["selection_history"] = {}
                audit_data["selection_history"][current_mode] = current_selection_audit

                # Write to run directory audit
                with tempfile.NamedTemporaryFile("w", dir=os.path.dirname(run_audit_file), delete=False) as tf:
                    json.dump(audit_data, tf, indent=2)
                    temp_name = tf.name
                os.replace(temp_name, run_audit_file)

                # Update shared lakehouse audit (Optional)
                os.makedirs(os.path.dirname(shared_audit_file), exist_ok=True)
                with tempfile.NamedTemporaryFile("w", dir=os.path.dirname(shared_audit_file), delete=False) as tf:
                    json.dump(audit_data, tf, indent=2)
                    temp_name = tf.name
                os.replace(temp_name, shared_audit_file)

                fcntl.flock(lf, fcntl.LOCK_UN)
        except Exception as e:
            logger.warning(f"Could not update audit file: {e}")

        selection_audit_hash = None
        if os.path.exists(run_dir / "selection_audit.json"):
            selection_audit_hash = hashlib.sha256((run_dir / "selection_audit.json").read_bytes()).hexdigest()

        if ledger:
            audit_payload = cast(
                Dict[str, Any],
                _sanitize(
                    {
                        "selection": {
                            "total_raw_symbols": len(returns.columns),
                            "total_selected": len(winners),
                            "clusters": audit_clusters,
                            "mode": current_mode,
                            "spec_version": spec_version,
                            "vetoes": vetoes,
                            "engine_metrics": sanitized_metrics,
                        },
                        "portfolio_clusters": {str(c): d["selected"] for c, d in audit_clusters.items()},
                        "winner_metadata": {w["symbol"]: {k: w.get(k) for k in ["exchange", "sector", "industry", "type", "identity"]} for w in winners},
                    }
                ),
            )
            ledger_metrics: Dict[str, Any] = {
                "n_winners": len(winners),
                "n_vetoes": len(vetoes),
                "spec_version": spec_version,
                "raw_pool_count": len(returns.columns),
                "selected_count": len(winners),
                "selection_mode": current_mode,
                "relaxation_stage": response.relaxation_stage,
                "active_thresholds": response.active_thresholds,
            }
            if isinstance(sanitized_metrics, dict):
                ledger_metrics.update(sanitized_metrics)
            ledger.record_outcome(
                step="natural_selection",
                status="success",
                output_hashes={
                    "candidates": hashlib.sha256(json.dumps(winners).encode()).hexdigest(),
                    "candidates_raw": meta_hash,
                    "selection_audit": selection_audit_hash or "unknown",
                },
                metrics=ledger_metrics,
                data=audit_payload,
                context={**sel_context_base, "selection_mode": current_mode},
            )

    logger.info(f"Natural Selection Complete for modes: {', '.join(modes)}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--top-n", type=int)
    parser.add_argument("--threshold", type=float)
    parser.add_argument("--max-clusters", type=int, default=25)
    parser.add_argument("--min-momentum", type=float)
    parser.add_argument("--mode", type=str, choices=["v2.0", "v2", "v2.1", "v3", "v3.1", "v3.2", "legacy"], help="Selection spec version")
    args = parser.parse_args()
    natural_selection(top_n_per_cluster=args.top_n, dist_threshold=args.threshold, max_clusters=args.max_clusters, min_momentum_score=args.min_momentum, mode=args.mode)
