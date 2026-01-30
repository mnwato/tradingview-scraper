from typing import Dict, List, Optional

from prefect import flow, task

from tradingview_scraper.orchestration.compute import RayComputeEngine
from tradingview_scraper.orchestration.sdk import QuantSDK


@task(name="Execute Sleeves (Ray)")
def task_execute_sleeves(sleeves: List[Dict[str, str]]) -> List[Dict]:
    """Execute strategy sleeves in parallel using Ray."""
    with RayComputeEngine() as engine:
        return engine.execute_sleeves(sleeves)


@task(name="Meta Aggregation")
def task_aggregation(meta_profile: str, run_id: str, profiles: List[str]):
    return QuantSDK.run_stage("meta.aggregation", meta_profile=meta_profile, run_id=run_id, profiles=profiles)


@task(name="Meta Optimization")
def task_optimization(meta_profile: str, run_id: str):
    return QuantSDK.run_stage("risk.optimize_meta", meta_profile=meta_profile, run_id=run_id)


@task(name="Weight Flattening")
def task_flattening(meta_profile: str, run_id: str, profiles: List[str]):
    results = []
    for prof in profiles:
        res = QuantSDK.run_stage("risk.flatten_meta", meta_profile=meta_profile, run_id=run_id, profile=prof)
        results.append(res)
    return results


@task(name="Forensic Report")
def task_reporting(meta_profile: str, run_id: str, profiles: List[str]):
    return QuantSDK.run_stage("risk.report_meta", meta_profile=meta_profile, run_id=run_id, profiles=profiles)


@flow(name="Meta Portfolio Flow")
def run_meta_flow(meta_profile: str, run_id: str, sleeves: Optional[List[Dict[str, str]]] = None, profiles: Optional[List[str]] = None):
    """
    Prefect Flow for Meta-Portfolio aggregation and optimization.
    """
    # 1. Execute Sleeves if provided
    if sleeves:
        task_execute_sleeves(sleeves)

    target_profiles = profiles or ["hrp", "min_variance", "equal_weight"]

    # 2. Pipeline Stages
    task_aggregation(meta_profile, run_id, target_profiles)
    task_optimization(meta_profile, run_id)
    task_flattening(meta_profile, run_id, target_profiles)
    task_reporting(meta_profile, run_id, target_profiles)

    return True
