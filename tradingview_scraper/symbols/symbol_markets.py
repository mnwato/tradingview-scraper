"""Module providing a function to scrape markets/exchanges where a symbol is traded."""

from typing import List, Optional, Dict

import requests

from tradingview_scraper.symbols.utils import (
    save_csv_file,
    save_json_file,
    generate_user_agent,
)


class SymbolMarkets:
    """
    A class to scrape markets and exchanges where a symbol is traded from TradingView.

    This class provides functionality to find all markets/exchanges where a specific
    symbol is listed, including stock exchanges, crypto platforms, and derivative markets.

    Attributes:
        export_result (bool): Flag to determine if results should be exported to file.
        export_type (str): Type of export format ('json' or 'csv').
        headers (dict): HTTP headers for requests.

    Example:
        >>> markets = SymbolMarkets(export_result=True, export_type='json')
        >>> results = markets.scrape(symbol='AAPL')
        >>> print(results['data'])
    """

    # Scanner endpoints for different regions
    SCANNER_ENDPOINTS = {
        'global': 'https://scanner.tradingview.com/global/scan',
        'america': 'https://scanner.tradingview.com/america/scan',
        'crypto': 'https://scanner.tradingview.com/crypto/scan',
        'forex': 'https://scanner.tradingview.com/forex/scan',
        'cfd': 'https://scanner.tradingview.com/cfd/scan',
    }

    # Default columns to fetch
    DEFAULT_COLUMNS = [
        'name',
        'close',
        'change',
        'change_abs',
        'volume',
        'exchange',
        'type',
        'description',
        'currency',
        'market_cap_basic',
    ]

    def __init__(self, export_result: bool = False, export_type: str = 'json'):
        """
        Initialize the SymbolMarkets scraper.

        Args:
            export_result (bool): Whether to export results to a file. Defaults to False.
            export_type (str): Export format ('json' or 'csv'). Defaults to 'json'.
        """
        self.export_result = export_result
        self.export_type = export_type
        self.headers = {"User-Agent": generate_user_agent()}

    def _build_payload(
        self,
        symbol: str,
        columns: Optional[List[str]] = None,
        limit: int = 150
    ) -> Dict:
        """
        Build the payload for the scanner API.

        Args:
            symbol (str): The symbol to search for.
            columns (List[str], optional): Columns to retrieve.
            limit (int): Maximum number of results. Defaults to 150.

        Returns:
            dict: The scanner API payload.
        """
        if columns is None:
            columns = self.DEFAULT_COLUMNS

        payload = {
            "filter": [
                {"left": "name", "operation": "match", "right": symbol}
            ],
            "columns": columns,
            "options": {
                "lang": "en"
            },
            "range": [0, limit]
        }

        return payload

    def scrape(
        self,
        symbol: str,
        columns: Optional[List[str]] = None,
        scanner: str = 'global',
        limit: int = 150
    ) -> Dict:
        """
        Scrape all markets/exchanges where a symbol is traded.

        Args:
            symbol (str): The symbol to search for (e.g., 'AAPL', 'BTCUSD').
            columns (List[str], optional): Specific columns to retrieve. If None, uses default columns.
            scanner (str): Scanner endpoint to use ('global', 'america', 'crypto', 'forex', 'cfd').
                          Defaults to 'global' which searches across all markets.
            limit (int): Maximum number of results. Defaults to 150.

        Returns:
            dict: A dictionary containing:
                - status (str): 'success' or 'failed'
                - data (List[Dict]): List of markets where the symbol is traded
                - total (int): Total number of markets found
                - error (str): Error message if failed

        Example:
            >>> markets = SymbolMarkets()
            >>>
            >>> # Find all markets for Apple stock
            >>> aapl_markets = markets.scrape(symbol='AAPL')
            >>> print(f"AAPL is traded on {aapl_markets['total']} markets")
            >>>
            >>> # Find only US markets for Bitcoin
            >>> btc_us = markets.scrape(symbol='BTCUSD', scanner='america')
            >>>
            >>> # Custom columns
            >>> custom_markets = markets.scrape(
            ...     symbol='TSLA',
            ...     columns=['name', 'close', 'volume', 'exchange']
            ... )
        """
        # Validate scanner
        if scanner not in self.SCANNER_ENDPOINTS:
            return {
                'status': 'failed',
                'error': f"Unsupported scanner: {scanner}. "
                         f"Supported scanners: {', '.join(self.SCANNER_ENDPOINTS.keys())}"
            }

        # Build payload
        payload = self._build_payload(symbol=symbol, columns=columns, limit=limit)

        # Get scanner URL
        url = self.SCANNER_ENDPOINTS[scanner]

        try:
            # Make request
            response = requests.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                json_response = response.json()

                # Extract data
                data = json_response.get('data', [])

                if not data:
                    return {
                        'status': 'failed',
                        'error': f'No markets found for symbol: {symbol}'
                    }

                # Format the data
                formatted_data = []
                for item in data:
                    symbol_data = item.get('d', [])
                    if len(symbol_data) > 0:
                        # Map data to field names
                        formatted_item = {
                            'symbol': item.get('s', ''),
                        }

                        # Map each field value
                        field_list = columns if columns else self.DEFAULT_COLUMNS
                        for idx, field in enumerate(field_list):
                            if idx < len(symbol_data):
                                formatted_item[field] = symbol_data[idx]

                        formatted_data.append(formatted_item)

                # Export if requested
                if self.export_result:
                    self._export(
                        data=formatted_data,
                        symbol=symbol,
                        data_category='markets'
                    )

                return {
                    'status': 'success',
                    'data': formatted_data,
                    'total': len(formatted_data),
                    'totalCount': json_response.get('totalCount', len(formatted_data))
                }
            else:
                return {
                    'status': 'failed',
                    'error': f'HTTP {response.status_code}: {response.text}'
                }

        except requests.RequestException as e:
            return {
                'status': 'failed',
                'error': f'Request failed: {str(e)}'
            }
        except Exception as e:
            return {
                'status': 'failed',
                'error': f'Request failed: {str(e)}'
            }

    def _export(
        self,
        data: List[Dict],
        symbol: Optional[str] = None,
        data_category: Optional[str] = None
    ) -> None:
        """
        Export scraped data to file.

        Args:
            data (List[Dict]): The data to export.
            symbol (str, optional): Symbol identifier for the filename.
            data_category (str, optional): Data category for the filename.
        """
        if self.export_type == 'json':
            save_json_file(data=data, symbol=symbol, data_category=data_category)
        elif self.export_type == 'csv':
            save_csv_file(data=data, symbol=symbol, data_category=data_category)
