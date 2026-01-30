import unittest
from unittest.mock import MagicMock
from tradingview_scraper.pipelines.selection.rankers.ensemble import EnsembleRanker
from tradingview_scraper.pipelines.selection.rankers.base import BaseRanker


class MockRanker(BaseRanker):
    def __init__(self, scores):
        self.scores_data = scores

    def rank(self, candidates, context, ascending=False):
        return sorted(candidates, key=lambda s: self.scores_data.get(s, 0), reverse=not ascending)

    def score(self, candidates, context):
        return [float(self.scores_data.get(c, 0.0)) for c in candidates]


class TestEnsembleSelection(unittest.TestCase):
    def test_weighted_ensemble_scoring(self):
        """Verify that multiple rankers can be ensembled via weighted average."""
        candidates = ["BTC", "ETH"]

        # Ranker A gives BTC=1.0, ETH=0.0
        ranker_a = MockRanker({"BTC": 1.0, "ETH": 0.0})
        # Ranker B gives BTC=0.0, ETH=1.0
        ranker_b = MockRanker({"BTC": 0.0, "ETH": 1.0})

        # Ensemble with 0.7 weight on A and 0.3 on B
        ensemble = EnsembleRanker(rankers={"a": ranker_a, "b": ranker_b}, weights={"a": 0.7, "b": 0.3})

        scores = ensemble.score(candidates, None)

        # BTC: 0.7*1 + 0.3*0 = 0.7
        # ETH: 0.7*0 + 0.3*1 = 0.3
        self.assertAlmostEqual(scores[0], 0.7)
        self.assertAlmostEqual(scores[1], 0.3)

        # Rank check
        ranked = ensemble.rank(candidates, None)
        self.assertEqual(ranked, ["BTC", "ETH"])


if __name__ == "__main__":
    unittest.main()
