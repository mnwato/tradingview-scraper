def summary():
    print("=== GENESIS TS FETCH REVIEW ===")
    print("1. Overview API: Checked standard fields (Perf.Y, etc).")
    print("   - Result: No explicit 'genesis_ts' or 'start_date' found.")

    print("2. Screener API: Probed for 'listed_date', 'ipo_date', etc.")
    print("   - Result: Fields not available or returned errors.")

    print("3. Streamer Method: Requesting max candles (e.g. 10000 1D).")
    print("   - Result: SUCCESS. Returns the first available candle timestamp.")

    print("\nConclusion: We must continue populating 'genesis_ts' via the Streamer method.")


if __name__ == "__main__":
    summary()
