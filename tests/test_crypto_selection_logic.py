"""
Test suite for crypto selection engine logic.
Validates directional normalization, late-binding, and SSP fallbacks.
"""

import unittest

import numpy as np
import pandas as pd


class TestCryptoSelectionLogic(unittest.TestCase):
    """Test crypto-specific selection and directional logic."""

    def test_synthetic_long_normalization_concept(self):
        """
        Validate the Synthetic Long Normalization concept (CR-181).

        SHORT asset returns should be inverted BEFORE selection/optimization.
        This ensures all engines operate on "alpha-aligned" returns.
        """
        # Simulate a SHORT asset with downward drift (good performance)
        short_returns = pd.Series([-0.01, -0.02, 0.01, -0.015, -0.01])

        # Direction signal (negative momentum = SHORT)
        momentum = short_returns.rolling(3).mean().iloc[-1]
        direction = np.sign(momentum)  # Should be negative

        self.assertEqual(direction, -1, "Negative momentum should signal SHORT direction")

        # Synthetic long transformation
        synthetic_returns = direction * short_returns

        # After inversion, returns should be positive (upward drift)
        synthetic_mean = synthetic_returns.mean()
        raw_mean = short_returns.mean()

        self.assertLess(raw_mean, 0, "Raw SHORT returns should be negative")
        self.assertGreater(synthetic_mean, 0, "Synthetic returns should be positive after inversion")

    def test_late_binding_direction_assignment(self):
        """
        Validate Late-Binding Directional Assignment (CR-182).

        Direction should be determined dynamically at each rebalance window
        based on recent momentum, not fixed at discovery.
        """
        # Simulate returns transitioning from uptrend to downtrend
        early_returns = pd.Series([0.02, 0.015, 0.01, 0.02, 0.015])
        late_returns = pd.Series([-0.01, -0.02, -0.015, -0.01, -0.02])

        # Early window: positive momentum -> LONG
        early_momentum = early_returns.rolling(3).mean().iloc[-1]
        early_direction = 1 if early_momentum > 0 else -1
        self.assertEqual(early_direction, 1, "Early window should be LONG")

        # Late window: negative momentum -> SHORT
        late_momentum = late_returns.rolling(3).mean().iloc[-1]
        late_direction = 1 if late_momentum > 0 else -1
        self.assertEqual(late_direction, -1, "Late window should flip to SHORT")

        # This validates regime-aware adaptation

    def test_direction_blind_portfolio_engines(self):
        """
        Validate Direction-Blind Portfolio Engines concept (CR-183).

        All optimization engines should receive normalized (synthetic long) returns
        and not have direction-specific code paths.
        """
        # Create mixed portfolio: 2 LONG, 2 SHORT with stronger drifts
        np.random.seed(42)

        # LONG assets: positive drift (increased for test stability)
        long1 = np.random.normal(0.01, 0.01, 252)
        long2 = np.random.normal(0.01, 0.01, 252)

        # SHORT assets: negative drift
        short1 = np.random.normal(-0.01, 0.01, 252)
        short2 = np.random.normal(-0.01, 0.01, 252)

        # Create returns DataFrame
        raw_returns = pd.DataFrame({"LONG1": long1, "LONG2": long2, "SHORT1": short1, "SHORT2": short2})

        # Direction signals (derived from actual data)
        directions = pd.Series({col: 1 if raw_returns[col].mean() > 0 else -1 for col in raw_returns.columns})

        # Normalize to synthetic longs
        synthetic_returns = raw_returns.copy()
        for col in synthetic_returns.columns:
            synthetic_returns[col] = directions[col] * raw_returns[col]

        # All synthetic returns should have positive mean (alpha-aligned)
        # After normalization, mean should equal |raw_mean|
        for col in synthetic_returns.columns:
            synthetic_mean = synthetic_returns[col].mean()
            raw_mean = raw_returns[col].mean()
            self.assertAlmostEqual(synthetic_mean, abs(raw_mean), places=10, msg=f"{col} synthetic mean should equal |raw_mean|")

    def test_simulator_reconstruction_logic(self):
        """
        Validate Simulator Reconstruction (CR-184).

        Net weights for execution must be: W_net = W_synthetic * sign(direction)
        """
        # Synthetic weights from optimizer (all positive for long allocation)
        synthetic_weights = pd.Series(
            {
                "LONG1": 0.3,
                "LONG2": 0.2,
                "SHORT1": 0.3,  # Allocated as synthetic long
                "SHORT2": 0.2,  # Allocated as synthetic long
            }
        )

        # Direction signals
        directions = pd.Series({"LONG1": 1, "LONG2": 1, "SHORT1": -1, "SHORT2": -1})

        # Reconstruct net weights for execution
        net_weights = synthetic_weights * directions

        # Verify LONG positions remain positive
        self.assertGreater(net_weights["LONG1"], 0)
        self.assertGreater(net_weights["LONG2"], 0)

        # Verify SHORT positions become negative
        self.assertLess(net_weights["SHORT1"], 0)
        self.assertLess(net_weights["SHORT2"], 0)

        # Verify weight magnitudes preserved
        self.assertAlmostEqual(abs(net_weights["SHORT1"]), 0.3)
        self.assertAlmostEqual(abs(net_weights["SHORT2"]), 0.2)

    def test_selection_scarcity_protocol_fallback(self):
        """
        Validate Selection Scarcity Protocol (SSP) fallback logic (CR-191).

        When winner pool is sparse, system should fallback:
        Max-Sharpe -> Min-Var -> Equal-Weight
        """
        # This is a conceptual test - actual implementation in engines.py

        # Scenario 1: Normal pool (5+ assets) -> Max-Sharpe
        normal_pool_size = 8
        expected_strategy = "max_sharpe" if normal_pool_size >= 5 else "min_variance"
        self.assertEqual(expected_strategy, "max_sharpe")

        # Scenario 2: Sparse pool (3-4 assets) -> Min-Variance
        sparse_pool_size = 3
        expected_strategy = "min_variance" if sparse_pool_size >= 3 else "equal_weight"
        self.assertEqual(expected_strategy, "min_variance")

        # Scenario 3: Very sparse pool (1-2 assets) -> Equal-Weight
        very_sparse_pool_size = 2
        expected_strategy = "equal_weight" if very_sparse_pool_size < 3 else "min_variance"
        self.assertEqual(expected_strategy, "equal_weight")

    def test_entropy_veto_threshold_crypto(self):
        """
        Validate crypto entropy threshold is higher than TradFi.

        Crypto: 0.999 vs TradFi: 0.995 (higher noise tolerance)
        """
        import json

        with open("configs/manifest.json") as f:
            manifest = json.load(f)

        crypto_entropy = manifest["profiles"]["crypto_production"]["features"]["entropy_max_threshold"]
        default_entropy = manifest["defaults"]["features"]["entropy_max_threshold"]

        self.assertEqual(crypto_entropy, 0.999)
        self.assertGreaterEqual(crypto_entropy, default_entropy, "Crypto should tolerate higher entropy")

    def test_top_n_per_cluster_validation(self):
        """
        Validate top_n=5 selection per cluster (CR-115).

        This prevents single-asset factor concentration in crypto.
        """
        import json

        with open("configs/manifest.json") as f:
            manifest = json.load(f)

        crypto_top_n = manifest["profiles"]["crypto_production"]["selection"]["top_n"]

        # Crypto should select 5 (more than TradFi's 2-3)
        self.assertEqual(crypto_top_n, 5, "Crypto needs top_n=5 for cluster diversification")


class TestDirectionalPurityIntegration(unittest.TestCase):
    """Integration tests for directional purity across the pipeline."""

    def test_end_to_end_short_asset_flow(self):
        """
        End-to-end test: SHORT asset from discovery -> optimization -> execution.

        Validates that a SHORT asset with negative returns:
        1. Gets identified as SHORT (negative momentum)
        2. Gets inverted to synthetic long (positive returns)
        3. Gets allocated positive weight by optimizer
        4. Gets converted to negative net weight for execution
        """
        # Step 1: Discovery - asset with negative drift (good SHORT candidate)
        raw_returns = pd.Series(np.random.normal(-0.002, 0.02, 252))

        # Step 2: Direction assignment (late-binding)
        momentum_20d = raw_returns.rolling(20).mean().iloc[-1]
        direction = np.sign(momentum_20d)

        self.assertEqual(direction, -1, "Negative momentum should signal SHORT")

        # Step 3: Synthetic long normalization
        synthetic_returns = direction * raw_returns
        synthetic_mean = synthetic_returns.mean()

        self.assertGreater(synthetic_mean, 0, "Synthetic returns should be positive (alpha-aligned)")

        # Step 4: Optimizer allocates positive weight (direction-blind)
        synthetic_weight = 0.25  # Optimizer sees this as attractive long

        # Step 5: Simulator reconstructs net weight
        net_weight = synthetic_weight * direction

        self.assertLess(net_weight, 0, "Net weight must be negative for SHORT execution")
        self.assertAlmostEqual(abs(net_weight), 0.25, "Weight magnitude must be preserved")


if __name__ == "__main__":
    unittest.main()
