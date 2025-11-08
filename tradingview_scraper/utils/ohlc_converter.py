from typing import List, Dict
import pkg_resources
import logging
import json
import os


logger = logging.getLogger(__name__)

class OHLCVConverter:
    def __init__(self, target_timeframe: str):
        
        
        self.timeframes: dict = self._load_timeframes()
        self._validate_timeframe(target_timeframe)
        self.target_interval = self._timeframe_to_minutes(timeframe=target_timeframe)


    def _timeframe_to_minutes(self, timeframe: str) -> int:
        """
        Convert a given timeframe string to its equivalent in minutes.

        Args:
            timeframe (str): The timeframe to convert (e.g., '1m', '1h', '1d', '1w', '1M').

        Returns:
            int: The equivalent value in minutes or None if conversion is not possible.
        """
        conversion_map = {
            "1m": 1,
            "5m": 5,
            "15m": 15,
            "30m": 30,
            "1h": 60,
            "2h": 120,
            "4h": 240,
            "1d": 1440,
            "1w": 10080,
            "1M": 302400
        }

        return conversion_map.get(timeframe)


    def _validate_timeframe(self, timeframe: str) -> None:
        """Validates the specified timeframe against the list of supported timeframes.

        Args:
            timeframe (str): The timeframe to validate.

        Raises:
            ValueError: If the specified timeframe is not in the list of supported timeframes.
        """
        valid_timeframes = self.timeframes.keys()
        if timeframe not in valid_timeframes:
            raise ValueError("This timeframe is not supported! Please check the list of supported timeframes.")


    def convert(self, data: List[Dict]) -> List[Dict]:
        if self.target_interval==1:
            return data
        if self.target_interval < 1:
            raise ValueError("Target interval must be 1 minute or greater")

        sorted_data = sorted(data, key=lambda x: x['timestamp'])
        resampled_data = []
        current_group = None
        count = 0
        idx = 0

        for item in sorted_data:
            if count == 0:
                # Start a new group
                current_group = {'timestamp': item['timestamp']}

                # Initialize OHLCV if present
                if 'open' in item: current_group['open'] = item['open']
                if 'high' in item: current_group['high'] = item['high']
                if 'low' in item: current_group['low'] = item['low']
                if 'close' in item: current_group['close'] = item['close']
                if 'volume' in item: current_group['volume'] = item['volume']

                # Add any other keys present in the item
                for key, value in item.items():
                    if key not in current_group:
                        current_group[key] = value

                count = 1
            else:
                # Update existing group
                if 'high' in current_group and 'high' in item:
                    current_group['high'] = max(current_group['high'], item['high'])
                if 'low' in current_group and 'low' in item:
                    current_group['low'] = min(current_group['low'], item['low'])
                if 'close' in item:
                    current_group['close'] = item['close']
                if 'volume' in current_group and 'volume' in item:
                    current_group['volume'] += item['volume']

                # Update other keys by setting their latest value
                for key, value in item.items():
                    if key not in {'timestamp', 'open', 'high', 'low', 'close', 'volume'}:
                        current_group[key] = value

                count += 1

            # Finalize the group if it reaches the target interval
            if count == self.target_interval:
                current_group['index'] = idx
                resampled_data.append(current_group)
                count = 0
                idx += 1

        # Add the last group if it exists
        if count > 0:
            current_group['index'] = idx
            resampled_data.append(current_group)

        return resampled_data


    def _load_timeframes(self) -> dict:
        """Load timeframes from a specified file.

        Returns:
            dict: A dictionary of timeframes loaded from the file. Returns a dict with '1d' as default.
        """
        path = pkg_resources.resource_filename('tradingview_scraper', 'data/timeframes.json')
        
        if not os.path.exists(path):
            logger.error("[ERROR] Timeframe file not found at %s.", path)
            return {"1d": None}

        try:
            with open(path, 'r', encoding='utf-8') as f:
                timeframes = json.load(f)
            return timeframes.get('indicators', {"1d": None})
        except (IOError, json.JSONDecodeError) as e:
            logger.error("[ERROR] Error reading timeframe file: %s", e)
            return {"1d": None}
