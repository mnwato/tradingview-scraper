from __future__ import annotations

import logging
from typing import Any, Dict, Optional, cast

import pandas as pd

from tradingview_scraper.execution.metadata import ExecutionMetadataCatalog
from tradingview_scraper.portfolio_engines.nautilus_loader import NautilusDataConverter
from tradingview_scraper.portfolio_engines.nautilus_provider import NautilusInstrumentProvider
from tradingview_scraper.portfolio_engines.nautilus_strategy import INITIAL_CASH_VAL, NautilusRebalanceStrategy
from tradingview_scraper.utils.metrics import calculate_performance_metrics

# Define types for linter
BacktestEngine: Any = cast(Any, None)
BacktestEngineConfig: Any = cast(Any, None)
Venue: Any = cast(Any, None)

try:
    from nautilus_trader.backtest.engine import BacktestEngine as _BacktestEngine
    from nautilus_trader.backtest.engine import BacktestEngineConfig as _BacktestEngineConfig
    from nautilus_trader.backtest.models.fill import FillModel
    from nautilus_trader.model import BookOrder
    from nautilus_trader.model.book import OrderBook
    from nautilus_trader.model.enums import BookType, OrderSide
    from nautilus_trader.model.identifiers import Venue as _Venue
    from nautilus_trader.model.objects import Price, Quantity

    BacktestEngine = _BacktestEngine
    BacktestEngineConfig = _BacktestEngineConfig
    Venue = _Venue

    HAS_NAUTILUS = True

    class ParityFillModel(FillModel):
        """
        Custom FillModel that applies a fixed percentage slippage to match
        the research simulator's friction assumptions.
        """

        def __init__(self, total_rate: float):
            super().__init__()
            self.total_rate = total_rate

        def get_orderbook_for_fill_simulation(
            self,
            instrument: Any,
            order: Any,
            best_bid: Any,
            best_ask: Any,
        ) -> Any:
            UNLIMITED = 1_000_000

            # Apply fixed percentage slippage
            shifted_bid = best_bid.as_double() * (1.0 - self.total_rate)
            shifted_ask = best_ask.as_double() * (1.0 + self.total_rate)

            book = OrderBook(
                instrument_id=instrument.id,
                book_type=BookType.L2_MBP,
            )

            bid_order = BookOrder(
                side=OrderSide.BUY,
                price=Price(shifted_bid, instrument.price_precision),
                size=Quantity(UNLIMITED, instrument.size_precision),
                order_id=1,
            )
            ask_order = BookOrder(
                side=OrderSide.SELL,
                price=Price(shifted_ask, instrument.price_precision),
                size=Quantity(UNLIMITED, instrument.size_precision),
                order_id=2,
            )

            book.add(bid_order, 0, 0)
            book.add(ask_order, 0, 0)

            return book

except ImportError:
    HAS_NAUTILUS = False

logger = logging.getLogger(__name__)


def run_nautilus_backtest(
    *,
    returns: pd.DataFrame,
    weights_df: pd.DataFrame,
    initial_holdings: Optional[pd.Series],
    settings: Any,
) -> Dict[str, Any]:
    """
    Unified NautilusTrader adapter.
    Bridges the Lakehouse data to an event-driven backtest engine.
    """
    if not HAS_NAUTILUS or BacktestEngine is None:
        logger.warning("NautilusTrader not installed, falling back to ReturnsSimulator")
        from tradingview_scraper.portfolio_engines.backtest_simulators import ReturnsSimulator

        return ReturnsSimulator().simulate(returns, weights_df, initial_holdings)

    # 1. Setup Components
    catalog = ExecutionMetadataCatalog()
    provider = NautilusInstrumentProvider(catalog=catalog)
    loader = NautilusDataConverter()

    # 2. Initialize Engine
    config = BacktestEngineConfig(trader_id="BACKTESTER-01")
    engine = BacktestEngine(config=config)

    # 3. Configure a single unified venue for backtest parity
    from nautilus_trader.model.currencies import USD
    from nautilus_trader.model.enums import AccountType, OmsType
    from nautilus_trader.model.objects import Money

    unified_venue_name = "BACKTEST"
    unified_venue = Venue(unified_venue_name)
    INITIAL_CASH = INITIAL_CASH_VAL

    # Match research friction using ParityFillModel
    total_rate = settings.backtest_slippage + settings.backtest_commission
    fill_model = ParityFillModel(total_rate=total_rate)

    engine.add_venue(
        venue=unified_venue,
        oms_type=OmsType.NETTING,
        account_type=AccountType.CASH,
        starting_balances=[Money(int(INITIAL_CASH), USD)],
        fill_model=fill_model,
    )

    # 4. Add Instruments (Mapped to unified venue)
    added_instrument_ids = set()
    instruments_map = {}
    for symbol in returns.columns:
        # Force instrument to the unified venue for simple backtesting
        symbol_only = str(symbol).split(":")[-1]
        unified_symbol_key = f"{unified_venue_name}:{symbol_only}"

        inst = provider.get_instrument_for_symbol(unified_symbol_key)
        if inst:
            engine.add_instrument(inst)
            added_instrument_ids.add(str(inst.id))
            instruments_map[str(symbol)] = inst
        else:
            print(f"ERROR: Could not create instrument for {symbol}")

    # 5. Add Data
    # CR-830: Pre-Start Priming to align T0 returns.
    # We must feed a T-1 bar (flat) so Nautilus trades at T-1 Close to capture T0 return.
    t0 = returns.index[0]
    t_minus_1 = t0 - pd.Timedelta(days=1)
    dummy_row = pd.DataFrame(0.0, index=[t_minus_1], columns=returns.columns)
    returns_primed = pd.concat([dummy_row, returns])

    bars_ordered_dict = loader.to_nautilus_bars(returns_primed, instrument_map=instruments_map)
    all_bars = []
    for symbol_str, bars in bars_ordered_dict.items():
        if not bars:
            continue
        bar_inst_id = str(bars[0].bar_type.instrument_id)
        if bar_inst_id in added_instrument_ids:
            all_bars.extend(bars)

    if all_bars:
        all_bars.sort(key=lambda x: x.ts_event)
        engine.add_data(all_bars)

    # 6. Add Strategy
    # Target weights need to include the primed day?
    # No, the strategy will look up weights by timestamp.
    # If a bar arrives at T-1, strategy might try to rebalance.
    # We want it to establish initial position at T-1.
    # So we should prepend the T0 weights to T-1 in target_weights.

    target_weights_raw = pd.DataFrame(index=returns.index)
    for symbol in returns.columns:
        symbol_only = str(symbol).split(":")[-1]
        unified_key = f"{symbol_only}.{unified_venue_name}"

        mask = weights_df["Symbol"] == symbol
        w_row = weights_df[mask]
        if not w_row.empty:
            try:
                # Use Net_Weight if available to capture direction (Long/Short)
                # This handles the "Physical Flattening" requirement
                if "Net_Weight" in w_row.columns:
                    val = w_row["Net_Weight"].values[0]
                else:
                    val = w_row["Weight"].values[0]
            except Exception:
                # Fallback to iloc access
                if "Net_Weight" in w_row.columns:
                    val = w_row["Net_Weight"].iloc[0]
                else:
                    val = w_row["Weight"].iloc[0]
            target_weights_raw[unified_key] = float(val)
        else:
            target_weights_raw[unified_key] = 0.0

    # Prepend T-1 weights (copy of T0) to ensure initial setup happens at T-1
    t0_weights = target_weights_raw.iloc[0:1].copy()
    t0_weights.index = [t_minus_1]
    target_weights = pd.concat([t0_weights, target_weights_raw])

    strategy = NautilusRebalanceStrategy(target_weights=target_weights, catalog=catalog)
    engine.add_strategy(strategy)

    # 7. Run
    engine.run()

    # MITIGATION: Log True Equity to dispel CashAccount confusion
    final_equity = strategy._get_nav()
    final_cash = 0.0
    try:
        acct = engine.portfolio.account(unified_venue)
        # Try balance_total(USD) first, fallback to iteration if needed
        try:
            final_cash = acct.balance_total(USD).as_double()
        except Exception:
            for bal in acct.balances():
                if hasattr(bal, "total"):
                    final_cash = float(bal.total)
                    break
    except Exception:
        pass  # Fallback safe

    invested_value = final_equity - final_cash
    pnl_pct = (final_equity - INITIAL_CASH) / INITIAL_CASH

    logger.info(
        f"\n=== NAUTILUS AUDIT: {strategy.__class__.__name__} ===\n"
        f"Initial Capital: ${INITIAL_CASH:,.2f}\n"
        f"Final Free Cash: ${final_cash:,.2f} (This is NOT Equity)\n"
        f"Final Asset Val: ${invested_value:,.2f}\n"
        f"---------------------------------------\n"
        f"TRUE EQUITY:     ${final_equity:,.2f}\n"
        f"ACTUAL PnL:      {pnl_pct:+.2%}\n"
        f"======================================="
    )

    # 8. Extract results
    return extract_nautilus_metrics(engine, cast(pd.DatetimeIndex, returns.index), strategy, INITIAL_CASH)


def extract_nautilus_metrics(engine: Any, index: pd.DatetimeIndex, strategy: Any, initial_cash: float) -> Dict[str, Any]:
    """
    Extracts performance metrics from Nautilus BacktestEngine and Strategy.
    """
    daily_returns = pd.Series(0.0, index=index)
    nav_series = pd.Series(initial_cash, index=index)  # Default

    try:
        # print(f"DEBUG: NAV History len: {len(strategy._nav_history)}")
        if strategy._nav_history:
            df_nav = pd.DataFrame(strategy._nav_history)
            # print(f"DEBUG: NAV df head:\n{df_nav.head()}")

            df_nav["dt"] = pd.to_datetime(df_nav["ts"], unit="ns", utc=True)
            df_nav.set_index("dt", inplace=True)

            # Ensure index is UTC DatetimeIndex for alignment
            index = pd.to_datetime(index, utc=True)

            # Prepend initial cash at the day before the start
            t0 = index[0] - pd.Timedelta(days=1)
            nav_series = df_nav["nav"].resample("D").last().reindex(index, method="ffill").fillna(initial_cash)

            # Combine with initial cash to capture Day 1 return
            nav_with_t0 = pd.concat([pd.Series([initial_cash], index=[t0]), nav_series])

            # Calculate daily returns
            daily_returns = nav_with_t0.pct_change().iloc[1:].fillna(0.0)

            # Compounding Fix for Pre-Start Priming (CR-830)
            # If we pre-primed, the return at T0 is actually captured in the change from T-1 to T0.
            # But wait, T-1 NAV is Initial Cash. T0 NAV should reflect the PnL of T0.
            # daily_returns index is [T0, T1, ...].
            # daily_returns[T0] = (NAV_T0 - NAV_T-1) / NAV_T-1.
            # If T-1 was flat (0 return) and we traded at T-1 Close, then T0 NAV includes T0 PnL.
            # So daily_returns[T0] IS the return of T0.
            # This matches the index alignment of `returns`.

            # The validation script showed we needed to compound if we had T-1 return.
            # But here `daily_returns` is derived from NAV.
            # If NAV_T0 is correct, then `pct_change` from `Initial_Cash` is correct.
            # So we just need to ensure `nav_series` (reindexed to `index`) has the correct values.

            # Reindexing `df_nav["nav"]` (which has high-res timestamps) to `index` (daily T0, T1...)
            # might miss the exact T0 Close update if timestamps drift.
            # Ideally we resample to 'D' using the same closing time.
            # Assuming 'D' defaults to day start or end?
            # `returns.index` is usually UTC midnight.
            # Nautilus bars are timestamped at event time.
            # If we sent T-1 bar at T-1 00:00, it closes.
            # If `nav_series` uses `resample("D").last()`, it takes the last NAV of the day.

            # If we primed T-1, we have a NAV record at T-1.
            # We have a NAV record at T0.
            # So `nav_series` will have values for T0, T1...
            # And `nav_with_t0` prepends T-1 (Initial).
            # So `pct_change` gives T0 return.
            # This seems correct without extra compounding logic here,
            # *provided* `df_nav` captures the post-close NAV of T0.

            # Check for fill artifact (sanity check)
            if len(daily_returns) > 0 and daily_returns.iloc[0] < -0.2:
                # If we see a massive drop on day 1, it might be an artifact of how initial cash is handled
                # but we should be careful here.
                logger.warning(f"Suspected Day 1 return artifact: {daily_returns.iloc[0]}")

    except Exception as e:
        print(f"ERROR: Failed to extract Nautilus metrics: {e}")

    # Use standard calculator
    metrics = calculate_performance_metrics(daily_returns)
    metrics["engine"] = "nautilus"
    metrics["daily_returns"] = daily_returns

    # Calculate Turnover from Strategy Fills
    total_turnover_pct = 0.0
    if hasattr(strategy, "fills_history"):
        print(f"DEBUG: Extracted {len(strategy.fills_history)} fills")

    if hasattr(strategy, "fills_history") and strategy.fills_history:
        try:
            fills_df = pd.DataFrame(strategy.fills_history)
            if not fills_df.empty:
                fills_df["dt"] = pd.to_datetime(fills_df["ts"], unit="ns", utc=True)
                fills_df["date"] = fills_df["dt"].dt.floor("D")

                # Process per day
                for date, group in fills_df.groupby("date"):
                    sum_abs_fills = group["value"].sum()

                    # Calculate net signed flow (Buy +, Sell -)
                    def get_signed_val(row):
                        s = str(row["side"]).upper()
                        val = row["value"]
                        if "BUY" in s:
                            return val
                        return -val

                    net_signed = group.apply(get_signed_val, axis=1).sum()

                    # Formula: 0.5 * (SumAbs + Abs(NetSigned))
                    # This reconstructs the "1-Way Turnover" including Cash flows
                    day_turnover_val = 0.5 * (sum_abs_fills + abs(net_signed))

                    # Normalize by NAV
                    nav = initial_cash
                    try:
                        if date in nav_series.index:
                            nav = nav_series.loc[date]
                        else:
                            # Use nearest available NAV
                            idx_loc = nav_series.index.get_indexer([date], method="nearest")[0]
                            if idx_loc != -1:
                                nav = nav_series.iloc[idx_loc]
                    except Exception:
                        pass

                    if nav > 0:
                        total_turnover_pct += day_turnover_val / nav

            metrics["turnover"] = total_turnover_pct
        except Exception as e:
            logger.warning(f"Failed to calculate turnover from fills: {e}")
            metrics["turnover"] = 0.0

    # Ensure non-nan sharpe if return is 0
    if pd.isna(metrics.get("sharpe")):
        metrics["sharpe"] = 0.0

    return metrics
