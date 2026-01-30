# Design Specification: Fractal Framework Consolidation (v1.0)

**Status**: Planning  
**Created**: 2026-01-21  
**Phases**: 305-330

## 1. Executive Summary

This document specifies the consolidation of the quantitative portfolio platform into a modular "Fractal Framework". The key insight from the architecture audit is that **most proposed abstractions already exist** - the work is primarily migration, extraction, and formalization rather than greenfield development.

### 1.1 Guiding Principle
**EXTEND existing patterns, do NOT create parallel structures.**

### 1.2 Audit Findings

| Category | Proposed | Reality | Action |
| :--- | :--- | :--- | :--- |
| Pipeline Stage | New `BaseModule` | Exists: `BasePipelineStage` | Preserve |
| Context Object | New `StrategyContext` | Exists: `SelectionContext` | Extend |
| Rankers | New `rankers/` | Exists: `pipelines/selection/rankers/` | Migrate to existing |
| Portfolio Engines | New `allocators/` | Exists: `portfolio_engines/impl/` | Preserve |
| Discovery | New `discovery/` | Gap: Only scripts | Create |
| Filters | New `filters/` | Gap: Scattered in PolicyStage | Extract |
| Meta-Portfolio | New `meta/` | Gap: Only orchestrator script | Formalize |

## 2. Existing Architecture (Preserve)

### 2.1 BasePipelineStage (DO NOT CHANGE)
```python
# pipelines/selection/base.py
class BasePipelineStage(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Friendly name of the stage."""
        pass

    @abstractmethod
    def execute(self, context: SelectionContext) -> SelectionContext:
        """Main execution logic. Must return modified context."""
        pass
```

### 2.2 SelectionContext (DO NOT CHANGE)
```python
# pipelines/selection/base.py
class SelectionContext(BaseModel):
    run_id: str
    params: Dict[str, Any]
    
    # Stage 1: Ingestion
    raw_pool: List[Dict[str, Any]]
    returns_df: pd.DataFrame
    
    # Stage 2: Feature Engineering
    feature_store: pd.DataFrame
    
    # Stage 3: Inference
    inference_outputs: pd.DataFrame
    model_metadata: Dict[str, Any]
    
    # Stage 4: Partitioning
    clusters: Dict[int, List[str]]
    
    # Stage 5: Policy Pruning
    winners: List[Dict[str, Any]]
    
    # Stage 6: Synthesis
    strategy_atoms: List[Any]
    composition_map: Dict[str, Dict[str, float]]
    
    audit_trail: List[Dict[str, Any]]
```

### 2.3 BaseRiskEngine (DO NOT CHANGE)
```python
# portfolio_engines/base.py
class BaseRiskEngine(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        return True

    @abstractmethod
    def optimize(
        self, *,
        returns: pd.DataFrame,
        clusters: Dict[str, List[str]],
        meta: Optional[Dict[str, Any]],
        stats: Optional[pd.DataFrame],
        request: EngineRequest
    ) -> EngineResponse:
        pass
```

## 3. Phase 305: Migrate StrategyRegimeRanker

### 3.1 Objective
Move `StrategyRegimeRanker` from `selection_engines/ranker.py` to `pipelines/selection/rankers/regime.py` for architectural consistency.

### 3.2 Current Location
- File: `tradingview_scraper/selection_engines/ranker.py`
- Imported by: `selection_engines/impl/v3_mps.py`

### 3.3 Target Location
- File: `tradingview_scraper/pipelines/selection/rankers/regime.py`
- Will be registered in: `rankers/factory.py`

### 3.4 Migration Steps
1. Create new file at target location with identical code.
2. Update factory to register `regime` ranker.
3. Update imports in `v3_mps.py` and `BacktestEngine`.
4. Add deprecation alias at old location for backwards compatibility.
5. Run tests to verify.

### 3.5 TDD Test Plan
```python
# tests/test_strategy_ranker.py (Update imports)
def test_regime_ranker_import_from_new_location():
    from tradingview_scraper.pipelines.selection.rankers.regime import StrategyRegimeRanker
    assert StrategyRegimeRanker is not None

def test_regime_ranker_deprecation_warning():
    import warnings
    with warnings.catch_warnings(record=True) as w:
        from tradingview_scraper.selection_engines.ranker import StrategyRegimeRanker
        assert len(w) == 1
        assert "deprecated" in str(w[0].message).lower()
```

## 4. Phase 310: Discovery Module

### 4.1 Objective
Formalize the discovery/scanning functionality into a proper module with testable interfaces.

### 4.2 Current State
- Scanners in `scripts/scanners/` directory
- No shared base class
- Direct file I/O coupling

### 4.3 Proposed Interface
```python
# pipelines/discovery/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class CandidateMetadata:
    """Standardized candidate schema."""
    symbol: str
    exchange: str
    asset_type: str  # "spot", "perp", "equity"
    market_cap_rank: Optional[int] = None
    volume_24h: Optional[float] = None
    sector: Optional[str] = None
    metadata: dict = field(default_factory=dict)

class BaseDiscoveryScanner(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Scanner identifier (e.g., 'binance_spot')."""
        pass

    @abstractmethod
    def discover(self, params: dict) -> List[CandidateMetadata]:
        """
        Execute discovery and return candidate list.
        
        Args:
            params: Scanner-specific parameters (e.g., min_volume, filters).
        
        Returns:
            List of standardized candidate metadata.
        """
        pass
```

### 4.4 Implementations
| Scanner | Source | Target |
| :--- | :--- | :--- |
| Binance Spot | `scripts/scanners/binance_spot_scanner.py` | `pipelines/discovery/binance.py` |
| TradingView | `scripts/scanners/tradingview_scanner.py` | `pipelines/discovery/tradingview.py` |
| OKX | `scripts/scanners/okx_scanner.py` | `pipelines/discovery/okx.py` |

### 4.5 TDD Test Plan
```python
# tests/test_discovery_scanners.py
import pytest
from unittest.mock import patch, MagicMock

def test_binance_scanner_returns_candidate_list():
    from tradingview_scraper.pipelines.discovery.binance import BinanceSpotScanner
    
    scanner = BinanceSpotScanner()
    with patch.object(scanner, '_fetch_exchange_info', return_value=MOCK_EXCHANGE_INFO):
        candidates = scanner.discover({"min_volume": 1_000_000})
    
    assert len(candidates) > 0
    assert all(isinstance(c, CandidateMetadata) for c in candidates)
    assert all(c.exchange == "BINANCE" for c in candidates)

def test_candidate_metadata_schema_compliance():
    from tradingview_scraper.pipelines.discovery.base import CandidateMetadata
    
    candidate = CandidateMetadata(
        symbol="BTCUSDT",
        exchange="BINANCE",
        asset_type="spot",
        volume_24h=1_000_000_000.0
    )
    
    assert candidate.symbol == "BTCUSDT"
    assert candidate.market_cap_rank is None  # Optional
```

## 5. Phase 315: Filter Module Extraction

### 5.1 Objective
Extract filter logic from `PolicyStage` into composable, testable filter classes.

### 5.2 Current State
Filter logic is embedded in `pipelines/selection/stages/policy.py`:
- Health vetoes (missing data, low liquidity)
- Spectral vetoes (high entropy, low efficiency)
- ECI/Friction vetoes

### 5.3 Proposed Interface
```python
# pipelines/selection/filters/base.py
from abc import ABC, abstractmethod
from typing import List, Tuple

class BaseFilter(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Filter identifier (e.g., 'darwinian')."""
        pass

    @abstractmethod
    def apply(
        self, 
        context: SelectionContext
    ) -> Tuple[SelectionContext, List[str]]:
        """
        Apply filter to context and return vetoed symbols.
        
        Args:
            context: Current pipeline context.
        
        Returns:
            Tuple of (modified_context, list_of_vetoed_symbols).
        """
        pass
```

### 5.4 Filter Implementations
| Filter | Logic | Thresholds |
| :--- | :--- | :--- |
| `DarwinianFilter` | Health vetoes (missing bars, low volume) | `strict_health=True`, `min_volume` |
| `SpectralFilter` | Entropy/Hurst/Efficiency vetoes | `entropy_max=0.995`, `efficiency_min=0.3` |
| `FrictionFilter` | ECI (Execution Cost Index) vetoes | `eci_max=0.02` |
| `PredictabilityFilter` | Alpha predictability vetoes | `feat_predictability_vetoes=True` |

### 5.5 Filter Chain Pattern
```python
# pipelines/selection/stages/policy.py (Refactored)
class SelectionPolicyStage(BasePipelineStage):
    def __init__(self, filters: Optional[List[BaseFilter]] = None):
        self.filters = filters or [
            DarwinianFilter(),
            SpectralFilter(),
            FrictionFilter(),
        ]
    
    def execute(self, context: SelectionContext) -> SelectionContext:
        all_vetoes = {}
        for f in self.filters:
            context, vetoed = f.apply(context)
            for sym in vetoed:
                all_vetoes.setdefault(sym, []).append(f.name)
        
        context.log_event("Policy", "FilterChainComplete", {"vetoes": all_vetoes})
        return context
```

### 5.6 TDD Test Plan
```python
# tests/test_filters.py
import pytest
import pandas as pd

def test_darwinian_filter_vetoes_missing_data():
    from tradingview_scraper.pipelines.selection.filters.darwinian import DarwinianFilter
    from tradingview_scraper.pipelines.selection.base import SelectionContext
    
    # Create context with one healthy and one unhealthy candidate
    context = SelectionContext(
        run_id="test",
        raw_pool=[
            {"symbol": "HEALTHY", "missing_pct": 0.0},
            {"symbol": "UNHEALTHY", "missing_pct": 0.5},  # 50% missing
        ],
        returns_df=pd.DataFrame()
    )
    
    f = DarwinianFilter(max_missing_pct=0.1)
    context, vetoed = f.apply(context)
    
    assert "UNHEALTHY" in vetoed
    assert "HEALTHY" not in vetoed

def test_spectral_filter_vetoes_high_entropy():
    from tradingview_scraper.pipelines.selection.filters.spectral import SpectralFilter
    
    context = create_context_with_features({
        "NOISY": {"entropy": 0.999, "efficiency": 0.5},
        "CLEAN": {"entropy": 0.85, "efficiency": 0.5},
    })
    
    f = SpectralFilter(entropy_max=0.995)
    context, vetoed = f.apply(context)
    
    assert "NOISY" in vetoed
    assert "CLEAN" not in vetoed
```

## 6. Phase 320: Meta-Portfolio Module

### 6.1 Objective
Formalize the meta-portfolio construction into a proper module with clear abstractions.

### 6.2 Current State
- Orchestration in `scripts/run_meta_pipeline.py`
- Ray/subprocess-based parallel execution
- Ad-hoc aggregation and flattening logic

### 6.3 Proposed Abstractions

#### A. MetaContext
```python
# pipelines/meta/base.py
class MetaContext(BaseModel):
    """Extended context for meta-portfolio construction."""
    
    run_id: str
    meta_profile: str  # e.g., "meta_benchmark"
    
    # Sleeve-Level Data
    sleeve_profiles: List[str]  # e.g., ["crypto_long", "crypto_short"]
    sleeve_weights: Dict[str, pd.DataFrame]  # profile -> weight_df
    sleeve_returns: Dict[str, pd.Series]  # profile -> cumulative_return_series
    
    # Meta-Level Data
    meta_returns: pd.DataFrame  # Sleeves as columns
    meta_weights: pd.Series  # Sleeve allocations
    
    # Final Output
    flattened_weights: pd.DataFrame  # Asset-level weights
    
    audit_trail: List[Dict[str, Any]]
```

#### B. SleeveAggregator
```python
# pipelines/meta/aggregator.py
class SleeveAggregator:
    """Builds meta-returns matrix from sleeve performance."""
    
    def aggregate(
        self, 
        sleeve_returns: Dict[str, pd.Series],
        join_method: str = "inner"
    ) -> pd.DataFrame:
        """
        Aggregate sleeve returns into a matrix.
        
        Args:
            sleeve_returns: Map of sleeve_name -> return_series.
            join_method: "inner" (common dates) or "outer" (all dates).
        
        Returns:
            DataFrame with sleeves as columns, dates as index.
        """
        pass
```

#### C. WeightFlattener
```python
# pipelines/meta/flattener.py
class WeightFlattener:
    """Projects meta-weights to individual asset weights."""
    
    def flatten(
        self,
        meta_weights: pd.Series,
        sleeve_weights: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """
        Project meta-weights to atom-level weights.
        
        Formula: atom_weight = meta_weight[sleeve] * sleeve_weight[atom]
        
        Args:
            meta_weights: Series of sleeve allocations (sum = 1.0).
            sleeve_weights: Map of sleeve_name -> weight_df.
        
        Returns:
            DataFrame with columns [Symbol, Weight, Direction, Sleeve].
        """
        pass
```

### 6.4 TDD Test Plan
```python
# tests/test_meta_pipeline.py
import pytest
import pandas as pd

def test_sleeve_aggregator_inner_join():
    from tradingview_scraper.pipelines.meta.aggregator import SleeveAggregator
    
    sleeve_returns = {
        "crypto_long": pd.Series([0.01, 0.02, 0.03], index=["2026-01-01", "2026-01-02", "2026-01-03"]),
        "crypto_short": pd.Series([0.02, 0.01], index=["2026-01-01", "2026-01-02"]),  # Missing 03
    }
    
    agg = SleeveAggregator()
    meta_returns = agg.aggregate(sleeve_returns, join_method="inner")
    
    assert len(meta_returns) == 2  # Only common dates
    assert list(meta_returns.columns) == ["crypto_long", "crypto_short"]

def test_weight_flattener_projection():
    from tradingview_scraper.pipelines.meta.flattener import WeightFlattener
    
    meta_weights = pd.Series({"crypto_long": 0.6, "crypto_short": 0.4})
    sleeve_weights = {
        "crypto_long": pd.DataFrame([
            {"Symbol": "BTCUSDT", "Weight": 0.5},
            {"Symbol": "ETHUSDT", "Weight": 0.5},
        ]),
        "crypto_short": pd.DataFrame([
            {"Symbol": "XRPUSDT", "Weight": 1.0},
        ]),
    }
    
    flattener = WeightFlattener()
    flat = flattener.flatten(meta_weights, sleeve_weights)
    
    # BTCUSDT: 0.6 * 0.5 = 0.30
    # ETHUSDT: 0.6 * 0.5 = 0.30
    # XRPUSDT: 0.4 * 1.0 = 0.40
    assert flat.loc[flat["Symbol"] == "BTCUSDT", "Weight"].iloc[0] == pytest.approx(0.30)
    assert flat["Weight"].sum() == pytest.approx(1.0)
```

## 7. Phase 330: Declarative Pipeline Composition (Optional)

### 7.1 Objective
Enable JSON-driven pipeline construction for configuration-as-code deployments.

### 7.2 Proposed Schema
```json
{
  "pipeline": "selection",
  "version": "4.0",
  "stages": [
    {"type": "ingestion", "params": {"candidates_path": "data/lakehouse/portfolio_candidates.json"}},
    {"type": "feature_engineering", "params": {"lookback": 60}},
    {"type": "inference", "params": {"ranker": "mps", "weights": {"momentum": 1.5}}},
    {"type": "clustering", "params": {"threshold": 0.7}},
    {"type": "policy", "params": {"filters": ["darwinian", "spectral"]}},
    {"type": "synthesis", "params": {}}
  ]
}
```

### 7.3 Factory Pattern
```python
# pipelines/factory.py
class PipelineFactory:
    @staticmethod
    def from_config(config: dict) -> SelectionPipeline:
        """Build pipeline from JSON config."""
        pass
```

### 7.4 Priority
**Low** - Current Python-based orchestration is sufficient. This is a future enhancement for GitOps workflows.

## 8. Implementation Order

| Phase | Scope | Dependencies | Effort |
| :--- | :--- | :--- | :--- |
| **305** | Migrate StrategyRegimeRanker | None | 0.5 day |
| **310** | Discovery Module | None | 1 day |
| **315** | Filter Module | None | 1 day |
| **320** | Meta-Portfolio Module | 305, 315 | 2 days |
| **330** | Declarative Composition | 310, 315, 320 | 2 days |

## 9. Risk Mitigation

### 9.1 Backwards Compatibility
- All migrations must include deprecation aliases.
- Old import paths must continue to work with warnings.

### 9.2 Regression Prevention
- Every phase must pass existing test suite before merge.
- No code changes without TDD test coverage.

### 9.3 Rollback Plan
- Each phase is atomic and can be reverted independently.
- Feature flags gate new module usage in production.

## 10. Success Criteria

- [ ] All tests pass (`make test`).
- [ ] No duplicate abstractions in codebase.
- [ ] `StrategyRegimeRanker` accessible from canonical path.
- [ ] Discovery scanners implement `BaseDiscoveryScanner`.
- [ ] Filters implement `BaseFilter` and are composable.
- [ ] Meta-portfolio uses formal `MetaContext` and `SleeveAggregator`.
- [ ] Documentation updated in `docs/specs/requirements_v3.md`.

---

## 11. Related Documents

### Orchestration Layer (Phases 340-360)
The Fractal Framework is extended by the Orchestration Layer, which adds:
- **Ray Compute Engine**: Parallel execution across workers
- **Prefect/DBOS Workflow Engine**: DAG orchestration, retries, observability
- **Callable/Addressable Stages**: CLI/SDK invocation for Claude skills

See: `docs/design/orchestration_layer_v1.md`

### Updated Implementation Order (Including Orchestration)

| Phase | Scope | Dependencies | Effort |
| :--- | :--- | :--- | :--- |
| **305** | Migrate StrategyRegimeRanker | None | 0.5 day |
| **310** | Discovery Module | None | 1 day |
| **315** | Filter Module | None | 1 day |
| **320** | Meta-Portfolio Module | 305, 315 | 2 days |
| **330** | Declarative Composition | 310, 315, 320 | 2 days |
| **340** | Stage Registry & SDK | 305-320 | 1.5 days |
| **345** | Ray Compute Layer | 340 | 1 day |
| **350** | Prefect Workflow Integration | 340, 345 | 1.5 days |
| **355** | Claude Skill Integration | 340, 350 | 1 day |
| **360** | Observability & Monitoring | 350 | 1 day |
