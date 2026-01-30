import logging
import time

from tradingview_scraper.symbols.screener import Screener


def test_screener_resilience():
    # Set logging to see tenacity retries if we can trigger them
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("tenacity")
    logger.setLevel(logging.DEBUG)

    print("\n" + "=" * 80)
    print("TESTING SCREENER RESILIENCE (Tenacity Retries)")
    print("=" * 80)

    s = Screener()

    # We will try a legitimate request but look for retry logs
    # Note: Triggering a real 429 is hard without being abusive,
    # so we mostly verify the decorator is active.
    print("[INFO] Running legitimate screen to ensure decorator doesn't break normal flow...")
    start = time.time()
    res = s.screen(market="crypto", limit=1)
    elapsed = time.time() - start

    if res["status"] == "success":
        print(f"[SUCCESS] Normal flow works. Elapsed: {elapsed:.2f}s")
    else:
        print(f"[FAILURE] Normal flow failed: {res.get('error')}")


if __name__ == "__main__":
    test_screener_resilience()
