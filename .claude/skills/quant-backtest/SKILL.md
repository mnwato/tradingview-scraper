---
name: quant-backtest
description: Run backtesting simulation on portfolio weights. Use when the user wants to validate a portfolio, run historical simulation, or analyze backtest results. Supports vectorized and Nautilus simulators.
compatibility: Claude Code
metadata:
  author: quant-team
  version: "1.0"
  pipeline: validation
allowed-tools: Bash(python:*) Bash(make:*) Read
---

# Quant Backtesting Pipeline

Run historical simulation on optimized portfolio weights to validate performance before live deployment.

## When to use this skill

Use this skill when the user wants to:
- Validate portfolio weights with backtesting
- Run walk-forward analysis
- Compare different optimization profiles
- Analyze Sharpe, Sortino, MaxDD metrics

## Arguments

- `run_id` - The run ID containing portfolio weights (required)
- `simulator` - Simulator type: `vectorbt`, `nautilus` (optional, default: vectorbt)

## How to run

1. **List available runs**:
   ```bash
   ls -la data/artifacts/summaries/runs/
   ```

2. **Run backtest**:
   ```bash
   make port-test RUN_ID=$ARGUMENTS
   ```

3. **View results**:
   - Equity curves: `data/artifacts/summaries/runs/<RUN_ID>/data/returns/*.pkl`
   - Tournament results: `data/artifacts/summaries/runs/<RUN_ID>/data/tournament_results.csv`

## Output

Report the following metrics for the primary profiles (Sharpe, Ann. Return, MaxDD).
