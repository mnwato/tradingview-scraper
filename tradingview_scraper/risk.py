import logging
import warnings
from typing import Dict, List, cast

import numpy as np
import pandas as pd
import scipy.cluster.hierarchy as sch
from scipy.optimize import minimize
from scipy.spatial.distance import squareform
from sklearn.covariance import ledoit_wolf

logger = logging.getLogger(__name__)


class VolatilityClusterer:
    """
    Identifies systemic risk units by clustering assets based on volatility co-movement.
    Assets that 'spike' together are grouped, even if their price returns are uncorrelated.
    """

    def __init__(self, window: int = 20):
        self.window = window

    def calculate_volatility_series(self, returns: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates log-volatility series for clustering.
        Using log-volatility normalizes the distribution of risk spikes.
        """
        if returns.empty or len(returns) < self.window:
            return pd.DataFrame(index=returns.index, columns=returns.columns)

        # Rolling realized volatility
        # Suppress ddof warning for sparse early windows
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            # Use ddof=0 to avoid "Degrees of freedom <= 0" warning
            vol_series = returns.rolling(window=self.window).std(ddof=0) * np.sqrt(252)

        # Log-transform to handle outliers and normalize distribution
        # Add small epsilon to avoid log(0)
        log_vol = np.log(vol_series + 1e-6)

        return log_vol.dropna()

    def cluster(self, returns: pd.DataFrame, t: float = 0.5) -> Dict[int, List[str]]:
        """
        Performs hierarchical clustering on volatility correlations.
        """
        log_vol = self.calculate_volatility_series(returns)
        if log_vol.empty or log_vol.shape[1] < 2:
            return {1: list(returns.columns)}

        # Volatility Correlation
        corr = log_vol.corr().fillna(0)

        # Distance Matrix (1 - Correlation)
        dist = np.sqrt(0.5 * (1 - corr.values.clip(-1, 1)))
        dist = (dist + dist.T) / 2
        np.fill_diagonal(dist, 0)

        condensed = squareform(dist, checks=False)
        link = sch.linkage(condensed, method="ward")

        # Flat clusters
        assignments = sch.fcluster(link, t=t, criterion="distance")

        clusters: Dict[int, List[str]] = {}
        for sym, cid in zip(log_vol.columns, assignments):
            cid_int = int(cid)
            clusters.setdefault(cid_int, []).append(str(sym))

        return clusters


class ShrinkageCovariance:
    """
    Provides robust covariance matrix estimation using Ledoit-Wolf shrinkage.
    Useful for small sample sizes or highly correlated assets (common in crypto).
    """

    def estimate(self, returns: pd.DataFrame) -> pd.DataFrame:
        """
        Estimates the shrunk covariance matrix.

        Args:
            returns: DataFrame of daily returns.

        Returns:
            DataFrame: Shrunk covariance matrix.
        """
        if returns.empty:
            return pd.DataFrame()

        # Ledoit-Wolf Shrinkage
        # returns.values expected shape: (n_samples, n_features)
        shrunk_cov, shrinkage = ledoit_wolf(returns.values)

        logger.info(f"Covariance estimated with Ledoit-Wolf (Shrinkage: {shrinkage:.4f})")

        return pd.DataFrame(shrunk_cov, index=returns.columns, columns=returns.columns)


class BarbellOptimizer:
    """
    Implements a Taleb-inspired Barbell Strategy.
    Combines a Maximum Diversification Core with high-optionality Aggressors.
    """

    REGIME_SPLITS = {
        "QUIET": {"core": 0.85, "aggressor": 0.15},
        "NORMAL": {"core": 0.90, "aggressor": 0.10},
        "TURBULENT": {"core": 0.95, "aggressor": 0.05},
        "CRISIS": {"core": 0.97, "aggressor": 0.03},
    }

    def _calculate_diversification_ratio(self, weights, volatilities, cov_matrix):
        weighted_vol = np.dot(weights, volatilities)
        port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))

        if port_vol == 0:
            return 0
        return weighted_vol / port_vol

    def optimize(self, returns: pd.DataFrame, antifragility_stats: pd.DataFrame, regime: str = "NORMAL") -> pd.DataFrame:
        """
        Optimizes the barbell portfolio based on the current market regime.
        """
        split = self.REGIME_SPLITS.get(regime, self.REGIME_SPLITS["NORMAL"])
        logger.info(f"Optimizing Barbell for {regime} regime (Core: {split['core']:.0%}, Aggressor: {split['aggressor']:.0%})")

        # 1. Identify Buckets
        # Aggressors: Top 10% or at least 2 assets by Antifragility Score
        n_agg = max(2, int(len(antifragility_stats) * 0.10))
        aggressors = antifragility_stats.sort_values("Antifragility_Score", ascending=False).head(n_agg)["Symbol"].tolist()

        core_candidates = [s for s in returns.columns if s not in aggressors]

        # Safety: If all assets are aggressors, fallback to equal weight across all
        if not core_candidates:
            logger.warning("No core candidates found. Falling back to equal weight aggressor portfolio.")
            agg_w = 1.0 / len(aggressors)
            portfolio = [{"Symbol": s, "Type": "AGGRESSOR (Antifragile)", "Weight": agg_w} for s in aggressors]
            return pd.DataFrame(portfolio)

        core_returns = returns[core_candidates]

        # 2. Optimize Core (Max Diversification)
        n_core = len(core_candidates)
        # Pre-calculate volatilities and shrunk covariance matrix
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            # Use ddof=0 to avoid warning on small core universes
            volatilities = core_returns.std(ddof=0) * np.sqrt(252)
        cov_matrix = ShrinkageCovariance().estimate(cast(pd.DataFrame, core_returns))

        init_weights = np.array([1.0 / n_core] * n_core)

        # Dynamic upper bound to ensure feasibility (sum of weights = 1.0)
        # In TURBULENT regimes, we cap individual core assets at 10% to prevent idiosyncratic crashes.
        if regime == "TURBULENT":
            upper_bound = max(0.1, 1.1 / n_core)
        else:
            upper_bound = max(0.2, 1.1 / n_core)

        bounds = tuple((0.0, upper_bound) for _ in range(n_core))
        constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}

        res_core = minimize(lambda w: -self._calculate_diversification_ratio(w, volatilities, cov_matrix), init_weights, method="SLSQP", bounds=bounds, constraints=constraints)

        # 3. Merge Results
        portfolio = []
        for i, symbol in enumerate(core_candidates):
            portfolio.append({"Symbol": symbol, "Type": "CORE (Safe)", "Weight": res_core.x[i] * split["core"]})

        agg_w = split["aggressor"] / len(aggressors)
        for symbol in aggressors:
            portfolio.append({"Symbol": symbol, "Type": "AGGRESSOR (Antifragile)", "Weight": agg_w})

        return pd.DataFrame(portfolio).sort_values("Weight", ascending=False)


class TailRiskAuditor:
    """
    Calculates tail risk metrics including Value at Risk (VaR) and
    Conditional Value at Risk (CVaR) / Expected Shortfall.
    """

    def calculate_metrics(self, returns: pd.DataFrame, confidence_level: float = 0.95) -> pd.DataFrame:
        """
        Calculates VaR and CVaR for each asset in the returns matrix.
        """
        stats = []
        for symbol in returns.columns:
            res = returns[symbol].dropna()
            if res.empty:
                continue

            # Value at Risk (VaR)
            var = float(res.quantile(1 - confidence_level))

            # Conditional Value at Risk (CVaR) / Expected Shortfall
            # The average of returns that are worse than VaR
            tail_loss = res[res <= var]
            cvar = float(tail_loss.mean()) if len(tail_loss) > 0 else var

            # Tail Ratio (Ratio of right tail to left tail)
            right_tail = float(res.quantile(confidence_level))
            left_tail = abs(var) if var != 0 else 1e-9
            tail_ratio = right_tail / left_tail

            stats.append(
                {
                    "Symbol": symbol,
                    f"VaR_{int(confidence_level * 100)}": var,
                    f"CVaR_{int(confidence_level * 100)}": cvar,
                    "Tail_Ratio": tail_ratio,
                    "Max_Drawdown": float((res.cumsum() - res.cumsum().cummax()).min()),  # Approx daily DD
                }
            )

        return pd.DataFrame(stats)


class AntifragilityAuditor:
    """
    Analyzes historical returns for convexity, skewness, and tail potential.
    """

    def audit(self, returns: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates antifragility metrics for each asset.
        """
        stats = []
        for symbol in returns.columns:
            res = returns[symbol]

            skew = res.skew()
            kurt = res.kurtosis()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                # Use ddof=0 to avoid Degrees of Freedom warning
                vol = res.std(ddof=0) * np.sqrt(252)

            threshold = float(res.quantile(0.95))
            tail_subset = res[res > threshold]
            tail_gain = float(tail_subset.mean()) if len(tail_subset) > 0 else 0.0

            stats.append({"Symbol": symbol, "Vol": vol, "Skew": skew, "Kurtosis": kurt, "Tail_Gain": tail_gain, "N": len(res.dropna())})

        df = pd.DataFrame(stats)

        # Antifragility Score: Favor Positive Skew and High Tail Gain
        # Significance Multiplier: Penalize assets with low history (< 252 days)
        df["Significance"] = (df["N"] / 252.0).clip(0, 1.0)

        df["Antifragility_Score"] = (
            (df["Skew"] - df["Skew"].min()) / (df["Skew"].max() - df["Skew"].min() + 1e-9) + (df["Tail_Gain"] - df["Tail_Gain"].min()) / (df["Tail_Gain"].max() - df["Tail_Gain"].min() + 1e-9)
        ) * df["Significance"]

        return df
