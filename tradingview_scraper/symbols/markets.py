"""Module providing a function to scrape market overview data (top stocks, indices, sectors, etc.)."""

from typing import List, Optional, Dict

import requests

from tradingview_scraper.symbols.utils import (
    save_csv_file,
    save_json_file,
    generate_user_agent,
)


class Markets:
    """
    A class to scrape market overview data from TradingView.

    This class provides functionality to retrieve market overview data such as
    top stocks by market cap, most active stocks, top gainers/losers by sector,
    and other market-wide statistics.

    Attributes:
        export_result (bool): Flag to determine if results should be exported to file.
        export_type (str): Type of export format ('json' or 'csv').
        headers (dict): HTTP headers for requests.

    Example:
        >>> markets = Markets(export_result=True, export_type='json')
        >>> top_stocks = markets.get_top_stocks(market='america', by='market_cap', limit=50)
        >>> print(top_stocks['data'])
    """

    # Scanner endpoints for different markets
    SCANNER_ENDPOINTS = {
        'america': 'https://scanner.tradingview.com/america/scan',
        'australia': 'https://scanner.tradingview.com/australia/scan',
        'canada': 'https://scanner.tradingview.com/canada/scan',
        'germany': 'https://scanner.tradingview.com/germany/scan',
        'india': 'https://scanner.tradingview.com/india/scan',
        'uk': 'https://scanner.tradingview.com/uk/scan',
        'crypto': 'https://scanner.tradingview.com/crypto/scan',
        'forex': 'https://scanner.tradingview.com/forex/scan',
        'global': 'https://scanner.tradingview.com/global/scan',
    }

    # Sorting criteria
    SORT_CRITERIA = {
        'market_cap': 'market_cap_basic',
        'volume': 'volume',
        'change': 'change',
        'price': 'close',
        'volatility': 'Volatility.D',
    }

    # Default columns
    DEFAULT_COLUMNS = [
        'name',
        'close',
        'change',
        'change_abs',
        'volume',
        'Recommend.All',
        'market_cap_basic',
        'price_earnings_ttm',
        'earnings_per_share_basic_ttm',
        'sector',
        'industry',
    ]

    def __init__(self, export_result: bool = False, export_type: str = 'json'):
        """
        Initialize the Markets scraper.

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
        if market not in self.SCANNER_ENDPOINTS:
            raise ValueError(
                f"Unsupported market: {market}. "
                f"Supported markets: {', '.join(self.SCANNER_ENDPOINTS.keys())}"
            )

    def _validate_sort_by(self, sort_by: str) -> str:
        """
        Validate and convert sort criteria.

        Args:
            sort_by (str): The sort criteria.

        Returns:
            str: The validated sort field.

        Raises:
            ValueError: If the sort criteria is not supported.
        """
        if sort_by in self.SORT_CRITERIA:
            return self.SORT_CRITERIA[sort_by]
        elif sort_by in self.SORT_CRITERIA.values():
            return sort_by
        else:
            raise ValueError(
                f"Unsupported sort criteria: {sort_by}. "
                f"Supported criteria: {', '.join(self.SORT_CRITERIA.keys())}"
            )

    def _build_payload(
        self,
        filters: Optional[List[Dict]] = None,
        columns: Optional[List[str]] = None,
        sort_by: str = 'market_cap',
        sort_order: str = 'desc',
        limit: int = 50
    ) -> Dict:
        """
        Build the payload for the scanner API.

        Args:
            filters (List[Dict], optional): Filter conditions.
            columns (List[str], optional): Columns to retrieve.
            sort_by (str): Field to sort by. Defaults to 'market_cap'.
            sort_order (str): Sort order ('asc' or 'desc'). Defaults to 'desc'.
            limit (int): Maximum number of results. Defaults to 50.

        Returns:
            dict: The scanner API payload.
        """
        if columns is None:
            columns = self.DEFAULT_COLUMNS

        # Validate and get sort field
        sort_field = self._validate_sort_by(sort_by)

        payload = {
            "columns": columns,
            "options": {
                "lang": "en"
            },
            "range": [0, limit],
            "sort": {
                "sortBy": sort_field,
                "sortOrder": sort_order
            }
        }

        if filters:
            payload["filter"] = filters

        return payload

    def get_top_stocks(
        self,
        market: str = 'america',
        by: str = 'market_cap',
        columns: Optional[List[str]] = None,
        limit: int = 50
    ) -> Dict:
        """
        Get top stocks by specified criteria.

        Args:
            market (str): The market to scan. Defaults to 'america'.
            by (str): Sorting criteria ('market_cap', 'volume', 'change', 'price', 'volatility').
                     Defaults to 'market_cap'.
            columns (List[str], optional): Columns to retrieve. If None, uses default columns.
            limit (int): Maximum number of results. Defaults to 50.

        Returns:
            dict: A dictionary containing:
                - status (str): 'success' or 'failed'
                - data (List[Dict]): List of top stocks
                - total (int): Total number of results
                - error (str): Error message if failed

        Example:
            >>> markets = Markets()
            >>>
            >>> # Get top 20 stocks by market cap
            >>> top_by_cap = markets.get_top_stocks(market='america', by='market_cap', limit=20)
            >>>
            >>> # Get most active stocks
            >>> most_active = markets.get_top_stocks(market='america', by='volume', limit=30)
            >>>
            >>> # Get biggest movers
            >>> biggest_movers = markets.get_top_stocks(market='america', by='change', limit=25)
        """
        # Validate market
        self._validate_market(market)

        # Build filters to get only stocks (not indices, ETFs, etc.)
        filters = [
            {"left": "type", "operation": "equal", "right": "stock"},
            {"left": "market_cap_basic", "operation": "nempty"}
        ]

        # Build payload
        payload = self._build_payload(
            filters=filters,
            columns=columns,
            sort_by=by,
            sort_order='desc',
            limit=limit
        )

        # Get scanner URL
        url = self.SCANNER_ENDPOINTS[market]

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
                        'error': f'No data found for market: {market}'
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
                        symbol=f"{market}_top_stocks",
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
