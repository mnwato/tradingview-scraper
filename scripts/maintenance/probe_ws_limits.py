import logging
import threading
import time

from tradingview_scraper.symbols.stream import StreamHandler

# Suppress debug logs for this test
logging.getLogger().setLevel(logging.INFO)


def test_parallel_websockets():
    max_conns = 10
    connections = []

    print("\n" + "=" * 80)
    print(f"PROBING PARALLEL WEBSOCKET LIMITS (Max {max_conns})")
    print("=" * 80)

    def connect_worker(idx):
        try:
            print(f"  [Worker {idx}] Connecting...")
            sh = StreamHandler("wss://data.tradingview.com/socket.io/websocket?from=chart%2FVEPYsueI%2F&type=chart")
            connections.append(sh)
            print(f"  [Worker {idx}] SUCCESS")
        except Exception as e:
            print(f"  [Worker {idx}] FAILED: {e}")

    threads = []
    for i in range(max_conns):
        t = threading.Thread(target=connect_worker, args=(i,))
        threads.append(t)
        t.start()
        time.sleep(0.5)

    for t in threads:
        t.join()

    print(f"\nTotal Active Connections: {len(connections)}/{max_conns}")

    # Cleanup
    for c in connections:
        try:
            c.close()
        except Exception:
            pass


if __name__ == "__main__":
    test_parallel_websockets()
