import os
import shutil
import tempfile
import pytest
import ray
from pathlib import Path

# Only run if ray is installed
try:
    import ray

    RAY_INSTALLED = True
except ImportError:
    RAY_INSTALLED = False


@pytest.mark.skipif(not RAY_INSTALLED, reason="Ray not installed")
class TestRayIsolation:
    @classmethod
    def setup_class(cls):
        if not ray.is_initialized():
            # Init ray locally
            ray.init(ignore_reinit_error=True)

    @classmethod
    def teardown_class(cls):
        ray.shutdown()

    def test_isolation_filesystem(self):
        """
        Verify that a Ray task with a defined runtime_env:
        1. Runs in a different directory than the driver.
        2. Cannot write to the driver's directory by default (unless absolute path used, but cwd is different).
        """

        # Create a temp dir to act as the "project root" for this test
        with tempfile.TemporaryDirectory() as tmpdir:
            # Shutdown previous ray to re-init with specific runtime_env
            ray.shutdown()

            # Create a source file
            Path(tmpdir).joinpath("source_file.txt").write_text("source")

            # Init Ray with this working_dir (Simulating the Orchestrator)
            ray.init(runtime_env={"working_dir": tmpdir}, ignore_reinit_error=True)

            # Define a task that writes a file to CWD and returns CWD
            @ray.remote
            def isolated_task():
                import os

                cwd = os.getcwd()
                with open("isolated_output.txt", "w") as f:
                    f.write("I am isolated")
                return cwd

            # Execute
            future = isolated_task.remote()
            worker_cwd = ray.get(future)

            # Assertions

            # 1. Worker CWD should NOT be the driver's CWD or the source tmpdir
            # Ray executes in /tmp/ray/session_.../runtime_resources/...
            assert worker_cwd != os.getcwd()
            assert worker_cwd != tmpdir

            # 2. The file written by the worker ("isolated_output.txt") should NOT exist in the source tmpdir
            # because the worker is running in a copy.
            assert not Path(tmpdir).joinpath("isolated_output.txt").exists()

            # 3. The source file SHOULD exist in the worker (implied if the task ran, but let's verify if we could)
            # We can't verify worker state after death, but the successful run implies env creation worked.

            ray.shutdown()

    def test_artifact_export_pattern(self):
        """
        Verify the 'Artifact Export' pattern where the worker zips results and copies them back.
        """
        with tempfile.TemporaryDirectory() as project_root:
            # Create a dummy script or logic
            Path(project_root).joinpath("script.py").write_text("print('hello')")

            output_dir = Path(project_root).joinpath("artifacts")
            output_dir.mkdir()

            # The persistence target on the "Host"
            final_storage = Path(tempfile.mkdtemp())

            # Init Ray with this working_dir
            ray.shutdown()
            ray.init(runtime_env={"working_dir": project_root}, ignore_reinit_error=True)

            @ray.remote
            def pipeline_task(storage_path_str):
                import os
                import shutil
                from pathlib import Path

                # simulate generating data
                os.makedirs("artifacts/run_123", exist_ok=True)
                with open("artifacts/run_123/result.json", "w") as f:
                    f.write('{"status": "success"}')

                # EXPORT STEP:
                # Zip the artifacts
                shutil.make_archive("artifacts_bundle", "zip", root_dir="artifacts", base_dir="run_123")

                # Copy to storage (simulating "upload")
                # In a real cluster, storage_path_str would be an S3 URL or shared mount.
                # Here we test the mechanism of writing to an absolute path provided by driver.
                shutil.copy("artifacts_bundle.zip", os.path.join(storage_path_str, "results.zip"))

                return True

            future = pipeline_task.remote(str(final_storage))
            result = ray.get(future)

            assert result is True

            # Verify persistence
            assert (final_storage / "results.zip").exists()

            # Verify it didn't pollute the source
            assert not (Path(project_root) / "artifacts" / "run_123").exists()
            assert not (Path(project_root) / "artifacts_bundle.zip").exists()

            ray.shutdown()
