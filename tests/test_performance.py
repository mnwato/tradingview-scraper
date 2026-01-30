import os
import shutil

import pytest

pytest.importorskip("pytest_benchmark", reason="pytest-benchmark not installed")

from tradingview_scraper.symbols.stream.lakehouse import LakehouseStorage
from tradingview_scraper.symbols.stream.persistent_loader import PersistentDataLoader


@pytest.fixture
def temp_lakehouse():
    path = "data/perf_test_lakehouse"
    os.makedirs(path, exist_ok=True)
    yield path
    if os.path.exists(path):
        shutil.rmtree(path)


def test_storage_write_performance(benchmark, temp_lakehouse):
    storage = LakehouseStorage(base_path=temp_lakehouse)
    # Generate 10,000 dummy candles
    candles = [{"timestamp": i, "open": i, "high": i + 1, "low": i - 1, "close": i, "volume": 100} for i in range(10000)]

    def do_write():
        storage.save_candles("BINANCE:PERFTEST", "1m", candles)

    benchmark(do_write)


def test_storage_read_performance(benchmark, temp_lakehouse):
    storage = LakehouseStorage(base_path=temp_lakehouse)
    candles = [{"timestamp": i, "close": i} for i in range(10000)]
    storage.save_candles("BINANCE:PERFTEST", "1m", candles)

    def do_read():
        # Load a range in the middle
        return storage.load_candles("BINANCE:PERFTEST", "1m", start_ts=2000, end_ts=8000)

    res = benchmark(do_read)
    assert len(res) > 0


def test_persistent_loader_fallback_overhead(benchmark, temp_lakehouse):
    # This benchmarks the logic overhead before/after storage check
    loader = PersistentDataLoader(lakehouse_path=temp_lakehouse)

    def check_logic():
        # Just check empty storage speed
        return loader.load("BINANCE:EMPTY", "2025-01-01", "2025-01-02", "1h")

    benchmark(check_logic)
