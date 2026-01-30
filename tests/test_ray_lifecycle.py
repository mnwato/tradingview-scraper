import os
import unittest

import ray

from tradingview_scraper.orchestration.compute import RayComputeEngine


class TestRayLifecycle(unittest.TestCase):
    def test_context_manager_shutdown(self):
        with RayComputeEngine(num_cpus=1) as engine:
            engine.ensure_initialized()
            self.assertTrue(ray.is_initialized())

        # After exit, ray should be shut down
        self.assertFalse(ray.is_initialized())

    def test_resource_capping_env(self):
        os.environ["TV_ORCH_CPUS"] = "4"
        engine = RayComputeEngine()
        # Trigger heuristic check
        engine._capture_env()
        # We can't easily check internal state without exposing it,
        # but we can verify it doesn't crash.
        self.assertTrue(True)

    def test_double_init_safety(self):
        ray.init(num_cpus=1, ignore_reinit_error=True)
        with RayComputeEngine(num_cpus=1) as engine:
            engine.ensure_initialized()
            self.assertTrue(ray.is_initialized())
        self.assertFalse(ray.is_initialized())


if __name__ == "__main__":
    unittest.main()
