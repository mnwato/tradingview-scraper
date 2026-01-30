from tradingview_scraper.symbols.stream.metadata import MetadataCatalog

catalog = MetadataCatalog()
df = catalog._df
active_df = df[df["valid_until"].isna()]
row = active_df[active_df["symbol"] == "BINANCE:1000BONKUSDT.P"]
if not row.empty:
    print(f"Genesis TS: {row.iloc[0]['genesis_ts']}")
else:
    print("Symbol not found")
