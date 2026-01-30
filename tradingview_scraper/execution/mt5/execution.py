"""
MT5 Execution Client.

Responsible for sending orders and tracking trade status.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from tradingview_scraper.execution.mt5.client import MT5Client

logger = logging.getLogger(__name__)


@dataclass
class MT5Order:
    """Internal MT5 Order structure."""

    symbol: str
    order_type: str  # 'BUY', 'SELL', 'BUY_LIMIT', 'SELL_LIMIT'
    volume: float
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    comment: str = ""
    magic: int = 0
    type_filling: Optional[int] = None  # Will default if None


class MT5ExecutionClient:
    """
    Responsible for sending orders and tracking trade status.
    """

    def __init__(self, mt5_client: MT5Client):
        self.client = mt5_client

    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Fetches account info (Balance, Equity, Margin)."""
        if not self.client.check_connected():
            return None

        mt5 = self.client.lib
        info = mt5.account_info()
        if info is None:
            logger.error("Failed to get account info")
            return None

        return info._asdict()

    def get_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetches open positions, optionally filtered by symbol."""
        if not self.client.check_connected():
            return []

        mt5 = self.client.lib
        if symbol:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()

        if positions is None:
            # error code?
            if mt5.last_error() != (1, "Success"):  # 1 is not usually success code in mt5, usually 0 or similar but generic check
                pass  # positions_get returns None on error, or empty tuple if none?
                # Actually documentation says None on error.
            return []

        return [pos._asdict() for pos in positions]

    def get_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetches active pending orders."""
        if not self.client.check_connected():
            return []

        mt5 = self.client.lib
        if symbol:
            orders = mt5.orders_get(symbol=symbol)
        else:
            orders = mt5.orders_get()

        if orders is None:
            return []

        return [o._asdict() for o in orders]

    def submit_order(self, order: MT5Order) -> Dict[str, Any]:
        """
        Submits an order to MT5.

        Returns:
            Dict with result info (retcode, ticket, comment, etc.)
        """
        if not self.client.check_connected():
            return {"retcode": -1, "comment": "Not connected"}

        mt5 = self.client.lib

        # Map string type to MT5 constant
        mt5_type = self._map_order_type(order.order_type)
        if mt5_type is None:
            return {"retcode": -1, "comment": f"Invalid order type: {order.order_type}"}

        action = mt5.TRADE_ACTION_DEAL
        if "LIMIT" in order.order_type or "STOP" in order.order_type:
            action = mt5.TRADE_ACTION_PENDING

        request = {
            "action": action,
            "symbol": order.symbol,
            "volume": order.volume,
            "type": mt5_type,
            "magic": order.magic,
            "comment": order.comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": order.type_filling if order.type_filling is not None else mt5.ORDER_FILLING_IOC,
        }

        if order.price:
            request["price"] = order.price

        # If market order, we might need to get current ask/bid for price field if required by strict servers,
        # but usually 0 or missing is fine for market unless execution mode requires it.
        # However, MT5 python docs say for MARKET buy/sell, price should be current ask/bid.
        if action == mt5.TRADE_ACTION_DEAL and not order.price:
            tick = mt5.symbol_info_tick(order.symbol)
            if tick:
                if mt5_type == mt5.ORDER_TYPE_BUY:
                    request["price"] = tick.ask
                elif mt5_type == mt5.ORDER_TYPE_SELL:
                    request["price"] = tick.bid

        if order.stop_loss:
            request["sl"] = order.stop_loss
        if order.take_profit:
            request["tp"] = order.take_profit

        result = mt5.order_send(request)

        if result is None:
            return {"retcode": -1, "comment": "order_send failed (returned None)"}

        return result._asdict()

    def close_position(self, ticket: int, volume: Optional[float] = None) -> Dict[str, Any]:
        """
        Closes a position by ticket.
        """
        if not self.client.check_connected():
            return {"retcode": -1, "comment": "Not connected"}

        mt5 = self.client.lib

        # Get position details to know symbol and type
        positions = mt5.positions_get(ticket=ticket)
        if not positions:
            return {"retcode": -1, "comment": "Position not found"}

        pos = positions[0]
        symbol = pos.symbol
        pos_type = pos.type  # 0 for BUY, 1 for SELL

        # Determine opposite type
        if pos_type == mt5.POSITION_TYPE_BUY:
            order_type = mt5.ORDER_TYPE_SELL
            price_type = "bid"
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price_type = "ask"

        vol_to_close = volume if volume else pos.volume

        # Get current price
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return {"retcode": -1, "comment": "Could not get price"}

        price = getattr(tick, price_type)

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": vol_to_close,
            "type": order_type,
            "position": ticket,
            "price": price,
            "magic": pos.magic,
            "comment": "Close position",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result is None:
            return {"retcode": -1, "comment": "order_send failed"}

        return result._asdict()

    def close_all_positions(self) -> List[Dict[str, Any]]:
        """Closes all open positions."""
        positions = self.get_positions()
        results = []
        for p in positions:
            res = self.close_position(p["ticket"], p["volume"])
            results.append(res)
        return results

    def _map_order_type(self, type_str: str) -> Optional[int]:
        """Maps string order type to MT5 constant."""
        mt5 = self.client.lib
        ts = type_str.upper()

        mapping = {
            "BUY": mt5.ORDER_TYPE_BUY,
            "SELL": mt5.ORDER_TYPE_SELL,
            "BUY_LIMIT": mt5.ORDER_TYPE_BUY_LIMIT,
            "SELL_LIMIT": mt5.ORDER_TYPE_SELL_LIMIT,
            "BUY_STOP": mt5.ORDER_TYPE_BUY_STOP,
            "SELL_STOP": mt5.ORDER_TYPE_SELL_STOP,
        }
        return mapping.get(ts)
