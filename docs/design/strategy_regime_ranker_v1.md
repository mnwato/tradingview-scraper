# Design Specification: Strategy-Specific Regime Ranker (v1.0)

## 1. Objective
Enhance the asset selection process by introducing a `StrategyRegimeRanker`. Instead of selecting assets purely based on momentum or volatility, this ranker scores assets based on their suitability for a specific trading strategy (e.g., Trend Following, Mean Reversion) given the asset's current market regime.

## 2. Problem Statement
- Current selection engines (like `HTR v3.4`) select assets based on generic "quality" metrics (Sharpe, Volatility, Momentum).
- However, a "High Quality" Trend asset (Strong Trend, Low Vol) is a "Bad Quality" Mean Reversion asset (No oscillations).
- We need to select the *right* assets for the *intended* strategy profile.

## 3. The Ranker Architecture

### 3.1 Interface
```python
class StrategyRegimeRanker:
    def rank(self, candidates: List[Dict], returns: pd.DataFrame, strategy: str) -> List[Dict]:
        """
        Ranks candidates by strategy fit score.
        Args:
            candidates: List of candidate metadata (must include 'symbol').
            returns: DataFrame of recent returns for candidates.
            strategy: 'trend_following' | 'mean_reversion' | 'breakout'
        Returns:
            Sorted candidates with 'rank_score' and 'regime_label' added.
        """
```

### 3.2 Strategy Profiles

#### A. Trend Following (`trend_following`)
- **Ideal Regime**: `INFLATIONARY_TREND`, `EXPANSION`.
- **Avoid**: `STAGNATION`, `CRISIS` (unless Short).
- **Metrics**:
    - High Hurst Exponent (> 0.55).
    - Positive Momentum.
    - Low to Medium Volatility (Stable Trend).
- **Scoring**: $Score = w_1 \cdot RegimeScore + w_2 \cdot Hurst + w_3 \cdot Momentum$.

#### B. Mean Reversion (`mean_reversion`)
- **Ideal Regime**: `STAGNATION` (Range bound), `CRISIS` (Oversold), `QUIET` (Oscillating).
- **Avoid**: `INFLATIONARY_TREND` (Runaway train).
- **Metrics**:
    - Low Hurst Exponent (< 0.45).
    - High Volatility (for Crisis reversion) or Low Vol (for Range).
    - High RSI divergence (if available) or simply high cyclicality.
- **Scoring**: $Score = w_1 \cdot RegimeScore + w_2 \cdot (1 - Hurst) + w_3 \cdot Volatility$.

### 3.3 Regime Scoring Matrix
The Ranker will calculate a `regime_fit` score (0.0 to 1.0) for each asset using `MarketRegimeDetector` on that asset's history.

| Asset Regime | Trend Fit | MeanRev Fit |
| :--- | :--- | :--- |
| **EXPANSION** | 1.0 | 0.2 |
| **INFLATIONARY_TREND** | 1.0 | 0.0 |
| **STAGNATION** | 0.0 | 1.0 |
| **CRISIS** | 0.5 (Short) | 0.8 (Bounce) |
| **QUIET** | 0.3 | 0.9 |
| **NORMAL** | 0.5 | 0.5 |

## 4. Implementation Details
- **Module**: `tradingview_scraper/selection_engines/ranker.py`
- **Dependency**: `MarketRegimeDetector` (from `tradingview_scraper.regime`).
- **Optimization**: Running `detect_regime` on 500 assets is slow (15ms * 500 = 7.5s).
    - Use `BacktestEngine`'s pre-calculated regime if possible? No, asset-specific regime is different from Market Regime.
    - We must run detector on each asset.
    - **Speedup**: Use the optimized `n_iter=10` HMM or GMM if appropriate. Or calculate simple metrics (Hurst) directly vectorized.
    - *Decision*: Ranker will compute `Hurst` and `Regime` for top candidates only (Refinement stage), not Discovery stage (thousands of assets).

## 5. Integration Point
- In `SelectionEngine.select` (e.g., `v3_4_htr.py`), after initial filtering (Liquidity, History), call `ranker.rank()` before Final Selection/Clustering.

## 6. Test Plan
- **Mock Data**: Create synthetic Trend series and MeanRev series.
- **Test 1**: `rank(..., strategy='trend_following')` should rank Trend series higher.
- **Test 2**: `rank(..., strategy='mean_reversion')` should rank MeanRev series higher.
