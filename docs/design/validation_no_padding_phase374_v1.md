# Design: Phase 374 Validation Tools “No Padding” Compliance (v1)

## 1. Purpose
Phase 374 removes “calendar padding” behaviors from validation/reporting utilities.

Padding (e.g., `fillna(0.0)`) can:
- hide calendar mismatches,
- distort volatility/correlation,
- violate the platform’s “No Padding” institutional standard.

## 2. Scope
Primary target:
- `scripts/validate_meta_parity.py`

Secondary targets (follow-up):
- other validation/reporting scripts that align calendars using `fillna(0.0)` for TradFi/mixed calendars.

## 3. Design

### 3.1 Calendar-Safe Alignment
For returns matrix `R[t, asset]`:
1. restrict to common assets between weights and returns,
2. use a date inner-join alignment, and
3. drop any rows with missing values after asset restriction.

Pseudo:
```
assets = [Symbol in weights if Symbol in returns.columns]
rets = returns[assets]
rets = rets.dropna(how="any")      # strict alignment; no padding
```

### 3.2 Report Alignment Loss
Validation output MUST log:
- rows before alignment,
- rows after alignment,
- percent rows dropped.

### 3.3 Path Determinism
Validation MUST resolve run dirs via settings (`settings.summaries_runs_dir`), not hard-coded paths.

## 4. Acceptance Criteria (TDD)
1. Validation does not call `fillna(0.0)` on returns.
2. Missing rows are dropped (row count decreases) rather than padded to 0.
3. Run dir resolution uses `settings.summaries_runs_dir`.

