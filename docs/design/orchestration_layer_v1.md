# Design Specification: Orchestration Layer (v1.0)

**Status**: Planning  
**Created**: 2026-01-21  
**Phases**: 340-360

## 1. Executive Summary

This document specifies the integration of a formal orchestration layer into the quantitative portfolio platform. The design introduces:

1. **Ray as Compute Engine**: Parallel execution of stages across workers
2. **Prefect/DBOS as Workflow Engine**: DAG orchestration, retries, observability
3. **Callable/Addressable Stages**: Each stage is independently invocable for Claude skill integration

### 1.1 Design Principles

| Principle | Description |
| :--- | :--- |
| **Separation of Concerns** | Compute (Ray) vs Orchestration (Prefect) vs Logic (Stages) |
| **Addressability** | Every stage has a unique URI: `quant://pipeline/stage/params` |
| **Idempotency** | Stages can be re-run safely with same inputs |
| **Observability** | All executions emit structured logs/metrics |
| **Composability** | Stages can be combined into DAGs declaratively |

### 1.2 Current State Audit

| Component | Current | Target |
| :--- | :--- | :--- |
| **Parallel Execution** | Ray (subprocess/actors) in `parallel_orchestrator_*.py` | Formalized Ray Compute Layer |
| **Workflow DAG** | Manual `run_step()` sequence in `ProductionPipeline` | Prefect Flow/Task decorators |
| **Stage Invocation** | Python method calls | Addressable CLI + SDK |
| **Retry/Recovery** | None (fail-fast) | Prefect automatic retry with backoff |
| **Observability** | Custom `AuditLedger` | Prefect UI + OpenTelemetry |

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLAUDE SKILL LAYER                          │
│  (Addressable Stage Invocation via CLI/SDK)                        │
│  quant://selection/ingestion?run_id=abc&profile=crypto_long        │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     WORKFLOW ENGINE (Prefect/DBOS)                  │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐             │
│  │Discovery│──▶│Selection│──▶│  Risk   │──▶│Execution│             │
│  │  Flow   │   │  Flow   │   │  Flow   │   │  Flow   │             │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘             │
│       │             │             │             │                   │
│       ▼             ▼             ▼             ▼                   │
│  ┌─────────────────────────────────────────────────────┐           │
│  │              TASK REGISTRY                          │           │
│  │  @task discover_candidates                          │           │
│  │  @task run_ingestion                                │           │
│  │  @task run_feature_engineering                      │           │
│  │  @task run_inference                                │           │
│  │  @task run_clustering                               │           │
│  │  @task run_policy                                   │           │
│  │  @task run_synthesis                                │           │
│  │  @task run_optimization                             │           │
│  └─────────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      COMPUTE ENGINE (Ray)                           │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │                    Ray Cluster                              │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │    │
│  │  │ Worker 1 │  │ Worker 2 │  │ Worker 3 │  │ Worker N │   │    │
│  │  │ (Sleeve) │  │ (Sleeve) │  │ (Stage)  │  │ (Stage)  │   │    │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │    │
│  └────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      STAGE LOGIC LAYER                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ BasePipelineStage.execute(context) -> context               │   │
│  │ BaseRiskEngine.optimize(returns, clusters, ...) -> response │   │
│  │ BaseFilter.apply(context) -> (context, vetoes)              │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## 3. Callable/Addressable Stage Interface

### 3.1 Stage Registry

Every stage must be registered with a unique identifier and schema:

```python
# tradingview_scraper/orchestration/registry.py
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Type

@dataclass
class StageSpec:
    """Specification for an addressable stage."""
    id: str                          # e.g., "selection.ingestion"
    name: str                        # Human-readable name
    stage_class: Type                # The BasePipelineStage subclass
    input_schema: Dict[str, Any]     # JSON Schema for inputs
    output_schema: Dict[str, Any]    # JSON Schema for outputs
    tags: list = field(default_factory=list)  # ["selection", "data"]
    
class StageRegistry:
    """Global registry of addressable stages."""
    
    _stages: Dict[str, StageSpec] = {}
    
    @classmethod
    def register(cls, spec: StageSpec) -> None:
        cls._stages[spec.id] = spec
    
    @classmethod
    def get(cls, stage_id: str) -> StageSpec:
        if stage_id not in cls._stages:
            raise KeyError(f"Unknown stage: {stage_id}")
        return cls._stages[stage_id]
    
    @classmethod
    def list_stages(cls, tag: str = None) -> list:
        """List all stages, optionally filtered by tag."""
        stages = list(cls._stages.values())
        if tag:
            stages = [s for s in stages if tag in s.tags]
        return stages
```

### 3.2 Stage Registration (Decorator Pattern)

```python
# tradingview_scraper/pipelines/selection/stages/ingestion.py
from tradingview_scraper.orchestration.registry import StageRegistry, StageSpec

@StageRegistry.register
class IngestionStage(BasePipelineStage):
    """
    Stage ID: selection.ingestion
    Loads candidates and returns from data sources.
    """
    
    SPEC = StageSpec(
        id="selection.ingestion",
        name="Candidate Ingestion",
        stage_class=None,  # Set by decorator
        input_schema={
            "type": "object",
            "properties": {
                "candidates_path": {"type": "string"},
                "returns_path": {"type": "string"},
            },
            "required": ["candidates_path"]
        },
        output_schema={
            "type": "object",
            "properties": {
                "raw_pool_count": {"type": "integer"},
                "returns_shape": {"type": "array", "items": {"type": "integer"}}
            }
        },
        tags=["selection", "data", "ingestion"]
    )
    
    @property
    def name(self) -> str:
        return "Ingestion"
    
    def execute(self, context: SelectionContext) -> SelectionContext:
        # ... implementation
        return context
```

### 3.3 CLI Invocation

```bash
# Invoke a single stage directly
$ quant stage run selection.ingestion \
    --run-id abc123 \
    --param candidates_path=data/lakehouse/candidates.json \
    --param returns_path=data/lakehouse/returns.csv

# List available stages
$ quant stage list --tag selection
selection.ingestion     Candidate Ingestion
selection.features      Feature Engineering
selection.inference     MPS Inference
selection.clustering    Hierarchical Clustering
selection.policy        Policy Pruning
selection.synthesis     Strategy Synthesis

# Get stage schema
$ quant stage schema selection.ingestion
{
  "id": "selection.ingestion",
  "input_schema": {...},
  "output_schema": {...}
}
```

### 3.4 SDK Invocation (For Claude Skills)

```python
# tradingview_scraper/orchestration/sdk.py
from tradingview_scraper.orchestration.registry import StageRegistry
from tradingview_scraper.pipelines.selection.base import SelectionContext

class QuantSDK:
    """SDK for programmatic stage invocation."""
    
    @staticmethod
    def run_stage(
        stage_id: str,
        context: SelectionContext = None,
        params: dict = None,
        run_id: str = None
    ) -> SelectionContext:
        """
        Execute a single stage.
        
        Args:
            stage_id: Registered stage identifier (e.g., "selection.ingestion")
            context: Existing context (or None to create new)
            params: Stage-specific parameters
            run_id: Run identifier for tracking
        
        Returns:
            Updated context after stage execution.
        """
        spec = StageRegistry.get(stage_id)
        
        if context is None:
            context = SelectionContext(
                run_id=run_id or generate_run_id(),
                params=params or {}
            )
        
        # Instantiate and execute
        stage = spec.stage_class(**params) if params else spec.stage_class()
        return stage.execute(context)
    
    @staticmethod
    def run_pipeline(
        pipeline_id: str,
        stages: list = None,
        params: dict = None,
        run_id: str = None
    ) -> SelectionContext:
        """
        Execute a sequence of stages.
        
        Args:
            pipeline_id: Pipeline identifier (e.g., "selection.full")
            stages: Optional subset of stages to run
            params: Global parameters
            run_id: Run identifier
        
        Returns:
            Final context after all stages.
        """
        # ... implementation
        pass
```

### 3.5 Claude Skill Integration

**IMPORTANT**: Claude Code skills are NOT Python functions. They are **SKILL.md files** following the [Agent Skills](https://agentskills.io) open standard.

See `docs/design/claude_skills_v1.md` for the complete Claude Skills design.

**Key Insight**: Skills are Markdown instructions that Claude reads and follows. They invoke the `QuantSDK` via bundled scripts:

```
.claude/skills/quant-select/
├── SKILL.md                    # Instructions Claude reads
└── scripts/
    └── run_pipeline.py         # Script Claude executes
```

**Example SKILL.md**:

```markdown
---
name: quant-select
description: Run the quantitative asset selection pipeline. Use when the user wants to select assets for a portfolio.
compatibility: Claude Code
allowed-tools: Bash(python:*) Read
---

# Quant Selection Pipeline

## How to run

python scripts/quant_cli.py stage run selection.full \
  --profile $ARGUMENTS \
  --run-id $(date +%Y%m%d_%H%M%S)
```

**Invocation**:
- User: `/quant-select crypto_long`
- Model: Automatically when user says "select assets for crypto"
```

## 4. Ray Compute Engine Integration

### 4.1 Existing Pattern (Preserve & Extend)

The codebase already has Ray integration in:
- `scripts/parallel_orchestrator_ray.py`: Subprocess-based parallel sleeves
- `scripts/parallel_orchestrator_native.py`: Ray Actor-based isolation

### 4.2 Formalized Ray Task Wrapper

```python
# tradingview_scraper/orchestration/compute.py
import ray
from typing import Any, Dict

@ray.remote(num_cpus=1, memory=2 * 1024 * 1024 * 1024)
def execute_stage_remote(
    stage_id: str,
    context_dict: Dict[str, Any],
    params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Ray remote function to execute a stage in a worker.
    
    Args:
        stage_id: Registered stage identifier
        context_dict: Serialized SelectionContext
        params: Stage parameters
    
    Returns:
        Serialized updated context
    """
    from tradingview_scraper.orchestration.registry import StageRegistry
    from tradingview_scraper.pipelines.selection.base import SelectionContext
    
    # Deserialize context
    context = SelectionContext(**context_dict)
    
    # Get and execute stage
    spec = StageRegistry.get(stage_id)
    stage = spec.stage_class(**params) if params else spec.stage_class()
    result_context = stage.execute(context)
    
    # Serialize result (avoid non-serializable fields)
    return result_context.model_dump(exclude={"returns_df", "feature_store"})


class RayComputeEngine:
    """Manages Ray cluster and task submission."""
    
    def __init__(self, num_cpus: int = None):
        if not ray.is_initialized():
            ray.init(num_cpus=num_cpus, ignore_reinit_error=True)
    
    def map_stages(
        self,
        stage_id: str,
        contexts: list,
        params: dict = None
    ) -> list:
        """
        Execute same stage across multiple contexts in parallel.
        
        Use case: Run IngestionStage for multiple profiles simultaneously.
        """
        futures = [
            execute_stage_remote.remote(stage_id, ctx.model_dump(), params or {})
            for ctx in contexts
        ]
        return ray.get(futures)
    
    def execute_dag(
        self,
        dag: "PrefectFlow",
        params: dict = None
    ) -> Any:
        """
        Execute a Prefect DAG with Ray as the task runner.
        """
        from prefect_ray import RayTaskRunner
        
        with dag.with_options(task_runner=RayTaskRunner()):
            return dag.run(**params)
```

### 4.3 Parallel Sleeve Execution (Improved)

```python
# tradingview_scraper/orchestration/sleeve_executor.py
import ray
from typing import List, Dict

@ray.remote(num_cpus=2, memory=4 * 1024 * 1024 * 1024)
class SleeveActor:
    """
    Ray Actor for isolated sleeve execution.
    Each sleeve runs in its own actor with dedicated resources.
    """
    
    def __init__(self, profile: str, run_id: str):
        self.profile = profile
        self.run_id = run_id
        self._setup_environment()
    
    def _setup_environment(self):
        import os
        os.environ["TV_PROFILE"] = self.profile
        os.environ["TV_RUN_ID"] = self.run_id
        
        from tradingview_scraper.settings import get_settings
        get_settings.cache_clear()
        self.settings = get_settings()
    
    def execute(self) -> Dict:
        """Run the full production pipeline for this sleeve."""
        from tradingview_scraper.orchestration.sdk import QuantSDK
        
        context = QuantSDK.run_pipeline(
            "selection.full",
            params={"profile": self.profile},
            run_id=self.run_id
        )
        
        return {
            "profile": self.profile,
            "run_id": self.run_id,
            "winners_count": len(context.winners),
            "status": "success"
        }


def execute_sleeves_parallel(sleeves: List[Dict]) -> List[Dict]:
    """
    Execute multiple sleeves in parallel using Ray Actors.
    
    Args:
        sleeves: List of {"profile": str, "run_id": str}
    
    Returns:
        List of execution results
    """
    if not ray.is_initialized():
        ray.init(ignore_reinit_error=True)
    
    actors = [
        SleeveActor.remote(s["profile"], s["run_id"])
        for s in sleeves
    ]
    
    futures = [actor.execute.remote() for actor in actors]
    return ray.get(futures)
```

## 5. Prefect/DBOS Workflow Integration

### 5.1 Why Prefect?

| Feature | Current (Manual) | Prefect |
| :--- | :--- | :--- |
| **Retry** | None | Automatic with exponential backoff |
| **DAG Visualization** | None | Prefect UI |
| **Scheduling** | Cron + Make | Native scheduling |
| **State Persistence** | AuditLedger | Prefect Orion DB |
| **Observability** | Log files | Prometheus/Grafana integration |
| **Parameterization** | Env vars | Typed Parameters |

### 5.2 Flow Definition

```python
# tradingview_scraper/orchestration/flows/selection_flow.py
from prefect import flow, task
from prefect.tasks import task_input_hash
from datetime import timedelta

from tradingview_scraper.pipelines.selection.base import SelectionContext
from tradingview_scraper.orchestration.registry import StageRegistry

# Cache task results for 1 hour based on inputs
@task(
    retries=3,
    retry_delay_seconds=60,
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(hours=1)
)
def run_ingestion(run_id: str, params: dict) -> dict:
    """Prefect task wrapper for Ingestion stage."""
    from tradingview_scraper.orchestration.sdk import QuantSDK
    
    context = QuantSDK.run_stage(
        "selection.ingestion",
        params=params,
        run_id=run_id
    )
    return context.model_dump(exclude={"returns_df"})

@task(retries=2)
def run_feature_engineering(context_dict: dict, params: dict) -> dict:
    """Prefect task wrapper for Feature Engineering stage."""
    from tradingview_scraper.pipelines.selection.base import SelectionContext
    from tradingview_scraper.orchestration.sdk import QuantSDK
    
    context = SelectionContext(**context_dict)
    context = QuantSDK.run_stage(
        "selection.features",
        context=context,
        params=params
    )
    return context.model_dump(exclude={"returns_df", "feature_store"})

@task(retries=2)
def run_inference(context_dict: dict, params: dict) -> dict:
    """Prefect task wrapper for Inference stage."""
    # ... similar pattern

@task(retries=2)
def run_clustering(context_dict: dict, params: dict) -> dict:
    """Prefect task wrapper for Clustering stage."""
    # ... similar pattern

@task(retries=2)
def run_policy(context_dict: dict, params: dict) -> dict:
    """Prefect task wrapper for Policy stage."""
    # ... similar pattern

@task(retries=2)
def run_synthesis(context_dict: dict, params: dict) -> dict:
    """Prefect task wrapper for Synthesis stage."""
    # ... similar pattern


@flow(name="Selection Pipeline", log_prints=True)
def selection_flow(
    run_id: str,
    profile: str,
    candidates_path: str = "data/lakehouse/portfolio_candidates.json",
    returns_path: str = "data/lakehouse/portfolio_returns.csv"
) -> dict:
    """
    Full selection pipeline as a Prefect Flow.
    
    DAG:
        ingestion -> features -> inference -> clustering -> policy -> synthesis
    """
    params = {
        "profile": profile,
        "candidates_path": candidates_path,
        "returns_path": returns_path
    }
    
    # Execute DAG
    ctx = run_ingestion(run_id, params)
    ctx = run_feature_engineering(ctx, params)
    ctx = run_inference(ctx, params)
    ctx = run_clustering(ctx, params)
    ctx = run_policy(ctx, params)
    ctx = run_synthesis(ctx, params)
    
    return ctx
```

### 5.3 Meta-Portfolio Flow (Parallel Sleeves)

```python
# tradingview_scraper/orchestration/flows/meta_flow.py
from prefect import flow, task
from prefect_ray import RayTaskRunner
from typing import List, Dict

@task
def execute_sleeve(profile: str, run_id: str) -> dict:
    """Execute a single sleeve pipeline."""
    from tradingview_scraper.orchestration.sdk import QuantSDK
    
    context = QuantSDK.run_pipeline(
        "selection.full",
        params={"profile": profile},
        run_id=run_id
    )
    return {
        "profile": profile,
        "run_id": run_id,
        "winners": [w["symbol"] for w in context.winners],
        "weights": context.composition_map
    }

@task
def aggregate_sleeves(sleeve_results: List[dict]) -> dict:
    """Build meta-returns matrix from sleeve results."""
    from tradingview_scraper.pipelines.meta.aggregator import SleeveAggregator
    
    aggregator = SleeveAggregator()
    return aggregator.aggregate_from_results(sleeve_results)

@task
def optimize_meta(meta_returns: dict, profile: str) -> dict:
    """Run meta-portfolio optimization."""
    from tradingview_scraper.orchestration.sdk import QuantSDK
    
    return QuantSDK.run_stage(
        "meta.optimization",
        params={"meta_returns": meta_returns, "profile": profile}
    )

@task
def flatten_weights(meta_weights: dict, sleeve_weights: dict) -> dict:
    """Project meta-weights to atom-level."""
    from tradingview_scraper.pipelines.meta.flattener import WeightFlattener
    
    flattener = WeightFlattener()
    return flattener.flatten(meta_weights, sleeve_weights)


@flow(
    name="Meta-Portfolio Pipeline",
    task_runner=RayTaskRunner()  # Parallel execution via Ray
)
def meta_flow(
    meta_profile: str,
    sleeves: List[str],
    run_id: str = None
) -> dict:
    """
    Meta-portfolio pipeline with parallel sleeve execution.
    
    DAG:
        [sleeve_1, sleeve_2, ..., sleeve_n] -> aggregate -> optimize -> flatten
    """
    import datetime
    
    run_id = run_id or f"{meta_profile}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Parallel sleeve execution (mapped task)
    sleeve_futures = execute_sleeve.map(
        profile=sleeves,
        run_id=[f"{run_id}_{s}" for s in sleeves]
    )
    
    # Aggregate results
    meta_returns = aggregate_sleeves(sleeve_futures)
    
    # Optimize
    meta_weights = optimize_meta(meta_returns, meta_profile)
    
    # Flatten
    final_weights = flatten_weights(
        meta_weights,
        {r["profile"]: r["weights"] for r in sleeve_futures}
    )
    
    return {
        "run_id": run_id,
        "meta_weights": meta_weights,
        "flattened_weights": final_weights
    }
```

### 5.4 DBOS Alternative (Lightweight)

If Prefect is too heavy, DBOS provides a simpler transactional workflow:

```python
# tradingview_scraper/orchestration/flows/dbos_flow.py
from dbos import DBOS, SetWorkflowID

@DBOS.workflow()
def selection_workflow(run_id: str, profile: str) -> dict:
    """DBOS transactional workflow for selection pipeline."""
    
    ctx = DBOS.step(run_ingestion)(run_id, profile)
    ctx = DBOS.step(run_feature_engineering)(ctx)
    ctx = DBOS.step(run_inference)(ctx)
    ctx = DBOS.step(run_clustering)(ctx)
    ctx = DBOS.step(run_policy)(ctx)
    ctx = DBOS.step(run_synthesis)(ctx)
    
    return ctx

@DBOS.step()
def run_ingestion(run_id: str, profile: str) -> dict:
    """DBOS step for ingestion."""
    from tradingview_scraper.orchestration.sdk import QuantSDK
    
    context = QuantSDK.run_stage(
        "selection.ingestion",
        params={"profile": profile},
        run_id=run_id
    )
    return context.model_dump()
```

## 6. Updated Phase Roadmap

### Phase 340: Stage Registry & SDK (SDD & TDD)
- [ ] **Design**: Update this document with finalized interfaces.
- [ ] **Test (TDD)**: Create `tests/test_stage_registry.py`
    - Test stage registration
    - Test stage invocation via SDK
    - Test CLI `quant stage run` command
- [ ] **Implementation**:
    - Create `tradingview_scraper/orchestration/registry.py`
    - Create `tradingview_scraper/orchestration/sdk.py`
    - Create `scripts/quant_cli.py` with `stage` subcommand
- [ ] **Migration**: Add `SPEC` to existing stages

### Phase 345: Ray Compute Layer (SDD & TDD)
- [ ] **Design**: Finalize `RayComputeEngine` interface.
- [ ] **Test (TDD)**: Create `tests/test_ray_compute.py`
    - Test parallel stage execution
    - Test sleeve actor isolation
- [ ] **Implementation**:
    - Create `tradingview_scraper/orchestration/compute.py`
    - Create `tradingview_scraper/orchestration/sleeve_executor.py`
- [ ] **Migration**: Update `run_meta_pipeline.py` to use new executor

### Phase 350: Prefect Workflow Integration (SDD & TDD)
- [ ] **Design**: Define Flow/Task patterns.
- [ ] **Test (TDD)**: Create `tests/test_prefect_flows.py`
    - Test selection flow execution
    - Test retry behavior
- [ ] **Implementation**:
    - Create `tradingview_scraper/orchestration/flows/selection_flow.py`
    - Create `tradingview_scraper/orchestration/flows/meta_flow.py`
- [ ] **Migration**: Add Prefect deployment configs

### Phase 355: Claude Skill Integration (SDD & TDD)
- [ ] **Design**: Define skill interface contract.
- [ ] **Test (TDD)**: Create `tests/test_claude_skills.py`
    - Test skill invocation
    - Test parameter validation
- [ ] **Implementation**:
    - Create `tradingview_scraper/skills/selection_skill.py`
    - Create `tradingview_scraper/skills/backtest_skill.py`
- [ ] **Documentation**: Create skill usage guide

### Phase 360: Observability & Monitoring (Optional)
- [ ] **Design**: OpenTelemetry integration.
- [ ] **Implementation**:
    - Add tracing spans to stages
    - Prometheus metrics export
    - Grafana dashboard

## 7. TDD Test Plan

### 7.1 Stage Registry Tests
```python
# tests/test_stage_registry.py
import pytest

def test_stage_registration():
    from tradingview_scraper.orchestration.registry import StageRegistry, StageSpec
    
    spec = StageSpec(
        id="test.stage",
        name="Test Stage",
        stage_class=MockStage,
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        tags=["test"]
    )
    
    StageRegistry.register(spec)
    assert StageRegistry.get("test.stage") == spec

def test_stage_list_by_tag():
    from tradingview_scraper.orchestration.registry import StageRegistry
    
    stages = StageRegistry.list_stages(tag="selection")
    assert all("selection" in s.tags for s in stages)

def test_unknown_stage_raises():
    from tradingview_scraper.orchestration.registry import StageRegistry
    
    with pytest.raises(KeyError):
        StageRegistry.get("nonexistent.stage")
```

### 7.2 SDK Tests
```python
# tests/test_quant_sdk.py
import pytest

def test_sdk_run_stage():
    from tradingview_scraper.orchestration.sdk import QuantSDK
    
    context = QuantSDK.run_stage(
        "selection.ingestion",
        params={"candidates_path": "tests/fixtures/candidates.json"},
        run_id="test_run"
    )
    
    assert context.run_id == "test_run"
    assert len(context.raw_pool) > 0

def test_sdk_run_pipeline():
    from tradingview_scraper.orchestration.sdk import QuantSDK
    
    context = QuantSDK.run_pipeline(
        "selection.full",
        params={"profile": "test_profile"},
        run_id="test_run"
    )
    
    assert len(context.winners) >= 0  # May be 0 for test data
    assert len(context.audit_trail) > 0
```

### 7.3 Ray Compute Tests
```python
# tests/test_ray_compute.py
import pytest
import ray

@pytest.fixture(scope="module")
def ray_cluster():
    ray.init(num_cpus=2, ignore_reinit_error=True)
    yield
    ray.shutdown()

def test_parallel_stage_execution(ray_cluster):
    from tradingview_scraper.orchestration.compute import RayComputeEngine
    
    engine = RayComputeEngine()
    contexts = [create_test_context(f"run_{i}") for i in range(3)]
    
    results = engine.map_stages("selection.ingestion", contexts)
    
    assert len(results) == 3
    assert all(r["run_id"].startswith("run_") for r in results)
```

### 7.4 Prefect Flow Tests
```python
# tests/test_prefect_flows.py
import pytest
from prefect.testing.utilities import prefect_test_harness

def test_selection_flow():
    from tradingview_scraper.orchestration.flows.selection_flow import selection_flow
    
    with prefect_test_harness():
        result = selection_flow(
            run_id="test_flow",
            profile="test_profile",
            candidates_path="tests/fixtures/candidates.json",
            returns_path="tests/fixtures/returns.csv"
        )
    
    assert "winners" in result or "error" in result
```

## 8. File Structure

```
tradingview_scraper/
├── orchestration/                   # NEW: Orchestration Layer
│   ├── __init__.py
│   ├── registry.py                  # StageRegistry, StageSpec
│   ├── sdk.py                       # QuantSDK
│   ├── compute.py                   # RayComputeEngine
│   ├── sleeve_executor.py           # SleeveActor, execute_sleeves_parallel
│   └── flows/                       # Prefect Flows
│       ├── __init__.py
│       ├── selection_flow.py
│       ├── meta_flow.py
│       └── discovery_flow.py
├── skills/                          # NEW: Claude Skills
│   ├── __init__.py
│   ├── selection_skill.py
│   ├── backtest_skill.py
│   └── discovery_skill.py
scripts/
├── quant_cli.py                     # NEW: CLI entrypoint
```

## 9. Dependencies

Add to `pyproject.toml`:

```toml
[project.optional-dependencies]
orchestration = [
    "prefect>=3.0",
    "prefect-ray>=0.4",
    "ray[default]>=2.9",
    "dbos>=0.10",  # Optional lightweight alternative
]
```

## 10. Success Criteria

- [ ] All stages registered in `StageRegistry`
- [ ] `quant stage list` shows all available stages
- [ ] `quant stage run <stage_id>` executes successfully
- [ ] `QuantSDK.run_stage()` works programmatically
- [ ] Parallel sleeve execution uses Ray actors
- [ ] Selection pipeline runs as Prefect flow
- [ ] Claude skills can invoke stages via SDK
- [ ] All TDD tests pass
