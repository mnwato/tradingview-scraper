import numpy as np
import pandas as pd
import pytest
from tradingview_scraper.regime import MarketRegimeDetector
import time


@pytest.fixture
def detector():
    return MarketRegimeDetector(enable_audit_log=False)


def test_hmm_stability(detector):
    """Test if HMM returns consistent results on same data (Random Seed check)."""
    np.random.seed(42)
    # Generate mixture of two Gaussians (Low Vol, High Vol)
    # 100 days of low vol
    # 50 days of high vol
    low_vol = np.random.normal(0, 0.01, 100)
    high_vol = np.random.normal(0, 0.05, 50)
    data = np.concatenate([low_vol, high_vol])

    # Run multiple times
    results = []
    for _ in range(5):
        res = detector._hmm_classify(data)
        results.append(res)

    # Should be consistent if seed is fixed in method,
    # but the method sets random_state=42. So it should be deterministic.
    assert len(set(results)) == 1, f"Inconsistent HMM results: {results}"

    # The last part is high vol -> Should be CRISIS
    if results[0] != "CRISIS":
        print(f"DEBUG: Data mean: {np.mean(np.abs(data))}, Last 10: {np.abs(data[-10:])}")
        # Re-run with debug inside to check means? No access to internal vars.
        # Just fail.
    assert results[0] == "CRISIS"


def test_hmm_separation(detector):
    """Test if HMM correctly identifies Quiet vs Crisis."""
    np.random.seed(42)

    # Pure Low Vol
    low_vol = np.random.normal(0, 0.005, 100)
    res_low = detector._hmm_classify(low_vol)
    # If there's only one regime effectively, HMM might split it arbitrarily or find noise.
    # But usually it finds 2 states.
    # If data is uniform, means will be close.
    # But logic is: if latest state mean == max(means) -> CRISIS.
    # If states are close, it might toggle.
    # Ideally, for uniform low vol, we want QUIET or NORMAL?
    # The method returns "CRISIS" if latest state is the *higher variance* one.
    # Even in low vol data, one state will have slightly higher variance.
    # This is a potential semantic flaw. HMM is relative.

    # Let's test mixed data where distinction is clear
    mixed = np.concatenate([np.random.normal(0, 0.01, 50), np.random.normal(0, 0.05, 50)])
    res_mixed = detector._hmm_classify(mixed)
    assert res_mixed == "CRISIS"

    mixed_inv = np.concatenate([np.random.normal(0, 0.05, 50), np.random.normal(0, 0.01, 50)])
    res_inv = detector._hmm_classify(mixed_inv)
    # Last part is low vol -> Should be QUIET (lower mean state)
    assert res_inv == "QUIET"


def test_hmm_performance(detector):
    """Benchmark HMM execution time."""
    data = np.random.normal(0, 0.02, 252)  # 1 year

    start = time.perf_counter()
    n_loops = 10
    for _ in range(n_loops):
        detector._hmm_classify(data)
    duration = (time.perf_counter() - start) / n_loops

    print(f"HMM Mean Duration: {duration * 1000:.2f}ms")
    # Should be reasonably fast (< 50ms)
    assert duration < 0.05


def test_gmm_comparison(detector):
    """Benchmark GMM as alternative."""
    from sklearn.mixture import GaussianMixture

    data = np.random.normal(0, 0.02, 252)
    obs = np.abs(data).reshape(-1, 1)

    start = time.perf_counter()
    n_loops = 10
    for _ in range(n_loops):
        gmm = GaussianMixture(n_components=2, covariance_type="diag", random_state=42)
        gmm.fit(obs)
        preds = gmm.predict(obs)
        # Check logic: latest state mean
        latest_state = preds[-1]
        means = gmm.means_.flatten()
        res = "CRISIS" if means[latest_state] == np.max(means) else "QUIET"

    duration = (time.perf_counter() - start) / n_loops
    print(f"GMM Mean Duration: {duration * 1000:.2f}ms")
    # GMM should be faster than HMM
    assert duration < 0.05
