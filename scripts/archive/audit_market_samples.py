import glob
import json
import os
from datetime import datetime


def audit_market_samples():
    sample_files = glob.glob("export/ohlc_*.json")
    if not sample_files:
        print("[ERROR] No sample files found in export/")
        return

    print("\n" + "=" * 100)
    print("DATALOADER MULTI-MARKET QUALITY AUDIT")
    print("=" * 100)
    print(f"{'Market/Symbol':<20} | {'Count':<6} | {'Gap Detected':<8} | {'First Date':<20} | {'Last Date':<20}")
    print("-" * 100)

    for f in sorted(sample_files):
        with open(f, "r") as j:
            data = json.load(j)
            if not data:
                continue

            symbol = os.path.basename(f).replace("ohlc_", "").replace(".json", "").upper()
            count = len(data)

            # Check for gaps (expecting approx 1h interval)
            # If diff > 1.5 hours, we flag a gap (could be expected for stocks)
            gaps = 0
            for i in range(1, len(data)):
                diff = data[i]["timestamp"] - data[i - 1]["timestamp"]
                if diff > 5400:  # 1.5 hours
                    gaps += 1

            first = datetime.fromtimestamp(data[0]["timestamp"]).strftime("%Y-%m-%d %H:%M")
            last = datetime.fromtimestamp(data[-1]["timestamp"]).strftime("%Y-%m-%d %H:%M")

            gap_str = "YES" if gaps > 0 else "NO"
            print(f"{symbol:<20} | {count:<6} | {gap_str:<12} | {first:<20} | {last:<20}")

    print("\n[RESEARCH NOTE] Gaps in Stocks/Indices are EXPECTED due to market close.")
    print("Crypto (BTCUSDT) should show NO gaps in a healthy stream.")


if __name__ == "__main__":
    audit_market_samples()
