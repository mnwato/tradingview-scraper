import unittest
import numpy as np
from scipy import stats


class TestAlphaCorrelation(unittest.TestCase):
    def test_rank_correlation_validity(self):
        """Verify that Spearman correlation detects preserved rank order despite scalar shift."""
        # Ground Truth: [0.1, 0.5, -0.2, 0.8]
        gt = np.array([0.1, 0.5, -0.2, 0.8])

        # Replicated: [0.2, 0.6, -0.1, 0.9] (Shifted by +0.1)
        # Ranks should be identical:
        # GT Ranks: [2, 3, 1, 4]
        # Rep Ranks: [2, 3, 1, 4]
        rep = gt + 0.1

        res = stats.spearmanr(gt, rep)
        self.assertAlmostEqual(res.statistic, 1.0)

    def test_sign_agreement(self):
        """Verify sign agreement calculation."""
        gt = np.array([0.1, 0.5, -0.2, -0.8])
        rep = np.array([0.2, 0.4, -0.3, 0.1])  # Last one flipped sign

        agreement = np.mean(np.sign(gt) == np.sign(rep))
        self.assertEqual(agreement, 0.75)


if __name__ == "__main__":
    unittest.main()
