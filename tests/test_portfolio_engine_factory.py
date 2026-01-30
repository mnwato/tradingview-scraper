import pytest
import pandas as pd
from tradingview_scraper.portfolio_engines import build_engine, list_available_engines
from tradingview_scraper.portfolio_engines.base import BaseRiskEngine


def test_list_available_engines():
    engines = list_available_engines()
    assert "custom" in engines
    assert "adaptive" in engines
    # At least one 3rd party engine should be available in this environment
    assert any(e in engines for e in ["skfolio", "riskfolio", "pyportfolioopt", "cvxportfolio"])


def test_build_engine_custom():
    engine = build_engine("custom")
    assert isinstance(engine, BaseRiskEngine)
    assert engine.name == "custom"


def test_build_engine_adaptive():
    engine = build_engine("adaptive")
    assert isinstance(engine, BaseRiskEngine)
    assert engine.name == "adaptive"


def test_build_engine_case_insensitivity():
    engine = build_engine("CUSTOM")
    assert engine.name == "custom"


def test_build_engine_invalid():
    with pytest.raises(ValueError, match="Unknown engine: non_existent"):
        build_engine("non_existent")


@pytest.mark.parametrize("engine_name", ["custom", "market", "adaptive"])
def test_engine_interface_compliance(engine_name):
    engine = build_engine(engine_name)
    assert hasattr(engine, "optimize")
    assert hasattr(engine, "name")
    assert isinstance(engine.name, str)
