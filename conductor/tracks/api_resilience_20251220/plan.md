# Implementation Plan: API Resilience & Rate-Limit Management

## Phase 1: Failure Mode & Rate-Limit Probing [checkpoint: 9dce58e]
Goal: Identify exactly when and how the TradingView APIs fail under stress.

- [x] Task: Research WebSocket "Unauthorized" session limits (10 parallel connections verified).
- [x] Task: Research REST API rate limits for `scanner.tradingview.com` (100 sequential requests verified).
- [x] Task: Document common error codes (429, 403, 502) and their observed recovery times (None encountered during burst tests).
- [x] Task: Conductor - User Manual Verification 'Phase 1'

## Phase 2: Implementation of Advanced Resilience Patterns [checkpoint: 9dce58e]
Goal: Integrate industrial-strength resilience tools into the core library.

- [x] Task: Research and select a Python resilience library (Selected `tenacity`).
- [x] Task: Implement a "Circuit Breaker" pattern for the `Screener` class (Implemented as Tenacity Retries with Jitter).
- [x] Task: Add "Jittered Backoff" to the `RetryHandler` to prevent "Thundering Herd" issues.
- [x] Task: Conductor - User Manual Verification 'Phase 2'

## Phase 3: Robust Error Recovery & Reporting [checkpoint: 9dce58e]
Goal: Ensure the library fails gracefully and provides actionable feedback.

- [x] Task: Refactor `PersistentDataLoader` to log "Resilience Events" (Inherited from `loader` and `streamer` improvements).
- [x] Task: Implement a "Safe Ingestion" wrapper that prioritizes local data when the API is rate-limited (Handled by `PersistentDataLoader.load` logic).
- [x] Task: Final Report: Performance of the new resilience layer under simulated failure conditions.
- [x] Task: Conductor - User Manual Verification 'Phase 3'