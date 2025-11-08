"""Module providing a function to scrape market movers data (gainers, losers, penny stocks, etc.)."""

from typing import List, Optional, Dict

import requests

from tradingview_scraper.symbols.utils import (
    save_csv_file,
    save_json_file,
    generate_user_agent,
)


class MarketMovers:
    """
    A class to scrape market movers data from TradingView.

    This class provides functionality to retrieve data for various market categories
    such as gainers, losers, most active stocks, penny stocks, pre-market and
    after-hours gainers.

    Attributes:
        export_result (bool): Flag to determine if results should be exported to file.
        export_type (str): Type of export format ('json' or 'csv').
        headers (dict): HTTP headers for requests.

    Example:
        >>> scraper = MarketMovers(export_result=True, export_type='json')
        >>> gainers = scraper.scrape(market='stocks-usa', category='gainers')
        >>> print(gainers['data'])
    """

    # Supported markets
    SUPPORTED_MARKETS = [
        'stocks-usa',
        'stocks-uk',
        'stocks-india',
        'stocks-australia',
        'stocks-canada',
        'crypto',
        'forex',
        'bonds',
        'futures',
    ]

    # Supported categories for stock markets
    STOCK_CATEGORIES = [
        'gainers',
        'losers',
        'most-active',
        'penny-stocks',
        'pre-market-gainers',
        'pre-market-losers',
        'after-hours-gainers',
        'after-hours-losers',
    ]

    # Default fields to fetch
    DEFAULT_FIELDS = [
        'name',
        'close',
        'change',
        'change_abs',
        'volume',
        'market_cap_basic',
        'price_earnings_ttm',
        'earnings_per_share_basic_ttm',
        'logoid',
        'description',
    ]

    def __init__(self, export_result: bool = False, export_type: str = 'json'):
        """
        Initialize the MarketMovers scraper.

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
                f"Supported markets: {', '.join(self.SUPPORTED_MARKETS)}"
            )

    def _validate_category(self, category: str, market: str) -> None:
        """
        Validate if the category is supported for the given market.

        Args:
            category (str): The category to validate.
            market (str): The market context.

        Raises:
            ValueError: If the category is not supported.
        """
        if market.startswith('stocks') and category not in self.STOCK_CATEGORIES:
            raise ValueError(
                f"Unsupported category: {category}. "
                f"Supported categories for stocks: {', '.join(self.STOCK_CATEGORIES)}"
            )

    def _build_scanner_payload(
        self,
        market: str,
        category: str,
        fields: Optional[List[str]] = None,
        limit: int = 50
    ) -> Dict:
        """
        Build the payload for the TradingView scanner API.

        Args:
            market (str): The market to scan.
            category (str): The category of market movers.
            fields (List[str], optional): Fields to retrieve.
            limit (int): Maximum number of results. Defaults to 50.

        Returns:
            dict: The scanner API payload.
        """
        if fields is None:
            fields = self.DEFAULT_FIELDS

        # Map category to filter conditions
        filter_conditions = self._get_filter_conditions(market, category)

        # Build sort configuration
        sort_config = self._get_sort_config(category)

        payload = {
            "columns": fields,
            "filter": filter_conditions,
            "options": {
                "lang": "en"
            },
            "range": [0, limit],
            "sort": sort_config
        }

        return payload

    def _get_filter_conditions(self, market: str, category: str) -> List[Dict]:
        """
        Get filter conditions based on market and category.

        Args:
            market (str): The market.
            category (str): The category.

        Returns:
            List[Dict]: Filter conditions for the scanner API.
        """
        filters = []

        # Base market filter
        if market == 'stocks-usa':
            filters.append({
                "left": "market",
                "operation": "equal",
                "right": "america"
            })
        elif market == 'stocks-uk':
            filters.append({
                "left": "market",
                "operation": "equal",
                "right": "uk"
            })
        elif market == 'stocks-india':
            filters.append({
                "left": "market",
                "operation": "equal",
                "right": "india"
            })
        elif market == 'stocks-australia':
            filters.append({
                "left": "market",
                "operation": "equal",
                "right": "australia"
            })
        elif market == 'stocks-canada':
            filters.append({
                "left": "market",
                "operation": "equal",
                "right": "canada"
            })

        # Category-specific filters
        if category == 'penny-stocks':
            filters.append({
                "left": "close",
                "operation": "less",
                "right": 5
            })
        elif category == 'gainers' or category == 'pre-market-gainers' or category == 'after-hours-gainers':
            filters.append({
                "left": "change",
                "operation": "greater",
                "right": 0
            })
        elif category == 'losers' or category == 'pre-market-losers' or category == 'after-hours-losers':
            filters.append({
                "left": "change",
                "operation": "less",
                "right": 0
            })

        return filters

    def _get_sort_config(self, category: str) -> Dict:
        """
        Get sort configuration based on category.

        Args:
            category (str): The category.

        Returns:
            Dict: Sort configuration for the scanner API.
        """
        if category in ['gainers', 'pre-market-gainers', 'after-hours-gainers']:
            return {
                "sortBy": "change",
                "sortOrder": "desc"
            }
        elif category in ['losers', 'pre-market-losers', 'after-hours-losers']:
            return {
                "sortBy": "change",
                "sortOrder": "asc"
            }
        elif category == 'most-active':
            return {
                "sortBy": "volume",
                "sortOrder": "desc"
            }
        elif category == 'penny-stocks':
            return {
                "sortBy": "volume",
                "sortOrder": "desc"
            }
        else:
            return {
                "sortBy": "change",
                "sortOrder": "desc"
            }

    def _get_scanner_url(self, market: str) -> str:
        """
        Get the appropriate scanner URL for the market.

        Args:
            market (str): The market.

        Returns:
            str: The scanner API URL.
        """
        if market == 'crypto':
            return "https://scanner.tradingview.com/crypto/scan"
        elif market == 'forex':
            return "https://scanner.tradingview.com/forex/scan"
        elif market == 'bonds':
            return "https://scanner.tradingview.com/bonds/scan"
        elif market == 'futures':
            return "https://scanner.tradingview.com/futures/scan"
        else:
            # Default to america for stocks
            return "https://scanner.tradingview.com/america/scan"

    def scrape(
        self,
        market: str = 'stocks-usa',
        category: str = 'gainers',
        fields: Optional[List[str]] = None,
        limit: int = 50
    ) -> Dict:
        """
        Scrape market movers data from TradingView.

        Args:
            market (str): The market to scrape. Defaults to 'stocks-usa'.
            category (str): The category of market movers. Defaults to 'gainers'.
            fields (List[str], optional): Specific fields to retrieve. If None, uses default fields.
            limit (int): Maximum number of results to return. Defaults to 50.

        Returns:
            dict: A dictionary containing:
                - status (str): 'success' or 'failed'
                - data (List[Dict]): List of market mover data if successful
                - error (str): Error message if failed

        Raises:
            ValueError: If market or category is not supported.

        Example:
            >>> scraper = MarketMovers()
            >>> # Get top gainers
            >>> gainers = scraper.scrape(market='stocks-usa', category='gainers', limit=20)
            >>>
            >>> # Get penny stocks
            >>> penny_stocks = scraper.scrape(market='stocks-usa', category='penny-stocks', limit=100)
            >>>
            >>> # Get pre-market gainers with custom fields
            >>> premarket = scraper.scrape(
            ...     market='stocks-usa',
            ...     category='pre-market-gainers',
            ...     fields=['name', 'close', 'change', 'volume'],
            ...     limit=30
            ... )
        """
        # Validate inputs
        self._validate_market(market)
        self._validate_category(category, market)

        # Build payload
        payload = self._build_scanner_payload(market, category, fields, limit)

        # Get scanner URL
        url = self._get_scanner_url(market)

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

                # Extract data from response
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
                        field_list = fields if fields else self.DEFAULT_FIELDS
                        for idx, field in enumerate(field_list):
                            if idx < len(symbol_data):
                                formatted_item[field] = symbol_data[idx]

                        formatted_data.append(formatted_item)

                # Export if requested
                if self.export_result:
                    self._export(
                        data=formatted_data,
                        symbol=f"{market}_{category}",
                        data_category='market_movers'
                    )

                return {
                    'status': 'success',
                    'data': formatted_data,
                    'total': len(formatted_data)
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
