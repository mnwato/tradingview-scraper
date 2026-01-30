CFD Screening Notes
===================

- Screener field limits: ``market='cfd'`` returns only ``name, close, change, change_abs, volume, Recommend.All``; requesting ``market_cap_calc`` errors. Rich indicators (Perf.W/1M/3M/6M, ADX, Volatility.D/W/M, ATR, RSI, Stoch.K, Value.Traded) require per-symbol Overview calls.
- Exchange filtering is required to avoid crypto-cap aggregates; OANDA symbols work (e.g., XAUUSD, US30USD, DE30EUR, AU200AUD, commodities).
- Base universe suggestion: filter ``exchange == OANDA``, sort by volume desc, limit 50–100.
- Multi-exchange screener option now OANDA-only (other CFD venues return negligible rows): ``configs/legacy/cfd_trend_multi.yaml`` with Rec >= 0.1, change >= 0, volume >= 1,000, sort by volume.
- Trend-following (OANDA screener-only prototype): see ``configs/legacy/cfd_trend_momentum.yaml``
  - Columns: ``name, close, volume, change, change_abs, Recommend.All``
  - Filters: Rec >= 0.2, change >= 0, volume >= 5,000 (adjust per broker), sort by volume desc.
  - Note: Without Overview, no ADX/Perf/Volatility gates are available; use Overview enrichment for production-quality trend filters.

CLI example
-----------
.. code-block:: bash

   # Legacy preset (archived)
   python -m tradingview_scraper.cfd_universe_selector --config configs/legacy/cfd_trend_momentum.yaml --verbose

   # Base preset (layered pipelines can build on this)
   # configs/presets/base_cfd.yaml

Recommendations for richer CFD screens
--------------------------------------
- Add Overview enrichment in configs to fetch: ``Perf.W``, ``Perf.1M/3M``, ``ADX``, ``Volatility.D/W/M``, ``ATR``, optionally ``RSI``/``Stoch.K``.
- Set liquidity via ``volume`` or ``Value.Traded`` if Overview provides it for the symbols.
- Use trend gates similar to futures/FX presets (e.g., Rec >= 0.1–0.2, ADX >= 20, Perf.W >= 0, Perf.1M >= 1–2%, Vol.D <= 6–8%).
