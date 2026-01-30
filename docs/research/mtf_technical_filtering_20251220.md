# Research Report: Multi-Timeframe (MTF) Technical Filtering for Trend Candidates

## 1. Executive Summary
This research explores the use of multi-timeframe (MTF) technical indicator alignment to filter initial trend signals into high-conviction opportunities. By analyzing indicators across 15m, 1h, and 1d timeframes, we can identify "Fractal Alignment" (trend synchronization) and avoid "Mean Reversion Traps."

## 2. Methodology & MTF Set
Candidates from primary trend scanners (e.g., Binance Top 50) are passed through a secondary MTF filter:
*   **Timeframes:** 15m (Entry/Local), 1h (Confirmation/Intermediate), 1d (Macro/Structural).
*   **Indicators:** RSI, EMA50, EMA200, ADX.

## 3. High-Conviction Filtering Rules (Proposed)

### Long Strategy (Bullish Alignment)
*   **Score 3/3:** Price > EMA50 on 15m, 1h, AND 1d.
*   **Macro Guard:** RSI(1d) > 50 (Not in a macro downtrend).
*   **Local Entry:** RSI(15m) < 70 (Not extremely overextended).

### Short Strategy (Bearish Alignment)
*   **Score 3/3:** Price < EMA50 on 15m, 1h, AND 1d.
*   **Macro Guard:** RSI(1d) < 50 (Macro weakness).
*   **Local Entry:** RSI(15m) > 30 (Not in a climax sell-off).

## 4. Case Study: BINANCE:PAXGUSDT
*   **Initial Scan:** Flagged as LONG candidate.
*   **MTF Analysis:**
    *   **1d_RSI:** 73.86 (Macro Bullish)
    *   **1h_RSI:** 48.69 (Intermediate Neutral)
    *   **15m_RSI:** 30.45 (Local Oversold / Pullback)
*   **Verdict:** This represents a "Dip in an Uptrend" opportunity. The macro is strong (73.86), but the local timeframe is oversold (30.45), indicating a high-probability entry for trend continuation.

## 5. Feasibility & Benchmarking
*   **Retrieval Speed:** Sequential fetching of 3 timeframes for a single symbol takes ~3.5 seconds (including safety sleeps). 
*   **Scaling:** For a Top 50 universe, a full MTF refresh takes ~175 seconds.
*   **Recommendation:** Perform MTF filtering **only** on symbols that pass the initial wide-universe trend scan to conserve API calls.
