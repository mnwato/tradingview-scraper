import pytest

from tradingview_scraper.selection_engines import build_selection_engine, list_known_selection_engines
from tradingview_scraper.selection_engines.base import BaseSelectionEngine


def test_list_known_selection_engines():
    engines = list_known_selection_engines()
    assert "v2.0" in engines
    assert "v2.1" in engines
    assert "v3.2" in engines
    assert "v3.4" in engines
    assert "baseline" in engines
    assert "liquid_htr" in engines
    assert "legacy" in engines


@pytest.mark.parametrize("name", ["v2.0", "v2.1", "v3.2", "v3.4", "baseline", "liquid_htr"])
def test_build_selection_engine(name):
    engine = build_selection_engine(name)
    assert isinstance(engine, BaseSelectionEngine)
    assert engine.name == name


def test_build_selection_engine_invalid():
    with pytest.raises(ValueError, match="Unknown selection engine: non_existent"):
        build_selection_engine("non_existent")
