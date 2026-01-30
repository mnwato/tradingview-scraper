# Design: Production Deployment Audit (v1)

## 1. Objective
To perform a final, comprehensive audit of the entire quantitative platform, ensuring that all architectural pillars, forensic gates, and telemetry layers are functioning at institutional-grade standards before marking the system as "Production Ready".

## 2. Full System Pass Criteria

The "Golden Run" must satisfy the following invariants:

| Component | Requirement | Validation Method |
| :--- | :--- | :--- |
| **Foundation** | Registry is consistent and gaps are filled. | `QuantSDK.validate_foundation()` |
| **Alpha** | No network I/O during selection. | Trace Audit (Spans) |
| **Meta** | Recursive aggregation and flattening sum conservation. | Stable Sum Gate ($< 10^{-4}$) |
| **Telemetry** | End-to-end trace linkage (Host + Ray Workers). | `forensic_trace.json` analysis |
| **Reporting** | Comparative performance metrics and diversity attribution. | `meta_portfolio_report.md` |

## 3. Artifact Archive Protocol

Upon a successful production run, the following directory structure must be finalized and locked:

```
data/artifacts/summaries/runs/<RUN_ID>/
├── audit.jsonl             # Unbroken decision ledger
├── config/                 # resolved_manifest.json (Replayability)
├── data/                   # snapshot/symlinks to foundation + local outputs
├── logs/                   # All trace-aware worker logs
├── reports/                # Forensic Markdown reports
└── forensic_trace.json     # Unified OTel performance trace
```

## 4. Final Sign-off
The system is declared ready when:
1. All TDD tests pass (`tests/test_*.py`).
2. The `meta_production` profile completes without warnings in the audit ledger.
3. The forensic report shows sane Sharpe and Sortino ratios for the ensembled sleeves.
