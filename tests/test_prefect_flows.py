import unittest
from unittest.mock import patch

from prefect.testing.utilities import prefect_test_harness

from tradingview_scraper.orchestration.flows.selection import run_selection_flow


class TestPrefectFlows(unittest.TestCase):
    def test_selection_flow_structure(self):
        """Verify the selection flow runs and calls the expected stages."""
        # Mock QuantSDK.run_stage to avoid actual execution
        with patch("tradingview_scraper.orchestration.sdk.QuantSDK.run_stage") as mock_run:
            # Setup mock returns
            from tradingview_scraper.pipelines.selection.base import SelectionContext

            mock_ctx = SelectionContext(run_id="test", params={})
            mock_run.return_value = mock_ctx

            with prefect_test_harness():
                # We need to ensure winners are >= 15 to exit loop early in test or just run 1 pass
                mock_ctx.winners = [{} for _ in range(20)]

                state = run_selection_flow(profile="test_profile", run_id="test_run")

                # Verify QuantSDK was called for each major stage
                # Ingestion, Features, Inference, Clustering, Policy, Synthesis
                # Stage IDs: selection.ingestion, selection.features, selection.inference,
                #            selection.clustering, selection.policy, selection.synthesis

                # Check call IDs
                called_ids = [call.args[0] for call in mock_run.call_args_list]
                self.assertIn("foundation.ingest", called_ids)
                self.assertIn("foundation.features", called_ids)
                self.assertIn("alpha.inference", called_ids)
                self.assertIn("alpha.clustering", called_ids)
                self.assertIn("alpha.policy", called_ids)
                self.assertIn("alpha.synthesis", called_ids)

    def test_sdk_pipeline_execution(self):
        """Verify the full DAG execution via QuantSDK."""
        from tradingview_scraper.orchestration.sdk import QuantSDK

        with patch("tradingview_scraper.orchestration.sdk.QuantSDK.run_stage") as mock_run:
            from tradingview_scraper.pipelines.selection.base import SelectionContext

            mock_ctx = SelectionContext(run_id="test", params={})
            mock_run.return_value = mock_ctx

            QuantSDK.run_pipeline("alpha.full", profile="test", run_id="test")

            # Should have called at least foundation.ingest and risk.optimize
            called_ids = [call.args[0] for call in mock_run.call_args_list]
            self.assertIn("foundation.ingest", called_ids)
            self.assertIn("risk.optimize", called_ids)


if __name__ == "__main__":
    unittest.main()
