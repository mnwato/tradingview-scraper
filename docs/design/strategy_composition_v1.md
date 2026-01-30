# Design Doc: Strategy Composition & Atomic Ensembles (v1.0)

## 1. Concept: The Fundamental Atom
The smallest unit of alpha is a **Strategy Atom**, defined as:
`Atom = (Asset, AlphaLogic, Direction, TimeScale)`

Examples:
- `A1 = (BTCUSDT, Momentum, LONG, 1h)`
- `A2 = (ETHUSDT, Trend, SHORT, 1d)`

Exactly ONE logic per atom is enforced to ensure attribution purity.

## 2. Strategy Composition
A **Complex Strategy** is a weighted composition of Atoms. In the 3-pillar architecture, Pillar 2 (Synthesis) focuses on producing these streams, while Pillar 3 (Allocation) manages the target risk profiles, including market neutrality.

### 2.1 Synthetic Long Normalization
SHORT atoms are inverted in Pillar 2 so that convex solvers see all atoms as alpha-positive contributors:
- $R_{syn,long} = R_{raw}$
- $R_{syn,short} = -clip(R_{raw}, upper=1.0)$ (short loss cap at -100%)

### 2.2 Allocation Responsibility (CR-290)
Market Neutrality is a **Pillar 3 (Allocation)** responsibility. Instead of pre-composing neutral pairs in the Synthesis layer, the Portfolio Engine is tasked with allocating across synthesized atoms while enforcing a global beta-neutrality constraint ($|w^T\beta| \le \text{Tolerance}$).

## 3. The 3-Pillar Integration

### Pillar 3: Allocation (Decoupled & Hardened)
- **Synthetic Hierarchical Clustering**: Allocation layer performs hierarchical clustering on synthesized return streams to identify logic-space correlations.
- **Constraint Hardening**: Market Neutral constraints utilize **Dynamic Beta-Tolerance Scaling**:
    - $N \ge 15$: Tolerance = 0.05
    - $N < 15$: Tolerance = 0.15
- **Numerical Hardening**: The `CLARABEL` solver is utilized for robust handling of neutral constraints and risk-parity profiles.
- **Experimental Guardrails**: The `market_neutral` constraint is gated by the `feat_market_neutral` feature flag.

## 4. Execution Layer (Flattening)
Final trade execution requires flattening strategy weights back to underlying physical assets:
$$Weight_{Asset,j} = \sum_{Strategies} (Weight_{Strategy,k} \times Factor_{Asset_j, k})$$
Where $Factor$ is $1.0$ for LONG atoms and $-1.0$ for SHORT atoms.

### 4.1 Weight Flattening Guard
The orchestrator implements a post-aggregation guard to verify that $\sum Weight_{Net}$ aligns with the target exposure ($0.0$ for Neutral, $1.0$ for Long-Only).

## 5. Cross-Pillar Audit Standards
To ensure 3-Pillar integrity, the platform mandates:
1. **Pillar 1 (Selection)**: Must emit granular feature and probability logs.
2. **Pillar 2 (Synthesis)**: Must explicitly record directional inversion factors.
3. **Pillar 3 (Allocation)**: Must log solver convergence and condition number (Kappa) statistics.
All signals are consolidated into the human-readable "Deep Forensic Report."
