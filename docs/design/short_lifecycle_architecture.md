# Design Document: Short Lifecycle Architecture (v1)

## 1. Objective
To standardize the handling of SHORT positions throughout the investment lifecycle, ensuring that the friction, mechanics, and risks of short selling are accurately modeled and executed. This architecture bridges the gap between "Negative Weights" (Mathematical Abstraction) and "Short Selling" (Operational Reality).

## 2. The Short Strategy Atom
In the v4 pipeline, a SHORT position is not merely a negative number; it is a distinct strategy atom with unique properties.
- **Definition**: `Atom(Asset, Logic, SHORT)`
- **Return Stream**: $R_{syn} = -clip(R_{raw}, upper=1.0) - Cost_{borrow}$ (enforces a -100% synthetic short loss cap)
- **Risk Profile**: Short positions have theoretically unlimited downside; the -100% cap is a numerical guardrail aligned with collateral-limited modeling.

## 3. The 6-Stage Short Lifecycle

### Stage 1: Identification (Selection Layer)
- **Signal**: Negative momentum or mean-reversion logic triggers a `SHORT` direction tag.
- **Veto Check (CR-730)**: The `SelectionPolicyStage` verifies `borrow_availability` metadata. If `inventory < min_threshold`, the atom is vetoed to prevent "Naked Shorting."

### Stage 2: Synthesis (Alpha Layer)
- **Inversion**: Returns are mathematically inverted.
- **Cost Injection (CR-700)**: A synthetic "drag" is applied to the return stream representing the estimated daily borrow cost (e.g., 0.01% or Funding Rate). This ensures the solver only selects shorts that generate alpha *after* paying for leverage.

### Stage 3: Allocation (Risk Layer)
- **Optimization**: The solver allocates a positive weight $W_{syn}$ to the inverted atom.
- **Constraint**: The `GrossLeverageConstraint` ensures $\sum |W_i| \le \text{TargetLeverage}$, preventing the portfolio from becoming over-extended.

### Stage 4: Realization (Orchestration Layer)
- **Mapping**: The orchestrator converts the positive strategy weight back to a physical negative weight: $W_{real} = -1 \times W_{syn}$.

### Stage 5: Execution (Order Layer)
- **State Analysis**: The Order Generator compares `Current_Pos` and `Target_Pos`.
- **Transitions**:
    - `Long -> Short`: `SELL` (Close Long) then `SELL_SHORT` (Open Short).
    - `Short -> Long`: `BUY_COVER` (Close Short) then `BUY` (Open Long).
    - `Short -> Neutral`: `BUY_COVER`.
    - `Neutral -> Short`: `SELL_SHORT`.

### Stage 6: Maintenance (Simulation/Live Layer)
- **Margin Monitoring (CR-710)**: Daily check of `Equity / Gross_Exposure`.
- **Liquidation**: If `Margin_Ratio < Maintenance_Margin` (e.g., 50%), a forced `BUY_COVER` is triggered to reduce exposure.

## 4. Friction Modeling
Standardizing the cost of shorts is critical for realistic backtests.
- **Interest**: $Cost_{daily} = |Position_{value}| \times (Rate_{borrow} / 365)$.
- **Dividends/Forks**: Short positions are liable for paying out any dividends or hard-fork value distributed by the asset.

## 5. Risk Management Integration
- **Stop-Loss**: Short positions require tighter stop-loss thresholds due to "Squeeze Risk" (Gamma spikes).
- **Concentration**: The `Directional Balance Constraint` (CR-640) ensures shorts never dominate the portfolio beyond a 60% threshold, mitigating systemic squeeze exposure.
