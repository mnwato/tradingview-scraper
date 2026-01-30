# Design: Atomic Pipeline v2 (MLOps Edition)

## 1. Objective
To modernize the atomic portfolio pipeline by applying MLOps principles of immutability, lineage, and data contract enforcement.

## 2. Standardized Vocabulary (The Hierarchy)

| Layer | Semantic Name | Technical Activity | Data Contract |
| :--- | :--- | :--- | :--- |
| **L0** | **Foundation** | Lakehouse State | Parquet/Feature Store |
| **L1** | **Ingestion Gate** | Recruitment & Validation | PIT-Fidelity, No-Padding |
| **L2** | **Alpha Inference** | HTR & Log-MPS Scoring | InferenceOutputs Schema |
| **L3** | **Strategy Synthesis** | Atom Composition | SyntheticMatrix Schema |
| **L4** | **Risk Allocation** | Convex Optimization | Simplex-Bounded Weights |

## 3. The Foundation Gate

### 3.1 Pre-flight Validation
Before a pipeline executes, the `QuantSDK.validate_foundation()` primitive will perform:
- **Existence Check**: Verify `returns_matrix.parquet` and `features_matrix.parquet` exist.
- **Freshness Check**: Ensure data is not stale (> 24h old for production profiles).
- **Schema Validation**: Confirm required columns (e.g., `symbol`, `timestamp`, `sector`) are present.

### 3.2 Ingestion Validator
A dedicated `IngestionValidator` class will be introduced to enforce:
- **Toxicity Bounds**: Drop assets with daily returns exceeding 500% (5.0).
- **Session Continuity**: Verify TradFi assets do not have data on weekends (inner-join enforcement).

## 4. Model Lineage & Immutability

### 4.1 Lakehouse Snapshots
To prevent concurrent DataOps jobs from corrupting an active Alpha run, the pipeline will:
1. Create a `snapshots/<RUN_ID>/` directory.
2. Symlink the current `data/lakehouse/` files into this directory.
3. Lock the `RUN_ID` to this specific version of the foundation.

### 4.2 Forensic Linking
The `trace_id` generated during the **Foundation Gate** will be injected into the `SelectionContext`. Every subsequent stage output (e.g., `portfolio_candidates.json`, `portfolio_optimized.json`) must include:
- `trace_id`
- `foundation_hash`
- `engine_version` (v3.5.x)

## 5. Implementation Roadmap (Stage Registry Refactor)

The following stages will be renamed for semantic clarity:

| Old ID | New ID | Category |
| :--- | :--- | :--- |
| `selection.ingestion` | `foundation.ingest` | foundation |
| `selection.features` | `foundation.features` | foundation |
| `selection.inference` | `alpha.inference` | alpha |
| `selection.clustering` | `alpha.clustering` | alpha |
| `selection.policy` | `alpha.policy` | alpha |
| `selection.synthesis` | `alpha.synthesis` | alpha |
| `allocation.optimize` | `risk.optimize` | risk |
| `meta.returns` | `meta.aggregation` | meta |

## 6. Security & Privacy
- Snapshots only contain symlinks to avoid data duplication and exposure.
- Personal Access Tokens (PATs) and Exchange Keys must never be logged in telemetry traces.
