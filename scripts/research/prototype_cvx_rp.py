import cvxportfolio as cvx
import numpy as np
import pandas as pd


class LogBarrier(cvx.costs.Cost):
    """
    Implements -sum(log(w)) for Risk Parity.
    """

    def __init__(self, n_assets):
        self.n = n_assets

    def compile_to_cvxpy(self, w_plus, z, w_plus_minus_w_bm, **kwargs):
        # w_plus includes cash at the end (usually)
        # We want to maximize sum(log(w_assets))
        import cvxpy as cp

        w_assets = w_plus[:-1]
        return cp.sum(cp.log(w_assets))


def run_prototype():
    # 1. Create Synthetic Data
    n_assets = 4
    dates = pd.date_range("2024-01-01", periods=100, tz="UTC")
    returns = pd.DataFrame(np.random.randn(100, n_assets) * 0.01 + 0.0005, index=dates, columns=pd.Index([f"A{i}" for i in range(n_assets)]))

    # 2. Define Objective for Risk Parity (ERC)
    # Maximize sum(log(w)) - 0.5 * w.T @ Sigma @ w
    # Minimize -sum(log(w)) + 0.5 * w.T @ Sigma @ w

    # Note: cvx.FullCovariance() is w.T @ Sigma @ w (I think? Or is it a cost?)
    # Documentation says FullCovariance() is a cost model for Risk.
    # Usually Risk = w.T @ Sigma @ w.

    try:
        # Check if we can define a custom cost
        log_cost = LogBarrier(n_assets)

        risk_model = cvx.FullCovariance()

        # Risk Parity Objective: Maximize sum(log(w)) - 0.5 * w.T @ Sigma @ w
        # This equivalent to Maximizing - (0.5 * Risk + Cost(-sum(log(w))))

        # log_cost returns -sum(log(w)) (convex)
        # risk_model returns wSw (convex)
        # We want to MAXIMIZE -(0.5*risk + log_cost)

        objective = -0.5 * risk_model - log_cost

        constraints = [cvx.LongOnly(), cvx.LeverageLimit(1.0)]

        policy = cvx.SinglePeriodOptimization(objective, constraints)

        # Run for one period
        t = returns.index[-1]

        # We need to hack the values_in_time call or run a backtest
        # Let's try values_in_time

        # Need to initialize the policy first? usually implicitly done.

        print("Attempting to solve...")
        # Use UserProvidedMarketData
        market_data = cvx.UserProvidedMarketData(
            returns=returns,
            volumes=pd.DataFrame(1e9, index=returns.index, columns=returns.columns),
            prices=pd.DataFrame(100.0, index=returns.index, columns=returns.columns),
            cash_key="USDOLLAR",
            min_history=pd.Timedelta("10 days"),
        )
        sim = cvx.MarketSimulator(market_data=market_data)
        res = sim.backtest(policy, start_time=dates[50], end_time=dates[51])

        print("Success!")
        print(res.w.iloc[-1])

    except Exception as e:
        print(f"Failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    run_prototype()
