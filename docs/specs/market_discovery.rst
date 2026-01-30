Trend Presets for US Stocks and ETFs
====================================

US equities (daily discovery)
-----------------------------
- Scanners:
  - ``configs/scanners/tradfi/sp500_trend.yaml`` (S&P 500 foundation)
  - ``configs/scanners/tradfi/nasdaq100_trend.yaml``
  - ``configs/scanners/tradfi/dw30_trend.yaml``
- Base universes: ``configs/base/universes/sp500.yaml``, ``configs/base/universes/nasdaq100.yaml``, ``configs/base/universes/dw30.yaml``
- Current scanners emphasize broad discovery; trend gates are intentionally relaxed/disabled in L4 configs and rely on institutional hygiene for basic filtering.

US ETF discovery (daily)
------------------------
- Scanner: ``configs/scanners/tradfi/bond_trend.yaml`` (bond ETF momentum)
- Base universe: ``configs/base/universes/bond_etfs.yaml``

Legacy presets (archived)
-------------------------
- ``configs/legacy/us_stocks_trend_momentum.yaml``
- ``configs/legacy/us_etf_trend_momentum.yaml``

Notes
-----
- Intended as starting presets; adjust volume floors and thresholds per regime.
- Uses Overview-enriched fields; screener alone won’t provide ADX/Perf/Volatility.
- Exchange is not constrained; base sort by market cap to prioritize larger names.
