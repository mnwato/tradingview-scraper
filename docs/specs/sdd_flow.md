# Specification: Specs Driven Development (SDD) Flow

## 1. Overview
Specs Driven Development (SDD) is the core methodology used to ensure the reliability and auditability of the TradingView Scraper quantitative platform. It mandates that every feature, optimization, or risk control starts with a formal specification and ends with a forensic audit.

## 2. The SDD Lifecycle

### Step 1: Requirements Definition (`docs/specs/`)
Define the "What" and "Why".
- Identify the quantitative need (e.g., "Directional Purity").
- Document specific constraints (e.g., "Correlation < 0.7").
- Define Success Criteria (e.g., "Sharpe Ratio improvement > 0.1").

### Step 2: Design Specification (`docs/design/`)
Define the "How".
- Architecture diagrams.
- Math/Signal logic formulas.
- Data schema updates.
- Infrastructure impacts.

### Step 3: Implementation & TDD
Code the logic.
- Atomic commits mapping to design stages.
- Unit tests validating the math against the spec.

### Step 4: Verification Sweep
Rerun the production pipelines.
- Execute full `flow-data` and `flow-production`.
- Generate fresh artifacts.

### Step 5: Forensic Audit (`docs/reports/`)
Validate the realized behavior.
- Ledger log traces.
- Performance comparisons.
- **Fractal Audit**: Review of `meta_cluster_tree_*.json` to verify sleeve-level risk contributions before physical collapse.
- Final "Health" sign-off.

## 3. Mandatory Artifacts
- **Audit Ledger (`audit.jsonl`)**: Machine-readable decision trail.
- **Risk Profiles Matrix**: Cross-engine performance comparison.
- **Cluster Metadata Tree**: Hierarchical view of fractal allocations.

## 4. Operational Invariants
- **No Spec, No Code**: Structural changes require a pre-commit spec update.
- **Audit Integrity**: Pipeline failures must be documented in `known_issues.md`.
- **Reproducibility**: Any run must be re-creatable using the archived `manifest.json`.
