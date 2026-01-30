Crypto CEX Screening Presets
============================

Overview
--------
- **Production Strategy (2026-01-09)**: BINANCE-only focus for the institutional crypto sleeve. This provides highest liquidity and cleaner signals without multi-exchange deduplication complexity.
- Base universes are split by instrument type: spot, perps (.P suffix), and dated futures (expiry-coded).
- Spot presets enforce a quote whitelist (USDT/USD/USDC/FDUSD/BUSD) and exclude perps and dated futures; perps presets require ``include_perps_only: true``; dated presets require expiry-coded symbols.
- Ordering: fetch with ``prefilter_limit`` (500) sorted by ``market_cap_calc``, then final sort ``Value.Traded`` and cap at ``limit`` (50).
- Columns: ``name, close, volume, Value.Traded, market_cap_calc, change, Recommend.All, ADX, Volatility.D/W/M, Perf.W/1M/3M, ATR``.
- Liquidity guard: ``Value.Traded >= $10M`` (institutional floor).

Production Exchange Strategy
----------------------------
- **BINANCE-Only (Recommended)**: The ``crypto_production`` profile uses BINANCE as the sole exchange for production allocations.
- **Rationale**: 
    - Highest global liquidity concentration
    - Cleanest order book depth for institutional execution
    - Eliminates multi-exchange deduplication complexity
    - Reduces cross-exchange arbitrage noise in signal generation
- **Global Aggregation (Research Only)**: Multi-exchange configs (``global_perp_top50.yaml``) remain available for research but are not used in production flows.

Current layered scanners (configs/scanners/crypto/)
---------------------------------------------------
**Production Set (BINANCE-only)**:

- ``configs/scanners/crypto/binance_trend.yaml``: Binance spot trend discovery (L4) built on ``binance_spot_top50`` with ADX >= 10 and momentum gates (Perf.W >= 0, Perf.1M >= 0). No 3M/6M anchors.
- ``configs/scanners/crypto/binance_perp_trend.yaml``: Binance perp trend discovery (L4) built on ``binance_perp_top50`` with ADX >= 10 and momentum gates (Perf.W >= 0, Perf.1M >= 0).
- ``configs/scanners/crypto/binance_perp_short.yaml``: Binance perp inverse trend discovery (L4) for capture during bearish/turbulent regimes.
- ``configs/scanners/crypto/binance_mtf_trend.yaml`` (**PLANNED**): Binance MTF trend discovery with daily + weekly confirmation screens.

**Research/Deprecated**:

- ``configs/scanners/crypto/vol_breakout.yaml``: Volatility breakout discovery (L4) - to be scoped to BINANCE-only.
- ``configs/scanners/crypto/global_mtf_trend.yaml``: Multi-exchange MTF trend discovery - archived for research use only.

These scanners are composed from layered presets under ``configs/base/`` and orchestrated via manifest pipelines.

Regime-Adaptive Exposure Policy
-------------------------------
- **Quiet/Normal Regimes**: Maximize capture of high-alpha momentum. Primary allocation to ``binance_perp_trend`` and ``global_mtf_trend``.
- **Turbulent/Bearish Regimes**: Enable ``binance_perp_short`` to capture alpha from deleveraging events. Tighten entropy thresholds to prioritize "Flight to Quality" (e.g., Gold-pegged tokens).

Legacy presets (paths under configs/legacy/)
--------------------------------------------
Spot trend (daily/weekly)
- ``crypto_cex_trend_momentum_spot_daily_long.yaml`` / ``..._short.yaml`` plus per-exchange spot trend variants: ``crypto_cex_trend_<exchange>_spot_daily_long.yaml`` / ``..._short.yaml`` (BINANCE/OKX/BYBIT/BITGET)
  - Liquidity: Value.Traded >= 50M (20M for per-exchange), Vol.D <= 8–15% or ATR/close <= 12%; quote whitelist USDT/USD/USDC/FDUSD/BUSD; exclude perps and dated futures.
  - Long: Rec>=0, ADX>=10, momentum change>=-0.2, Perf.W>=-0.5, Perf.1M>=0, Perf.3M>=0.5. Short: Rec<=-0.2, ADX>=10, momentum inverted.
  - Sort: market_cap_calc then Value.Traded; limit 100 (spot) or 50 (per-exchange).
- ``crypto_cex_trend_momentum_spot_weekly_long.yaml`` / ``..._short.yaml``
  - Same liquidity/vol caps; weekly horizons (long: Perf.W>=0, Perf.1M>=0.5, Perf.3M>=1; shorts inverted).

Perps trend (daily)
- ``crypto_cex_trend_momentum_perp_daily_long.yaml`` / ``..._short.yaml`` (multi-exchange)
- Per-exchange: ``crypto_cex_trend_<exchange>_perp_daily_long.yaml`` / ``..._short.yaml``
  - ``include_perps_only: true``; Liquidity Value.Traded >= 50M (20M per-exchange); Vol.D <= 8–15% or ATR/close <= 12%.
  - Sort by Value.Traded; majors ensured via .P symbols in per-exchange variants.

Dated futures trend (daily)
- ``crypto_cex_trend_momentum_dated_daily_long.yaml`` / ``..._short.yaml`` (multi-exchange)
- Per-exchange: ``crypto_cex_trend_<exchange>_dated_daily_long.yaml`` / ``..._short.yaml``
  - ``include_dated_futures_only: true``; quote whitelist; Liquidity Value.Traded >= 50M (10M per-exchange); Vol caps as above; daily momentum as spot.

Legacy/other presets
- Cross-sectional, mean-reversion, and TS momentum presets remain as-is (xs_momentum/mean_reversion, ts_momentum/mean_reversion, MTF variants). Volume/vol thresholds there may differ; adjust per strategy.

Base universes (legacy paths under configs/legacy/)
---------------------------------------------------
- Spot: ``crypto_cex_base_top50.yaml`` – excludes perps and dated futures, quote whitelist USDT/USD/USDC/FDUSD/BUSD, Value.Traded >= 1.5M, volume >= 2M, Vol.D <= 20% or ATR/close <= 15%, dedupe by base, limit 50, sorted by market_cap_calc then Value.Traded. Majors ensured.
- Perps: ``crypto_cex_base_top50_perp.yaml`` – `include_perps_only: true`, excludes dated, Value.Traded >= 7.5M, volume >= 2M, Vol.D <= 20% or ATR/close <= 15%, dedupe by base, prefer perps, limit 50, sorted by Value.Traded; majors ensured via `.P` symbols.
- Dated futures: ``crypto_cex_base_top50_dated.yaml`` – `include_dated_futures_only: true`, excludes perps, quote whitelist, Value.Traded >= 5M, Vol.D <= 25% or ATR/close <= 20%, dedupe by base, limit 50, sorted by Value.Traded (currently yields 0 under these floors).
- Per-exchange splits for spot/perps/dated: ``crypto_cex_base_top50_<exchange>.yaml``, ``..._<exchange>_perp.yaml``, ``..._<exchange>_dated.yaml`` (BINANCE/OKX/BYBIT/BITGET). Spot floors per exchange: BINANCE/OKX/BYBIT Value.Traded >= 1.5M; BITGET >= 1.0M (volume >= 2M, same vol caps as multi-spot). Perps use Value.Traded >= 7.5M (volume >= 2M). Dated use Value.Traded >= 5M.
- **Binance Top 50 (Active L1 Bases)**:
    - **Spot**: ``configs/base/universes/binance_spot_top50.yaml``. Logic: Fetch Top 200 by Market Cap (pre-filter), then select Top 50 by Daily Volume (Value.Traded). Strict quote whitelist (USDT/USDC/USD/FDUSD/BUSD).
    - **Perps**: ``configs/base/universes/binance_perp_top50.yaml``. Logic: Same two-stage funnel (Top 200 Mcap -> Top 50 Vol), restricted to perp contracts.
- **Global Perp Top 50 (Multi-Exchange)**: ``configs/base/universes/global_perp_top50.yaml``. Logic: Exchanges BINANCE/OKX/BYBIT/BITGET, prefilter 200 by Market Cap, then Top 50 by Value.Traded.
- Merged views: ``outputs/crypto_trend_runs/merged_base_universe_spot.json`` and ``..._perp.json`` aggregate per-exchange spot/perp bases into normalized symbols with their tradable exchange symbols; dated is empty at current floors.

Usage
-----
Run any preset via CLI (example):

.. code-block:: bash

   # Current layered scanner
   python -m tradingview_scraper.futures_universe_selector --config configs/scanners/crypto/binance_trend.yaml --verbose

   # Legacy preset (archived)
   python -m tradingview_scraper.futures_universe_selector --config configs/legacy/crypto_cex_trend_momentum.yaml --verbose

Indicator Field Categories (crypto overview availability)
-------------------------------------------------------
- Trend/strength: ``Recommend.All``, ``ADX``
- Momentum/returns: ``change``, ``Perf.W``, ``Perf.1M``, ``Perf.3M``, ``Perf.6M``
- Volatility: ``Volatility.D``, ``Volatility.W``, ``Volatility.M``, ``ATR``
- Oscillators: ``RSI``, ``Stoch.K``
- Liquidity/size: ``volume``, ``Value.Traded``, ``market_cap_calc`` (and basic/diluted variants)

Selection & Gating Strategy (2026-01-08 Uplift)
-----------------------------------------------
- Discovery uses a two-stage funnel: Top 500 Mcap -> Top 50 Volume (Value.Traded).
- **Short-Cycle Momentum**: Scanners prioritize Daily (change), Weekly (Perf.W), and Monthly (Perf.1M) velocity. Lookbacks > 1 month (Perf.3M/6M) are excluded to ensure early entry into rapid crypto rotations.
- Trend scanners (L4) use relaxed ADX floors (10 for Spot/Perps) and neutral-to-positive Recommendation (>= 0).
- **Natural Selection (Noise Floor)**: Log-MPS v3.2 is tuned for maximum breadth (top_n=25) with relaxed entropy (0.999). It acts as a statistical noise floor rather than an alpha filter.
- Institutional diversity floor (min 5 assets) is enforced via lowered clustering distance thresholds and disabling dynamic redundancy pruning for crypto sleeves.

Gold Peg Fidelity & Tracking Quality
-------------------------------------
- **Policy**: Assets pegged to physical commodities (e.g. Gold) must demonstrate high-fidelity tracking.
- **Audit Findings**: ``OKX:XAUTUSDT.P`` maintains high correlation (>0.98) with direct gold (``XAUUSDT.P``). ``BINANCE:PAXGUSDT.P`` has detached (correlation < 0.45) and provides misleading "Noise Alpha."
- **Institutional Standard**: Blacklist ``BINANCE:PAXGUSDT.P``. Prioritize ``XAUT`` or direct ``XAU`` perps for safe-haven anchors.

High Entropy in Crypto Markets
------------------------------
- Entropy (specifically Permutation Entropy) measures the complexity and statistical "unpredictability" of a return series.
- A score of 1.0 represents a pure random walk (white noise). Institutional TradFi assets typically range from 0.85 to 0.95.
- Crypto assets frequently exhibit high entropy (0.98–0.99) due to:
    - **Microstructure Noise**: Fragmented liquidity and high-frequency retail flow.
    - **Efficiency Paradox**: Extremely rapid pricing of sentiment-driven information.
    - **Speculative Volatility**: Leverage liquidations causing erratic jumps that break traditional trend models.
- **Policy**: We accept higher entropy baseline (up to 0.995) for crypto to avoid excessive vetoes of genuine high-alpha momentum, while still rejecting pure noise components.

Screener vs. Overview field availability
----------------------------------------
- Screener (crypto) fields are limited: ``name``, ``symbol``, ``close``, ``change``, ``change_abs``, ``volume``, ``market_cap_calc``, ``Recommend.All``. Use these for server-side filters.
- Overview provides richer fields used in presets: ``Perf.W``, ``Perf.1M``, ``Perf.3M``, ``Perf.6M``, ``ADX``, ``Volatility.*``, ``ATR``, ``RSI``, ``Stoch.K``, and liquidity proxies like ``Value.Traded``. (Fundamental fields may be present but are often not meaningful for crypto.)

Multi-Timeframe (MTF) crypto notes
-----------------------------------
- Intraday fields (e.g., ``change|1h``, ``Perf.4H``) are not available via Screener/Overview; MTF must use daily/weekly/monthly fields.
- Current global MTF long (``configs/scanners/crypto/global_mtf_trend.yaml``): daily trend gate (Rec>=0.1, ADX>=20, Perf.W/Perf.1M/Perf.3M > {0,0.5,1.0}), plus a weekly confirmation screen (Rec|1W>=0.1, ADX|1W>=20, Perf.1M>0). Monthly screen removed for execution relevance (4h–15m downstream horizon).
- Legacy sample configs remain for reference:
  - Spot long: ``configs/legacy/crypto_cex_mtf_monthly_weekly_daily.yaml``, ``configs/legacy/crypto_cex_mtf_weekly_daily_daily.yaml``.
  - Spot short: ``configs/legacy/crypto_cex_mtf_monthly_weekly_daily_short.yaml``, ``configs/legacy/crypto_cex_mtf_weekly_daily_daily_short.yaml``.
  - Perps short: ``configs/legacy/crypto_cex_mtf_weekly_daily_daily_perps_short.yaml``.
  - Mixed trend/MR: ``configs/legacy/crypto_cex_mtf_trend_mr_trend.yaml`` (monthly trend → weekly MR → daily trend) and ``configs/legacy/crypto_cex_mtf_mr_trend_trend.yaml`` (monthly MR → weekly trend → daily trend).
- If longs return empty under bearish regimes, relax momentum/Rec/ADX gates or lower Value.Traded floors (e.g., spot/perps 10–20M; dated 5–10M).


Notes
-----
- Recent runs (prefilter 400) show spot longs empty and dated futures empty under current thresholds; shorts return sparse sets, perps shorts return healthy lists. To surface longs or dated: lower Value.Traded floors (e.g., spot/perps to 10–20M, dated to 5–10M) and relax long momentum/Rec/ADX gates.
- Majors can still be filtered out under bearish regimes if Perf.W/1M/3M thresholds stay positive; relax momentum gates or add ``ensure_symbols`` per exchange to guarantee inclusion.
- Dated futures are explicitly separated to avoid contaminating spot/perp runs; adjust ``value_traded_min`` downward if dated lists come back empty.
- Quote whitelist and dated/perp flags are enforced in post-filtering; widen quotes or disable exclusions if you need broader coverage.

Production Hardening Checklist (2026-01-09)
-------------------------------------------
**Scanner Consolidation**:

- [PLANNED] Archive ``global_mtf_trend.yaml`` to ``configs/archive/``
- [PLANNED] Create ``binance_mtf_trend.yaml`` with daily + weekly confirmation
- [PLANNED] Scope ``vol_breakout.yaml`` to BINANCE-only
- [PLANNED] Update ``scripts/run_crypto_scans.sh`` or deprecate

**Predictability Gates**:

- [PLANNED] Create ``configs/base/hygiene/institutional_crypto.yaml`` with entropy/Hurst filters
- [PLANNED] Add ``predictability`` block to scanner YAML schema
- [PLANNED] Implement post-scan filtering in ``FuturesUniverseSelector``

**Backtesting Fidelity**:

- [PLANNED] Increase ``backtest_slippage`` to 0.001 for crypto
- [PLANNED] Increase ``backtest_commission`` to 0.0004 for CEX fees
- [PLANNED] Document ``feat_dynamic_selection: false`` rationale

**Meta-Portfolio Integration**:

- [PLANNED] Verify crypto sleeve in ``flow-meta-production``
- [PLANNED] Add calendar alignment guardrails (no weekend padding)
- [PLANNED] Add sleeve weight bounds (5% min, 50% max)
