import argparse
import json
import logging
import os
import threading
from concurrent.futures import ALL_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple, cast

import matplotlib

matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt  # type: ignore
import numpy as np
import pandas as pd
import scipy.cluster.hierarchy as sch
import seaborn as sns  # type: ignore
from scipy.spatial.distance import squareform

from tradingview_scraper.futures_universe_selector import FuturesUniverseSelector
from tradingview_scraper.settings import get_settings  # type: ignore
from tradingview_scraper.symbols.stream.metadata import DataProfile
from tradingview_scraper.symbols.stream.persistent_loader import PersistentDataLoader

logging.basicConfig(level=logging.INFO, format="%(message)s", force=True)
logger = logging.getLogger("forex_universe_analysis")


def _resolve_export_dir(run_id: Optional[str] = None) -> Path:
    export_root = Path("export")
    run_id = run_id or os.getenv("TV_EXPORT_RUN_ID") or ""

    if run_id:
        candidate = export_root / run_id
        if candidate.exists():
            return candidate

    if export_root.exists():
        best_dir: Optional[Path] = None
        best_mtime = -1.0
        for subdir in export_root.iterdir():
            if not subdir.is_dir():
                continue
            matches = list(subdir.glob("universe_selector_*.json"))
            if not matches:
                continue
            newest = max(p.stat().st_mtime for p in matches)
            if newest > best_mtime:
                best_mtime = newest
                best_dir = subdir
        if best_dir is not None:
            return best_dir

    return export_root


def _find_latest_export_file(export_dir: Path, export_symbol: str, data_category: str = "universe_selector") -> Path:
    pattern = f"{data_category}_{export_symbol.lower()}_*.json"
    matches = list(export_dir.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No exports matching {pattern} under {export_dir}")
    return max(matches, key=lambda p: p.stat().st_mtime)


def _load_export_payload(path: Path) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return {}, [cast(Dict[str, Any], x) for x in payload if isinstance(x, dict)]

    if not isinstance(payload, dict):
        return {}, []

    data = payload.get("data")
    if not isinstance(data, list):
        return cast(Dict[str, Any], payload.get("meta") or {}), []

    rows = [cast(Dict[str, Any], x) for x in data if isinstance(x, dict)]
    return cast(Dict[str, Any], payload.get("meta") or {}), rows


def _venue_count(row: Mapping[str, Any]) -> int:
    alternates = row.get("alternates")
    n_alts = len(alternates) if isinstance(alternates, list) else 0
    return 1 + n_alts


def _safe_float(value: Any) -> Optional[float]:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if np.isnan(num):
        return None
    return num


def _format_int(value: Any) -> str:
    num = _safe_float(value)
    if num is None:
        return "-"
    return f"{int(round(num)):,}"


def _format_float(value: Any, digits: int = 3) -> str:
    num = _safe_float(value)
    if num is None:
        return "-"
    fmt = f"{{:.{digits}f}}"
    return fmt.format(num)


def _format_pct(value: Any, digits: int = 2) -> str:
    num = _safe_float(value)
    if num is None:
        return "-"
    fmt = f"{{:.{digits}f}}%"
    return fmt.format(num * 100)


def _markdown_table(rows: Iterable[Mapping[str, Any]], columns: List[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, separator]
    for r in rows:
        cells = []
        for col in columns:
            val = r.get(col, "")
            if val is None:
                val = ""
            cells.append(str(val))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _compute_quote_to_usd(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    """Compute USD per quote currency using selected USD crosses."""
    close_by_pair: Dict[str, float] = {}
    for r in rows:
        sym = str(r.get("symbol") or "")
        pair = FuturesUniverseSelector._forex_pair_identity(sym)
        close = _safe_float(r.get("close"))
        if pair and close:
            close_by_pair[pair] = close

    fx: Dict[str, float] = {"USD": 1.0}

    # Quote -> USD
    def inv(pair: str) -> Optional[float]:
        px = close_by_pair.get(pair)
        if px:
            return 1.0 / px
        return None

    def direct(pair: str) -> Optional[float]:
        return close_by_pair.get(pair)

    # USD crosses
    maybe = {
        "JPY": inv("USDJPY"),
        "CAD": inv("USDCAD"),
        "CHF": inv("USDCHF"),
        "EUR": direct("EURUSD"),
        "GBP": direct("GBPUSD"),
        "AUD": direct("AUDUSD"),
        "NZD": direct("NZDUSD"),
    }
    for k, v in maybe.items():
        if v is not None:
            fx[k] = v

    return fx


def _build_pair_rows(rows: List[Dict[str, Any]], quote_to_usd: Dict[str, float]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in rows:
        sym = str(row.get("symbol") or "")
        pair = FuturesUniverseSelector._forex_pair_identity(sym)
        base, quote = FuturesUniverseSelector._extract_base_quote(sym)
        venues = _venue_count(row)

        vt_agg = _safe_float(row.get("Value.Traded")) or 0.0
        quote_usd = quote_to_usd.get(quote)
        vt_usd = vt_agg * quote_usd if quote_usd is not None else None

        out.append(
            {
                "pair": pair,
                "symbol": sym,
                "exchange": sym.split(":", 1)[0] if ":" in sym else "",
                "base": base,
                "quote": quote,
                "venues": venues,
                "volume": _safe_float(row.get("volume")) or 0.0,
                "volume_rep": _safe_float(row.get("volume_rep")) or _safe_float(row.get("volume")) or 0.0,
                "Value.Traded": vt_agg,
                "Value.Traded_rep": _safe_float(row.get("Value.Traded_rep")) or _safe_float(row.get("Value.Traded")) or 0.0,
                "Value.Traded_usd": vt_usd,
                "Volatility.D": _safe_float(row.get("Volatility.D")),
                "atr_pct": _safe_float(row.get("atr_pct")),
                "ADX": _safe_float(row.get("ADX")),
                "Recommend.All": _safe_float(row.get("Recommend.All")),
                "Perf.W": _safe_float(row.get("Perf.W")),
                "Perf.1M": _safe_float(row.get("Perf.1M")),
                "Perf.3M": _safe_float(row.get("Perf.3M")),
                "alternates": row.get("alternates") if isinstance(row.get("alternates"), list) else [],
            }
        )
    return out


def _filter_tradable(
    rows: List[Dict[str, Any]],
    *,
    exclude_ig_singletons: bool,
    min_venues: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    tradable: List[Dict[str, Any]] = []
    excluded: List[Dict[str, Any]] = []

    for r in rows:
        sym = str(r.get("symbol") or "")
        venues = int(r.get("venues") or 0)
        is_ig_singleton = sym.upper().startswith("IG:") and venues <= 1

        if exclude_ig_singletons and is_ig_singleton:
            excluded.append(r)
            continue

        if venues < min_venues:
            excluded.append(r)
            continue

        tradable.append(r)

    return tradable, excluded


def _write_liquidity_report(
    output_dir: Path,
    *,
    export_path: Path,
    export_meta: Dict[str, Any],
    tradable: List[Dict[str, Any]],
    excluded: List[Dict[str, Any]],
    quote_to_usd: Dict[str, float],
    include_excluded: bool,
) -> Path:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    run_id = export_meta.get("run_id") or os.getenv("TV_EXPORT_RUN_ID") or ""

    # Rank by USD notional if available, fallback to aggregated volume
    def rank_key(r: Dict[str, Any]) -> Tuple[int, float, float]:
        vt_usd = r.get("Value.Traded_usd")
        if isinstance(vt_usd, (int, float)):
            return (2, float(vt_usd), float(r.get("volume") or 0))
        return (1, 0.0, float(r.get("volume") or 0))

    ranked = sorted(tradable, key=rank_key, reverse=True)

    lines: List[str] = []
    lines.append("# Forex Tradable Universe Report")
    lines.append("")
    lines.append(f"**Generated:** {ts}")
    if run_id:
        lines.append(f"**TV_EXPORT_RUN_ID:** `{run_id}`")
    lines.append(f"**Export File:** `{export_path}`")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Selected pairs in export: {len(tradable) + len(excluded)}")
    lines.append(f"- Tradable pairs (post filters): {len(tradable)}")
    lines.append(f"- Excluded pairs: {len(excluded)}")
    lines.append("")

    if include_excluded and excluded:
        lines.append("## Excluded")
        ex_rows = sorted(excluded, key=lambda r: float(r.get("volume") or 0))
        cols = [
            "pair",
            "symbol",
            "venues",
            "volume",
            "Value.Traded",
        ]
        lines.append(_markdown_table(ex_rows, cols))
        lines.append("")

    lines.append("## FX Conversion (Quote → USD)")
    lines.append("`Value.Traded` is denominated in the pair's quote currency. `Value.Traded_usd` is approximated using the USD crosses from the same export (e.g. `USDJPY`, `USDCAD`, `EURUSD`).")
    lines.append("")
    fx_rows = [{"quote": k, "usd_per_quote": f"{v:.6g}"} for k, v in sorted(quote_to_usd.items())]
    lines.append(_markdown_table(fx_rows, ["quote", "usd_per_quote"]))
    lines.append("")

    lines.append("## Tradable Pairs (Ranked)")

    table_rows: List[Dict[str, Any]] = []
    for r in ranked:
        table_rows.append(
            {
                "pair": r.get("pair"),
                "symbol": r.get("symbol"),
                "venues": r.get("venues"),
                "vol_agg": _format_int(r.get("volume")),
                "vol_rep": _format_int(r.get("volume_rep")),
                "vt_agg": _format_int(r.get("Value.Traded")),
                "vt_usd": _format_int(r.get("Value.Traded_usd")),
                "Vol.D": _format_float(r.get("Volatility.D"), 3),
                "atr%": _format_pct(r.get("atr_pct"), 3),
                "Perf.1M": _format_float(r.get("Perf.1M"), 2),
                "Perf.3M": _format_float(r.get("Perf.3M"), 2),
            }
        )

    columns = ["pair", "symbol", "venues", "vol_agg", "vol_rep", "vt_agg", "vt_usd", "Vol.D", "atr%", "Perf.1M", "Perf.3M"]
    lines.append(_markdown_table(table_rows, columns))

    report_path = output_dir / "forex_universe_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")

    # Sidecar CSV for machine parsing
    df = pd.DataFrame(ranked)
    csv_path = output_dir / "forex_universe_report.csv"
    df.to_csv(csv_path, index=False)

    return report_path


def _robust_correlation(returns: pd.DataFrame) -> pd.DataFrame:
    symbols: List[str] = [str(c) for c in returns.columns]
    n = len(symbols)
    corr_matrix = np.eye(n)

    for i in range(n):
        for j in range(i + 1, n):
            s1 = symbols[i]
            s2 = symbols[j]
            v1 = cast(np.ndarray, returns[s1].values)
            v2 = cast(np.ndarray, returns[s2].values)
            mask = np.logical_and(np.logical_and(v1 != 0, v2 != 0), np.logical_and(~np.isnan(v1), ~np.isnan(v2)))
            v1_clean = v1[mask]
            v2_clean = v2[mask]

            if len(v1_clean) < 20:
                c = 0.0
            else:
                c = float(np.corrcoef(v1_clean, v2_clean)[0, 1])
                if np.isnan(c):
                    c = 0.0

            corr_matrix[i, j] = c
            corr_matrix[j, i] = c

    idx = pd.Index(symbols)
    return pd.DataFrame(corr_matrix, index=idx, columns=idx)


def _build_returns_matrix(
    tradable: List[Dict[str, Any]],
    *,
    lookback_days: int,
    interval: str,
    batch_size: int,
    min_history_frac: float,
    max_gaps: int,
    backfill: bool,
    gapfill: bool,
    jwt_token: str,
) -> Tuple[pd.DataFrame, Dict[str, Any], List[str], List[Dict[str, Any]]]:
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)

    returns_map: Dict[str, pd.Series] = {}
    meta_map: Dict[str, Any] = {}
    skipped: List[str] = []
    health_records: List[Dict[str, Any]] = []
    lock = threading.Lock()

    def fetch(pair: str, symbol: str, meta: Dict[str, Any]) -> None:
        local = PersistentDataLoader(websocket_jwt_token=jwt_token)

        def record(status: str, reason: str = "", **extra: Any) -> None:
            payload: Dict[str, Any] = {
                "pair": pair,
                "symbol": symbol,
                "interval": interval,
                "status": status,
                "reason": reason,
            }
            payload.update(extra)
            with lock:
                health_records.append(payload)

        try:
            depth = min(max(lookback_days + 20, 120), 2000)

            if backfill:
                logger.info("Backfilling %s (%s) depth=%s", pair, symbol, depth)
                local.sync(symbol, interval=interval, depth=depth, total_timeout=120)

            if gapfill:
                logger.info("Gap filling %s (%s)", pair, symbol)
                local.repair(
                    symbol,
                    interval=interval,
                    max_depth=depth,
                    max_fills=5,
                    max_time=90,
                    total_timeout=90,
                    profile=DataProfile.FOREX,
                )

            df = local.load(symbol, start_date, end_date, interval=interval)
            if df.empty:
                record("missing", "empty_df")
                with lock:
                    skipped.append(pair)
                return

            df = df.copy()
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s").dt.date
            dates = sorted(set(df["timestamp"].tolist()))
            first_date = str(dates[0]) if dates else ""
            last_date = str(dates[-1]) if dates else ""

            expected_days: Optional[int] = None
            coverage: Optional[float] = None
            if interval == "1d":
                expected_days = int(len(pd.bdate_range(start_date.date(), end_date.date())))
                coverage = (len(dates) / expected_days) if expected_days else None

            gaps = local.storage.detect_gaps(symbol, interval, profile=DataProfile.FOREX, start_ts=start_date.timestamp())
            gaps_count = len(gaps)

            if coverage is not None and coverage < min_history_frac:
                record(
                    "skip",
                    f"coverage<{min_history_frac}",
                    candles=len(df),
                    expected_days=expected_days,
                    coverage=coverage,
                    gaps=gaps_count,
                    first=first_date,
                    last=last_date,
                )
                with lock:
                    skipped.append(pair)
                return

            if gaps_count > max_gaps:
                record(
                    "skip",
                    f"gaps>{max_gaps}",
                    candles=len(df),
                    expected_days=expected_days,
                    coverage=coverage,
                    gaps=gaps_count,
                    first=first_date,
                    last=last_date,
                )
                with lock:
                    skipped.append(pair)
                return

            close = cast(pd.Series, df.set_index("timestamp")["close"])
            rets = close.pct_change().dropna()

            meta["health"] = {
                "interval": interval,
                "candles": len(df),
                "expected_days": expected_days,
                "coverage": coverage,
                "gaps": gaps_count,
                "first": first_date,
                "last": last_date,
            }

            record(
                "ok",
                candles=len(df),
                expected_days=expected_days,
                coverage=coverage,
                gaps=gaps_count,
                first=first_date,
                last=last_date,
                returns=int(len(rets)),
            )

            with lock:
                returns_map[pair] = rets
                meta_map[pair] = meta
        except Exception as exc:
            logger.warning("Failed loading %s (%s): %s", pair, symbol, exc)
            record("error", str(exc))
            with lock:
                skipped.append(pair)

    symbols = [(str(r.get("pair") or ""), str(r.get("symbol") or ""), r) for r in tradable]
    symbols = [(p, s, r) for p, s, r in symbols if p and s]

    if not symbols:
        return pd.DataFrame(), {}, [], []

    max_workers = max(1, batch_size)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for pair, symbol, r in symbols:
            meta = {
                "pair": pair,
                "symbol": symbol,
                "exchange": r.get("exchange"),
                "base": r.get("base"),
                "quote": r.get("quote"),
                "venues": r.get("venues"),
                "volume": r.get("volume"),
                "volume_rep": r.get("volume_rep"),
                "value_traded": r.get("Value.Traded"),
                "value_traded_usd": r.get("Value.Traded_usd"),
            }
            futures.append(executor.submit(fetch, pair, symbol, meta))
        wait(futures, return_when=ALL_COMPLETED)

    returns_df = pd.DataFrame(returns_map)
    returns_df = returns_df.fillna(0.0)

    # Drop sparse columns based on non-zero return count (treat 0 as missing)
    if len(returns_df) and min_history_frac > 0:
        min_count = int(len(returns_df) * min_history_frac)
        keep_cols = [c for c in returns_df.columns if int((returns_df[c] != 0).sum()) >= min_count]
        returns_df = returns_df[keep_cols]
        meta_map = {k: v for k, v in meta_map.items() if k in keep_cols}

    # Drop zero-variance columns
    if not returns_df.empty:
        var = returns_df.var()
        if isinstance(var, pd.Series):
            keep_cols = [str(c) for c, v in var.items() if float(v) > 0]
            returns_df = returns_df[keep_cols]
            meta_map = {k: v for k, v in meta_map.items() if k in keep_cols}

    return cast(pd.DataFrame, returns_df), meta_map, skipped, health_records


def _cluster_and_plot(
    returns: pd.DataFrame,
    *,
    output_dir: Path,
    max_clusters: int,
    linkage: str,
) -> Tuple[Path, Dict[int, List[str]]]:
    corr = _robust_correlation(returns)

    dist = np.sqrt(0.5 * (1 - np.clip(corr.values, -1, 1)))
    dist = (dist + dist.T) / 2
    np.fill_diagonal(dist, 0)

    condensed = squareform(dist, checks=False)
    link = sch.linkage(condensed, method=linkage)

    cluster_assignments = sch.fcluster(link, t=max_clusters, criterion="maxclust")
    clusters: Dict[int, List[str]] = {}
    for sym, cid in zip(corr.columns, cluster_assignments):
        clusters.setdefault(int(cid), []).append(str(sym))

    cmap = sns.diverging_palette(230, 20, as_cmap=True)
    g = sns.clustermap(
        corr,
        row_linkage=link,
        col_linkage=link,
        cmap=cmap,
        vmin=-1,
        vmax=1,
        center=0,
        square=True,
        linewidths=0.5,
        figsize=(18, 18),
        cbar_kws={"shrink": 0.5},
        xticklabels=True,
        yticklabels=True,
    )
    plt.setp(g.ax_heatmap.get_xticklabels(), rotation=90, fontsize=8)
    plt.setp(g.ax_heatmap.get_yticklabels(), rotation=0, fontsize=8)
    g.fig.suptitle("Forex Correlation Clustermap", fontsize=18, y=1.02)

    image_path = output_dir / "forex_universe_clustermap.png"
    plt.savefig(image_path, bbox_inches="tight", dpi=150)
    plt.close()

    return image_path, clusters


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze forex base universe export and generate report + clusters")
    parser.add_argument("--export-symbol", default="forex_base_universe")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--exclude-ig-singletons", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--min-venues", type=int, default=1)
    parser.add_argument(
        "--include-excluded",
        action="store_true",
        default=False,
        help="Include a table of excluded pairs (e.g. IG-only singletons) in the report",
    )

    parser.add_argument("--lookback-days", type=int, default=int(os.getenv("FOREX_LOOKBACK_DAYS", "365")))
    parser.add_argument("--interval", default=os.getenv("FOREX_INTERVAL", "1d"))
    parser.add_argument("--batch-size", type=int, default=int(os.getenv("FOREX_BATCH_SIZE", "4")))
    parser.add_argument("--min-history-frac", type=float, default=float(os.getenv("FOREX_MIN_HISTORY_FRAC", "0.8")))
    parser.add_argument("--max-gaps", type=int, default=int(os.getenv("FOREX_MAX_GAPS", "5")))
    parser.add_argument("--backfill", action="store_true", default=os.getenv("FOREX_BACKFILL", "0") == "1")
    parser.add_argument("--gapfill", action="store_true", default=os.getenv("FOREX_GAPFILL", "0") == "1")

    parser.add_argument("--max-clusters", type=int, default=int(os.getenv("FOREX_MAX_CLUSTERS", "8")))
    parser.add_argument("--linkage", default=os.getenv("FOREX_LINKAGE", "ward"))

    parser.add_argument("--skip-history", action="store_true", default=False)

    args = parser.parse_args()

    export_dir = _resolve_export_dir(args.run_id)
    export_path = _find_latest_export_file(export_dir, args.export_symbol)
    meta, raw_rows = _load_export_payload(export_path)

    if not raw_rows:
        logger.error("No data rows found in %s", export_path)
        return 2

    quote_to_usd = _compute_quote_to_usd(raw_rows)
    pair_rows = _build_pair_rows(raw_rows, quote_to_usd)

    tradable, excluded = _filter_tradable(
        pair_rows,
        exclude_ig_singletons=bool(args.exclude_ig_singletons),
        min_venues=int(args.min_venues),
    )

    output_dir = get_settings().prepare_summaries_run_dir()
    report_path = _write_liquidity_report(
        output_dir,
        export_path=export_path,
        export_meta=meta,
        tradable=tradable,
        excluded=excluded,
        quote_to_usd=quote_to_usd,
        include_excluded=bool(args.include_excluded),
    )
    logger.info("✅ Forex report written to %s", report_path)

    if args.skip_history:
        return 0

    jwt_token = os.getenv("TRADINGVIEW_JWT_TOKEN", "unauthorized_user_token")
    returns_df, meta_map, skipped, health_records = _build_returns_matrix(
        tradable,
        lookback_days=int(args.lookback_days),
        interval=str(args.interval),
        batch_size=int(args.batch_size),
        min_history_frac=float(args.min_history_frac),
        max_gaps=int(args.max_gaps),
        backfill=bool(args.backfill),
        gapfill=bool(args.gapfill),
        jwt_token=jwt_token,
    )

    health_path = output_dir / "forex_universe_data_health.csv"
    pd.DataFrame(health_records).to_csv(health_path, index=False)

    ok_count = sum(1 for r in health_records if r.get("status") == "ok")
    lines = report_path.read_text(encoding="utf-8").splitlines()
    lines.append("")
    lines.append("## Data Health")
    lines.append("")
    lines.append(f"Health report: `{health_path}`")
    lines.append(f"- Attempted: {len(health_records)}")
    lines.append(f"- OK: {ok_count}")
    lines.append(f"- Non-OK: {len(health_records) - ok_count}")
    report_path.write_text("\n".join(lines), encoding="utf-8")

    logger.info("✅ Data health report written to %s", health_path)

    if skipped:
        logger.info("Skipped history for: %s", ", ".join(sorted(set(skipped))))

    if returns_df.shape[1] < 3 or returns_df.empty:
        logger.warning("Not enough return series to cluster (cols=%s).", returns_df.shape[1])
        return 0

    # Persist returns + meta for reuse
    lakehouse = Path("data/lakehouse")
    lakehouse.mkdir(parents=True, exist_ok=True)
    returns_path = lakehouse / "forex_universe_returns.pkl"
    meta_path = lakehouse / "forex_universe_meta.json"
    with open(returns_path, "wb") as f_out:
        returns_df.to_pickle(f_out)
    meta_path.write_text(json.dumps(meta_map, indent=2), encoding="utf-8")

    image_path, clusters = _cluster_and_plot(
        returns_df,
        output_dir=output_dir,
        max_clusters=int(args.max_clusters),
        linkage=str(args.linkage),
    )

    clusters_path = output_dir / "forex_universe_clusters.json"
    clusters_path.write_text(json.dumps(clusters, indent=2), encoding="utf-8")

    # Append a short cluster summary to the existing report
    lines = report_path.read_text(encoding="utf-8").splitlines()
    lines.append("")
    lines.append("## Hierarchical Clusters")
    lines.append("")
    lines.append(f"Returns matrix: `{returns_path}` ({returns_df.shape[0]} dates x {returns_df.shape[1]} pairs)")
    lines.append(f"Clustermap: ![Forex Clustermap](./{image_path.name})")
    lines.append("")

    cluster_rows: List[Dict[str, Any]] = []
    corr = _robust_correlation(returns_df)
    for cid, members in sorted(clusters.items(), key=lambda x: int(x[0])):
        syms = [s for s in members if s in corr.columns]
        avg_corr = 1.0
        if len(syms) > 1:
            sub = corr.loc[syms, syms].to_numpy()
            tri = sub[np.triu_indices_from(sub, k=1)]
            avg_corr = float(np.mean(tri)) if len(tri) else 1.0
        cluster_rows.append(
            {
                "cluster": cid,
                "size": len(syms),
                "avg_corr": f"{avg_corr:.3f}",
                "members": ", ".join(f"`{s}`" for s in sorted(syms)),
            }
        )

    lines.append(_markdown_table(cluster_rows, ["cluster", "size", "avg_corr", "members"]))
    report_path.write_text("\n".join(lines), encoding="utf-8")

    logger.info("✅ Forex clustering artifacts: %s, %s", image_path, clusters_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
