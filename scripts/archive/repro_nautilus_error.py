import os
import sys

# Ensure project root in path
sys.path.append(os.getcwd())

try:
    from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue

    print("Testing Nautilus ID construction with simple symbol...")
    symbol_str = "TRXUSDT"
    venue_str = "BACKTEST"

    sym = Symbol(symbol_str)
    venue = Venue(venue_str)
    inst_id = InstrumentId(sym, venue)
    print(f"InstrumentId: {inst_id}")
    print(f"To list: {inst_id.to_list()}")


except Exception as e:
    print(f"CAUGHT ERROR: {e}")
    import traceback

    traceback.print_exc()
