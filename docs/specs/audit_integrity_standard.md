# Standard: Audit Ledger Integrity & Replayability (Jan 2026)

This document defines the formal technical standard for the **Audit Ledger 2.0**, ensuring long-term research integrity and regulatory readiness.

## 1. Cryptographic Chaining
- **Mechanism**: Every record contains a `prev_hash` field referencing the SHA-256 hash of the immediate predecessor.
- **Root of Trust**: The run begins with a `genesis` block pinning the environment (`uv.lock`) and version control state (Git HEAD).
- **Security**: Any modification to a past record invalidates the entire subsequent chain.

## 2. Deterministic Lineage (Data Hashing)
To ensure that a backtest result can be replayed months later, the **Data Lineage** must be immutable.
- **Standard**: `get_df_hash` must ignore memory addresses and purely structural metadata.
- **Normalization**: All indices are converted to `%Y-%m-%d %H:%M:%S` naive UTC strings before hashing. This prevents "Fail" results due to differing timezone interpretations between research and execution environments.

## 3. Atomic Decision Pairs
Decision points are recorded as an **Intent-Outcome** pair:
1.  **Intent Block**: Records the parameters $(\mu, \gamma, \lambda)$ and the **input hashes** (Returns Matrix + Cluster Tree).
2.  **Outcome Block**: Records the **output hash** (Weight Vector) and performance metrics.

## 4. Replay Protocol
A valid "Replay Audit" must demonstrate:
1.  **Input Parity**: Current data slice hash == Intent input hash.
2.  **Execution Parity**: Re-running the optimizer with the recorded parameters yields the same weight vector.
3.  **Outcome Parity**: Re-executed output hash == Outcome output hash.

## 5. Compliance Alignment
- **SEC Rule 17a-4**: Supports non-rewriteable, non-erasable recordkeeping standards.
- **MiFID II RTS 6**: Provides the "Order Lifecycle" transparency required for algorithmic trade reconstruction.
