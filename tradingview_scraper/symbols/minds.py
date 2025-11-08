"""Module providing a function to scrape Minds community discussions from TradingView."""

from typing import Optional, Dict, List
from datetime import datetime

import requests

from tradingview_scraper.symbols.utils import (
    save_csv_file,
    save_json_file,
    generate_user_agent,
)


class Minds:
    """
    A class to scrape Minds community discussions and insights from TradingView.

    This class provides functionality to retrieve community-generated content including
    questions, discussions, trading ideas, and sentiment from TradingView's Minds feature.

    Attributes:
        export_result (bool): Flag to determine if results should be exported to file.
        export_type (str): Type of export format ('json' or 'csv').
        headers (dict): HTTP headers for requests.

    Example:
        >>> minds = Minds(export_result=True, export_type='json')
        >>> discussions = minds.get_minds(symbol='NASDAQ:AAPL', limit=20)
        >>> print(discussions['data'])
    """

    # Minds API endpoint
    MINDS_API_URL = 'https://www.tradingview.com/api/v1/minds/'

    # Sort options
    SORT_OPTIONS = {
        'recent': 'recent',
        'popular': 'popular',
        'trending': 'trending',
    }

    def __init__(self, export_result: bool = False, export_type: str = 'json'):
        """
        Initialize the Minds scraper.

        Args:
            export_result (bool): Whether to export results to a file. Defaults to False.
            export_type (str): Export format ('json' or 'csv'). Defaults to 'json'.
        """
        self.export_result = export_result
        self.export_type = export_type
        self.headers = {"User-Agent": generate_user_agent()}

    def _validate_symbol(self, symbol: str) -> str:
        """
        Validate and format symbol.

        Args:
            symbol (str): The symbol to validate.

        Returns:
            str: Formatted symbol.

        Raises:
            ValueError: If symbol is invalid.
        """
        if not symbol or not isinstance(symbol, str):
            raise ValueError("Symbol must be a non-empty string")

        symbol = symbol.strip().upper()

        # Add exchange prefix if not present
        if ':' not in symbol:
            raise ValueError(
                "Symbol must include exchange prefix (e.g., 'NASDAQ:AAPL', 'BITSTAMP:BTCUSD')"
            )

        return symbol

    def _validate_sort(self, sort: str) -> str:
        """
        Validate sort option.

        Args:
            sort (str): The sort option to validate.

        Returns:
            str: Validated sort option.

        Raises:
            ValueError: If sort option is invalid.
        """
        if sort not in self.SORT_OPTIONS:
            raise ValueError(
                f"Unsupported sort option: {sort}. "
                f"Supported options: {', '.join(self.SORT_OPTIONS.keys())}"
            )
        return self.SORT_OPTIONS[sort]

    def _parse_mind(self, item: Dict) -> Dict:
        """
        Parse a single mind item.

        Args:
            item (Dict): Raw mind item from API.

        Returns:
            Dict: Parsed mind data.
        """
        # Parse author info
        author = item.get('author', {})
        author_data = {
            'username': author.get('username'),
            'profile_url': f"https://www.tradingview.com{author.get('uri', '')}",
            'is_broker': author.get('is_broker', False),
        }

        # Parse created date
        created = item.get('created', '')
        try:
            created_datetime = datetime.fromisoformat(
                created.replace('Z', '+00:00')
            )
            created_formatted = created_datetime.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, AttributeError):
            created_formatted = created

        # Parse symbols mentioned
        symbols = item.get('symbols', {})
        symbols_list = list(symbols.values()) if symbols else []

        # Build parsed data
        parsed = {
            'uid': item.get('uid'),
            'text': item.get('text', ''),
            'url': item.get('url', ''),
            'author': author_data,
            'created': created_formatted,
            'symbols': symbols_list,
            'total_likes': item.get('total_likes', 0),
            'total_comments': item.get('total_comments', 0),
            'modified': item.get('modified', False),
            'hidden': item.get('hidden', False),
        }

        return parsed

    def get_minds(
        self,
        symbol: str,
        sort: str = 'recent',
        limit: int = 50
    ) -> Dict:
        """
        Get Minds discussions for a symbol.

        Args:
            symbol (str): The symbol to get discussions for (e.g., 'NASDAQ:AAPL').
            sort (str): Sort order ('recent', 'popular', 'trending'). Defaults to 'recent'.
            limit (int): Maximum number of results. Defaults to 50.

        Returns:
            dict: A dictionary containing:
                - status (str): 'success' or 'failed'
                - data (List[Dict]): List of minds discussions
                - total (int): Total number of results
                - symbol_info (Dict): Information about the symbol
                - next_cursor (str): Cursor for pagination
                - error (str): Error message if failed

        Example:
            >>> minds = Minds()
            >>>
            >>> # Get recent discussions for Apple
            >>> aapl_minds = minds.get_minds(symbol='NASDAQ:AAPL', sort='recent', limit=30)
            >>>
            >>> # Get popular discussions for Bitcoin
            >>> btc_minds = minds.get_minds(symbol='BITSTAMP:BTCUSD', sort='popular', limit=20)
            >>>
            >>> # Get trending discussions
            >>> trending = minds.get_minds(symbol='NASDAQ:TSLA', sort='trending', limit=25)
        """
        try:
            # Validate inputs
            symbol = self._validate_symbol(symbol)
            sort_option = self._validate_sort(sort)

            # Build request parameters
            params = {
                'symbol': symbol,
                'limit': limit,
                'sort': sort_option,
            }

            # Make request
            response = requests.get(
                self.MINDS_API_URL,
                params=params,
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                json_response = response.json()

                # Extract data
                results = json_response.get('results', [])

                if not results:
                    return {
                        'status': 'failed',
                        'error': f'No discussions found for symbol: {symbol}'
                    }

                # Parse each mind
                parsed_data = [self._parse_mind(item) for item in results]

                # Extract metadata
                meta = json_response.get('meta', {})
                symbol_info = meta.get('symbols_info', {}).get(symbol, {})

                # Extract next cursor for pagination
                next_cursor = json_response.get('next', '')

                # Export if requested
                if self.export_result:
                    self._export(
                        data=parsed_data,
                        symbol=symbol.replace(':', '_'),
                        data_category='minds'
                    )

                return {
                    'status': 'success',
                    'data': parsed_data,
                    'total': len(parsed_data),
                    'symbol_info': symbol_info,
                    'next_cursor': next_cursor
                }
            else:
                return {
                    'status': 'failed',
                    'error': f'HTTP {response.status_code}: {response.text}'
                }

        except ValueError as e:
            return {
                'status': 'failed',
                'error': str(e)
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

    def get_all_minds(
        self,
        symbol: str,
        sort: str = 'recent',
        max_results: int = 200
    ) -> Dict:
        """
        Get all available Minds discussions for a symbol with pagination.

        Args:
            symbol (str): The symbol to get discussions for.
            sort (str): Sort order ('recent', 'popular', 'trending'). Defaults to 'recent'.
            max_results (int): Maximum total results to retrieve. Defaults to 200.

        Returns:
            dict: A dictionary containing all discussions up to max_results.

        Example:
            >>> minds = Minds()
            >>> all_discussions = minds.get_all_minds(
            ...     symbol='NASDAQ:AAPL',
            ...     sort='popular',
            ...     max_results=100
            ... )
        """
        try:
            # Validate inputs
            symbol = self._validate_symbol(symbol)
            sort_option = self._validate_sort(sort)

            all_data = []
            next_cursor = None
            page = 1

            while len(all_data) < max_results:
                # Build parameters
                params = {
                    'symbol': symbol,
                    'limit': min(50, max_results - len(all_data)),
                    'sort': sort_option,
                }

                # Add cursor if not first page
                if next_cursor:
                    params['c'] = next_cursor

                # Make request
                response = requests.get(
                    self.MINDS_API_URL,
                    params=params,
                    headers=self.headers,
                    timeout=10
                )

                if response.status_code != 200:
                    break

                json_response = response.json()
                results = json_response.get('results', [])

                if not results:
                    break

                # Parse and add to collection
                parsed_data = [self._parse_mind(item) for item in results]
                all_data.extend(parsed_data)

                # Check for next page
                next_url = json_response.get('next', '')
                if not next_url or '?c=' not in next_url:
                    break

                # Extract cursor from next URL
                next_cursor = next_url.split('?c=')[1].split('&')[0]
                page += 1

            # Get symbol info from first page
            symbol_info = {}
            if all_data:
                first_result = self.get_minds(symbol=symbol, sort=sort, limit=1)
                if first_result['status'] == 'success':
                    symbol_info = first_result.get('symbol_info', {})

            # Export if requested
            if self.export_result and all_data:
                self._export(
                    data=all_data,
                    symbol=symbol.replace(':', '_'),
                    data_category='minds_all'
                )

            return {
                'status': 'success',
                'data': all_data,
                'total': len(all_data),
                'pages': page,
                'symbol_info': symbol_info
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
