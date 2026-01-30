# Deep Audit Plan: Export Side-Effects (2026-01-16)

## 1. Context
We recently identified and fixed an issue where `PersistentDataLoader` inadvertently triggered raw OHLC JSON exports via `Streamer(export_result=True)`, polluting the export directory and causing log noise.
To ensure system-wide hygiene, we must perform a broader audit to detect if this pattern exists elsewhere in the codebase.

## 2. Objective
Identify and remediate any other instances where `Streamer`, `Screener`, or `Overview` classes are instantiated with `export_result=True` in contexts where file generation is unintended or unmanaged.

## 3. Audit Scope
- **Target Classes**: `Streamer`, `Screener`, `Overview`, `Technicals`, `News`.
- **Keywords**: `export_result=True`, `save_json_file`, `save_csv_file`.
- **Directories**: `tradingview_scraper/`, `scripts/`.

## 4. Execution Steps

### 4.1 Static Analysis
1.  **Search**: Grep for `Streamer(`, `Screener(`, `Overview(` to find all instantiations.
2.  **Analyze**: Review constructor arguments for `export_result=True`.
3.  **Context Check**: Determine if the usage implies a need for file export (e.g., CLI tools) or internal data processing (where export should be disabled).

### 4.2 Pipeline Verification
1.  **Check Active Runs**: Monitor the 4 ongoing production pipelines (`binance_spot_rating_*`) to ensure they are completing successfully and not generating new garbage.
2.  **Log Review**: Scan logs for any other "Skipping invalid candidate format" occurrences or file saving logs `[INFO] JSON file saved at:` in unexpected places.

## 5. Remediation Strategy
- If unwarranted exports are found, set `export_result=False`.
- If exports are required but mismanaged, ensure they use a dedicated subdirectory or specific filename pattern that doesn't interfere with downstream consumers.

## 6. Deliverable
- A "Deep Audit Report" summarizing findings and any corrective actions taken.
