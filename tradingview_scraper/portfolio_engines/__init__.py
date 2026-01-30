from __future__ import annotations
from typing import Dict, List, Type

from .backtest_simulators import (
    BaseSimulator,
    CVXPortfolioSimulator,
    ReturnsSimulator,
    VectorBTSimulator,
    build_simulator,
)
from .base import BaseRiskEngine, EngineRequest, EngineResponse, EngineUnavailableError, ProfileName, MarketBaselineEngine
from .cluster_adapter import ClusteredUniverse, build_clustered_universe

from .impl.custom import CustomClusteredEngine
from .impl.skfolio import SkfolioEngine
from .impl.riskfolio import RiskfolioEngine
from .impl.pyportfolioopt import PyPortfolioOptEngine
from .impl.cvxportfolio import CVXPortfolioEngine
from .impl.adaptive import AdaptiveMetaEngine

_ENGINE_CLASSES: Dict[str, Type[BaseRiskEngine]] = {
    "market": MarketBaselineEngine,
    "custom": CustomClusteredEngine,
    "skfolio": SkfolioEngine,
    "riskfolio": RiskfolioEngine,
    "pyportfolioopt": PyPortfolioOptEngine,
    "cvxportfolio": CVXPortfolioEngine,
    "adaptive": AdaptiveMetaEngine,
}


def list_known_engines() -> List[str]:
    return sorted(_ENGINE_CLASSES.keys())


def list_available_engines() -> List[str]:
    out = []
    for name, cls in _ENGINE_CLASSES.items():
        try:
            if cls.is_available():
                out.append(name)
        except Exception:
            continue
    return sorted(out)


def build_engine(name: str) -> BaseRiskEngine:
    key = name.strip().lower()
    if key not in _ENGINE_CLASSES:
        raise ValueError(f"Unknown engine: {name}")
    return _ENGINE_CLASSES[key]()


__all__ = [
    "BaseSimulator",
    "ReturnsSimulator",
    "CVXPortfolioSimulator",
    "VectorBTSimulator",
    "build_simulator",
    "BaseRiskEngine",
    "EngineRequest",
    "EngineResponse",
    "EngineUnavailableError",
    "ProfileName",
    "ClusteredUniverse",
    "build_clustered_universe",
    "build_engine",
    "list_known_engines",
    "list_available_engines",
]
