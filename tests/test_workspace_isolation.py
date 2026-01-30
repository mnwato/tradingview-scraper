import unittest
import os
import shutil
from pathlib import Path
from tradingview_scraper.utils.workspace import WorkspaceManager


class TestWorkspaceIsolation(unittest.TestCase):
    def setUp(self):
        self.test_root = Path("tests/tmp_workspace")
        if self.test_root.exists():
            shutil.rmtree(self.test_root)
        self.test_root.mkdir(parents=True)

        self.lakehouse = self.test_root / "lakehouse"
        self.lakehouse.mkdir()

        # Create dummy foundation data
        (self.lakehouse / "portfolio_candidates.json").write_text('{"symbols": ["BTC"]}')
        (self.lakehouse / "data.parquet").write_text("dummy parquet content")

    def test_golden_snapshot_immutability(self):
        """Verify that mutating source files doesn't affect the snapshot's metadata."""
        manager = WorkspaceManager(run_id="test_run", data_root=self.test_root)
        # Override manager paths for test
        manager.lakehouse_dir = self.lakehouse
        manager.snapshots_dir = self.test_root / "snapshots"

        snapshot_path = manager.create_golden_snapshot()

        # Mutate source
        (self.lakehouse / "portfolio_candidates.json").write_text('{"symbols": ["ETH"]}')

        # Snapshot should still have BTC (since it was copied)
        snapshot_content = (snapshot_path / "portfolio_candidates.json").read_text()
        self.assertIn("BTC", snapshot_content)
        self.assertNotIn("ETH", snapshot_content)

    def test_worker_workspace_setup(self):
        """Verify that worker workspace symlinks are correctly established."""
        worker_root = self.test_root / "worker"
        host_root = self.test_root / "host"
        host_root.mkdir()
        (host_root / "data").mkdir()
        (host_root / "data" / "lakehouse").mkdir()
        (host_root / "data" / "export").mkdir()

        manager = WorkspaceManager(run_id="test_run", data_root=host_root / "data")
        manager.setup_worker_workspace(worker_cwd=worker_root, host_cwd=host_root)

        # Check symlinks
        self.assertTrue((worker_root / "data" / "lakehouse").is_symlink())
        self.assertTrue((worker_root / "data" / "export").is_symlink())
        self.assertTrue((worker_root / "data" / "artifacts").is_dir())

    def tearDown(self):
        if self.test_root.exists():
            shutil.rmtree(self.test_root)


if __name__ == "__main__":
    unittest.main()
