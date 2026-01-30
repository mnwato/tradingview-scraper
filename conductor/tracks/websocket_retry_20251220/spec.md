# Spec: Robust WebSocket Retry Mechanism

## Overview
The `Streamer` class currently lacks a robust retry mechanism for WebSocket connections. If the connection drops or fails initially, the scraper stops. This track aims to implement an automatic retry mechanism with exponential backoff to improve the library's reliability for long-running data collection tasks.

## Objectives
- Automatically reconnect when a WebSocket connection is lost or fails to open.
- Implement exponential backoff to prevent overwhelming the server during outages.
- Allow configuration of maximum retry attempts and initial/maximum delay.
- Ensure the state (e.g., requested symbols and indicators) is restored upon reconnection.

## Requirements
- **Exponential Backoff:** Start with a small delay (e.g., 1s), doubling it with each failure up to a maximum cap (e.g., 60s).
- **Configurability:** Users should be able to specify `max_retries` and `backoff_factor`.
- **State Persistence:** The system must remember what it was streaming so it can resume after a successful reconnect.
- **Logging:** Clear logging of reconnection attempts and failures.

## Acceptance Criteria
- [ ] A disconnected WebSocket triggers a reconnection attempt.
- [ ] Reconnection attempts follow an exponential backoff pattern.
- [ ] After a successful reconnect, data streaming resumes for the originally requested symbol/indicators.
- [ ] If `max_retries` is reached, a descriptive exception is raised.
- [ ] Unit tests verify the retry logic and backoff timing.
