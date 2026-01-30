import json
import time

from tradingview_scraper.symbols.stream import RealTimeData


def research_raw_packets():
    symbols = ["BINANCE:BTCUSDT", "FX_IDC:EURUSD"]
    rt = RealTimeData()
    gen = rt.get_latest_trade_info(exchange_symbol=symbols)

    print(f"[INFO] Researching raw packets for {symbols}...")
    start_time = time.time()
    packets_captured = 0
    max_packets = 20

    output_file = "docs/raw_packet_research.json"
    captured = []

    try:
        for packet in gen:
            if isinstance(packet, dict) and packet.get("m") != "h":
                captured.append(packet)
                packets_captured += 1
                print(f"Captured packet {packets_captured}/{max_packets}: {packet.get('m')}")

            if packets_captured >= max_packets or (time.time() - start_time > 30):
                break
    except Exception as e:
        print(f"[ERROR] Stream interrupted: {e}")

    with open(output_file, "w") as f:
        json.dump(captured, f, indent=2)

    print(f"\n[DONE] Captured {packets_captured} packets to {output_file}")


if __name__ == "__main__":
    research_raw_packets()
