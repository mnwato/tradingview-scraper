# Design Doc: Directional Synthetic Logic (v1.0)

## 1. Context & Objective
Quantitative optimization engines (Convex Solvers) are mathematically designed to find optimal positive weights for positive expected returns. Handling `SHORT` directions requires a transformation that aligns "Price Decline" with "Positive Alpha."

## 2. Synthetic Long Normalization
We implement **Synthetic Long Normalization** to allow direction-naive solvers to handle short-biased atoms.

### 2.1 The Transformation
In **Pillar 2 (Synthesis)**, Strategy Atoms tagged with `direction: SHORT` undergo return inversion:
$$R_{syn,short} = -clip(R_{raw}, upper=1.0) \times Signal_{logic}$$
This enforces the synthetic short loss cap at `-100%` for extreme single-bar moves.

### 2.2 Numerical Impact
1. **Positive Expected Return**: A falling asset ($R_{raw} < 0$) with a positive logic signal produces a positive synthetic return ($R_{syn} > 0$), making it attractive to the solver.
2. **Covariance Stability**: Inverting returns preserves the variance but flips the sign of the covariance relative to other atoms. This correctly identifies the short atom as a diversifier or hedge in logic-space.
3. **Constraint Integrity**: The solver operates in a "Long-Only" strategy space (weights $\ge 0$), which is significantly more stable than allowing negative weights in 3rd party optimization libraries.

## 3. Realization & Mapping
While the solver sees a "Long" position in a strategy atom, the backtest simulator and implementation layer must map this back to the physical asset.

### 3.1 Weight Reporting
- **Strategy Weight ($W_{strat}$)**: The weight returned by the solver for the atom (always $\ge 0$).
- **Net Weight ($W_{net}$)**: 
    - Calculated during **Weight Flattening**: $W_{net} = \sum (W_{strat, i} \times Factor_i)$
    - $Factor = 1.0$ for LONG atoms, $-1.0$ for SHORT atoms.


### 3.2 Realized Return Calculation
The backtest simulator must calculate PnL using the raw returns and net weights:
$$PnL = W_{net} \times R_{raw}$$
By substitution:
$$PnL = (-1 \times W_{syn}) \times R_{raw}$$
With the synthetic-short definition $R_{syn,short} = -clip(R_{raw}, upper=1.0)$, the solver-facing view is:
$$W_{syn} \times R_{syn,short} = W_{syn} \times (-clip(R_{raw}, upper=1.0))$$
This is equivalent to shorting the raw asset under the platform’s collateral-limited modeling (the `-100%` short loss cap).

### 3.3 Simulation Boundary (Nautilus Parity)
To maintain architectural purity, the **Nautilus Simulator** must be strictly "Logic-Agnostic".
- **Input**: Flattened Physical Weights ($W_{net}$).
- **Operation**: Execution of physical BUY/SELL orders.
- **Prohibition**: The simulator must **NOT** perform logic inversion, handle "Strategy Atoms", or manage synthetic return streams. All mapping from Logic ($W_{syn}$) to Physical ($W_{net}$) must occur **upstream** in the Order Generator or Simulation Wrapper.

## 4. Risks & Mitigations
- **Borrow Costs**: Shorting incurs costs. These must be modeled as a drag on $R_{syn}$ prior to optimization.
- **Reporting Confusion**: Audit logs must clearly distinguish between $W_{syn}$ and $W_{net}$ to prevent "Inverse Exposure" hallucinations during forensic review.
