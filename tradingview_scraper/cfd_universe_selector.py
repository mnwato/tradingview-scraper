"""CFD universe selector wrapper.

This module re-uses the generic FuturesUniverseSelector plumbing but should be
used with CFD-focused configs (e.g., OANDA). Screener fields are limited; prefer
Overview enrichment in configs where richer indicators are required.
"""

from __future__ import annotations

from tradingview_scraper.futures_universe_selector import (
    FuturesUniverseSelector,
    SelectorConfig,
    load_config,
    load_config_from_env,
)
from tradingview_scraper.futures_universe_selector import (
    main as _shared_main,
)

__all__ = [
    "FuturesUniverseSelector",
    "SelectorConfig",
    "load_config",
    "load_config_from_env",
    "main",
]


def main(argv=None) -> int:
    return _shared_main(argv)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
