# Design Specification: HMM Regime Detector Optimization (v1.0)

## 1. Objective
Audit, benchmark, and optimize the Hidden Markov Model (HMM) component of the `MarketRegimeDetector`. The goal is to ensure stability, performance, and semantic correctness in identifying volatility regimes (Crisis vs Quiet).

## 2. Current Implementation Analysis
- **Method**: `_hmm_classify(self, x: np.ndarray) -> str`
- **Library**: `hmmlearn.hmm.GaussianHMM`
- **Input**: Absolute returns (`np.abs(x)`), standardized.
- **Config**: 2 components, `diag` covariance, 50 iterations.
- **Logic**:
    - Fits HMM to the window.
    - Predicts hidden states.
    - If the current state corresponds to the higher mean (of absolute returns), label `CRISIS`.
    - Else `QUIET`.
- **Issues**:
    - **Stability**: HMM fitting is non-convex; results depends on random initialization.
    - **Performance**: Fitting an HMM on every window (rolling) is computationally expensive ($O(N \cdot K^2)$).
    - **Semantics**: Is "High Volatility" always "Crisis"? Sometimes it's just "Active/Normal" vs "Dead/Quiet".

## 3. Research Hypothesis
1.  **GMM Alternative**: A simple Gaussian Mixture Model (GMM) might capture the "two distributions of volatility" just as well as HMM, without the transition matrix overhead, if the temporal persistence is weak or not needed for simple classification.
2.  **Stability Fix**: Fix random seed or use smarter initialization (e.g., k-means init).
3.  **Optimization**: Reduce `n_iter` or relax convergence tolerance for speed.

## 4. Benchmark Plan
- **Metric**: Execution time per call.
- **Metric**: Consistency (Jaccard index of labels across runs with different seeds).
- **Metric**: Separation (Distance between state means).

## 5. Proposed Changes
1.  **Refactor**: Extract HMM logic into a dedicated method/class `VolatilityRegimeHMM` for better testing.
2.  **Optimization**:
    - Investigate `GMM` as a fallback or replacement.
    - If sticking with HMM, implement "Warm Start" (pass previous transition matrix) if possible (hard in rolling window without state persistence).
    - Actually, `hmmlearn` doesn't support warm start easily across different data lengths.
3.  **Configuration**: Expose HMM params in `__init__`.

## 6. Success Criteria
- HMM tests pass deterministically.
- Benchmarking shows acceptable latency (< 10ms per asset).
- Clear distinction between "High Vol" (Crisis) and "Low Vol" (Quiet/Normal).
