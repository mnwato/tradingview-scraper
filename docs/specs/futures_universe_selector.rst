Futures Trend-Following Universe Selector
=========================================

Context
-------
- Build a spec-driven universe selector/screener for commodity futures to support trend-following workflows.
- Leverage existing tradingview-scraper primitives (Screener for futures, Overview for enrichment, export utilities).
- Provide configuration, CLI, and Python API to filter futures by liquidity, volatility, and trend strength.

Scope
-----
- Instruments: exchange-prefixed commodity futures (e.g., ``NYMEX:CL1!``, ``COMEX:GC1!``, ``CBOT:ZC1!``), defaulting to front-month continuous contracts; allow explicit contract lists.
- Markets: use TradingView ``futures`` scanner endpoint; allow narrowing to specific exchanges/venues.
- Filters: volume/liquidity, volatility, and trend strength (momentum/ADX/recommendation) with configurable thresholds.
- Outputs: structured results suitable for downstream portfolio builders; optional JSON/CSV export via existing utils.
- Out of scope: order routing, portfolio sizing, intraday execution logic, multi-leg spreads.

Personas & Usage
----------------
- Quant researcher: runs daily/weekly screen to refresh eligible instruments.
- Strategy engineer: integrates selector in a pipeline and consumes structured output programmatically.
- Ops/debug: dry-run to inspect payloads and filter decisions without hitting external APIs (uses mocks or recorded responses).

Dependencies
------------
- ``tradingview_scraper.symbols.screener.Screener``: futures scanner, supports filters, columns, sorting, export hooks.
- ``tradingview_scraper.symbols.overview.Overview``: optional per-symbol enrichment (e.g., ``Volatility.D``, ``Perf.*``, ``ATR``, ``Recommend.All``) when not returned by the screener.
- ``tradingview_scraper.symbols.utils``: ``save_json_file``, ``save_csv_file``, ``generate_user_agent``.

Functional Requirements
-----------------------
- Universe definition
  - Configurable list of allowed exchanges/contracts; default to continuous front-month commodity futures.
  - Optional include/exclude lists (symbols, exchanges, asset groups like metals/energy/agri).
  - Max results cap; pagination support beyond 50 rows using Screener ranges.
- Data fields & columns
  - Minimum columns: ``symbol``, ``name``, ``close``, ``volume``, ``change``, ``Recommend.All``.
  - Volatility fields: prefer ``Volatility.D``; fallback to ``ATR`` and computed ``atr_pct = ATR/close`` when available.
  - Trend fields: ``Recommend.All``, ``ADX``, ``Perf.W``, ``Perf.1M``, ``Perf.3M``; optionally ``Stoch.K`` if present.
  - Additional optional columns: ``high``, ``low``, ``open`` for context; allow user-specified passthrough columns.
- Filters
  - Liquidity: ``volume >= volume_min``; optional secondary filter on exchange-specific minimums.
  - Volatility: enforce ``Volatility.D`` within ``[vol_min, vol_max]``; if unavailable, use ``atr_pct`` bounds.
  - Trend strength (configurable rule set):
    - ``recommendation``: ``Recommend.All >= rec_min``.
    - ``adx``: ``ADX >= adx_min``.
    - ``momentum``: positive returns across configurable horizons (e.g., ``Perf.1M > 0`` AND ``Perf.3M > 0``).
    - Allow AND/OR composition between trend rules; default AND.
  - Exclusion: drop symbols missing required fields or failing data quality checks (NaN/None).
- Sorting & limiting
  - Sort by configurable key (default ``volume desc``); secondary sort by ``Recommend.All desc``.
  - Apply limit after server response and post-filters; honor pagination to fetch enough rows before trimming.
- Output contract
  - Return dict with ``status``, ``data`` (list of entries), ``filters_applied`` metadata, and ``errors`` list if any.
  - Each entry includes raw fields plus ``passes`` map (per-filter bool) and derived fields (e.g., ``atr_pct``).
  - Support export via existing JSON/CSV utilities when ``export_result`` is true.
- Configuration
  - Accept YAML/JSON config file or Python dict.
  - Keys: ``markets`` (default ["futures"]), ``exchanges``, ``include_symbols``, ``exclude_symbols``, ``base_currencies`` (for forex: filter by base currency), ``allowed_spot_quotes`` (for forex: filter by quote currency), ``columns``, ``volume``, ``volatility``, ``trend`` (direction, timeframe, rules, logic), ``sort_by``, ``sort_order``, ``limit``, ``pagination_size``, ``retries``, ``timeout``, ``export`` block (``enabled``, ``type``).
  - Provide default config embedded in code and show sample config in docs.
- Interfaces
  - Python: ``FuturesUniverseSelector(config: Mapping, screener: Screener = None, overview: Overview = None)`` with ``run() -> Dict``.
  - CLI: ``python -m tradingview_scraper.futures_universe_selector --config path --export json --limit 100 --dry-run``.

Strategies
----------
See :doc:`strategies` for detailed definitions of specific setups like "Confirmed Short" and standard base universes.

Error handling & resilience
---------------------------
- Handle HTTP failures, empty payloads, schema mismatches; surface clear messages and partial results when possible.
  - Retry with backoff for transient network errors; configurable retry count and timeout.
  - Dry-run mode returns the built Screener payloads without remote calls.
- Observability
  - Structured logs for: payloads sent, result counts, filter drop counts, retry attempts, and export paths.
  - Toggle verbosity; quiet mode for pipelines.

Design & Flow
-------------
- Build Screener payload from config
  - Market: ``futures`` endpoint.
  - Filters assembled from liquidity, volatility, and trend requirements using supported operations (``greater``, ``less``, ``in_range``, etc.).
  - Columns combine required, trend, volatility, and user-specified fields; deduplicate.
  - Sort config mapped to Screener ``sortBy``/``sortOrder``.
- Fetch candidates
  - Call ``Screener.screen`` with pagination chunk size (default 50) until reaching requested limit or exhaustion.
  - Aggregate results; short-circuit on hard failures unless ``allow_partial`` is set.
- Enrich (optional)
  - For symbols missing volatility/trend fields, call ``Overview.get_symbol_overview`` in batches (sequential by default; future option for limited concurrency) and compute derived ``atr_pct``.
- Post-filtering
  - Apply client-side filters that were not expressible or missing in the Screener response; record per-filter pass/fail.
  - Drop incomplete rows when required fields are absent.
- Output & export
  - Attach metadata (payloads, counts, filter logic, warnings) and return structured result.
  - Export via existing JSON/CSV helpers when enabled.

Configuration Examples
----------------------
.. code-block:: yaml

   markets: ["futures"]
   exchanges: ["NYMEX", "COMEX", "CBOT", "ICEUS", "CME"]
   include_symbols: []
   exclude_symbols: []
   columns: ["name", "close", "volume", "change", "Recommend.All", "ADX", "Volatility.D", "Perf.W", "Perf.1M", "Perf.3M", "ATR"]
   volume:
     min: 2000
   volatility:
     min: 0.5
     max: 10.0
     fallback_use_atr_pct: true
     atr_pct_max: 0.06
   trend:
     direction: "long"      # options: long, short
     timeframe: "monthly"   # options: daily, weekly, monthly
     logic: "AND"
     rules:
       recommendation:
         enabled: true
         min: 0.3
       adx:
         enabled: true
         min: 20
       momentum:
         enabled: true
         horizons: {Perf.1M: 0, Perf.3M: 0}
   sort_by: volume
   sort_order: desc
   limit: 100
   pagination_size: 50
   retries: 2
    timeout: 10
     export:
       enabled: true
       type: json

Optional Multi-Screen Blocks
----------------------------
- ``trend_screen`` / ``confirm_screen`` / ``execute_screen`` are optional sequential filters (recommendation/ADX/momentum plus osc/volatility) evaluated after base liquidity/volatility/trend checks. They currently support daily/weekly/monthly fields; intraday remains out of scope.
 
Legacy Preset Configurations (configs/legacy/)
----------------------------------------------
- ``configs/legacy/futures_trend_momentum.yaml``: broad commodities, volume >= 5k, ADX >= 20, Rec >= 0.2, momentum across daily/W/1M with 3M confirmation; limit 100 sorted by volume.
- ``configs/legacy/futures_metals_trend_momentum.yaml``: COMEX/NYMEX metals, volume >= 1k, volatility guard (Vol.D <= 8% or ATR/close <= 10%), ADX >= 20, Perf.1M >= 1%, Perf.3M >= 3%.
- ``configs/legacy/index_futures_trend_momentum.yaml``: major equity index futures across CME/CBOT/EUREX/ICEUS/HKEX/SGX, volume >= 10k, ADX >= 15, Perf.1M >= 1%, Perf.3M >= 2%.
- ``configs/legacy/futures_bonds_trend_momentum.yaml``: CBOT/EUREX govies, volume >= 1k, volatility guard (Vol.D <= 5% or ATR/close <= 5%), ADX >= 12, Perf.1M >= 0.5%, Perf.3M >= 1%.

Current L4 scanners (configs/scanners/)
---------------------------------------
- ``configs/scanners/tradfi/metals_trend.yaml`` (futures metals trend).
- ``configs/scanners/tradfi/global_macro.yaml`` (commodity majors trend + recommendation).
- ``configs/scanners/tradfi/bond_trend.yaml`` (bond ETF momentum).
- ``configs/scanners/tradfi/forex_trend.yaml`` (forex trend).

Recent Notes from E2E Validation
--------------------------------

- Futures scanner returns many non-commodity venues by default; include explicit exchanges (e.g., COMEX, NYMEX, CME, ICEUS, CBOT) to avoid unrelated markets dominating results.
- Include only supported futures fields (e.g., ``name``, ``close``, ``volume``, ``change``, ``Recommend.All``, ``ADX``, ``Volatility.D``, ``Perf.1M``, ``Perf.3M``, ``ATR``); unsupported fields (like ``market_cap_basic`` or ``symbol`` in columns) trigger HTTP 400.
- Working CLI examples:
  - Dry-run to inspect payload: ``python -m tradingview_scraper.futures_universe_selector --config /tmp/futures_selector_live.yaml --dry-run --verbose``
  - Live run with exchange and trend filters (example returned gold/silver/platinum trending contracts): ``python -m tradingview_scraper.futures_universe_selector --config /tmp/futures_selector_live.yaml --verbose``
- Output formats: stdout defaults to pretty JSON; pass ``--print-format table`` for a Markdown table of results (dry-run remains JSON to show payloads).
- Trend timeframe support: ``trend.timeframe`` can be ``daily`` (uses ``change`` + ``Perf.W`` as default momentum fields), ``weekly`` (``Perf.W``), or ``monthly`` (``Perf.1M``/``Perf.3M``); adjust ``trend.momentum.horizons`` to override.
- Trend direction support: ``trend.direction`` controls comparisons (``long`` uses >= thresholds; ``short`` uses <= for recommendation and inverted momentum comparisons; ADX remains a magnitude gate).

Planned Multi-Timeframe (3-Screen) Support
------------------------------------------
- Roles: Trend (high TF) to set bias; Confirmation (mid TF) to align continuation; Execution (low TF) to time entries with oscillators/volatility.
- Suggested sets: (A) weekly → daily → 4h/6h, (B) daily → 4h → 1h, (C) 12h → 4h → 1h, (D) monthly → weekly → daily. Futures/FX: A/D; Crypto: B/C; Equities: D.
- Indicator splits: Trend uses Rec/ADX + slower momentum (Perf.1M/3M/6M or Perf.W/1M) with a volatility guard; Confirmation relaxes gates and uses faster momentum/ROC + optional volume surge; Execution uses short momentum (change/Perf.W-equivalent), oscillators (RSI/Stoch), and tight ATR/close.
- Schema sketch (planned): support ``trend_screen``, ``confirm_screen``, ``execute_screen`` blocks with their own ``timeframe``, thresholds, and required columns, plus CLI overrides (e.g., ``--trend-tf weekly --confirm-tf daily --execute-tf 4h``).
- Limitation: current implementation only supports daily/weekly/monthly fields from Screener/Overview; intraday (4h/1h/12h) not available in Screener/Overview (``change|1h``/``Perf.4H`` queries fail). MTF currently constrained to higher timeframes.
 
Testing Strategy
----------------


- Unit tests (mocked HTTP)
  - Payload builder covers filters, columns, sorting, pagination range composition.
  - Trend rule evaluator for AND/OR logic and per-filter pass maps.
  - Enrichment path: when a field is missing in screener response, Overview fallback is invoked.
  - Config validation and defaults (including rejection of invalid markets/exchanges or missing thresholds).
- Integration/smoke (optional, marked slow)
  - Hit ``futures`` scanner with tiny limit (e.g., 3) and assert ``status == success`` and non-empty data.
  - Verify export writes file when enabled.
- Regression fixtures
  - Recorded screener JSON used to ensure stable post-filter behavior without live calls.

Open Items / Risks
------------------
- Field availability: confirm ``Volatility.D``, ``ATR``, and ``Perf.*`` fields are consistently returned by the futures scanner; otherwise rely on Overview enrichment.
- Contract mapping: clarify whether to include multiple expiries per commodity or only front-month continuous tickers.
- Performance: batching Overview calls may be slow; consider simple sequential default with room for future concurrency flag.
- Data freshness: screener/overview data is only as fresh as TradingView provides; no guarantee on intraday completeness.
- Authentication: if endpoints require cookies/JWT in some environments, allow passing headers via config.

Implementation Notes (spec-driven checkpoints)
----------------------------------------------
- Step 1: config schema and validation utilities with defaults.
- Step 2: payload builder for Screener (futures), including pagination setup.
- Step 3: post-filter engine (trend, volatility, liquidity) with per-filter annotations.
- Step 4: optional Overview enrichment and derived metrics (``atr_pct``).
- Step 5: CLI entrypoint wiring config -> selector -> export; add logging and dry-run.
- Step 6: tests (unit + optional smoke) and documentation update hooks.
