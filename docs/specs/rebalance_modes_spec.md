# Functional Specification: Backtest Rebalance Modes

## 1. Mathematical Standards

### A. Weight Drift (Window Mode)
In `window` mode, the actual weight of an asset $i$ at time $t$ within a window starting at $t_0$ is:
$$w_{i,t} = \frac{w_{i,t_0} \cdot (1 + r_{i,t})}{ \sum_{j=1}^n w_{j,t_0} \cdot (1 + r_{j,t}) }$$
where $r_{i,t}$ is the cumulative return of asset $i$ from $t_0$ to $t$.

### B. Constant Weights (Daily Mode)
In `daily` mode, the system executes trades at each time step $t$ such that:
$$w_{i,t} = w_{i,target}$$
This requires a trade size $u_{i,t}$ to correct the drift from $t-1$:
$$u_{i,t} = w_{i,target} - w_{i,t-1,drift}$$

## 2. Operational Logic

### A. Window Rebalancing (`rebalance_mode: window`)
1.  **At $t_0$ (Start of Window)**:
    - Compare previous holdings $h_{t-1}$ with new target weights $w_{target}$.
    - Execute rebalance trades.
    - Apply transaction costs (Slippage + Commission).
2.  **For $t > t_0$**:
    - If `feat_rebalance_tolerance` is **FALSE**: Execute no further trades.
    - If `feat_rebalance_tolerance` is **TRUE**: 
        - Calculate drift $D_t = \sum |w_{actual,t} - w_{target}|$.
        - If $D_t > \text{rebalance\_drift\_limit}$: Trigger intra-window rebalance and charge friction.

### B. Daily Rebalancing (`rebalance_mode: daily`)
1.  **At each $t$**:
    - Calculate necessary trades to maintain $w_{target}$.
    - Apply transaction costs to every trade.
    - Aggregate cumulative turnover.

## 3. Simulator Mapping

| Simulator | `window` Implementation | `daily` Implementation |
| :--- | :--- | :--- |
| **CVXPortfolio** | `cvp.Hold()` policy after initial $t_0$ trade. | `cvp.FixedWeights()` policy. |
| **VectorBT** | Single-row weight matrix at $t_0$. | Multi-row broadcasted weight matrix. |
| **Custom/Returns** | Apply friction once at $t_0$; track drift returns. | Calculate daily turnover and subtract daily friction. |

## 4. Production Standards (2026 Audit)

### A. Momentum Drift Alpha
The 2026 rebalance audit revealed that `window` mode consistently outperforms `daily` mode for momentum-driven strategies. 
- **Mechanism**: Asset winners naturally increase their portfolio weight through drift. `daily` rebalancing prematurely sells these winners to return to target ("cutting the flowers"). 
- **Discovery**: `window` mode captured ~5% more absolute return in high-alpha `v3.1` profiles while reducing turnover by 17%.

### B. Default State
- **Production Default**: `window` (Trade once per window, hold through drift).
- **Institutional/Canary Default**: `daily` (Only if combined with `feat_turnover_penalty`).
- **Default Tolerance**: `False`
- **Drift Limit**: `0.05` (5%)
