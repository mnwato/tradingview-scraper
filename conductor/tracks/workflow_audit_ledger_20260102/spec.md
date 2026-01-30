# Spec: E2E Workflow & Audit Ledger Integration

## 1. Goal
Ensure the entire quantitative pipeline (Discovery -> Prep -> Audit -> Selection -> Optimization) is cryptographically traceable using the `AuditLedger`. Every decision must be recorded as an `intent` or `outcome` with stable input/output hashes.

## 2. Pipeline Stages
1.  **Discovery (Scanners)**: Record `intent` (scanner config hash) and `outcome` (symbol list hash).
2.  **Preparation (Data Prep)**: Record `intent` (target symbols) and `outcome` (returns matrix hash).
3.  **Forensic Audit (Risk/Antifragility)**: Record `intent` (returns matrix hash) and `outcome` (risk stats hash).
4.  **Natural Selection (Pruning)**: Record `intent` (selection mode/params) and `outcome` (winners manifest hash).
5.  **Optimization (Final Weights)**: Record `intent` (risk profile) and `outcome` (target weights hash).

## 3. Cryptographic Requirements
- All DataFrames/Series must be hashed using `get_df_hash()`.
- All JSON manifests must be sorted and hashed using `hashlib.sha256()`.
- The `prev_hash` chain must be maintained across separate script executions.
