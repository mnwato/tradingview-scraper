import time

from locust import User, between, task

from tradingview_scraper.symbols.stream.persistent_loader import PersistentDataLoader

# We must avoid hammering the real API too much, so we'll simulate
# the logic with a slight delay if we wanted to test purely internal scalability.
# But here we want to test real connection throughput.


class LakehouseIngestorUser(User):
    wait_time = between(1, 5)  # Simulate real-world intervals between syncs

    def on_start(self):
        self.loader = PersistentDataLoader(lakehouse_path="data/locust_lakehouse")
        self.symbols = ["BINANCE:BTCUSDT", "BINANCE:ETHUSDT", "BINANCE:SOLUSDT", "BINANCE:XRPUSDT", "BINANCE:ADAUSDT"]

    @task
    def sync_random_symbol(self):
        symbol = self.symbols[int(time.time()) % len(self.symbols)]
        start_time = time.time()
        try:
            # We fetch 100 candles to keep it light but verify connection
            new_records = self.loader.sync(symbol, interval="1h", depth=100)
            total_time = (time.time() - start_time) * 1000
            # Report success to locust
            self.environment.events.request.fire(
                request_type="WS_SYNC",
                name=symbol,
                response_time=total_time,
                response_length=new_records,
                exception=None,
            )
        except Exception as e:
            total_time = (time.time() - start_time) * 1000
            self.environment.events.request.fire(
                request_type="WS_SYNC",
                name=symbol,
                response_time=total_time,
                response_length=0,
                exception=e,
            )

    @task(3)  # More frequent reads from cache
    def load_from_cache(self):
        symbol = self.symbols[int(time.time()) % len(self.symbols)]
        start_time = time.time()
        try:
            # Load last 24h
            df = self.loader.load(symbol, "2025-12-19", "2025-12-20", interval="1h")
            total_time = (time.time() - start_time) * 1000
            self.environment.events.request.fire(
                request_type="CACHE_LOAD",
                name=symbol,
                response_time=total_time,
                response_length=len(df),
                exception=None,
            )
        except Exception as e:
            total_time = (time.time() - start_time) * 1000
            self.environment.events.request.fire(
                request_type="CACHE_LOAD",
                name=symbol,
                response_time=total_time,
                response_length=0,
                exception=e,
            )
