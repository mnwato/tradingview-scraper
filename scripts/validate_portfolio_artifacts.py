import argparse
import glob
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, cast

import numpy as np
import pandas as pd

# Add the project root to the path so we can import internal modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradingview_scraper.settings import get_settings
from tradingview_scraper.symbols.stream.lakehouse import LakehouseStorage
from tradingview_scraper.symbols.stream.metadata import DataProfile, MetadataCatalog, get_symbol_profile

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("portfolio_auditor")

# Configuration
LAKEHOUSE_PATH = os.getenv("LAKEHOUSE_DIR", "data/lakehouse")


def get_run_artifacts():
    settings = get_settings()
    run_dir = settings.prepare_summaries_run_dir()

    # CR-831: Workspace Isolation
    c_raw = os.getenv("CANDIDATES_RAW", str(run_dir / "data" / "portfolio_candidates_raw.json"))
    c_sel = os.getenv("CANDIDATES_SELECTED", str(run_dir / "data" / "portfolio_candidates.json"))
    r_mat = os.getenv("RETURNS_MATRIX", str(run_dir / "data" / "returns_matrix.parquet"))

    # Fallback for raw returns if they exist separately
    r_raw = os.getenv("RETURNS_RAW", r_mat)

    return c_raw, c_sel, r_mat, r_raw


CANDIDATES_RAW_FILE, CANDIDATES_FILE, RETURNS_FILE, RETURNS_RAW_FILE = get_run_artifacts()
OPTIMIZED_FILE = os.path.join(LAKEHOUSE_PATH, "portfolio_optimized_v2.json")

FRESHNESS_THRESHOLD_HOURS = 24  # CR-829: Tightened for Crypto (Previously 72)
# Daily bars for TradFi can be stale across weekends/holidays; use a day-based threshold.
FRESHNESS_THRESHOLD_DAYS_TRADFI = int(os.getenv("FRESHNESS_THRESHOLD_DAYS_TRADFI", "5"))

# Institutional Safety Limits
BETA_THRESHOLD_DEFENSIVE = 0.50  # Max beta for Min Variance


class PortfolioAuditor:
    def __init__(self):
        self.storage = LakehouseStorage(base_path=LAKEHOUSE_PATH)
        self.catalog = MetadataCatalog(base_path=LAKEHOUSE_PATH)
        self.results_by_profile: Dict[DataProfile, List[Dict[str, Any]]] = {p: [] for p in DataProfile}
        self.summary: Dict[str, Any] = {
            "total": 0,
            "profiles": {p.value: 0 for p in DataProfile},
            "status_counts": {"OK": 0, "OK (MARKET CLOSED)": 0, "DEGRADED (GAPS)": 0, "STALE": 0, "MISSING": 0, "DROPPED": 0},
        }
        self.audit_failures = []

    def _symbol_from_lakehouse_filename(self, filename: str) -> Optional[str]:
        # Expected: <EXCHANGE>_<TICKER>_<INTERVAL>.parquet with <TICKER> possibly containing underscores.
        if not filename.endswith(".parquet"):
            return None
        stem = filename[: -len(".parquet")]
        parts = stem.split("_")
        if len(parts) < 3:
            return None
        exchange = parts[0]
        interval = parts[-1]
        if not exchange or not interval:
            return None
        ticker = "_".join(parts[1:-1])
        if not ticker:
            return None
        return f"{exchange}:{ticker}"

    def _strip_atom_suffix(self, symbol: str) -> str:
        """Removes strategy/direction suffix from Atom ID to get physical symbol."""
        # Standard Atom format: EXCHANGE:TICKER_logic_DIRECTION
        # If it contains no underscore after the first colon, it's likely already physical.
        if "_" not in symbol:
            return symbol

        # Split by underscore and check if last part is LONG/SHORT
        parts = symbol.split("_")
        if parts[-1] in ["LONG", "SHORT"]:
            # Reconstruct the part before the first suffix underscore
            # Usually: Symbol_Logic_Direction
            # But Symbol might have underscores too if it's qualified incorrectly,
            # though EXCHANGE:TICKER shouldn't have many.
            # Most reliable: find the first underscore after the ':'
            colon_idx = symbol.find(":")
            if colon_idx != -1:
                first_underscore = symbol.find("_", colon_idx)
                if first_underscore != -1:
                    return symbol[:first_underscore]
        return symbol

    def _resolve_candidate_symbol(self, symbol: str, *, interval: str, returns_symbols: set) -> str:
        # If it looks like an Atom ID, strip it first to find physical file
        phys_symbol = self._strip_atom_suffix(symbol)

        # Selected-mode candidates should already be fully qualified (EXCHANGE:SYMBOL).
        if ":" in phys_symbol:
            return phys_symbol

        # Raw-mode candidates may be unqualified (e.g., "AAPL"). If the lakehouse already contains a
        # unique match for the daily parquet, resolve it so health checks don't false-fail.
        try:
            lakehouse_dir = os.path.join(LAKEHOUSE_PATH)
            # Match any exchange prefix (NASDAQ_AAPL_1d.parquet, NYSE_AAPL_1d.parquet, ...).
            glob_pat = os.path.join(lakehouse_dir, f"*_{phys_symbol}_{interval}.parquet")
            matches = sorted([p for p in glob.glob(glob_pat) if os.path.isfile(p)])
        except Exception:
            return phys_symbol

        resolved: List[str] = []
        for path in matches:
            candidate = self._symbol_from_lakehouse_filename(os.path.basename(path))
            if candidate:
                resolved.append(candidate)

        if not resolved:
            return phys_symbol
        if len(resolved) == 1:
            return resolved[0]

        # Use returns_symbols (which are Atoms) to disambiguate if needed
        # We need to find which Atom matches our physical symbol
        for res in resolved:
            for ret_s in returns_symbols:
                if ret_s.startswith(res + "_"):
                    return res

        # Prefer common US venues if ambiguous.
        preferred_prefixes = ("NASDAQ:", "NYSE:", "AMEX:")
        for pref in preferred_prefixes:
            for cand in resolved:
                if cand.startswith(pref):
                    return cand

        return resolved[0]

    def calculate_market_sensitivity(self, assets: List[Dict[str, Any]], returns_df: Optional[pd.DataFrame]) -> Tuple[float, float]:
        """Calculates Beta and Correlation to SPY benchmark."""
        benchmark = "AMEX:SPY"
        if returns_df is None or returns_df.empty or benchmark not in returns_df.columns:
            return 0.0, 0.0

        weights_map = {str(a["Symbol"]): float(a["Weight"]) for a in assets}
        common_symbols = [s for s in weights_map.keys() if s in returns_df.columns]
        if not common_symbols:
            return 0.0, 0.0

        sub_rets = cast(pd.DataFrame, returns_df[common_symbols])
        w = np.array([weights_map[s] for s in common_symbols], dtype=float)
        port_rets = (sub_rets * w).sum(axis=1)

        market_rets = returns_df[benchmark]
        combined = pd.concat([port_rets, market_rets], axis=1).dropna()
        if len(combined) < 20:
            return 0.0, 0.0

        p_rets = combined.iloc[:, 0]
        m_rets = combined.iloc[:, 1]

        correlation = float(p_rets.corr(m_rets))
        # Ensure row vectors are passed to np.cov for correct shape
        if len(p_rets) > 1:
            cov_matrix = np.cov(p_rets.values, m_rets.values)
            cov = cov_matrix[0, 1]
            var_m = np.var(m_rets.values, ddof=1)  # Sample variance
            beta = float(cov / var_m) if var_m > 1e-12 else 0.0
        else:
            beta = 0.0

        return beta, correlation

    def run_health_check(self, type_filter: str = "all", mode: str = "selected", strict: bool = False):
        print("\n" + "=" * 100)
        print(f"PORTFOLIO DATA HEALTH CHECK ({mode.upper()}) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if strict:
            print("MODE: STRICT (Gaps are considered failures)")
        print("=" * 100)

        target_file = CANDIDATES_FILE if mode == "selected" else CANDIDATES_RAW_FILE
        if not os.path.exists(target_file):
            logger.error(f"❌ Candidates file missing: {target_file}")
            return False

        with open(target_file, "r") as f:
            candidates = json.load(f)

        returns_file = RETURNS_FILE if mode == "selected" else RETURNS_RAW_FILE
        if not os.path.exists(returns_file):
            # Fallback to parquet
            parquet_file = returns_file.replace(".pkl", ".parquet")
            if os.path.exists(parquet_file):
                returns_file = parquet_file
            else:
                # Try common name
                common_parquet = os.path.join(LAKEHOUSE_PATH, "returns_matrix.parquet")
                if os.path.exists(common_parquet):
                    returns_file = common_parquet

        returns_symbols = set()
        if os.path.exists(returns_file):
            try:
                if returns_file.endswith(".parquet"):
                    returns_df = pd.read_parquet(returns_file)
                else:
                    returns_df = pd.read_pickle(returns_file)
                if isinstance(returns_df, pd.DataFrame):
                    returns_symbols = set(returns_df.columns)
            except Exception:
                pass

        settings = get_settings()
        now = datetime.now()
        lookback_env = os.getenv("PORTFOLIO_LOOKBACK_DAYS")
        lookback_days = int(lookback_env) if lookback_env else int(settings.resolve_portfolio_lookback_days())
        lookback_cutoff = (now - timedelta(days=lookback_days)).timestamp()

        for c in candidates:
            raw_symbol = c["symbol"]
            # Atoms have format Asset_Logic_Direction
            # If logic is present, raw_symbol might be the atom_id if called from certain contexts
            # But the catalog needs the PHYSICAL symbol.
            physical_symbol = str(c.get("symbol", ""))

            symbol = self._resolve_candidate_symbol(physical_symbol, interval="1d", returns_symbols=returns_symbols)
            meta = self.catalog.get_instrument(symbol)
            profile = get_symbol_profile(symbol, meta)

            if type_filter == "crypto" and profile != DataProfile.CRYPTO:
                continue
            if type_filter == "trad" and profile == DataProfile.CRYPTO:
                continue

            self.summary["total"] += 1
            self.summary["profiles"][profile.value] += 1

            file_path = self.storage._get_path(symbol, "1d")
            file_exists = os.path.exists(file_path)
            last_ts = self.storage.get_last_timestamp(symbol, "1d")

            if not file_exists:
                self._record(profile, symbol, "MISSING")
                continue

            is_fresh = False
            if last_ts:
                last_dt = pd.Timestamp(last_ts, unit="s", tz="UTC")
                age_hours = (now.astimezone(last_dt.tz) - last_dt).total_seconds() / 3600
                if profile == DataProfile.CRYPTO:
                    is_fresh = age_hours <= FRESHNESS_THRESHOLD_HOURS
                else:
                    # TradFi: Be more lenient during known holidays/weekends
                    # Use Market-Day normalization: 22:00 UTC belongs to NEXT day
                    def to_market_date(dt):
                        if profile in [DataProfile.FOREX, DataProfile.FUTURES] and dt.hour >= 20:
                            return (dt + timedelta(hours=4)).date()
                        return dt.date()

                    last_market_date = to_market_date(last_dt)
                    today = now.date()

                    if last_market_date:
                        try:
                            from typing import Any

                            d1: Any = today
                            d2: Any = last_market_date
                            diff_days = (d1 - d2).days
                            is_fresh = diff_days <= FRESHNESS_THRESHOLD_DAYS_TRADFI
                        except Exception:
                            is_fresh = False

            if not is_fresh:
                self._record(profile, symbol, "STALE", last_ts)
                continue

            all_gaps = self.storage.detect_gaps(symbol, "1d", profile=profile, start_ts=lookback_cutoff)
            recent_gaps = all_gaps

            status = "OK"
            if recent_gaps:
                status = "DEGRADED (GAPS)"
            elif all_gaps:
                status = "OK (MARKET CLOSED)"

            if symbol not in returns_symbols:
                if mode == "selected":
                    status = "DROPPED"
                else:
                    # In raw mode, symbols might not be in returns yet because returns are built AFTER validation usually
                    # But if we are validating strictly, we might care.
                    # For now, "DROPPED" is confusing for raw mode if it just means "not yet processed"
                    # But the logic below says if mode == "raw", critical_health ignores "DROPPED".
                    # Let's keep it but clarify for raw mode.
                    pass

            self._record(profile, symbol, status, last_ts, len(recent_gaps))

        if self.summary["total"] == 0:
            logger.error("❌ No candidates found to validate. Check scanner outputs.")
            # In development/raw mode, if scanners returned 0 results, this is a valid failure state
            # but we shouldn't crash the script if we want to debug.
            # However, for the pipeline, 0 candidates means we can't proceed.
            return False

        self._print_health_dashboard()

        status_counts = self.summary["status_counts"]
        if mode == "raw":
            # Raw pool is a staging set; allow staleness (final gate is selected-mode health).
            critical_health = status_counts["MISSING"]
        else:
            critical_health = status_counts["MISSING"]
            if strict:
                critical_health += status_counts["STALE"] + status_counts["DEGRADED (GAPS)"]

        self.generate_health_report(mode=mode)

        return critical_health == 0

    def generate_health_report(self, mode: str = "selected"):
        md = []
        md.append(f"# 🏥 Data Health & Integrity Report ({mode.upper()})")
        md.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md.append("\n---")

        md.append("\n## 📊 Summary by Status")
        md.append("| Status | Count |")
        md.append("| :--- | :--- |")
        for status, count in self.summary["status_counts"].items():
            if count > 0:
                md.append(f"| {status} | {count} |")

        md.append("\n## 📂 Asset Class Breakdown")
        md.append("| Profile | Count |")
        md.append("| :--- | :--- |")
        for profile_val, count in self.summary["profiles"].items():
            if count > 0:
                md.append(f"| {profile_val} | {count} |")

        for profile in DataProfile:
            results = self.results_by_profile[profile]
            if not results:
                continue
            md.append(f"\n## 📦 {profile.value} Assets")
            md.append("| Symbol | Status | Last Date | Recent Gaps |")
            md.append("| :--- | :--- | :--- | :--- |")
            sorted_results = sorted(results, key=lambda x: (x["status"] != "OK", x["symbol"]))
            for r in sorted_results:
                status_str = r["status"]
                if "OK" in status_str:
                    status_str = f"✅ {status_str}"
                elif status_str in ["MISSING", "STALE"]:
                    status_str = f"❌ {status_str}"
                else:
                    status_str = f"⚠️ {status_str}"
                md.append(f"| `{r['symbol']}` | {status_str} | {r['last_date']} | {r['gaps']} |")

        settings = get_settings()
        settings.prepare_summaries_run_dir()
        report_path = settings.run_reports_dir / "selection" / f"data_health_{mode}.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w") as f:
            f.write("\n".join(md))
        print(f"✅ Data health report generated at: {report_path}")

    def run_logic_audit(self):
        print("\n" + "=" * 100)
        print("PORTFOLIO QUANTITATIVE LOGIC AUDIT")
        print("=" * 100)

        if not os.path.exists(OPTIMIZED_FILE):
            print("⚠️ No optimized portfolio file found to audit.")
            return True

        with open(OPTIMIZED_FILE, "r") as f:
            data = json.load(f)

        returns_df: Optional[pd.DataFrame] = None
        if os.path.exists(RETURNS_FILE):
            raw_rets = pd.read_pickle(RETURNS_FILE)
            if isinstance(raw_rets, pd.DataFrame):
                returns_df = raw_rets

        all_passed = True
        profiles = data.get("profiles", {})

        for name, p_data in profiles.items():
            print(f"\n[ AUDITING PROFILE: {name.upper()} ]")
            assets = p_data.get("assets", [])
            clusters = p_data.get("clusters", [])

            # 1. Weight Normalization (100% sum)
            total_w = sum(a["Weight"] for a in assets)
            if abs(total_w - 1.0) > 0.001:
                self._fail(f"Profile '{name}' weight sum is {total_w:.4f} (expected 1.0)")
                all_passed = False
            else:
                print(f"✅ Weight Normalization: {total_w:.2%}")

            # 2. Cluster Concentration Cap (25%)
            cluster_weights = {c["Cluster_Label"]: c["Gross_Weight"] for c in clusters}
            over_capped = [c_id for c_id, w in cluster_weights.items() if w > 0.251]
            if over_capped:
                self._fail(f"Profile '{name}' clusters exceed 25% cap: {over_capped}")
                all_passed = False
            else:
                max_c = max(cluster_weights.values()) if cluster_weights else 0
                print(f"✅ Cluster Concentration: Max bucket is {max_c:.2%}")

            # 3. Market Sensitivity (Beta Audit)
            beta, corr = self.calculate_market_sensitivity(assets, returns_df)
            if name == "min_variance" and beta > BETA_THRESHOLD_DEFENSIVE:
                self._fail(f"Profile '{name}' beta is too high: {beta:.2f} (max {BETA_THRESHOLD_DEFENSIVE})")
                all_passed = False
            else:
                print(f"✅ Market Sensitivity: Beta={beta:.2f}, Corr={corr:.2f}")

            # 4. Barbell Insulation & Uniqueness
            if name == "barbell":
                aggressors = [a for a in assets if "AGGRESSOR" in a.get("Type", "")]
                core = [a for a in assets if "CORE" in a.get("Type", "")]

                agg_clusters = set(str(a["Cluster_ID"]) for a in aggressors)
                if len(agg_clusters) != len(aggressors):
                    self._fail(f"Barbell aggressors are not from unique clusters! ({len(agg_clusters)} vs {len(aggressors)})")
                    all_passed = False
                else:
                    print(f"✅ Aggressor Uniqueness: {len(agg_clusters)} unique buckets")

                core_clusters = set(str(a["Cluster_ID"]) for a in core)
                overlap = agg_clusters.intersection(core_clusters)
                if overlap:
                    self._fail(f"Barbell insulation breach! Overlap in clusters: {overlap}")
                    all_passed = False
                else:
                    print("✅ Risk Insulation: Zero overlap between Core and Aggressors")

                agg_w = sum(a["Weight"] for a in aggressors)
                if agg_w < 0.049 or agg_w > 0.31:
                    self._fail(f"Barbell aggressor weight is {agg_w:.4f} (expected 0.05-0.30 range)")
                else:
                    print(f"✅ Sleeve Balance: {agg_w:.1%} Aggressors / {1.0 - agg_w:.1%} Core")

            # 5. Metadata Completeness
            missing_metadata = [a["Symbol"] for a in assets if a.get("Sector") == "N/A" or not a.get("Description")]
            if missing_metadata:
                print(f"⚠️ Metadata Warning: {len(missing_metadata)} assets have incomplete sector/description.")
            else:
                print("✅ Metadata Completeness: 100%")

        if not all_passed:
            print("\n❌ LOGIC AUDIT FAILED")
            for f in self.audit_failures:
                print(f"  - {f}")
        else:
            print("\n✅ ALL QUANTITATIVE LOGIC CHECKS PASSED")

        return all_passed

    def _record(self, profile, symbol, status, last_ts=None, gap_count=0):
        last_date = datetime.fromtimestamp(last_ts).strftime("%Y-%m-%d") if last_ts else "N/A"
        self.results_by_profile[profile].append({"symbol": symbol, "status": status, "last_date": last_date, "gaps": gap_count})
        self.summary["status_counts"][status] += 1

    def _fail(self, message):
        self.audit_failures.append(message)

    def _print_health_dashboard(self):
        for profile in DataProfile:
            results = self.results_by_profile[profile]
            if not results:
                continue
            print(f"\n[ {profile.value} ASSETS ]")
            print(f"{'SYMBOL':<25} | {'STATUS':<20} | {'LAST DATE':<12} | {'RECENT GAPS'}")
            print("-" * 80)
            sorted_results = sorted(results, key=lambda x: (x["status"] != "OK", x["symbol"]))
            for r in sorted_results:
                icon = "✅" if "OK" in r["status"] else "❌" if r["status"] in ["MISSING", "STALE"] else "⚠️"
                print(f"{r['symbol']:<25} | {icon} {r['status']:<17} | {r['last_date']:<12} | {r['gaps']}")

        print("\n" + "=" * 100)
        print("SUMMARY BY STATUS")
        print("-" * 40)
        for status, count in self.summary["status_counts"].items():
            if count > 0:
                print(f"{status:<20}: {count}")
        print("=" * 100)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", choices=["crypto", "trad", "all"], default="all")
    parser.add_argument("--mode", choices=["selected", "raw"], default="selected")
    parser.add_argument("--only-health", action="store_true")
    parser.add_argument("--only-logic", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Fail if any gaps are detected")
    args = parser.parse_args()

    auditor = PortfolioAuditor()

    health_ok = True
    logic_ok = True

    if not args.only_logic:
        health_ok = auditor.run_health_check(type_filter=args.type, mode=args.mode, strict=args.strict)

    if not args.only_health:
        logic_ok = auditor.run_logic_audit()

    if not health_ok or not logic_ok:
        sys.exit(1)
    else:
        sys.exit(0)
