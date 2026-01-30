import os
from unittest.mock import MagicMock, patch

from scripts.research.grand_4d_tournament import run_grand_tournament


@patch("scripts.research.grand_4d_tournament.BacktestEngine")
@patch("scripts.research.grand_4d_tournament.get_settings")
def test_run_grand_tournament_rebalance_loop(mock_get_settings, mock_bt_class, tmp_path):
    from tradingview_scraper.settings import FeatureFlags

    mock_settings = MagicMock()
    mock_settings.features = FeatureFlags()
    mock_settings.cluster_cap = 0.2
    mock_settings.run_id = "run-123"
    mock_settings.run_data_dir = tmp_path
    mock_settings.prepare_summaries_run_dir.return_value = tmp_path
    mock_settings.promote_summaries_latest = MagicMock()
    mock_settings.dynamic_universe = False
    mock_get_settings.return_value = mock_settings

    captured_configs = []

    def bt_side_effect():
        captured_configs.append(
            {
                "selection": mock_settings.features.selection_mode,
                "rebalance": mock_settings.features.feat_rebalance_mode,
            }
        )
        bt_inst = MagicMock()
        bt_inst.run_tournament.return_value = {"meta": {}, "results": {}, "returns": {}}
        return bt_inst

    mock_bt_class.side_effect = bt_side_effect

    with patch.dict(os.environ, {}, clear=True):
        run_grand_tournament(
            selection_modes=["v3.1", "v3.2"],
            rebalance_modes=["window", "daily_5pct"],
            engines=["custom"],
            profiles=["hrp"],
            simulators=["custom"],
        )

    assert len(captured_configs) == 4
    assert captured_configs[0]["rebalance"] == "window"
    assert captured_configs[0]["selection"] == "v3.1"
    assert captured_configs[-1]["rebalance"] == "daily_5pct"
    assert captured_configs[-1]["selection"] == "v3.2"
    assert mock_settings.dynamic_universe is False
