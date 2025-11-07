"""Module providing a function to scrape fundamental financial graphs data from TradingView."""

from typing import List, Optional, Dict

import requests

from tradingview_scraper.symbols.utils import (
    save_csv_file,
    save_json_file,
    generate_user_agent,
)


class FundamentalGraphs:
    """
    A class to scrape fundamental financial data for symbols from TradingView.

    This class provides functionality to retrieve detailed fundamental financial metrics
    including income statement, balance sheet, cash flow, margins, ratios, and valuation data.

    Attributes:
        export_result (bool): Flag to determine if results should be exported to file.
        export_type (str): Type of export format ('json' or 'csv').
        headers (dict): HTTP headers for requests.

    Example:
        >>> fundamentals = FundamentalGraphs(export_result=True, export_type='json')
        >>> data = fundamentals.get_fundamentals(symbol='NASDAQ:AAPL')
        >>> print(data['data'])
    """

    # Symbol API endpoint
    SYMBOL_API_URL = 'https://scanner.tradingview.com/symbol'

    # Field categories
    INCOME_STATEMENT_FIELDS = [
        'total_revenue',
        'revenue_per_share_ttm',
        'total_revenue_fy',
        'gross_profit',
        'gross_profit_fy',
        'operating_income',
        'operating_income_fy',
        'net_income',
        'net_income_fy',
        'EBITDA',
        'basic_eps_net_income',
        'earnings_per_share_basic_ttm',
        'earnings_per_share_diluted_ttm',
    ]

    BALANCE_SHEET_FIELDS = [
        'total_assets',
        'total_assets_fy',
        'cash_n_short_term_invest',
        'cash_n_short_term_invest_fy',
        'total_debt',
        'total_debt_fy',
        'stockholders_equity',
        'stockholders_equity_fy',
        'book_value_per_share_fq',
    ]

    CASH_FLOW_FIELDS = [
        'cash_f_operating_activities',
        'cash_f_operating_activities_fy',
        'cash_f_investing_activities',
        'cash_f_investing_activities_fy',
        'cash_f_financing_activities',
        'cash_f_financing_activities_fy',
        'free_cash_flow',
    ]

    MARGIN_FIELDS = [
        'gross_margin',
        'gross_margin_percent_ttm',
        'operating_margin',
        'operating_margin_ttm',
        'pretax_margin_percent_ttm',
        'net_margin',
        'net_margin_percent_ttm',
        'EBITDA_margin',
    ]

    PROFITABILITY_FIELDS = [
        'return_on_equity',
        'return_on_equity_fq',
        'return_on_assets',
        'return_on_assets_fq',
        'return_on_investment_ttm',
    ]

    LIQUIDITY_FIELDS = [
        'current_ratio',
        'current_ratio_fq',
        'quick_ratio',
        'quick_ratio_fq',
    ]

    LEVERAGE_FIELDS = [
        'debt_to_equity',
        'debt_to_equity_fq',
        'debt_to_assets',
    ]

    VALUATION_FIELDS = [
        'market_cap_basic',
        'market_cap_calc',
        'market_cap_diluted_calc',
        'enterprise_value_fq',
        'price_earnings_ttm',
        'price_book_fq',
        'price_sales_ttm',
        'price_free_cash_flow_ttm',
    ]

    DIVIDEND_FIELDS = [
        'dividends_yield',
        'dividends_per_share_fq',
        'dividend_payout_ratio_ttm',
    ]

    # All fundamental fields combined
    ALL_FIELDS = (
        INCOME_STATEMENT_FIELDS +
        BALANCE_SHEET_FIELDS +
        CASH_FLOW_FIELDS +
        MARGIN_FIELDS +
        PROFITABILITY_FIELDS +
        LIQUIDITY_FIELDS +
        LEVERAGE_FIELDS +
        VALUATION_FIELDS +
        DIVIDEND_FIELDS
    )

    def __init__(self, export_result: bool = False, export_type: str = 'json'):
        """
        Initialize the FundamentalGraphs scraper.

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
                "Symbol must include exchange prefix (e.g., 'NASDAQ:AAPL', 'NYSE:JPM')"
            )

        return symbol

    def get_fundamentals(
        self,
        symbol: str,
        fields: Optional[List[str]] = None
    ) -> Dict:
        """
        Get comprehensive fundamental financial data for a symbol.

        Args:
            symbol (str): The symbol to get fundamentals for (e.g., 'NASDAQ:AAPL').
            fields (List[str], optional): Specific fields to retrieve. If None, retrieves all fields.

        Returns:
            dict: A dictionary containing:
                - status (str): 'success' or 'failed'
                - data (Dict): Fundamental financial data
                - error (str): Error message if failed

        Example:
            >>> fundamentals = FundamentalGraphs()
            >>>
            >>> # Get all fundamental data for Apple
            >>> aapl = fundamentals.get_fundamentals(symbol='NASDAQ:AAPL')
            >>>
            >>> # Get specific fields only
            >>> revenue = fundamentals.get_fundamentals(
            ...     symbol='NASDAQ:AAPL',
            ...     fields=['total_revenue', 'net_income', 'EBITDA']
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
                        data_category='fundamentals'
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

    def get_income_statement(self, symbol: str) -> Dict:
        """
        Get income statement data for a symbol.

        Args:
            symbol (str): The symbol to get income statement for.

        Returns:
            dict: Income statement data including revenue, profit, earnings.
        """
        return self.get_fundamentals(symbol=symbol, fields=self.INCOME_STATEMENT_FIELDS)

    def get_balance_sheet(self, symbol: str) -> Dict:
        """
        Get balance sheet data for a symbol.

        Args:
            symbol (str): The symbol to get balance sheet for.

        Returns:
            dict: Balance sheet data including assets, debt, equity.
        """
        return self.get_fundamentals(symbol=symbol, fields=self.BALANCE_SHEET_FIELDS)

    def get_cash_flow(self, symbol: str) -> Dict:
        """
        Get cash flow statement data for a symbol.

        Args:
            symbol (str): The symbol to get cash flow for.

        Returns:
            dict: Cash flow data including operating, investing, financing activities.
        """
        return self.get_fundamentals(symbol=symbol, fields=self.CASH_FLOW_FIELDS)

    def get_margins(self, symbol: str) -> Dict:
        """
        Get margin metrics for a symbol.

        Args:
            symbol (str): The symbol to get margins for.

        Returns:
            dict: Margin data including gross, operating, net, EBITDA margins.
        """
        return self.get_fundamentals(symbol=symbol, fields=self.MARGIN_FIELDS)

    def get_profitability(self, symbol: str) -> Dict:
        """
        Get profitability ratios for a symbol.

        Args:
            symbol (str): The symbol to get profitability for.

        Returns:
            dict: Profitability data including ROE, ROA, ROI.
        """
        return self.get_fundamentals(symbol=symbol, fields=self.PROFITABILITY_FIELDS)

    def get_liquidity(self, symbol: str) -> Dict:
        """
        Get liquidity ratios for a symbol.

        Args:
            symbol (str): The symbol to get liquidity for.

        Returns:
            dict: Liquidity data including current ratio, quick ratio.
        """
        return self.get_fundamentals(symbol=symbol, fields=self.LIQUIDITY_FIELDS)

    def get_leverage(self, symbol: str) -> Dict:
        """
        Get leverage ratios for a symbol.

        Args:
            symbol (str): The symbol to get leverage for.

        Returns:
            dict: Leverage data including debt-to-equity, debt-to-assets.
        """
        return self.get_fundamentals(symbol=symbol, fields=self.LEVERAGE_FIELDS)

    def get_valuation(self, symbol: str) -> Dict:
        """
        Get valuation metrics for a symbol.

        Args:
            symbol (str): The symbol to get valuation for.

        Returns:
            dict: Valuation data including market cap, P/E, P/B, P/S ratios.
        """
        return self.get_fundamentals(symbol=symbol, fields=self.VALUATION_FIELDS)

    def get_dividends(self, symbol: str) -> Dict:
        """
        Get dividend information for a symbol.

        Args:
            symbol (str): The symbol to get dividends for.

        Returns:
            dict: Dividend data including yield, per share, payout ratio.
        """
        return self.get_fundamentals(symbol=symbol, fields=self.DIVIDEND_FIELDS)

    def compare_fundamentals(
        self,
        symbols: List[str],
        fields: Optional[List[str]] = None
    ) -> Dict:
        """
        Compare fundamental data across multiple symbols.

        Args:
            symbols (List[str]): List of symbols to compare.
            fields (List[str], optional): Specific fields to compare. If None, uses key metrics.

        Returns:
            dict: A dictionary containing:
                - status (str): 'success' or 'failed'
                - data (List[Dict]): List of fundamental data for each symbol
                - comparison (Dict): Side-by-side comparison of metrics
                - error (str): Error message if failed

        Example:
            >>> fundamentals = FundamentalGraphs()
            >>> comparison = fundamentals.compare_fundamentals(
            ...     symbols=['NASDAQ:AAPL', 'NASDAQ:MSFT', 'NASDAQ:GOOGL'],
            ...     fields=['total_revenue', 'net_income', 'market_cap_basic']
            ... )
        """
        try:
            # Use key metrics if no fields specified
            if not fields:
                fields = [
                    'total_revenue', 'net_income', 'EBITDA',
                    'market_cap_basic', 'price_earnings_ttm',
                    'return_on_equity_fq', 'debt_to_equity_fq'
                ]

            all_data = []
            comparison = {}

            # Get data for each symbol
            for symbol in symbols:
                result = self.get_fundamentals(symbol=symbol, fields=fields)
                if result['status'] == 'success':
                    all_data.append(result['data'])

                    # Build comparison dict
                    for field in fields:
                        if field not in comparison:
                            comparison[field] = {}
                        comparison[field][symbol] = result['data'].get(field)

            if not all_data:
                return {
                    'status': 'failed',
                    'error': 'No data retrieved for any symbols'
                }

            # Export if requested
            if self.export_result:
                export_data = {
                    'symbols': symbols,
                    'data': all_data,
                    'comparison': comparison
                }
                self._export(
                    data=export_data,
                    symbol='comparison',
                    data_category='fundamentals'
                )

            return {
                'status': 'success',
                'data': all_data,
                'comparison': comparison
            }

        except Exception as e:
            return {
                'status': 'failed',
                'error': f'Comparison failed: {str(e)}'
            }

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
