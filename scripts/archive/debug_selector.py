import logging

from tradingview_scraper.futures_universe_selector import FuturesUniverseSelector, load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debug_selector")


def debug_selection(config_path: str):
    cfg = load_config(config_path)
    # Set limit higher to see more candidates
    cfg.limit = 200
    cfg.base_universe_limit = 200

    selector = FuturesUniverseSelector(cfg)

    # We want to manually trace the pipeline
    columns = selector._build_columns()
    filters = selector._build_filters(cfg.markets[0])

    logger.info(f"Filters sent to TV: {filters}")

    # 1. Screen
    raw_data, errors = selector._screen_market(cfg.markets[0], filters, columns, exchange=cfg.exchanges[0])
    logger.info(f"Raw candidates from TV: {len(raw_data)}")

    if errors:
        logger.warning(f"Screen errors: {errors}")

    # 2. Basic Filters
    rows = selector._apply_basic_filters(raw_data)
    logger.info(f"After basic filters (stables, type, etc.): {len(rows)}")

    # 3. Market Cap Guard
    rows = selector._apply_market_cap_filter(rows)
    logger.info(f"After Market Cap guard: {len(rows)}")

    # 4. Volatility
    vol_rows = [r for r in rows if selector._evaluate_volatility(r)[0]]
    logger.info(f"After Volatility filter: {len(vol_rows)}")

    # 5. Liquidity (Floor)
    liq_rows = [r for r in vol_rows if selector._evaluate_liquidity(r)]
    logger.info(f"After Liquidity filter: {len(liq_rows)}")

    # 6. Aggregation
    if cfg.dedupe_by_symbol:
        agg_rows = selector._aggregate_by_base(liq_rows)
        logger.info(f"After Aggregation (Dedupe by base): {len(agg_rows)}")
    else:
        agg_rows = liq_rows

    # Final Selected
    logger.info(f"Final Selection Count: {len(agg_rows)}")

    # Print some examples
    if agg_rows:
        print("\nTop 10 Selected Symbols:")
        for r in agg_rows[:10]:
            print(f"  {r['symbol']:<20} | VT: ${r.get('Value.Traded', 0):,.0f} | MC: {r.get('market_cap_external', 'N/A')}")

    # Check why others failed
    if len(raw_data) > len(agg_rows):
        print("\nExamples of filtered out symbols:")
        seen = {r["symbol"] for r in agg_rows}
        count = 0
        for r in raw_data:
            if r["symbol"] not in seen:
                print(f"  {r['symbol']:<20} | VT: ${r.get('Value.Traded', 0):,.0f} | MC: {r.get('market_cap_calc', 'N/A')}")
                # check filters
                _, atr_pct = selector._evaluate_volatility(r)
                print(f"    Vol.D: {r.get('Volatility.D')}, ATR/P: {atr_pct}")
                count += 1
                if count >= 5:
                    break


if __name__ == "__main__":
    debug_selection("configs/crypto_cex_base_top50_binance_dated.yaml")
