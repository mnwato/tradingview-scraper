# Specification: Strict Scoreboard Issue Playbooks v1 (Jan 2026)

This document provides **reproducible research + audit playbooks** for the strict-scoreboard issue backlog in `docs/specs/plan.md`.

Scope:
- Strict-scoreboard oriented: focus on why `is_candidate` is empty vs non-empty and how to resolve root causes.
- Diagnostics are explicitly **non-gating** unless a spec promotes them into thresholded gates.
- Commands are designed to be deterministic and artifact-driven (run-scoped files under `artifacts/summaries/runs/<RUN_ID>/`).

## 0. Common Preflight (Required for Every Investigation)

For a target run:

1. **Verify audit ledger hash chain**
   - `uv run scripts/archive/verify_ledger.py artifacts/summaries/runs/<RUN_ID>/audit.jsonl`
2. **Confirm scoreboard artifacts exist**
   - `ls -1 artifacts/summaries/runs/<RUN_ID>/data/tournament_scoreboard.csv artifacts/summaries/runs/<RUN_ID>/data/tournament_candidates.csv`
3. **Confirm window settings**
   - Inspect `audit.jsonl` for `context.train_window/test_window/step_size` (first `backtest_optimize:intent` record is sufficient).

Helper (veto distribution) – deterministic summary from scoreboard:

```bash
python - <<'PY'
import pandas as pd
from collections import Counter
from pathlib import Path

run_id = "20260105-180000"
df = pd.read_csv(Path(f"artifacts/summaries/runs/{run_id}/data/tournament_scoreboard.csv"))

def split_fail(s):
    s = "" if s is None else str(s)
    if not s or s == "nan":
        return []
    return [p.strip() for p in s.split(";") if p.strip()]

c = Counter()
for s in df.get("candidate_failures", []):
    for p in split_fail(s):
        c[p] += 1

is_cand = df["is_candidate"].fillna(False).astype(bool)
is_base = df.get("is_baseline", False)
if not hasattr(is_base, "astype"):
    is_base = False
else:
    is_base = is_base.fillna(False).astype(bool)

print("rows", len(df))
print("candidates_total", int(is_cand.sum()))
print("candidates_nonbaseline", int((is_cand & ~is_base).sum()))
print("candidates_baseline", int((is_cand & is_base).sum()))
print("top_vetoes", dict(c.most_common(12)))
PY
```

## 1. ISS-001 — Simulator parity gate realism (`sim_parity`)

### Goal
Make the parity gate:
- computed only when parity is meaningful (both simulators present and not in fallback),
- auditable (identify worst offenders),
- useful (gate blocks true divergences, not noise), and
- not a “silent no-op” (e.g., parity always 0.0 due to fallback mode).

### Evidence Runs
- Parity as dominant veto: `20260105-174600` (120/20/20; `sim_parity` vetoed 76/92 rows).
- Larger-window context: `20260105-180000` (180/40/20; parity veto reduced to 12/92).
- Earlier parity behavior: `20260105-004747`, `20260105-011037`.

### Actions
1. **Distribution audit (scoreboard-level)**
   - Compute parity gap distribution overall and per `(selection, engine, profile)`:
     - mean/median/p95/max
     - top 10 offenders
2. **Artifact audit (return series)**
   - For the worst offenders, load:
     - `data/returns/<sim>_<engine>_<profile>.pkl` for `cvxportfolio` and `nautilus`
     - compare daily series overlap, correlations, and annualized return differences.
3. **Log audit (fallback mode)**
   - Search the run log for Nautilus fallback strings (must be absent for meaningful parity):
     - `NautilusTrader adapter running in parity fallback mode`
4. **Friction alignment sanity**
   - Verify friction knobs match (slippage/commission/cash asset) across simulators and are recorded in settings.

### Commands (deterministic)
**A. Scoreboard parity summary**
```bash
python - <<'PY'
import pandas as pd
from pathlib import Path

run_id = "20260105-174600"
df = pd.read_csv(Path(f"artifacts/summaries/runs/{run_id}/data/tournament_scoreboard.csv"))

vals = df["parity_ann_return_gap"].dropna().astype(float)
print("n_rows", len(df), "n_parity", len(vals))
if len(vals):
    print("mean", float(vals.mean()), "median", float(vals.median()), "p95", float(vals.quantile(0.95)), "max", float(vals.max()))

top = df.sort_values("parity_ann_return_gap", ascending=False).head(12)
print(top[["selection","engine","profile","simulator","parity_ann_return_gap","candidate_failures"]].to_string(index=False))
PY
```

**B. Compare daily series for a specific offender**
```bash
python - <<'PY'
import pandas as pd
from pathlib import Path

run_id = "20260105-004747"
returns_dir = Path(f"artifacts/summaries/runs/{run_id}/data/returns")

# Example keys; replace with actual offender keys from the scoreboard.
key_cvx = "cvxportfolio_custom_hrp"
key_nt  = "nautilus_custom_hrp"

s1 = pd.read_pickle(returns_dir / f"{key_cvx}.pkl").dropna()
s2 = pd.read_pickle(returns_dir / f"{key_nt}.pkl").dropna()

idx = s1.index.intersection(s2.index)
s1, s2 = s1.loc[idx], s2.loc[idx]

def ann_return(s):
    if s.empty:
        return None
    return float((1.0 + s).prod() ** (252.0 / len(s)) - 1.0)

print("overlap_days", len(idx))
print("ann_return_cvx", ann_return(s1))
print("ann_return_nt", ann_return(s2))
print("corr", float(s1.corr(s2)) if len(idx) > 2 else None)
print("mean_abs_gap", float((s1 - s2).abs().mean()) if len(idx) else None)
PY
```

### Acceptance
- Parity is never computed from fallback-mode simulators (or fallback is explicitly tagged and treated as missing parity).
- A production-parity mini-matrix produces non-empty strict candidates without weakening parity into a no-op.

## 2. ISS-002 — `af_dist` dominance under larger windows (`180/40/20`)

### Goal
Explain and (if appropriate) fix why `af_dist` becomes the dominant veto once temporal fragility is stabilized by longer windows.

### Baseline policy note
- Baseline rows are not guaranteed to pass strict gates, but **they may be valid strict candidates if they do pass**.
- In particular, baseline `benchmark` being eligible under `min_af_dist = -0.20` is acceptable if it meets the full strict gate stack, and may be treated as an “anchor candidate” for stability runs.
- `raw_pool_ew` is primarily treated as a calibration signal for fragility/tails; if it passes strict gates, it is valid (not auto-excluded).
  - Policy record: `docs/specs/iss002_policy_decision_20260105.md`

### Evidence Run
- `20260105-170324` (180/40/20, pre-fix): `missing:af_dist` dominates because `antifragility_dist.is_sufficient=false` for all rows (tail size 8; tail-sufficiency fix landed after this run).
- `20260105-180000` (180/40/20): baseline rows fail `af_dist` (negative values).
- `20260105-191332` (180/40/20, defaults): `af_dist` is the dominant veto (24/27 rows); strict candidates are non-empty (3/27), but baselines remain non-candidates due to negative `af_dist`.

### Actions
1. **Baseline interpretation audit**
   - Inspect baseline rows’ `af_dist`, `stress_alpha`, and tail multipliers.
2. **Metric definition audit**
   - Confirm `af_dist` definition for baseline series is intended to be directly comparable to strategies.
3. **Calibration decision**
   - Decide whether baselines are reference-only (allowed to fail `af_dist`) or whether baseline expectations should differ (must be spec’d).
4. **Component attribution**
   - Decompose `af_dist` into `skew` and `log(tail_asym)` to see whether the veto is driven by distribution skew (common) vs tail asymmetry.
5. **Threshold sensitivity**
   - Recompute “would-be candidates” under alternate `min_af_dist` values using the existing scoreboard outputs (no tournament rerun required).

### Commands
**A. Baseline rows (scoreboard values)**
```bash
python - <<'PY'
import pandas as pd
from pathlib import Path

run_id = "20260105-191332"
df = pd.read_csv(Path(f"artifacts/summaries/runs/{run_id}/data/tournament_scoreboard.csv"))
base = df[(df["engine"]=="market") & (df["profile"].isin(["market","benchmark","raw_pool_ew"]))].copy()
print(base[["simulator","profile","avg_window_sharpe","af_dist","stress_alpha","cvar_mult","mdd_mult","temporal_fragility","candidate_failures"]].to_string(index=False))
PY
```

**B. Component breakdown from tournament payload (`skew`, `tail_asym`)**
```bash
python - <<'PY'
import json
import math
import pandas as pd
from pathlib import Path

run_id = "20260105-191332"
run_dir = Path(f"artifacts/summaries/runs/{run_id}")
payload_path = run_dir / "grand_4d_tournament_results.json"
payload = json.loads(payload_path.read_text())

results = payload["rebalance_audit_results"]["window"]["v3.2"]
rows = []
for sim, sim_blob in results.items():
    for eng, eng_blob in sim_blob.items():
        for prof, prof_blob in eng_blob.items():
            dist = (prof_blob.get("summary") or {}).get("antifragility_dist") or {}
            if not dist:
                continue
            tail_asym = float(dist.get("tail_asym"))
            skew = float(dist.get("skew"))
            af = float(dist.get("af_dist"))
            rows.append(
                {
                    "simulator": sim,
                    "engine": eng,
                    "profile": prof,
                    "af_dist": af,
                    "skew": skew,
                    "tail_asym": tail_asym,
                    "log_tail_asym": float(math.log(tail_asym + 1e-12)),
                }
            )

df = pd.DataFrame(rows).sort_values("af_dist")
print(df.to_string(index=False))
PY
```

**C. Sensitivity: strict candidates under alternate `min_af_dist` (no rerun)**
```bash
python - <<'PY'
import pandas as pd
from pathlib import Path

run_id = "20260105-191332"
df = pd.read_csv(Path(f"artifacts/summaries/runs/{run_id}/data/tournament_scoreboard.csv"))

MAX_FRICTION = 0.3
MAX_FRAGILITY = 2.75302
MIN_JACCARD = 0.3
MIN_STRESS_ALPHA = 0.0
MAX_TURNOVER = 0.5
MAX_TAIL_MULT = 1.25
MAX_PARITY = 0.015

def strict_mask(min_af: float):
    m = pd.Series(True, index=df.index)
    m &= df["friction_decay"].astype(float) <= MAX_FRICTION
    m &= df["temporal_fragility"].astype(float) <= MAX_FRAGILITY
    m &= df["selection_jaccard"].astype(float) >= MIN_JACCARD
    m &= df["af_dist"].astype(float) >= min_af
    m &= df["stress_alpha"].astype(float) >= MIN_STRESS_ALPHA
    m &= df["avg_turnover"].astype(float) <= MAX_TURNOVER
    m &= df["cvar_mult"].astype(float) <= MAX_TAIL_MULT
    m &= df["mdd_mult"].astype(float) <= MAX_TAIL_MULT
    m &= df["parity_ann_return_gap"].astype(float) <= MAX_PARITY
    return m

thresholds = [-0.6, -0.4, -0.3, -0.25, -0.2, -0.1, 0.0, 0.1]
print("rows", len(df), "current_candidates", int(df["is_candidate"].fillna(False).astype(bool).sum()))
for t in thresholds:
    m = strict_mask(float(t))
    base = df["engine"].eq("market") & df["profile"].isin(["market", "benchmark", "raw_pool_ew"])
    print(f"min_af_dist={t:>5}: candidates={int(m.sum()):>2} (baseline_candidates={int(m[base].sum())})")
PY
```

### Deep dive note
- `docs/specs/audit_iss002_af_dist_dominance_20260105.md` (component-level analysis + threshold sensitivity on Run `20260105-191332`).

### Acceptance
- `af_dist` semantics for baselines are documented, including whether negative values are expected.
- Strict candidates remain non-empty for `180/40/20` even if baselines are reference-only.

## 3. ISS-003 — Baseline row policy (presence vs eligibility)

### Goal
Make baseline expectations unambiguous across docs and tooling.

### Actions
1. **Policy decision record**
   - Choose one:
     - Baselines are reference-only (must be present and audit-complete; may fail strict gates).
     - Baselines must pass a subset of gates (requires explicit exemptions + spec).
2. **Codify**
   - Ensure `docs/specs/plan.md` and `docs/specs/benchmark_standards_v1.md` match the policy.
3. **Validation**
   - Ensure smokes produce non-empty candidates under the chosen policy (not necessarily baseline candidates).

### Acceptance
- Single, consistent baseline policy across docs/specs and scoreboard behavior.

## 4. ISS-004 — Temporal fragility stress-test vs production window defaults

### Goal
Establish a clear windowing policy:
- `120/20/20` as stress probe (fragility amplifier),
- `180/40/20` as stability default (robustness probe),
without breaking production parity expectations.

### Actions
1. **Dual-smoke execution**
   - Run identical dimension grids with only windowing changed:
     - Smoke A: `120/20/20`
     - Smoke B: `180/40/20` (overlapping)
2. **Compare veto distributions**
   - Confirm temporal fragility drops materially in Smoke B.
3. **Publish recommended defaults**
   - Update spec docs with recommended windowing for each use case.

### Acceptance
- Stability-default smoke yields non-empty strict candidates reliably.
- Stress smoke remains useful as a sign-flip detector without becoming the only “production” view.

## 5. ISS-005 — Friction alignment (`friction_decay`) failures

### Goal
Explain and reduce `friction_decay` vetoes without weakening the gate.

### Actions
1. **Row-level offender list**
   - Sort scoreboard by `friction_decay` and isolate baseline vs non-baseline offenders.
2. **Model audit**
   - Verify friction inputs are consistent across simulators and recorded in settings (slippage/commission).
3. **Sensitivity analysis**
   - Re-run a small smoke with only friction parameters changed (if needed) and compare the veto rate.

### Acceptance
- Friction gate failures are explainable (diagnostics exist) and reduced in stability-default runs.

## 6. ISS-006 — HRP cluster universe collapse to `n=2` (skfolio HRP not exercised)

### Goal
Ensure skfolio HRP is exercised under production-parity smokes when skfolio is enabled (or else reflect reality in runbook dims).

### Actions
1. **Log scan for fallback warnings**
   - Confirm whether `skfolio hrp: cluster_benchmarks n=2 < 3; using custom HRP fallback.` appears.
2. **Universe breadth test**
   - Increase universe breadth (e.g., `selection.top_n`) or change smoke dimensions so `n>=3` clusters is reliably achieved.
3. **Re-run smoke and confirm skfolio HRP path executed**

### Acceptance
- Production-parity smokes either (a) reliably hit `n>=3` and exercise skfolio HRP, or (b) explicitly disable skfolio HRP in those conditions by spec.

## 7. ISS-007 — `min_variance` beta gate stability

### Goal
Confirm beta gating is stable across windowing regimes and aligned with defensive intent.

### Actions
1. Compare `min_variance` beta distributions under:
   - `120/20/20` (e.g., `20260105-174600`)
   - `180/40/20` (e.g., `20260105-180000`)
2. Identify whether vetoes cluster by simulator or by engine.

### Acceptance
- Beta gate veto rate is stable and explainable; defensive profiles do not pass with high beta.
