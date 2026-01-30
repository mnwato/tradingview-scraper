import unittest
from tradingview_scraper.orchestration.runner import DAGRunner
from tradingview_scraper.orchestration.registry import StageRegistry


class TestDAGOrchestration(unittest.TestCase):
    def setUp(self):
        # Register some dummy stages for testing
        @StageRegistry.register(id="test.step1", name="Step 1", description="First step", category="test")
        def step1(context):
            context["history"].append("step1")
            return context

        @StageRegistry.register(id="test.step2", name="Step 2", description="Second step", category="test")
        def step2(context):
            context["history"].append("step2")
            return context

    def test_linear_execution(self):
        """Verify that stages are executed in linear sequence."""
        pipeline = ["test.step1", "test.step2"]
        runner = DAGRunner(pipeline)

        initial_context = {"history": []}
        final_context = runner.execute(initial_context)

        self.assertEqual(final_context["history"], ["step1", "step2"])

    def test_failure_abortion(self):
        """Verify that pipeline stops on first failure."""

        @StageRegistry.register(id="test.fail", name="Fail Step", description="Failing step", category="test")
        def fail_step(context):
            raise RuntimeError("Intentional Failure")

        pipeline = ["test.step1", "test.fail", "test.step2"]
        runner = DAGRunner(pipeline)

        initial_context = {"history": []}
        with self.assertRaises(RuntimeError):
            runner.execute(initial_context)

    def test_parallel_execution_mock(self):
        """Verify that parallel branches are handled (sequentially in test)."""
        pipeline = ["test.step1", ["test.step2", "test.step2"]]
        runner = DAGRunner(pipeline)

        initial_context = {"history": []}
        final_context = runner.execute(initial_context)

        # history should have 3 items: step1, step2, step2
        self.assertEqual(len(final_context["history"]), 3)
        self.assertEqual(final_context["history"][0], "step1")
        self.assertEqual(final_context["history"][1], "step2")
        self.assertEqual(final_context["history"][2], "step2")


if __name__ == "__main__":
    unittest.main()
