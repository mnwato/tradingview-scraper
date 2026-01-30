from prefect import flow, task

from tradingview_scraper.orchestration.sdk import QuantSDK
from tradingview_scraper.pipelines.selection.base import SelectionContext


@task(name="Ingestion", retries=2)
def task_ingestion(run_id: str, profile: str, **kwargs) -> SelectionContext:
    return QuantSDK.run_stage("foundation.ingest", run_id=run_id, profile=profile, **kwargs)


@task(name="Feature Engineering")
def task_features(context: SelectionContext) -> SelectionContext:
    return QuantSDK.run_stage("foundation.features", context=context)


@task(name="Inference")
def task_inference(context: SelectionContext) -> SelectionContext:
    return QuantSDK.run_stage("alpha.inference", context=context)


@task(name="Clustering")
def task_clustering(context: SelectionContext) -> SelectionContext:
    return QuantSDK.run_stage("alpha.clustering", context=context)


@task(name="Policy")
def task_policy(context: SelectionContext, relaxation_stage: int) -> SelectionContext:
    # Update context params for relaxation stage
    context.params["relaxation_stage"] = relaxation_stage
    return QuantSDK.run_stage("alpha.policy", context=context)


@task(name="Synthesis")
def task_synthesis(context: SelectionContext) -> SelectionContext:
    return QuantSDK.run_stage("alpha.synthesis", context=context)


@flow(name="Selection Flow")
def run_selection_flow(profile: str, run_id: str, **kwargs):
    """
    Prefect Flow implementing the HTR selection process.
    """
    ctx = task_ingestion(run_id, profile, **kwargs)
    ctx = task_features(ctx)
    ctx = task_inference(ctx)
    ctx = task_clustering(ctx)

    # HTR Loop (Simplified for Prefect DAG visibility)
    # Note: In a real HTR loop, we might break early.
    # Prefect 3.x supports conditional tasks.

    for stage in [1, 2, 3, 4]:
        ctx = task_policy(ctx, relaxation_stage=stage)
        if len(ctx.winners) >= 15:
            break

    ctx = task_synthesis(ctx)
    return ctx
