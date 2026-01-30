# Specification: Robust Async Screener Parity

## 1. Overview
The goal of this track is to upgrade `AsyncScreener` to match the reliability and feature set of the synchronous `Screener` class. This includes supporting all markets, implementing robust retry logic, and adding support for large-scale paginated requests.

## 2. Requirements

### A. Market & Column Parity
- `AsyncScreener` must support all markets listed in the synchronous `Screener.SUPPORTED_MARKETS`.
- Default columns for `crypto`, `forex`, and stocks must be consistent between both implementations.

### B. Resilience & Retries
- Implement asynchronous retry logic using `tenacity`.
- Retry on `aiohttp.ClientError`, HTTP 429 (Rate Limit), and HTTP 5xx errors.
- Use exponential backoff with jitter.

### C. Data Export
- Add support for exporting results to JSON and CSV files using `save_json_file` and `save_csv_file` utilities.

### D. Advanced Async Features
- **Auto-Pagination**: If `limit` > 50, the screener should automatically perform multiple requests in chunks of 50 and aggregate results.
- **Concurrency Guard**: Use an `asyncio.Semaphore` to limit the number of concurrent outgoing requests in `screen_many` to avoid triggering API-level protection.

## 3. Success Criteria
- `AsyncScreener` passes all tests in `tests/test_async_screener.py` (which will be expanded).
- Large scans (e.g., limit=150) successfully return the full dataset.
- Parallel scans of multiple configurations complete reliably without 429 errors.
