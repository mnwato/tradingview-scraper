from typing import Dict, List, Optional, Tuple

import numpy as np


class BlackLittermanEstimator:
    """
    Implements Black-Litterman model to blend market equilibrium returns with specific views.
    """

    def __init__(self, tau: float = 0.05, omega_scale: float = 1.0):
        self.tau = tau
        self.omega_scale = omega_scale

    def estimate(self, mu_equilibrium: np.ndarray, cov: np.ndarray, views_p: Optional[np.ndarray] = None, views_q: Optional[np.ndarray] = None, omega: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Blends equilibrium returns with views.
        """
        if views_p is None or views_q is None:
            return mu_equilibrium

        # Default omega (uncertainty of views) if not provided
        if omega is None:
            # Heuristic: omega is proportional to tau * P * cov * P.T
            # omega_scale allows tuning the confidence (lower = higher confidence)
            omega = np.diag(np.diag(views_p @ (self.tau * cov) @ views_p.T)) * self.omega_scale

        try:
            inv_tau_cov = np.linalg.inv(self.tau * cov)
            inv_omega = np.linalg.inv(omega)

            p_t = views_p.T

            # Posterior mean formula
            term_left = np.linalg.inv(inv_tau_cov + p_t @ inv_omega @ views_p)
            term_right = inv_tau_cov @ mu_equilibrium + p_t @ inv_omega @ views_q

            mu_bl = term_left @ term_right
            return mu_bl
        except Exception:
            return mu_equilibrium

    @staticmethod
    def generate_regime_views(
        symbols: List[str], regime: str, hurst_scores: Dict[str, float], expansion_target: float = 0.15, inflation_target: float = 0.08, crisis_target: float = -0.10, n_assets: int = 3
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Generates P and Q matrices based on All Weather Quadrants.
        """
        n = len(symbols)

        # 1. EXPANSION: Favor high-Hurst (trending) assets
        if regime == "EXPANSION":
            targets = sorted([(s, h) for s, h in hurst_scores.items() if s in symbols], key=lambda x: x[1], reverse=True)[:n_assets]
            q_val = expansion_target

        # 2. INFLATIONARY_TREND: Favor stable trending assets but with lower targets
        elif regime == "INFLATIONARY_TREND":
            targets = sorted([(s, h) for s, h in hurst_scores.items() if s in symbols and h > 0.5], key=lambda x: x[1], reverse=True)[:n_assets]
            q_val = inflation_target

        # 3. CRISIS: Defensive views (expect negative returns for high-vol clusters)
        elif regime == "CRISIS":
            targets = sorted([(s, h) for s, h in hurst_scores.items() if s in symbols], key=lambda x: x[1], reverse=True)[:n_assets]
            q_val = crisis_target

        else:
            return None, None

        if not targets:
            return None, None

        p = np.zeros((len(targets), n))
        q = np.zeros(len(targets))

        for i, (sym, _) in enumerate(targets):
            idx = symbols.index(sym)
            p[i, idx] = 1.0
            q[i] = q_val

        return p, q
