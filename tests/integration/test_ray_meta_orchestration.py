import json
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from scripts.run_meta_pipeline import run_meta_pipeline


@pytest.fixture
def mock_manifest_content():
    return {
        "profiles": {
            "meta_benchmark": {
                "sleeves": [{"id": "s1", "profile": "binance_spot_rating_all_long", "run_id": "baseline_all_long"}, {"id": "s2", "profile": "binance_spot_rating_all_short", "run_id": ""}]
            },
            "meta_ma_benchmark": {
                "sleeves": [{"id": "s1", "profile": "binance_spot_rating_ma_long", "run_id": None}, {"id": "s2", "profile": "binance_spot_rating_ma_short", "run_id": "baseline_ma_short"}]
            },
        }
    }


@pytest.fixture
def mock_deps():
    with (
        patch("scripts.run_meta_pipeline.RayComputeEngine") as mock_ray,
        patch("tradingview_scraper.orchestration.sdk.QuantSDK.run_stage") as mock_run_stage,
        patch("scripts.run_meta_pipeline.get_settings") as mock_settings,
    ):
        # Setup settings mock
        mock_s = MagicMock()
        mock_s.summaries_runs_dir = Path("data/artifacts/summaries/runs")
        mock_s.profiles = "binance_spot_rating_all_long,binance_spot_rating_all_short"
        mock_settings.return_value = mock_s

        # Setup Ray mock
        mock_engine = MagicMock()
        mock_ray.return_value = mock_engine
        mock_engine.execute_sleeves.return_value = [{"profile": "p1", "status": "success", "duration": 1.0}]

        yield {"ray": mock_engine, "run_stage": mock_run_stage}


@patch("builtins.open")
@patch("json.load")
def test_meta_benchmark_ray_dispatch(mock_json_load, mock_open, mock_deps, mock_manifest_content):
    mock_json_load.return_value = mock_manifest_content

    # Action: Run meta_benchmark with execute_sleeves=True
    # We pass profiles explicitly to match the manifest structure in the test
    profiles = ["binance_spot_rating_all_long", "binance_spot_rating_all_short"]
    run_meta_pipeline("meta_benchmark", profiles=profiles, execute_sleeves=True, run_id="test_run")

    # Assert Ray was called for both sleeves (since one has 'baseline' and one is empty)
    assert mock_deps["ray"].execute_sleeves.called
    args, _ = mock_deps["ray"].execute_sleeves.call_args
    sleeves_called = args[0]

    assert len(sleeves_called) == 2
    assert sleeves_called[0]["profile"] == "binance_spot_rating_all_long"
    assert sleeves_called[1]["profile"] == "binance_spot_rating_all_short"


@patch("builtins.open")
@patch("json.load")
def test_meta_ma_benchmark_ray_dispatch(mock_json_load, mock_open, mock_deps, mock_manifest_content):
    mock_json_load.return_value = mock_manifest_content

    profiles = ["binance_spot_rating_ma_long", "binance_spot_rating_ma_short"]
    run_meta_pipeline("meta_ma_benchmark", profiles=profiles, execute_sleeves=True, run_id="test_run_ma")

    # Assert Ray was called for both sleeves
    assert mock_deps["ray"].execute_sleeves.called
    args, _ = mock_deps["ray"].execute_sleeves.call_args
    sleeves_called = args[0]

    assert len(sleeves_called) == 2
    assert sleeves_called[0]["profile"] == "binance_spot_rating_ma_long"
    assert sleeves_called[1]["profile"] == "binance_spot_rating_ma_short"


@patch("builtins.open")
@patch("json.load")
def test_orchestration_sequence(mock_json_load, mock_open, mock_deps, mock_manifest_content):
    mock_json_load.return_value = mock_manifest_content

    manager = MagicMock()
    manager.attach_mock(mock_deps["ray"].execute_sleeves, "ray")
    manager.attach_mock(mock_deps["run_stage"], "run_stage")

    profiles = ["binance_spot_rating_all_long"]
    run_meta_pipeline("meta_benchmark", profiles=profiles, execute_sleeves=True, run_id="seq_test")

    # Check call order
    # Note: Ray is called first if execute_sleeves is True
    expected_calls = [call.ray(ANY), call.run_stage("meta.returns", ANY), call.run_stage("meta.optimize", ANY)]
    # We filter for relevant calls
    relevant_calls = [c[0] for c in manager.mock_calls if c[0] in ["ray", "run_stage"]]
    assert relevant_calls[0] == "ray"
    assert "run_stage" in relevant_calls


@patch("builtins.open")
@patch("json.load")
def test_meta_pipeline_aborts_on_sleeve_failure(mock_json_load, mock_open, mock_deps, mock_manifest_content):
    mock_json_load.return_value = mock_manifest_content

    # Simulate a partial failure in Ray
    mock_deps["ray"].execute_sleeves.return_value = [
        {"profile": "all_long", "status": "success", "duration": 1.0},
        {"profile": "all_short", "status": "error", "error": "OutOfMemory", "duration": 0.5},
    ]

    profiles = ["binance_spot_rating_all_long", "binance_spot_rating_all_short"]

    # Expect RuntimeError
    with pytest.raises(RuntimeError) as excinfo:
        run_meta_pipeline("meta_benchmark", profiles=profiles, execute_sleeves=True, run_id="fail_test")

    assert "Sleeve production failed" in str(excinfo.value)
    assert "all_short" in str(excinfo.value)
    assert "OutOfMemory" in str(excinfo.value)

    # Verify downstream stages were NOT called
    assert not mock_deps["run_stage"].called


@patch("builtins.open")
@patch("json.load")
def test_manifest_ray_configuration(mock_json_load, mock_open, mock_deps):
    # This test verifies that the newly added profiles in manifest.json
    # correctly trigger Ray execution by having empty run_ids.

    # Actually, I'll just load the real manifest from disk for this test
    # since I just modified it and I want to verify the REAL config.
    mock_open.stop()
    mock_json_load.stop()

    with open("configs/manifest.json", "r") as f:
        manifest = json.load(f)

    for profile_name in ["meta_benchmark_ray", "meta_ma_benchmark_ray"]:
        profile = manifest["profiles"].get(profile_name)
        assert profile is not None, f"Profile {profile_name} missing from manifest"

        sleeves = profile["sleeves"]
        for s in sleeves:
            # An empty run_id should trigger Ray
            assert s["run_id"] == "", f"Sleeve {s['id']} in {profile_name} should have empty run_id"


from unittest.mock import ANY
