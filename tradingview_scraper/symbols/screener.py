"""Module providing a function to screen stocks, crypto, forex, and other markets with custom filters."""

from typing import List, Optional, Dict, Any

import requests

from tradingview_scraper.symbols.utils import (
    save_csv_file,
    save_json_file,
    generate_user_agent,
)


class Screener:
    """
    A class to screen financial instruments from TradingView with custom filters.

    This class provides functionality to screen stocks, crypto, forex, bonds,
    and futures with various technical and fundamental filters.

    Attributes:
        export_result (bool): Flag to determine if results should be exported to file.
        export_type (str): Type of export format ('json' or 'csv').
        headers (dict): HTTP headers for requests.

    Example:
        >>> screener = Screener(export_result=True, export_type='json')
        >>> results = screener.screen(
        ...     market='america',
        ...     filters=[{'left': 'close', 'operation': 'greater', 'right': 100}],
        ...     columns=['name', 'close', 'volume', 'market_cap_basic']
        ... )
        >>> print(results['data'])
    """

    # Supported markets
    SUPPORTED_MARKETS = {
        'america': 'https://scanner.tradingview.com/america/scan',
        'australia': 'https://scanner.tradingview.com/australia/scan',
        'canada': 'https://scanner.tradingview.com/canada/scan',
        'germany': 'https://scanner.tradingview.com/germany/scan',
        'india': 'https://scanner.tradingview.com/india/scan',
        'israel': 'https://scanner.tradingview.com/israel/scan',
        'italy': 'https://scanner.tradingview.com/italy/scan',
        'luxembourg': 'https://scanner.tradingview.com/luxembourg/scan',
        'mexico': 'https://scanner.tradingview.com/mexico/scan',
        'spain': 'https://scanner.tradingview.com/spain/scan',
        'turkey': 'https://scanner.tradingview.com/turkey/scan',
        'uk': 'https://scanner.tradingview.com/uk/scan',
        'crypto': 'https://scanner.tradingview.com/crypto/scan',
        'forex': 'https://scanner.tradingview.com/forex/scan',
        'cfd': 'https://scanner.tradingview.com/cfd/scan',
        'futures': 'https://scanner.tradingview.com/futures/scan',
        'bonds': 'https://scanner.tradingview.com/bonds/scan',
        'global': 'https://scanner.tradingview.com/global/scan',
    }

    # Common filter operations
    OPERATIONS = [
        'greater',
        'less',
        'egreater',  # equal or greater
        'eless',     # equal or less
        'equal',
        'nequal',    # not equal
        'in_range',
        'not_in_range',
        'above',
        'below',
        'crosses',
        'crosses_above',
        'crosses_below',
        'has',
        'has_none_of',
    ]

    # Default columns for stock screener
    DEFAULT_STOCK_COLUMNS = [
        'name',
        'close',
        'change',
        'change_abs',
        'volume',
        'Recommend.All',
        'market_cap_basic',
        'price_earnings_ttm',
        'earnings_per_share_basic_ttm',
    ]

    # Default columns for crypto screener
    DEFAULT_CRYPTO_COLUMNS = [
        'name',
        'close',
        'change',
        'change_abs',
        'volume',
        'market_cap_calc',
        'Recommend.All',
    ]

    # Default columns for forex screener
    DEFAULT_FOREX_COLUMNS = [
        'name',
        'close',
        'change',
        'change_abs',
        'Recommend.All',
    ]

    def __init__(self, export_result: bool = False, export_type: str = 'json'):
        """
        Initialize the Screener.

        Args:
            export_result (bool): Whether to export results to a file. Defaults to False.
            export_type (str): Export format ('json' or 'csv'). Defaults to 'json'.
        """
        self.export_result = export_result
        self.export_type = export_type
        self.headers = {"User-Agent": generate_user_agent()}

    def _validate_market(self, market: str) -> None:
        """
        Validate if the market is supported.

        Args:
            market (str): The market to validate.

        Raises:
            ValueError: If the market is not supported.
        """
        if market not in self.SUPPORTED_MARKETS:
            raise ValueError(
                f"Unsupported market: {market}. "
                f"Supported markets: {', '.join(self.SUPPORTED_MARKETS.keys())}"
            )

    def _get_default_columns(self, market: str) -> List[str]:
        """
        Get default columns based on market type.

        Args:
            market (str): The market type.

        Returns:
            List[str]: Default columns for the market.
        """
        if market == 'crypto':
            return self.DEFAULT_CRYPTO_COLUMNS
        elif market == 'forex':
            return self.DEFAULT_FOREX_COLUMNS
        else:
            return self.DEFAULT_STOCK_COLUMNS

    def _build_payload(
        self,
        filters: Optional[List[Dict[str, Any]]] = None,
        columns: Optional[List[str]] = None,
        market: str = 'america',
        sort: Optional[Dict[str, str]] = None,
        range_limit: tuple = (0, 50)
    ) -> Dict:
        """
        Build the payload for the scanner API.

        Args:
            filters (List[Dict], optional): List of filter conditions.
            columns (List[str], optional): Columns to retrieve.
            market (str): The market type. Defaults to 'america'.
            sort (Dict, optional): Sort configuration with 'sortBy' and 'sortOrder'.
            range_limit (tuple): Range for pagination (start, end). Defaults to (0, 50).

        Returns:
            dict: The scanner API payload.
        """
        if columns is None:
            columns = self._get_default_columns(market)

        payload = {
            "columns": columns,
            "options": {
                "lang": "en"
            },
            "range": list(range_limit)
        }

        if filters:
            payload["filter"] = filters

        if sort:
            payload["sort"] = sort

        return payload

    def screen(
        self,
        market: str = 'america',
        filters: Optional[List[Dict[str, Any]]] = None,
        columns: Optional[List[str]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = 'desc',
        limit: int = 50
    ) -> Dict:
        """
        Screen financial instruments based on custom filters.

        Args:
            market (str): The market to screen. Defaults to 'america'.
            filters (List[Dict], optional): List of filter conditions. Each filter should have:
                - left (str): Field name to filter on
                - operation (str): Operation type (greater, less, equal, in_range, etc.)
                - right (Any): Value(s) to compare against
            columns (List[str], optional): Columns to retrieve. If None, uses default columns.
            sort_by (str, optional): Field to sort by.
            sort_order (str): Sort order ('asc' or 'desc'). Defaults to 'desc'.
            limit (int): Maximum number of results. Defaults to 50.

        Returns:
            dict: A dictionary containing:
                - status (str): 'success' or 'failed'
                - data (List[Dict]): List of screened instruments if successful
                - total (int): Total number of results
                - error (str): Error message if failed

        Example:
            >>> screener = Screener()
            >>>
            >>> # Screen stocks with price > 100 and volume > 1M
            >>> filters = [
            ...     {'left': 'close', 'operation': 'greater', 'right': 100},
            ...     {'left': 'volume', 'operation': 'greater', 'right': 1000000}
            ... ]
            >>> results = screener.screen(
            ...     market='america',
            ...     filters=filters,
            ...     sort_by='volume',
            ...     sort_order='desc',
            ...     limit=20
            ... )
            >>>
            >>> # Screen crypto by market cap
            >>> crypto_filters = [
            ...     {'left': 'market_cap_calc', 'operation': 'greater', 'right': 1000000000}
            ... ]
            >>> crypto_results = screener.screen(
            ...     market='crypto',
            ...     filters=crypto_filters,
            ...     columns=['name', 'close', 'market_cap_calc', 'change'],
            ...     limit=50
            ... )
            >>>
            >>> # Screen with price range
            >>> range_filters = [
            ...     {'left': 'close', 'operation': 'in_range', 'right': [50, 200]}
            ... ]
            >>> range_results = screener.screen(market='america', filters=range_filters)
        """
        # Validate market
        self._validate_market(market)

        # Build sort configuration
        sort_config = None
        if sort_by:
            sort_config = {
                "sortBy": sort_by,
                "sortOrder": sort_order
            }

        # Build payload
        payload = self._build_payload(
            filters=filters,
            columns=columns,
            market=market,
            sort=sort_config,
            range_limit=(0, limit)
        )

        # Get scanner URL
        url = self.SUPPORTED_MARKETS[market]

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
                        field_list = columns if columns else self._get_default_columns(market)
                        for idx, field in enumerate(field_list):
                            if idx < len(symbol_data):
                                formatted_item[field] = symbol_data[idx]

                        formatted_data.append(formatted_item)

                # Export if requested
                if self.export_result:
                    self._export(
                        data=formatted_data,
                        symbol=f"{market}_screener",
                        data_category='screener'
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
        Export screened data to file.

        Args:
            data (List[Dict]): The data to export.
            symbol (str, optional): Symbol identifier for the filename.
            data_category (str, optional): Data category for the filename.
        """
        if self.export_type == 'json':
            save_json_file(data=data, symbol=symbol, data_category=data_category)
        elif self.export_type == 'csv':
            save_csv_file(data=data, symbol=symbol, data_category=data_category)
