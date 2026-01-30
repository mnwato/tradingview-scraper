import argparse
import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import pandas as pd
import requests

from tradingview_scraper.symbols.screener import Screener
from tradingview_scraper.symbols.utils import generate_user_agent

INDEX_MAP = {
    "sp500": "SPX",
    "nasdaq100": "NDX",
}

SLICKCHARTS_URLS = {
    "sp500": "https://www.slickcharts.com/sp500",
    "nasdaq100": "https://www.slickcharts.com/nasdaq100",
}

ETF_URLS = {
    "sp500": "https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf/1467271812596.ajax?fileType=csv&fileName=IVV_holdings&dataType=fund",
    "nasdaq100": "https://www.invesco.com/us/financial-professional/qqq-etf/holdings/",
}

PREF_EXCH = ["NASDAQ", "NYSE", "AMEX"]


def _load_symbol_map(parquet_path: Path) -> Dict[str, str]:
    if not parquet_path.exists():
        return {}
    df = pd.read_parquet(parquet_path, columns=["symbol", "base", "exchange"])
    df = df.dropna(subset=["symbol", "base"])
    # Normalize
    df["base"] = df["base"].str.upper()
    df["exchange"] = df["exchange"].str.upper()

    symbol_map: Dict[str, str] = {}
    for base, group in df.groupby("base"):
        base_key = str(base)
        # Prefer known US exchanges
        group_sorted = sorted(
            group.to_dict("records"),
            key=lambda r: PREF_EXCH.index(r.get("exchange", "")) if r.get("exchange", "") in PREF_EXCH else len(PREF_EXCH),
        )
        symbol_map[base_key] = group_sorted[0]["symbol"]
    return symbol_map


def _map_tickers_to_symbols(tickers: Iterable[str], symbol_map: Dict[str, str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for t in tickers:
        key = t.upper().strip()
        sym = symbol_map.get(key, key)
        if sym and sym not in seen:
            out.append(sym)
            seen.add(sym)
    return out


def fetch_index_constituents_screener(index_code: str, market: str = "america", page_size: int = 200, max_rows: int = 1500) -> List[str]:
    screener = Screener(export_result=False)
    filters = [
        {"left": "type", "operation": "in_range", "right": ["stock", "dr"]},
        {"left": "index", "operation": "equal", "right": index_code},
    ]
    columns = ["name", "close", "volume", "change", "market_cap_basic"]

    results: List[Dict] = []
    start = 0
    while True:
        resp = screener.screen(
            market=market,
            filters=filters,
            columns=columns,
            sort_by="volume",
            sort_order="desc",
            limit=page_size,
            range_start=start,
        )
        data = resp.get("data", []) if isinstance(resp, dict) else []
        if not data:
            break
        results.extend(data)
        if len(data) < page_size or len(results) >= max_rows:
            break
        start += page_size

    seen = set()
    deduped: List[str] = []
    for row in results:
        sym = (row.get("symbol") or "").strip().upper()
        if sym and sym not in seen:
            deduped.append(sym)
            seen.add(sym)
    return deduped


class _TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables: List[List[List[str]]] = []
        self.current_table: List[List[str]] = []
        self.current_row: List[str] = []
        self.current_cell: List[str] = []
        self._table_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._table_depth += 1
            if self._table_depth == 1:
                self.current_table = []
        if self._table_depth == 0:
            return
        if tag in {"td", "th"}:
            self.current_cell = []
        if tag == "tr":
            self.current_row = []

    def handle_endtag(self, tag):
        if self._table_depth == 0:
            return
        if tag in {"td", "th"}:
            text = "".join(self.current_cell).strip()
            self.current_row.append(text)
            self.current_cell = []
        if tag == "tr":
            if self.current_row:
                self.current_table.append(self.current_row)
            self.current_row = []
        if tag == "table":
            self._table_depth -= 1
            if self._table_depth == 0 and self.current_table:
                self.tables.append(self.current_table)
                self.current_table = []

    def handle_data(self, data):
        if self._table_depth > 0 and self.current_cell is not None:
            self.current_cell.append(data)


def _fetch_tables(url: str) -> List[List[List[str]]]:
    headers = {"User-Agent": generate_user_agent()}
    resp = requests.get(url, timeout=30, headers=headers)
    resp.raise_for_status()
    parser = _TableParser()
    parser.feed(resp.text)
    return parser.tables


def _extract_tickers_from_table(tables: List[List[List[str]]], key_words: List[str]) -> List[str]:
    for table in tables:
        if not table:
            continue
        header = table[0]
        sym_col = next((i for i, c in enumerate(header) if any(k in c.lower() for k in key_words)), None)
        if sym_col is None:
            continue
        tickers = [r[sym_col] for r in table[1:] if len(r) > sym_col]
        cleaned = [t.upper().replace(".", "-").strip() for t in tickers if t]
        if cleaned:
            return cleaned
    return []


def fetch_index_constituents_wikipedia(index_name: str) -> List[str]:
    if index_name == "sp500":
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = _fetch_tables(url)
        tickers = _extract_tickers_from_table(tables, ["symbol"])
        return tickers

    if index_name == "nasdaq100":
        url = "https://en.wikipedia.org/wiki/Nasdaq-100"
        tables = _fetch_tables(url)
        tickers = _extract_tickers_from_table(tables, ["ticker", "symbol"])
        return tickers

    return []


def fetch_index_constituents_slickcharts(index_name: str) -> List[str]:
    url = SLICKCHARTS_URLS.get(index_name)
    if not url:
        return []
    try:
        tables = _fetch_tables(url)
    except Exception:
        return []
    tickers = _extract_tickers_from_table(tables, ["ticker", "symbol"])
    return tickers


def fetch_index_constituents_etf(index_name: str) -> List[str]:
    url = ETF_URLS.get(index_name)
    if not url:
        return []
    headers = {"User-Agent": generate_user_agent()}
    try:
        # Some ETF pages return HTML; try to detect CSV by content-type
        resp = requests.get(url, timeout=30, headers=headers)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "").lower()
        if "text/csv" in content_type or resp.text.strip().startswith("Ticker"):
            from io import StringIO

            df = pd.read_csv(StringIO(resp.text))
        else:
            # Try to find a table in HTML
            tables = pd.read_html(resp.text)
            if not tables:
                return []
            df = tables[0]
        # Find ticker column
        col = next((c for c in df.columns if "ticker" in str(c).lower() or "symbol" in str(c).lower()), None)
        if col is None:
            return []
        tickers = df[col].astype(str).str.upper().str.replace(".", "-").str.strip().tolist()
        return [t for t in tickers if t]
    except Exception:
        return []


def write_symbol_file(path: Path, symbols: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(symbols)
    path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Update index constituent symbol lists from TradingView/Wikipedia")
    parser.add_argument("--sp500-file", default="data/index/sp500_symbols.txt", help="Output path for S&P 500 symbols")
    parser.add_argument("--nasdaq100-file", default="data/index/nasdaq100_symbols.txt", help="Output path for Nasdaq 100 symbols")
    parser.add_argument("--symbols-parquet", default="data/lakehouse/symbols.parquet", help="Path to symbols parquet for exchange prefixes")
    parser.add_argument("--page-size", type=int, default=200, help="Screener page size")
    parser.add_argument("--max-rows", type=int, default=1500, help="Max rows to fetch per index")
    args = parser.parse_args()

    outputs = {
        "sp500": Path(args.sp500_file),
        "nasdaq100": Path(args.nasdaq100_file),
    }

    symbol_map = _load_symbol_map(Path(args.symbols_parquet))

    for name, code in INDEX_MAP.items():
        symbols = fetch_index_constituents_screener(code, page_size=args.page_size, max_rows=args.max_rows)
        source = "screener"
        if not symbols:
            tickers = fetch_index_constituents_slickcharts(name)
            if tickers:
                symbols = _map_tickers_to_symbols(tickers, symbol_map)
                source = "slickcharts"
        if not symbols:
            tickers = fetch_index_constituents_etf(name)
            if tickers:
                symbols = _map_tickers_to_symbols(tickers, symbol_map)
                source = "etf_holdings"
        if not symbols:
            tickers = fetch_index_constituents_wikipedia(name)
            symbols = _map_tickers_to_symbols(tickers, symbol_map) if tickers else []
            source = "wikipedia"
        out_path = outputs[name]
        write_symbol_file(out_path, symbols)
        print(json.dumps({"index": name, "code": code, "count": len(symbols), "output": str(out_path), "source": source}, indent=2))


if __name__ == "__main__":
    main()
