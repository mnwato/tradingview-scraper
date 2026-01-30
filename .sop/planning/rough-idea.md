# Rough Idea

## Concept
Build **fractal portfolio optimization** capabilities backed by **MLOps-style pipelines** that can:

- Scan candidate assets / strategy atoms
- Filter for hygiene and data integrity
- Rank and select candidates
- Feed downstream portfolio optimization and reporting

## Notes / Initial Direction
- Emphasis on pipeline orchestration and reproducibility (scan → filter → rank → optimize).
- Expect multiple pipelines (e.g., universe scan, feature computation, ranking, risk/constraints, backtest simulation).

## Addendum (2026-01-21)
Shift emphasis toward **cleanup/refactor of Data + Alpha pipelines** to **speed up the feedback loop** during iteration (faster dev runs, tighter inner loop), while preserving institutional reproducibility and auditability.
