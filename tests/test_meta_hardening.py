import unittest
from scripts.flatten_meta_weights import flatten_weights
from scripts.build_meta_returns import build_meta_returns
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestMetaHardening(unittest.TestCase):
    def test_recursion_cycle_detection(self):
        """Verify that circular dependencies are caught."""
        # Test with a mock that would otherwise loop
        with self.assertRaises(RuntimeError) as cm:
            build_meta_returns(meta_profile="meta_cycle", output_path="test.pkl", visited=["meta_cycle"])
        self.assertIn("Circular dependency", str(cm.exception))

    def test_max_depth_protection(self):
        """Verify that max fractal depth is enforced."""
        with self.assertRaises(RuntimeError) as cm:
            build_meta_returns(meta_profile="meta_deep", output_path="test.pkl", depth=4)
        self.assertIn("Max fractal depth exceeded", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
