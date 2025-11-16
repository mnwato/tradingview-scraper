"""Module providing a function to scrape symbol overview data from TradingView."""

from typing import List, Optional, Dict

import requests

from tradingview_scraper.symbols.utils import (
    save_csv_file,
    save_json_file,
    generate_user_agent,
)


class Overview:
    """
    A class to scrape comprehensive overview data for symbols from TradingView.

    This class provides functionality to retrieve detailed information about a symbol
    including profile, statistics, financials, performance metrics, technical indicators,
    and fundamental data.

    Attributes:
        export_result (bool): Flag to determine if results should be exported to file.
        export_type (str): Type of export format ('json' or 'csv').
        headers (dict): HTTP headers for requests.

    Example:
        >>> overview = Overview(export_result=True, export_type='json')
        >>> data = overview.get_symbol_overview(symbol='NASDAQ:AAPL')
        >>> print(data['data'])
    """

    # Symbol API endpoint
    SYMBOL_API_URL = 'https://scanner.tradingview.com/symbol'

    # Field categories
    BASIC_FIELDS = [
        'name',
        'description',
        'type',
        'subtype',
        'exchange',
        'country',
        'sector',
        'industry',
    ]

    PRICE_FIELDS = [
        'close',
        'change',
        'change_abs',
        'change_from_open',
        'high',
        'low',
        'open',
        'volume',
        'Value.Traded',
        'price_52_week_high',
        'price_52_week_low',
    ]

    MARKET_FIELDS = [
        'market_cap_basic',
        'market_cap_calc',
        'market_cap_diluted_calc',
        'shares_outstanding',
        'shares_float',
        'shares_diluted',
    ]

    VALUATION_FIELDS = [
        'price_earnings_ttm',
        'price_book_fq',
        'price_sales_ttm',
        'price_free_cash_flow_ttm',
        'earnings_per_share_basic_ttm',
        'earnings_per_share_diluted_ttm',
        'book_value_per_share_fq',
    ]

    DIVIDEND_FIELDS = [
        'dividends_yield',
        'dividends_per_share_fq',
        'dividend_payout_ratio_ttm',
    ]

    FINANCIAL_FIELDS = [
        'total_revenue',
        'revenue_per_share_ttm',
        'net_income_fy',
        'gross_margin_percent_ttm',
        'operating_margin_ttm',
        'net_margin_percent_ttm',
        'return_on_equity_fq',
        'return_on_assets_fq',
        'return_on_investment_ttm',
        'debt_to_equity_fq',
        'current_ratio_fq',
        'quick_ratio_fq',
        'EBITDA',
        'employees',
    ]

    PERFORMANCE_FIELDS = [
        'Perf.W',
        'Perf.1M',
        'Perf.3M',
        'Perf.6M',
        'Perf.Y',
        'Perf.YTD',
    ]

    VOLATILITY_FIELDS = [
        'Volatility.D',
        'Volatility.W',
        'Volatility.M',
        'beta_1_year',
    ]

    TECHNICAL_FIELDS = [
        'Recommend.All',
        'RSI',
        'CCI20',
        'ADX',
        'MACD.macd',
        'Stoch.K',
        'ATR',
    ]

    # All fields combined
    ALL_FIELDS = (
        BASIC_FIELDS +
        PRICE_FIELDS +
        MARKET_FIELDS +
        VALUATION_FIELDS +
        DIVIDEND_FIELDS +
        FINANCIAL_FIELDS +
        PERFORMANCE_FIELDS +
        VOLATILITY_FIELDS +
        TECHNICAL_FIELDS
    )

    def __init__(self, export_result: bool = False, export_type: str = 'json'):
        """
        Initialize the Overview scraper.

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

    def get_symbol_overview(
        self,
        symbol: str,
        fields: Optional[List[str]] = None
    ) -> Dict:
        """
        Get comprehensive overview data for a symbol.

        Args:
            symbol (str): The symbol to get overview for (e.g., 'NASDAQ:AAPL', 'BITSTAMP:BTCUSD').
            fields (List[str], optional): Specific fields to retrieve. If None, retrieves all fields.

        Returns:
            dict: A dictionary containing:
                - status (str): 'success' or 'failed'
                - data (Dict): Symbol overview data
                - error (str): Error message if failed

        Example:
            >>> overview = Overview()
            >>>
            >>> # Get full overview for Apple stock
            >>> aapl = overview.get_symbol_overview(symbol='NASDAQ:AAPL')
            >>>
            >>> # Get specific fields only
            >>> btc = overview.get_symbol_overview(
            ...     symbol='BITSTAMP:BTCUSD',
            ...     fields=['close', 'market_cap_basic', 'change', 'volume']
            ... )
        """
        try:
            # Validate symbol
            symbol = self._validate_symbol(symbol)

            # Use provided fields or all fields
            field_list = fields if fields else self.ALL_FIELDS

            # Build request parameters
            params = {
                'symbol': symbol,
                'fields': ','.join(field_list)
            }

            # Make request
            response = requests.get(
                self.SYMBOL_API_URL,
                params=params,
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()

                if not data:
                    return {
                        'status': 'failed',
                        'error': f'No data found for symbol: {symbol}'
                    }

                # Add symbol to the data
                data['symbol'] = symbol

                # Export if requested
                if self.export_result:
                    self._export(
                        data=data,
                        symbol=symbol.replace(':', '_'),
                        data_category='overview'
                    )

                return {
                    'status': 'success',
                    'data': data
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

    def get_profile(self, symbol: str) -> Dict:
        """
        Get basic profile information for a symbol.

        Args:
            symbol (str): The symbol to get profile for.

        Returns:
            dict: Profile data including name, description, exchange, sector, industry, country.
        """
        return self.get_symbol_overview(symbol=symbol, fields=self.BASIC_FIELDS)

    def get_statistics(self, symbol: str) -> Dict:
        """
        Get market statistics for a symbol.

        Args:
            symbol (str): The symbol to get statistics for.

        Returns:
            dict: Statistics including market cap, shares, valuation ratios.
        """
        fields = self.MARKET_FIELDS + self.VALUATION_FIELDS + self.DIVIDEND_FIELDS
        return self.get_symbol_overview(symbol=symbol, fields=fields)

    def get_financials(self, symbol: str) -> Dict:
        """
        Get financial metrics for a symbol.

        Args:
            symbol (str): The symbol to get financials for.

        Returns:
            dict: Financial data including revenue, margins, ratios, EBITDA.
        """
        return self.get_symbol_overview(symbol=symbol, fields=self.FINANCIAL_FIELDS)

    def get_performance(self, symbol: str) -> Dict:
        """
        Get performance metrics for a symbol.

        Args:
            symbol (str): The symbol to get performance for.

        Returns:
            dict: Performance data including weekly, monthly, yearly returns.
        """
        return self.get_symbol_overview(symbol=symbol, fields=self.PERFORMANCE_FIELDS)

    def get_technicals(self, symbol: str) -> Dict:
        """
        Get technical indicators for a symbol.

        Args:
            symbol (str): The symbol to get technicals for.

        Returns:
            dict: Technical indicators including RSI, MACD, ADX, recommendations.
        """
        fields = self.TECHNICAL_FIELDS + self.VOLATILITY_FIELDS
        return self.get_symbol_overview(symbol=symbol, fields=fields)

    def _export(
        self,
        data: Dict,
        symbol: Optional[str] = None,
        data_category: Optional[str] = None
    ) -> None:
        """
        Export scraped data to file.

        Args:
            data (Dict): The data to export.
            symbol (str, optional): Symbol identifier for the filename.
            data_category (str, optional): Data category for the filename.
        """
        # For CSV export, convert dict to list of dicts
        export_data = [data] if isinstance(data, dict) else data

        if self.export_type == 'json':
            save_json_file(data=export_data, symbol=symbol, data_category=data_category)
        elif self.export_type == 'csv':
            save_csv_file(data=export_data, symbol=symbol, data_category=data_category)
