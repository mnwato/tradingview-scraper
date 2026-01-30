"""
MT5 Data Client.

Responsible for fetching market data from MetaTrader 5.
"""

import logging
from typing import Any, Dict, Optional

import pandas as pd

from tradingview_scraper.execution.mt5.client import MT5Client

logger = logging.getLogger(__name__)


class MT5DataClient:
    """
    Responsible for fetching historical and real-time market data.
    """

    def __init__(self, mt5_client: MT5Client):
        self.client = mt5_client

    def get_latest_tick(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetches the latest tick for a symbol.

        Args:
            symbol: The symbol identifier.

        Returns:
            Dict containing tick data or None if failed.
        """
        if not self.client.check_connected():
            logger.error("MT5 Client not connected.")
            return None

        mt5 = self.client.lib
        tick = mt5.symbol_info_tick(symbol)

        if tick is None:
            # Check if symbol exists or is selected
            if not mt5.symbol_select(symbol, True):
                logger.warning(f"Symbol {symbol} not found or could not be selected.")
                return None

            # Retry
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                logger.warning(f"Failed to get tick for {symbol} after selection.")
                return None

        return tick._asdict()

    def get_history(self, symbol: str, timeframe: str, count: int = 1000) -> Optional[pd.DataFrame]:
        """
        Fetches historical bars.

        Args:
            symbol: Symbol identifier.
            timeframe: Timeframe string (e.g., "1m", "1h", "D1").
            count: Number of bars to fetch.

        Returns:
            DataFrame with OHLCV data or None.
        """
        if not self.client.check_connected():
            return None

        mt5 = self.client.lib
        tf_constant = self._map_timeframe(timeframe)

        if tf_constant is None:
            logger.error(f"Invalid timeframe: {timeframe}")
            return None

        rates = mt5.copy_rates_from_pos(symbol, tf_constant, 0, count)

        if rates is None:
            logger.warning(f"Failed to get history for {symbol}")
            return None

        if len(rates) == 0:
            return pd.DataFrame()

        # Convert to DataFrame
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")

        return df

    def _map_timeframe(self, tf: str) -> Optional[int]:
        """Maps string timeframe to MT5 constant."""
        mt5 = self.client.lib
        tf = tf.upper()

        mapping = {
            "1M": mt5.TIMEFRAME_M1,
            "5M": mt5.TIMEFRAME_M5,
            "15M": mt5.TIMEFRAME_M15,
            "30M": mt5.TIMEFRAME_M30,
            "1H": mt5.TIMEFRAME_H1,
            "4H": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1,
            "1D": mt5.TIMEFRAME_D1,
            "W1": mt5.TIMEFRAME_W1,
            "1W": mt5.TIMEFRAME_W1,
            "MN1": mt5.TIMEFRAME_MN1,
        }

        return mapping.get(tf)
