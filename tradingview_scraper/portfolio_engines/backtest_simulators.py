import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, cast

import numpy as np
import pandas as pd

from tradingview_scraper.settings import get_settings
from tradingview_scraper.utils.metrics import calculate_performance_metrics

logger = logging.getLogger("backtest_simulators")


def _calculate_standard_turnover(w_target: pd.Series, h_init: Optional[pd.Series]) -> float:
    """
    Calculates one-way turnover for a rebalance from h_init to w_target.
    If h_init is None, assumes 100% buy-in from cash.
    """
    w1 = w_target.copy()
    if "cash" not in w1.index:
        w1["cash"] = max(0.0, 1.0 - w1.sum())

    if h_init is None:
        w0 = pd.Series(0.0, index=w1.index)
        w0["cash"] = 1.0
    else:
        w0 = h_init.copy()
        if "cash" not in w0.index:
            w0["cash"] = max(0.0, 1.0 - w0.sum())

    all_assets = sorted(list(set(w1.index) | set(w0.index)))
    w1 = w1.reindex(all_assets, fill_value=0.0)
    w0 = w0.reindex(all_assets, fill_value=0.0)

    return float((w1 - w0).abs().sum()) / 2.0


def _calculate_asset_turnover(w_target: pd.Series, h_init: Optional[pd.Series]) -> float:
    """
    Calculates the total absolute trade volume for non-cash assets.
    This is used for friction calculation (slippage/commission).
    """
    w1 = w_target.copy()
    # Ensure we only look at non-cash assets for cost calculation
    if "cash" in w1.index:
        w1 = w1.drop(index="cash")

    if h_init is None:
        w0 = pd.Series(0.0, index=w1.index)
    else:
        w0 = h_init.copy()
        if "cash" in w0.index:
            w0 = w0.drop(index="cash")

    all_assets = sorted(list(set(w1.index) | set(w0.index)))
    w1 = w1.reindex(all_assets, fill_value=0.0)
    w0 = w0.reindex(all_assets, fill_value=0.0)

    return float((w1 - w0).abs().sum())


class BaseSimulator(ABC):
    """Abstract base class for all backtest simulators."""

    @abstractmethod
    def simulate(
        self,
        returns: pd.DataFrame,
        weights_df: pd.DataFrame,
        initial_holdings: Optional[pd.Series] = None,
    ) -> Dict[str, Any]:
        """
        Runs a simulation over the test_data period.
        """
        pass


class ReturnsSimulator(BaseSimulator):
    """
    Standard simulator using direct returns summation.
    Includes estimated friction based on turnover.
    """

    def simulate(
        self,
        returns: pd.DataFrame,
        weights_df: pd.DataFrame,
        initial_holdings: Optional[pd.Series] = None,
    ) -> Dict[str, Any]:
        settings = get_settings()
        target_len = len(returns)

        # Use Net_Weight to handle directional returns correctly (Long/Short).
        # Fallback to Weight if Net_Weight is missing.
        w_target = pd.Series(dtype=float)
        if "Net_Weight" in weights_df.columns:
            w_target = weights_df.set_index("Symbol")["Net_Weight"].astype(float)
        else:
            w_target = weights_df.set_index("Symbol")["Weight"].astype(float)

        if isinstance(w_target, pd.DataFrame):
            w_target = w_target.iloc[:, 0]
        w_target = cast(pd.Series, w_target)

        if "cash" not in w_target.index:
            w_target["cash"] = max(0.0, 1.0 - w_target.abs().sum())

        rebalance_mode = settings.features.feat_rebalance_mode
        tolerance_enabled = settings.features.feat_rebalance_tolerance
        drift_limit = settings.features.rebalance_drift_limit
        total_rate = settings.backtest_slippage + settings.backtest_commission

        # 1. Initial Rebalance at t=0
        # Friction is calculated only on non-cash assets
        asset_turnover_t0 = _calculate_asset_turnover(w_target, initial_holdings)
        friction_t0 = asset_turnover_t0 * total_rate

        daily_p_rets = []
        current_weights = w_target.copy()
        # Reported turnover remains the standard one-way including cash for consistency
        total_turnover = _calculate_standard_turnover(w_target, initial_holdings)

        for t in range(target_len):
            returns_t = returns.iloc[t].reindex(current_weights.index, fill_value=0.0)

            # CR-193: Short Risk Isolation (Bankruptcy Simulation)
            # Calculate contribution per asset with logic:
            # If w < 0 (Short) and r > 1.0 (Price > 2x), the loss is capped at -|w|.
            # Contrib = w * r.
            # If w=-0.1, r=2.0 -> Contrib=-0.2. Loss is 200% of collateral.
            # Cap: If r > 1.0, r_eff = 1.0.
            # Then Contrib = w * 1.0 = -0.1.

            # Vectorized application of cap for shorts
            # r_eff = r.where((w >= 0) | (r <= 1.0), 1.0)

            # We need to apply this logic per asset
            # Separate Longs and Shorts
            w_long = current_weights.where(current_weights > 0, 0.0)
            w_short = current_weights.where(current_weights < 0, 0.0)

            # Apply return cap for shorts: if return > 1.0 (100%), clip it to 1.0 for the short side
            # This simulates liquidation at -100% equity
            r_short_eff = returns_t.clip(upper=1.0)

            # PnL = Long_Contrib + Short_Contrib
            long_contrib = (w_long * returns_t).sum()
            short_contrib = (w_short * r_short_eff).sum()

            p_ret_t = long_contrib + short_contrib

            drift_weights = current_weights * (1 + returns_t)
            # Note: For drift, we technically should also liquidate the short position if it blows up.
            # If r > 1.0 for a short asset, its weight becomes 0 (liquidated)?
            # Or it stays at 0 value?
            # If we short $100 (w=-0.1). Price doubles. Liability $200. Equity $0.
            # Position value = 0?
            # Standard drift: w_new = w_old * (1+r).
            # If w=-0.1, r=1.0 -> w_new = -0.1 * 2.0 = -0.2.
            # This implies the liability doubled relative to base.
            # But if we were liquidated, w_new should be 0.

            # Implementing drift liquidation logic:
            # If w < 0 and r > 1.0: set w_drift = 0.0 (Asset removed from portfolio)
            # But we must be careful about cash impact.
            # If liquidated, the loss is realized against cash/equity.

            # Simulating drift with liquidation is complex for a simple vector looper.
            # For now, we accept the PnL cap (performance metric correctness)
            # and let the drift weights evolve naturally (assuming margin call covered by other assets for the sake of next-day weights).
            # But if we want Strict Isolation, the weight should vanish.

            # Let's apply the PnL cap logic for the return stream, which is the primary output.
            # p_ret_t is already corrected.

            # Drift weights normalization
            w_sum = drift_weights.sum()
            if abs(w_sum) > 1e-6:
                drift_weights = drift_weights / w_sum
            else:
                drift_weights = current_weights.copy()

            friction_t = 0.0

            if rebalance_mode == "daily":
                do_rebalance = True
                if tolerance_enabled:
                    drift_dist = (drift_weights - w_target).abs().sum() / 2.0
                    if drift_dist <= drift_limit:
                        do_rebalance = False

                if do_rebalance:
                    asset_turnover_t = _calculate_asset_turnover(w_target, drift_weights)
                    friction_t = asset_turnover_t * total_rate
                    current_weights = w_target.copy()
                    total_turnover += _calculate_standard_turnover(w_target, drift_weights)
                else:
                    current_weights = drift_weights
            else:
                current_weights = drift_weights

            net_ret_t = p_ret_t - friction_t
            if t == 0:
                net_ret_t -= friction_t0

            daily_p_rets.append(net_ret_t)

        p_returns = pd.Series(daily_p_rets, index=returns.index)
        res = calculate_performance_metrics(p_returns)
        res["daily_returns"] = p_returns
        res["turnover"] = total_turnover
        res["final_weights"] = current_weights
        return res


class CVXPortfolioSimulator(BaseSimulator):
    """High-fidelity friction simulator using CVXPortfolio."""

    def __init__(self):
        try:
            import cvxportfolio as cvp
            from cvxportfolio.policies import Policy

            self.cvp = cvp
            self.Policy = Policy
        except ImportError:
            self.cvp = None
            self.Policy = None

    def simulate(
        self,
        returns: pd.DataFrame,
        weights_df: pd.DataFrame,
        initial_holdings: Optional[pd.Series] = None,
    ) -> Dict[str, Any]:
        if self.cvp is None:
            return ReturnsSimulator().simulate(returns, weights_df, initial_holdings)

        settings = get_settings()
        cash_key = "cash"

        start_t = returns.index[0]
        end_t = returns.index[-1]
        universe = list(returns.columns)
        if cash_key not in universe:
            universe.append(cash_key)

        # Use Net_Weight to handle directional returns correctly (Long/Short).
        if "Net_Weight" in weights_df.columns:
            w_target_raw = weights_df.set_index("Symbol")["Net_Weight"].astype(float)
        else:
            w_target_raw = weights_df.set_index("Symbol")["Weight"].astype(float)

        if isinstance(w_target_raw, pd.DataFrame):
            w_target_raw = w_target_raw.iloc[:, 0]

        # Target weights (normalized to 1.0)
        w_target_norm = cast(pd.Series, w_target_raw).reindex(universe, fill_value=0.0)
        w_sum = w_target_norm.abs().sum()
        if w_sum > 1.0:
            w_target_norm = w_target_norm / w_sum
            w_sum = 1.0
        w_target_norm[cash_key] = max(0.0, 1.0 - w_sum)

        rebalance_mode = settings.features.feat_rebalance_mode

        # Determine initial wealth and holdings
        if initial_holdings is not None:
            h_init = initial_holdings.reindex(universe, fill_value=0.0).astype(np.float64)
            v_init = float(h_init.sum())

            # CR-FIX: Hard Bankruptcy Gate
            # If wealth is below dust threshold (e.g. $0.01 on a $1.0 start),
            # the portfolio is liquidated and stays in cash.
            if v_init < 1e-2:
                logger.warning(f"Portfolio Bankruptcy Detected (Wealth={v_init:.6f}). Liquidating to cash.")
                h_init = pd.Series(0.0, index=universe, dtype=np.float64)
                h_init[cash_key] = max(1e-6, v_init)  # Preserve tiny remainder in cash
                v_init = float(h_init.sum())
        else:
            h_init = pd.Series(0.0, index=universe, dtype=np.float64)
            h_init[cash_key] = 1.0
            v_init = 1.0

        # w_target in dollars = normalized_target_weights * current_wealth
        h_target = w_target_norm * v_init

        if rebalance_mode == "daily":
            # For daily rebalance, CVXPortfolio takes care of scaling weights to wealth internally
            # if we use FixedWeights.
            policy = self.cvp.FixedWeights(w_target_norm)
        else:
            # Rebalance once at start of period
            trades = pd.DataFrame(0.0, index=returns.index, columns=pd.Index(universe))
            trades.iloc[0] = h_target - h_init
            policy = self.cvp.FixedTrades(trades)

        cost_list: List[Any] = [self.cvp.TransactionCost(a=settings.backtest_slippage + settings.backtest_commission)]
        if settings.features.feat_short_costs:
            cost_list.append(self.cvp.HoldingCost(short_fees=settings.features.short_borrow_cost))

        try:
            # Clip extreme returns to prevent numerical instability
            returns_cvx = returns.astype(np.float64).clip(-0.9, 10.0).fillna(0.0)
            if cash_key not in returns_cvx.columns:
                returns_cvx[cash_key] = 0.0

            # CR-FIX: Ensure h_init sum is strictly used as V_init for the simulator
            # MarketSimulator with returns uses absolute $ wealth.
            simulator = self.cvp.MarketSimulator(returns=returns_cvx, costs=cost_list, cash_key=cash_key, min_history=pd.Timedelta(days=0))

            # Execute backtest
            result = simulator.backtest(policy, start_time=start_t, end_time=end_t, h=h_init)

            # Forensic Clipping of realized returns
            # result.returns are the realized fractional returns of the portfolio
            if hasattr(result, "returns") and not result.returns.empty:
                realized_returns = result.returns.copy()
            else:
                realized_returns = result.v.pct_change().dropna()

            realized_returns.index = returns.index[: len(realized_returns)]
            realized_returns = realized_returns.clip(-0.9999, 10.0)

            res = calculate_performance_metrics(realized_returns)

            # We must return absolute holdings to maintain state across windows
            # result.h is absolute dollar holdings per asset
            final_h = result.h.iloc[-1]

            res.update(
                {
                    "daily_returns": realized_returns,
                    "final_holdings": final_h,  # Persist absolute $
                    "final_weights": result.w.iloc[-1],
                    "turnover": float(result.turnover.sum()),
                }
            )
            return res
        except Exception as e:
            logger.error(f"cvxportfolio backtest failed: {e}")
            return ReturnsSimulator().simulate(returns, weights_df, initial_holdings)
        except Exception as e:
            logger.error(f"cvxportfolio failed: {e}")
            return ReturnsSimulator().simulate(returns, weights_df, initial_holdings)


# Backward-compatible alias (legacy/tests).
CvxPortfolioSimulator = CVXPortfolioSimulator


class VectorBTSimulator(BaseSimulator):
    """High-performance vectorized simulator using VectorBT."""

    def __init__(self):
        try:
            import vectorbt as vbt

            self.vbt = vbt
        except ImportError:
            self.vbt = None

    def simulate(
        self,
        returns: pd.DataFrame,
        weights_df: pd.DataFrame,
        initial_holdings: Optional[pd.Series] = None,
    ) -> Dict[str, Any]:
        if self.vbt is None:
            return ReturnsSimulator().simulate(returns, weights_df, initial_holdings)

        vbt = self.vbt
        settings = get_settings()

        rebalance_mode = settings.features.feat_rebalance_mode

        # Use Net_Weight to handle directional returns correctly in VectorBT
        if "Net_Weight" in weights_df.columns:
            w_series = weights_df.set_index("Symbol")["Net_Weight"].astype(float)
        else:
            w_series = weights_df.set_index("Symbol")["Weight"].astype(float)

        if isinstance(w_series, pd.DataFrame):
            w_series = w_series.iloc[:, 0]
        w_series = cast(pd.Series, w_series)

        prices = (1.0 + returns[w_series.index]).cumprod()

        if rebalance_mode == "daily":
            w_df = pd.DataFrame([w_series.values] * len(prices), columns=w_series.index, index=prices.index)
        else:
            w_df = pd.DataFrame(np.nan, columns=w_series.index, index=prices.index)
            w_df.iloc[0] = w_series.values

        portfolio = vbt.Portfolio.from_orders(
            close=prices, size=w_df, size_type="target_percent", fees=settings.backtest_slippage + settings.backtest_commission, freq="D", init_cash=100.0, cash_sharing=True, group_by=True
        )
        # Shift and cap returns
        p_returns = portfolio.returns().fillna(0.0)

        res = calculate_performance_metrics(p_returns)
        res["daily_returns"] = p_returns

        # Calculate true turnover from trades
        # value() gives total portfolio value.
        # trades.value() gives value of each trade.
        # Sum of absolute trade values / 2 = Turnover
        # But we need to be careful about initial vs drift

        # NOTE: VBT trades might include the initial buy-in.
        # If we passed initial_holdings, VBT doesn't know about them in `from_orders` unless we start with positions?
        # `from_orders` assumes cash start.
        # So VBT simulation here IS from cash.
        # Turnover reported by VBT trades will be sum(|trades|)/2
        # But this includes the full buy-in turnover (1.0).
        # We need to replace the t0 turnover with the delta from initial_holdings.

        # Get total VBT turnover
        # trades.value is a Series.
        # But wait, group_by=True means we have one group.
        # portfolio.trades.value() returns a Series of trade values.
        # We sum abs.

        # Better: use our calculated turnover for t0, and add VBT turnover for t1+?
        # In window mode, no trades after t0. So _calculate_standard_turnover is correct.
        # In daily mode, trades happen t1+.

        t0_turnover = _calculate_standard_turnover(w_series, initial_holdings)

        if rebalance_mode == "daily":
            # VBT Total turnover = t0_full_buy + t1_drift + ...
            # We want = t0_delta + t1_drift + ...
            # So we take VBT Total - t0_full_buy + t0_delta

            # Estimate VBT t0 turnover (should be ~1.0 if full invested)
            vbt_t0_turnover = _calculate_standard_turnover(w_series, None)

            # Approximate total turnover from VBT stats?
            # Or assume drift is small and our t0 turnover is dominant?
            # Let's try to get VBT total trade value.
            try:
                # Value of all trades
                total_trade_val = portfolio.trades().value.abs().sum()
                vbt_total_turnover = total_trade_val / 2.0 / 100.0  # Normalize by init_cash=100

                # Correct it
                final_turnover = vbt_total_turnover - vbt_t0_turnover + t0_turnover
                res["turnover"] = max(0.0, final_turnover)
            except Exception:
                # Fallback
                res["turnover"] = t0_turnover
        else:
            res["turnover"] = t0_turnover

        return res


def build_simulator(name: str) -> BaseSimulator:
    if name == "custom":
        return ReturnsSimulator()
    elif name == "cvxportfolio":
        return CVXPortfolioSimulator()
    elif name == "vectorbt":
        return VectorBTSimulator()
    elif name == "nautilus":
        return NautilusSimulator()
    raise ValueError(f"Unknown simulator: {name}")


class NautilusSimulator(BaseSimulator):
    """Event-driven high-fidelity simulator using NautilusTrader (Placeholder)."""

    def simulate(self, returns: pd.DataFrame, weights_df: pd.DataFrame, initial_holdings: Optional[pd.Series] = None) -> Dict[str, Any]:
        # Requirement: Physical Flattening
        # Ensure we are not passing Strategy Atoms (e.g. "BINANCE:BTCUSDT_rating_ma_LONG") to the simulator.
        if "Symbol" in weights_df.columns and not weights_df.empty:
            sample_symbol = str(weights_df["Symbol"].iloc[0])
            # Heuristic check for unflattened logic atoms
            if "_rating_" in sample_symbol or "_logic_" in sample_symbol:
                logger.warning(f"NautilusSimulator received potential Strategy Atom: {sample_symbol}. Ensure weights are flattened to physical symbols before simulation.")

        try:
            from tradingview_scraper.portfolio_engines.nautilus_adapter import run_nautilus_backtest

            return run_nautilus_backtest(returns=returns, weights_df=weights_df, initial_holdings=initial_holdings, settings=get_settings())
        except Exception as e:
            logger.warning(f"Nautilus adapter unavailable, falling back to custom simulator: {e}")
            return ReturnsSimulator().simulate(returns, weights_df, initial_holdings)
