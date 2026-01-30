from pathlib import Path
from unittest.mock import ANY, MagicMock, patch

import pytest

from tradingview_scraper.orchestration.compute import RayComputeEngine


@pytest.fixture
def mock_ray():
    with patch("tradingview_scraper.orchestration.compute.ray") as mock:
        mock.is_initialized.return_value = False
        yield mock


def test_engine_initialization(mock_ray):
    engine = RayComputeEngine(num_cpus=4)
    engine.ensure_initialized()

    mock_ray.init.assert_called_once_with(num_cpus=4, ignore_reinit_error=True, runtime_env=ANY)


@patch("tradingview_scraper.orchestration.compute.SleeveActor")
def test_dispatch_sleeves(mock_actor_cls, mock_ray):
    mock_actor = MagicMock()
    mock_actor_cls.remote.return_value = mock_actor
    mock_ray.get.return_value = [{"status": "success"}]

    engine = RayComputeEngine()
    sleeves = [{"profile": "p1", "run_id": "r1"}]

    results = engine.execute_sleeves(sleeves)

    mock_actor_cls.remote.assert_called_once()
    mock_actor.run_pipeline.remote.assert_called_once_with("p1", "r1")
    assert results[0]["status"] == "success"


@patch("tradingview_scraper.orchestration.sleeve_executor.os.symlink")
@patch("tradingview_scraper.orchestration.sleeve_executor.get_settings")
@patch("tradingview_scraper.orchestration.sleeve_executor.Path")
def test_sleeve_actor_init(mock_path_cls, mock_get_settings, mock_symlink):
    from tradingview_scraper.orchestration.sleeve_executor import SleeveActorImpl

    # Mock settings
    mock_s = MagicMock()
    mock_get_settings.return_value = mock_s

    # Setup Path mocks
    target_path = MagicMock(spec=Path)
    target_path.exists.return_value = False

    host_path = MagicMock(spec=Path)
    host_path.exists.return_value = True

    # Path instantiation logic: link_subdir does Path(host_cwd) / target_path
    mock_path_cls.side_effect = lambda *args: host_path if "/host/cwd" in str(args) else target_path

    mock_s.lakehouse_dir = target_path
    mock_s.export_dir = target_path
    mock_s.data_dir = MagicMock()

    env_vars = {"TV_STRICT_HEALTH": "1"}
    host_cwd = "/host/cwd"

    # Instantiate
    actor = SleeveActorImpl(host_cwd, env_vars)

    # Check symlinks
    assert mock_symlink.call_count >= 2
