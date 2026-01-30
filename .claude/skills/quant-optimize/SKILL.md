---
name: quant-optimize
description: Run portfolio optimization on selected assets. Use when the user wants to optimize portfolio weights, run HRP/MinVar/MaxSharpe, or generate allocation recommendations.
compatibility: Claude Code
metadata:
  author: quant-team
  version: "1.0"
  pipeline: allocation
allowed-tools: Bash(python:*) Bash(make:*) Read
---

# Quant Portfolio Optimization

Run convex optimization to determine optimal portfolio weights from selected assets.

## When to use this skill

Use this skill when the user wants to:
- Optimize portfolio weights
- Run HRP, MinVar, or MaxSharpe optimization
- Generate allocation recommendations
- Compare different risk profiles

## Optimization profiles

- `hrp` - Hierarchical Risk Parity (default, most robust)
- `min_variance` - Minimum Variance
- `max_sharpe` - Maximum Sharpe Ratio
- `equal_weight` - Equal weight baseline
- `risk_parity` - Risk Parity (ERC)

## How to run

1. **Run optimization with default profile (HRP)**:
   ```bash
   make port-optimize RUN_ID=$ARGUMENTS
   ```

2. **Run with specific profile**:
   ```bash
   python scripts/optimize_portfolio.py \
     --run-id $ARGUMENTS \
     --profile hrp
   ```

3. **View results**:
   ```bash
   cat data/artifacts/summaries/runs/<RUN_ID>/data/portfolio_optimized_v2.json
   ```

## Example usage

User: "Optimize the latest run with HRP"
→ Execute: `make port-optimize RUN_ID=<latest>`
