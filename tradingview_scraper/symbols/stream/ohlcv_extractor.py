"""TradingView OHLCV data extractor with reusable functions"""

import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from websocket import create_connection

# Relative import for use within the package
from .price import RealTimeData


class OHLCVExtractor(RealTimeData):
    """Custom OHLCV data extractor with reusable functions"""
    
    def __init__(self, debug_mode: bool = False):
        # Don't call super().__init__() to avoid opening WebSocket during construction
        # Configure necessary attributes that would normally be set by the base class
        self.request_header = {
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9,fa;q=0.8",
            "Cache-Control": "no-cache",
            "Connection": "Upgrade",
            "Host": "data.tradingview.com",
            "Origin": "https://www.tradingview.com",
            "Pragma": "no-cache",
            "Sec-WebSocket-Extensions": "permessage-deflate; client_max_window_bits",
            "Upgrade": "websocket",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"
            ),
        }
        # Keep same URL as base class without opening connection yet
        self.ws_url = "wss://data.tradingview.com/socket.io/websocket?from=screener%2F"
        self.validate_url = (
            "https://scanner.tradingview.com/symbol?symbol={exchange}%3A{symbol}&fields=market&no_404=false"
        )
        self.ws = None  # Will be created per call in get_ohlcv_data

        self.timeout_seconds = 30  # Timeout to avoid infinite loops
        self.debug_mode = debug_mode
        
        # Configure logging level based on debug mode
        if not debug_mode:
            # Silence debug logs from specific library, not the root logger
            logging.getLogger('tradingview_scraper').setLevel(logging.WARNING)
            logging.getLogger('websocket').setLevel(logging.WARNING)

    def get_ohlcv_data(self, symbol: str, timeframe: str = "1D", bars_count: int = 10, 
                       timeout: int = 30) -> Dict[str, Any]:
        """
        Retrieves OHLCV data for a specific symbol and returns it in JSON format.
        
        Args:
            symbol (str): Symbol in 'EXCHANGE:SYMBOL' format (e.g., 'BINANCE:BTCUSDT')
            timeframe (str): Desired timeframe ('1', '5', '15', '30', '60', '1D', '1W', '1M')
            bars_count (int): Number of historical bars to retrieve
            timeout (int): Maximum wait time in seconds
            
        Returns:
            Dict[str, Any]: Dictionary with OHLCV data and metadata
        """
        start_time = time.time()
        
        result = {
            "success": False,
            "symbol": symbol,
            "timeframe": timeframe,
            "bars_requested": bars_count,
            "bars_received": 0,
            "data": [],
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "processing_time_seconds": 0,
                "error": None
            }
        }
        
        try:
            # NEW: recreate WebSocket connection per call to avoid reusing closed sockets
            try:
                if getattr(self, "ws", None) is not None:
                    try:
                        self.ws.close() if self.ws else None
                    except Exception:
                        pass
                self.ws = create_connection(self.ws_url, headers=self.request_header)
            except Exception as conn_e:
                result["metadata"]["error"] = f"Error initializing WebSocket: {conn_e}"
                return result
            
            # Generate sessions
            quote_session = self.generate_session(prefix="qs_")
            chart_session = self.generate_session(prefix="cs_")
            
            # Initialize sessions
            self._initialize_sessions(quote_session, chart_session)
            self._add_symbol_to_sessions_custom(quote_session, chart_session, symbol, timeframe, bars_count)
            
            # Get data
            data_generator = self.get_data()
            
            packet_count = 0
            for packet in data_generator:
                packet_count += 1
                
                # Check timeout
                if time.time() - start_time > timeout:
                    result["metadata"]["error"] = f"Timeout after {timeout} seconds"
                    if self.debug_mode:
                        print(f"⏰ Timeout reached after {timeout} seconds")
                    break
                
                if isinstance(packet, dict) and 'm' in packet:
                    if packet['m'] == 'timescale_update':
                        # Extract OHLC data
                        ohlc_data = self._extract_ohlc_from_packet(packet)
                        if ohlc_data:
                            result["success"] = True
                            result["data"] = ohlc_data
                            result["bars_received"] = len(ohlc_data)
                            break
                    
                    elif packet['m'] in ['protocol_error', 'critical_error']:
                        error_msg = packet.get('p', 'Unknown error')
                        result["metadata"]["error"] = f"Server error: {error_msg}"
                        break
                
                # Limit processed packets
                if packet_count >= 50:
                    result["metadata"]["error"] = "No OHLC data found in 50 packets"
                    break
                    
        except Exception as e:
            result["metadata"]["error"] = str(e)
        
        finally:
            result["metadata"]["processing_time_seconds"] = round(time.time() - start_time, 2)
            
        return result
    
    def _add_symbol_to_sessions_custom(self, quote_session: str, chart_session: str, 
                                     exchange_symbol: str, timeframe: str, bars_count: int):
        """
        Adds the symbol to sessions with custom timeframe and bar count.
        """
        resolve_symbol = json.dumps({"adjustment": "splits", "symbol": exchange_symbol})
        
        self.send_message("quote_add_symbols", [quote_session, f"={resolve_symbol}"])
        self.send_message("resolve_symbol", [chart_session, "sds_sym_1", f"={resolve_symbol}"])
        self.send_message("create_series", [chart_session, "sds_1", "s1", "sds_sym_1", timeframe, bars_count, ""]) 
        self.send_message("quote_fast_symbols", [quote_session, exchange_symbol])
        self.send_message("create_study", [chart_session, "st1", "st1", "sds_1", 
                            "Volume@tv-basicstudies-246", {"length": 20, "col_prev_close": "false"}])
        self.send_message("quote_hibernate_all", [quote_session])
    
    def _extract_ohlc_from_packet(self, packet: Dict) -> List[Dict[str, Any]]:
        """
        Extracts OHLC data from a response packet.
        
        Returns:
            List[Dict]: List of OHLC bars with standard format
        """
        ohlc_bars = []
        ohlc_series = []  # Initialize to avoid unbound variable error
        
        try:
            if 'p' in packet and len(packet['p']) > 1:
                p_data = packet['p']
                
                if isinstance(p_data, list):
                    for item in p_data:
                        if isinstance(item, dict) and 'sds_1' in item:
                            sds_data = item['sds_1']
                            
                            if isinstance(sds_data, dict) and 's' in sds_data:
                                ohlc_series = sds_data['s']
                                
                                for bar in ohlc_series:
                                    if isinstance(bar, dict) and 'v' in bar and len(bar['v']) >= 6:
                                        timestamp = bar['v'][0]
                                        open_price = bar['v'][1]
                                        high_price = bar['v'][2]
                                        low_price = bar['v'][3]
                                        close_price = bar['v'][4]
                                        volume = bar['v'][5]
                                        
                                        # Calculate percentage change
                                        change_percent = 0
                                        if open_price > 0:
                                            change_percent = ((close_price - open_price) / open_price) * 100
                                        
                                        ohlc_bar = {
                                            "timestamp": timestamp,
                                            "datetime": datetime.fromtimestamp(timestamp).isoformat(),
                                            "date": datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d'),
                                            "time": datetime.fromtimestamp(timestamp).strftime('%H:%M:%S'),
                                            "open": open_price,
                                            "high": high_price,
                                            "low": low_price,
                                            "close": close_price,
                                            "volume": volume,
                                            "change_percent": round(change_percent, 4)
                                        }
                                        
                                        ohlc_bars.append(ohlc_bar)
                                        
                                break  # Only process the first data set found
        except Exception as e:
            print(f"Error extracting OHLC data: {e}")
            
        return ohlc_bars
    
    def get_multiple_symbols_ohlcv(self, symbols: List[str], timeframe: str = "1D", 
                                  bars_count: int = 10, timeout: int = 30) -> Dict[str, Any]:
        """
        Retrieves OHLCV data for multiple symbols.
        
        Args:
            symbols (List[str]): List of symbols in 'EXCHANGE:SYMBOL' format
            timeframe (str): Desired timeframe
            bars_count (int): Number of bars per symbol
            timeout (int): Timeout per symbol
            
        Returns:
            Dict[str, Any]: Dictionary with data for all symbols
        """
        results = {
            "success": True,
            "total_symbols": len(symbols),
            "successful_symbols": 0,
            "failed_symbols": 0,
            "timeframe": timeframe,
            "bars_requested": bars_count,
            "timestamp": datetime.now().isoformat(),
            "data": {},
            "errors": {}
        }
        
        for symbol in symbols:
            if self.debug_mode:
                print(f"Processing {symbol}...")
            
            try:
                # Create new instance for each symbol to avoid conflicts
                extractor = OHLCVExtractor(debug_mode=self.debug_mode)
                symbol_data = extractor.get_ohlcv_data(symbol, timeframe, bars_count, timeout)
                
                if symbol_data["success"]:
                    results["data"][symbol] = symbol_data
                    results["successful_symbols"] += 1
                else:
                    results["errors"][symbol] = symbol_data["metadata"]["error"]
                    results["failed_symbols"] += 1
                    
            except Exception as e:
                results["errors"][symbol] = str(e)
                results["failed_symbols"] += 1
            
            # Small pause between symbols
            time.sleep(1)
        
        if results["failed_symbols"] > 0:
            results["success"] = False
            
        return results


# Convenience functions for direct use
def get_ohlcv_json(symbol: str, timeframe: str = "1D", bars_count: int = 10, 
                   save_to_file: bool = False, filename: Optional[str] = None, debug: bool = False) -> Dict[str, Any]:
    """
    Convenience function to retrieve OHLCV data for a symbol.
    """
    extractor = OHLCVExtractor(debug_mode=debug)
    result = extractor.get_ohlcv_data(symbol, timeframe, bars_count)
    
    if save_to_file:
        if not filename:
            safe_symbol = symbol.replace(':', '_')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"ohlcv_{safe_symbol}_{timeframe}_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        if debug:
            print(f"Data saved to: {filename}")
    
    return result


def get_multiple_ohlcv_json(symbols: List[str], timeframe: str = "1D", bars_count: int = 10,
                           save_to_file: bool = False, filename: Optional[str] = None, debug: bool = False) -> Dict[str, Any]:
    """
    Convenience function to retrieve OHLCV data for multiple symbols.
    """
    extractor = OHLCVExtractor(debug_mode=debug)
    result = extractor.get_multiple_symbols_ohlcv(symbols, timeframe, bars_count)
    
    if save_to_file:
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"ohlcv_multiple_{timeframe}_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        if debug:
            print(f"Data saved to: {filename}")
    
    return result
