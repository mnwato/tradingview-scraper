# Strategy Integration Requirements v1 (Modular Design)

## 1. Overview
The platform is transitioning to a modular strategy architecture where alpha sources (Atoms) are grouped into **Strategies** within the manifest and integrated into the global v4 Selection & Allocation pipeline.

## 2. Manifest Abstraction (Strategies vs Pipelines)
To ensure precise logic assignment and organizational clarity, the `discovery` block in `manifest.json` now supports a `strategies` layer.

### 2.1 Schema Definition
- **Profile**: Contains a `discovery` block.
- **Strategy**: A named group of scanners (e.g., `rating_ma`, `vol_breakout`).
- **Logic Injection**: The name of the strategy is automatically injected as the `logic` field for all atoms discovered by its scanners.

Example Manifest:
```json
"discovery": {
  "strategies": {
    "rating_ma": {
      "scanners": ["scanners/crypto/ratings/binance_perp_rating_ma_long", ...],
      "interval": "1d"
    }
  }
}
```

## 3. The Strategy Atom
Each Atom is defined by a triplet: `(Asset, Logic, Direction)`.
- **Asset**: Canonical symbol (e.g., `BINANCE:BTCUSDT`).
- **Logic**: The alpha generation strategy name (e.g., `rating_all`, `rating_ma`, `rating_osc`).
- **Direction**: `LONG` or `SHORT`.

## 4. Modular Scanners (Trend Following)
Scanners must emit candidates with enriched technical ratings from TradingView.

### 4.1 technical_rating_scanner
- **Source**: TradingView `Recommend.All`, `Recommend.MA`, `Recommend.Other`.
- **Ranking Logic**:
    - **LONG**: `Recommend.* > 0.0` (Strict Buy/Strong Buy only).
    - **SHORT**: `Recommend.* < 0.0` (Strict Sell/Strong Sell only).
- **Institutional Liquidity Floors**:
    - **Perpetuals**: `Value.Traded > 50,000,000 USD`.
    - **Spot**: `Value.Traded > 20,000,000 USD`.
- **Base Universe Standard (L1)**:
    - Discovery scanners must inherit from the audited pure baseline configurations to ensure strict venue isolation:
        - `binance_spot_base.yaml`: Enforces strictly **>$20M 24h Volume** and `type: spot`.
        - `binance_perp_base.yaml`: Enforces strictly **>$50M 24h Volume** and `type: swap`.
    - **Venue Isolation**: Spot and Perp outputs are strictly separated. Scanners must not mix assets from different market types to maintain implementation purity.
    - **Purity Standard**: Base scanners utilize explicit TradingView server-side filters (`filters` list) and avoid redundant Pydantic-side `volume` blocks.
    - **Zero Alpha Bias**: Base pools are unranked (sorted by `name`) and stripped of all technical gates to ensure 100% data density for downstream Inference.
- **Discovery Sorting**: 
    - Scanners must sort by the primary rating (e.g. `Recommend.All`, `Recommend.MA`) during discovery to ensure the most extreme sentiment signals are recruited first.
    - **LONG**: `sort_by: RatingField, order: desc`.
    - **SHORT**: `sort_by: RatingField, order: asc`.
- **Output**: A candidates manifest containing ratings and intended direction.
- **Implementation Purity (Venue Selection)**:
    - Scanners must prioritize **Stablecoin-quoted** instruments (`USDT`, `USDC`, `FDUSD`) for discovery.
    - Regional fiat pairs (`TRY`, `IDR`, `BRL`, etc.) are permitted only if no stablecoin venue meets the liquidity floor, to avoid artificial alpha driven by local currency devaluation.
- **Velocity Capping (Alpha Hygiene)**:
    - Atoms displaying extreme velocity (**ROC > 50%** or **ROC < -50%**) are flagged as "Anomaly Candidates" and must be strictly validated by the `SelectionPolicyStage` vetoes to prevent blow-off top recruitment.


### 4.2 Discovery Architecture (Lean Recruitment)
- **Constraint**: Scanners MUST avoid complex conditional filtering (e.g. `IF Volatility < 10 AND ROC > 20`).
- **Philosophy**: The discovery layer is for high-throughput recruitment based on Liquidity and Primary Alpha (Rating).
- **Offload to Selection**: All statistical shaping, outlier pruning (e.g. `ROC > 100%`), and hygiene checks (e.g. `ADX`, `Kurtosis`) must be implemented as **Vetoes** in the `SelectionPolicyStage`.
- **Reasoning**: This prevents premature alpha leakage and ensures that "noisy" but potentially high-value candidates are evaluated contextually by the Inference engine rather than being blindly discarded by the scraper.

## 5. Tier 2 Alpha Features (Enrichment)
To enable advanced scoring and risk partitioning in the Selection Pipeline, the following fields are persisted but not used for discovery-stage filtering.

### 5.1 volatility_d (Volatility.D)
- **Source**: TradingView daily trailing volatility.
- **Usage**: Used in `PartitioningStage` to prevent high-volatility atoms from dominating risk-parity clusters.

### 5.2 volume_change_pct (volume_change)
- **Source**: TradingView 24h volume change percentage.
- **Usage**: Used in `InferenceStage` as a "Momentum Confirmation" multiplier; positive volume spikes confirm the conviction of rating signals.

### 5.3 rate_of_change (ROC)
- **Source**: TradingView Rate of Change indicator.
- **Usage**: Used in `InferenceStage` as a core momentum feature to capture the velocity of price movement over the standard lookback period.

## 6. Pipeline Integration

### 6.1 Strategy as an Asset (Independent Streams)
The architecture supports treating each Strategy as an independent asset class for Meta-Portfolio allocation.
- **Granular Profiles**: Manifest profiles (e.g., `crypto_rating_all`, `crypto_rating_ma`) allow for the isolated execution of a single strategy logic.
- **Synthetic Return Streams**: The output of a strategy-specific pipeline run is a "Portfolio Equity Curve" that can be treated as a synthetic asset (e.g., `Strategy_Rating_MA_Returns`).
- **Meta-Composition**: These synthetic streams can be ingested by the Pillar 4 Meta-Allocation engine to construct multi-strategy portfolios with diversified alpha sources.

### 6.2 Data Persistence
Technical ratings must be preserved from the **Discovery** stage through the **Lakehouse** and into the **Inference** stage.
- **Lakehouse Metadata**: `portfolio_meta.json` must store ratings as features.
- **Deduplication**: Atoms with the same `(Asset, Logic)` must be pruned based on rating strength or liquidity.
- **Venue Isolation**: Spot and Perpetual outputs are strictly separated at the discovery stage. Scanners are partitioned by market type (`type: spot` vs `type: swap`) to prevent cross-venue implementation errors.
- **Workflow Isolation**: Rating-based strategies are managed via the `crypto_rating_alpha` profile to prevent dilution of standard trend-following sleeves.

### 6.2 Selection Pipeline (v4)
- **Feature Engineering**: Ratings should be used as primary alpha scores or as confirmation filters.
- **Clustering (HRP)**: Assets discovered via different logic modules should be clustered together to ensure portfolio-wide factor diversity.

### 6.3 Meta-Portfolio Composition (Combined Profiles)
- **Native Hedging**: Strategy profiles (e.g., `crypto_rating_all`) intentionally combine LONG and SHORT scanners.
- **Reasoning**: This allows the Pillar 3 Allocation Engines (HRP, MinVar) to dynamically optimize the hedge ratio based on live correlations, rather than forcing a static 50/50 split at the profile level.
- **Market Neutrality**: The `market_neutral` profile (`|beta| < 0.15`) relies on this combined pool to construct beta-neutral portfolios natively.

### 6.4 Directional Validation Profiles
- **Baseline Isolation**: Simple Spot LONG and Spot SHORT profiles (e.g., `binance_spot_rating_all_long/short`) are used to validate the individual efficacy of directional signals.
- **Runbook**: `docs/runbooks/binance_spot_ratings_all_long_short_runbook_v1.md`
- **Ensemble Integrity**: These profiles provide the ground truth for "Synthetic Return Streams", ensuring that when they are combined in a Meta-Portfolio, the resulting Sharpe gain is driven by true diversification rather than mathematical artifacts.
- **Audit Contract**: Atomic sleeves intended for meta inclusion SHOULD satisfy the artifact + reproducibility contract in `docs/design/atomic_sleeve_audit_contract_v1.md`.

## 8. Meta-Portfolio Ensembling (Pillar 4)
The Pillar 4 layer enables the creation of "Portfolios of Portfolios" by ensembling synthetic return streams.

### 8.1 Requirements for Production Readiness
1. **Joined Return Persistence**: Every strategy specific run must persist its full-history equity curve as a `.pkl` file in `data/returns`.
2. **Inner-Join Synchronization**: Meta-allocation must utilize inner joins on the index to handle multi-asset calendar discrepancies (e.g. BTC 24/7 vs SPY 5/7).
3. **Identity Preservation**: Consolidated meta-reports must map synthetic symbols back to their original `(Asset, Logic, Direction)` identity.
4. **Audit Provenance**: Meta-manifests must record the `run_id` and genesis metadata of every constituent sleeve.

### 8.2 Directional Validation Protocol (LONG/SHORT Mixing)
To validate the system's ability to ensemble mixed-direction alpha, the following benchmarking tournament is mandated:
1. **Sleeve A (Long Baseline)**: `binance_spot_rating_all_long`.
2. **Sleeve B (Short Baseline)**: `binance_spot_rating_all_short`.
3. **Ensemble (Meta Benchmark)**: Combined 50/50 HRP allocation.
4. **Success Criteria**:
    - **Net Beta Reduction**: The ensemble must demonstrate lower correlation to BTC than the Long sleeve.
    - **Sharpe Gain**: The ensembled equity curve must achieve a higher Sharpe ratio than either isolated sleeve through diversification.
    - **Weight Fidelity**: Meta-optimized weights must correctly reflect the relative risk contribution of each directional stream.
5. **Directional Correction Gate (Hard)**:
    - Run the Directional Correction Sign Test on both sleeves and require PASS before meta ensembling.
    - Spec: `docs/specs/directional_correction_sign_test_v1.md`

### 8.3 Meta-Performance Attribution (Pillar 4 Metrics)
To ensure transparency in ensembled portfolios, meta-reports must provide:
1. **Sleeve-Level Metrics**: Individual Sharpe/Vol/Return for each synthetic stream.
2. **Ensemble Metrics**: Total performance of the weighted sleeve combination (Meta-Sharpe).
3. **Correlation Matrix**: Inner-sleeve correlation to identify factor overlap.
4. **Drift Stability Audit**: Verification that no synthetic stream encountered numerical scaling anomalies during simulation.

## 11. Granular Alpha Modules
To maximize meta-portfolio diversification, the system prioritizes granular technical factors over composite signals.
- **Trend Module (MA)**: Driven by `Recommend.MA` across 14 moving averages. Target for `binance_spot_rating_ma` sleeves.
- **Momentum Module (OSC)**: Driven by `Recommend.Other` across oscillators (RSI, Stochastic, etc.). Target for `binance_spot_rating_osc` sleeves.
- **Normalization**: All granular modules must follow the **Synthetic Long Normalization** standard before meta-aggregation:
  - $R_{syn,long} = R_{raw}$
  - $R_{syn,short} = -clip(R_{raw}, upper=1.0)$ (short loss cap at -100%)
  - Reference audit: `docs/specs/directional_correction_sign_test_v1.md`

## 13. Institutional Liquidity Preservation
To prevent alpha dilution and ensure tradeability, the system maintains strict liquidity floors for all asset classes.
- **Binance Spot Standard**: Minimum **$20M USD** daily traded volume.
- **Futures/Swap Standard**: Minimum **$50M USD** daily traded volume.
- **Remediation Order**: If a strategy pool is sparse, the system must first resolve data health issues (staleness/gaps) and then expand scanner breadth within the same liquidity tier. Lowering liquidity floors is only permitted as a last resort under explicit regime-shift authorization.

## 15. Workflow-Driven Data Ingestion (Pillar 0)
To eliminate sequential script bottlenecks, data ingestion is promoted to "Pillar 0" with a dedicated workflow engine.
- **Idempotency**: Every fetch task must be idempotent. Re-running a task for a `STABLE` asset must result in a zero-op.
- **Dependency Tracking**: Pillar 1 (Discovery) tasks trigger Pillar 0 (Ingestion) requests. Pillar 2 (Synthesis) waits for Pillar 0 completion.
- **Parallelism**: Data fetching is parallelized at the symbol level using a managed worker pool, with rate-limiting handled centrally.
- **Forensic Ledger**: Every data unit (Symbol/Interval) maintains its own audit trail within the run-specific ledger, identifying exactly which fetch attempt provided the data.
