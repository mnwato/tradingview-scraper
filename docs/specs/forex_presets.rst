Forex Trend Preset
==================

Overview
--------
- Base universe: FX, exchanges from discovery (high prevalence): FX_IDC, THINKMARKETS, BLACKBULL, ICMARKETS, ACTIVTRADES, FUSIONMARKETS, OANDA, TRADENATIONSB, TRADENATION, FXOPEN, FX, SKILLING, FPMARKETS, VELOCITY, CAPITALCOM, VANTAGE, PEPPERSTONE.
- Columns (overview-enriched): ``name, close, volume, change, Recommend.All, ADX, Volatility.D, Perf.W, Perf.1M, Perf.3M, ATR``.
- Volatility gate: ``Volatility.D <= 6%`` or ``ATR/close <= 6%`` fallback.
- Liquidity: volume >= 1,000,000,000 (tick-volume proxy; adjust as needed).
- Sorting: volume desc (base and final).
- Currency filtering: ``base_currencies`` and ``allowed_spot_quotes`` restrict pairs to major/minor crosses (G8: USD, EUR, JPY, GBP, CHF, CAD, AUD, NZD), excluding exotics.

Current Scanner (configs/scanners/tradfi/forex_trend.yaml)
---------------------------------------------------------
- L4 scanner composed from:
  - L2 template: ``configs/base/templates/forex_base.yaml`` (inherits institutional hygiene).
  - L1 hygiene: ``configs/base/hygiene/institutional.yaml`` (ADX + Rec floors and column set).
- Trend gates: ADX >= 20, momentum ``Perf.W >= 0.5`` and ``Perf.1M >= 1.0``.
- Limit: 50; export symbol ``global_forex_trend``.

Legacy Preset (configs/legacy/forex_trend_momentum.yaml)
--------------------------------------------------------
- Trend (daily, long): Rec >= 0.2, ADX >= 15, change >= 0, Perf.W >= 0.0%, Perf.1M >= 0.5%, Perf.3M >= 1.5%.
- Volume floor: 1,000,000,000; exchanges limited to FX_IDC/THINKMARKETS/OANDA/VANTAGE/FUSIONMARKETS.
- No export by default.
- Latest run (bearish regime): 4 candidates (THINKMARKETS:CHFJPY, EURJPY, EURNOK, USDBRL).

Usage
-----
.. code-block:: bash

   # Current scanner (layered presets)
   python -m tradingview_scraper.futures_universe_selector --config configs/scanners/tradfi/forex_trend.yaml --verbose

   # Legacy preset (archived)
   python -m tradingview_scraper.futures_universe_selector --config configs/legacy/forex_trend_momentum.yaml --verbose

Notes
-----
- Screener for FX exposes only a few fields (name, close, change/change_abs, volume, Recommend.All); richer fields come from per-symbol Overview.
- Use ``base_currencies`` and ``allowed_spot_quotes`` filters to target major/minor pairs only, excluding exotic pairs (e.g., USD/TRY, EUR/PLN).
- For looser regimes, reduce Rec/ADX or momentum thresholds if the screen returns no candidates.
