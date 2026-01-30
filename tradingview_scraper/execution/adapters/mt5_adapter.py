import logging
import os
from typing import List, Optional

from tradingview_scraper.execution.mt5.client import MT5Client, MT5Config
from tradingview_scraper.execution.mt5.execution import MT5ExecutionClient, MT5Order
from tradingview_scraper.execution.oms import ExecutionEngine, OrderSide, OrderType, UnifiedAccountState, UnifiedOrderRequest, UnifiedOrderResult, UnifiedPosition

logger = logging.getLogger(__name__)


class Mt5OmsAdapter(ExecutionEngine):
    """
    Native MT5 Adapter implementation.
    Connects directly using the MetaTrader5 Python library (Windows Only).
    """

    def __init__(self, login: int = 0, password: str = "", server: str = "", path: Optional[str] = None):
        """
        Args:
            login: MT5 account login number.
            password: MT5 account password.
            server: MT5 broker server name.
            path: Path to terminal.exe (optional).
        """
        # Allow loading from env vars if not provided
        self.login = login or int(os.getenv("MT5_LOGIN", "0"))
        self.password = password or os.getenv("MT5_PASSWORD", "")
        self.server = server or os.getenv("MT5_SERVER", "")
        self.path = path or os.getenv("MT5_PATH")

        self.mt5_client = MT5Client()
        self.exec_client = MT5ExecutionClient(self.mt5_client)

    def connect(self) -> None:
        """Establishes connection to the MT5 terminal."""
        config = MT5Config(login=self.login, password=self.password, server=self.server, path=self.path)
        success = self.mt5_client.initialize(config)
        if not success:
            logger.error("Failed to connect to MT5.")
            # We might want to raise an exception here or just log
            # Usually strict adapters should raise
            # raise ConnectionError("Failed to initialize MT5")

    def disconnect(self) -> None:
        """Terminates connection."""
        self.mt5_client.shutdown()

    def get_account_state(self) -> UnifiedAccountState:
        info = self.exec_client.get_account_info()
        if not info:
            # If not connected or error, return empty state
            return UnifiedAccountState(balance=0.0, equity=0.0)

        return UnifiedAccountState(
            balance=float(info.get("balance", 0.0)),
            equity=float(info.get("equity", 0.0)),
            used_margin=float(info.get("margin", 0.0)),
            available_margin=float(info.get("margin_free", 0.0)),
            currency=info.get("currency", "USD"),
        )

    def get_positions(self) -> List[UnifiedPosition]:
        raw_positions = self.exec_client.get_positions()
        unified = []

        for p in raw_positions:
            # p: {ticket, symbol, type, volume, price_open, profit, ...}
            # Map type (0=BUY, 1=SELL usually in MT5)
            # We can use the client's knowledge or just raw integers if we know them.
            # MT5 constant: 0=BUY, 1=SELL
            side = OrderSide.BUY if p.get("type") == 0 else OrderSide.SELL

            unified.append(
                UnifiedPosition(
                    symbol=p.get("symbol", ""),
                    side=side,
                    quantity=float(p.get("volume", 0.0)),
                    avg_price=float(p.get("price_open", 0.0)),
                    unrealized_pnl=float(p.get("profit", 0.0)),
                    ticket_id=str(p.get("ticket", "")),
                )
            )
        return unified

    def submit_order(self, order: UnifiedOrderRequest) -> UnifiedOrderResult:
        # Map Unified Order to MT5 Order

        # Determine order type string
        # Unified: side=BUY/SELL, type=MARKET/LIMIT
        mt5_type_str = order.side.value  # "BUY" or "SELL"

        if order.type == OrderType.LIMIT:
            mt5_type_str += "_LIMIT"  # "BUY_LIMIT"
        elif order.type == OrderType.STOP:
            mt5_type_str += "_STOP"
        # MARKET is default "BUY"/"SELL"

        mt5_order = MT5Order(
            symbol=order.symbol,
            order_type=mt5_type_str,
            volume=order.quantity,
            price=order.price,
            comment=order.ref_id or "",
            magic=123456,  # Should be configurable?
        )

        # For STOP/LIMIT, price is required.
        # wrapper.submit_order handles price logic.

        resp = self.exec_client.submit_order(mt5_order)

        # Resp: {retcode, ticket, comment, ...}
        # MT5 retcode 10009 is TRADE_RETCODE_DONE
        retcode = resp.get("retcode")

        if retcode != 10009:  # DONE
            # Check for partial filling or placement?
            # 10008 is PLACED (for pending)
            if retcode == 10008:
                ticket = str(resp.get("order", ""))  # For pending orders, key is 'order' usually
                return UnifiedOrderResult(id=ticket, status="PENDING")

            error_msg = f"MT5 Error {retcode}: {resp.get('comment')}"
            return UnifiedOrderResult(id="", status="REJECTED", error=error_msg)

        # Success (Deal executed)
        # For deals, the order ticket is in 'order' or 'deal'?
        # order_send returns result structure. 'order' field is the order ticket.
        ticket = str(resp.get("order", ""))

        # We can try to get fill info immediately or just return filled
        return UnifiedOrderResult(id=ticket, status="FILLED", filled_qty=resp.get("volume", 0.0), avg_fill_price=resp.get("price", 0.0))

    def close_position(self, symbol: str, quantity: Optional[float] = None) -> UnifiedOrderResult:
        # Find position ticket for symbol
        positions = self.get_positions()
        target = next((p for p in positions if p.symbol == symbol), None)

        if not target:
            return UnifiedOrderResult(id="", status="REJECTED", error="Position not found")

        ticket = int(target.ticket_id) if target.ticket_id else 0

        resp = self.exec_client.close_position(ticket=ticket, volume=quantity)

        retcode = resp.get("retcode")
        if retcode != 10009:
            error_msg = f"MT5 Error {retcode}: {resp.get('comment')}"
            return UnifiedOrderResult(id=str(ticket), status="REJECTED", error=error_msg)

        return UnifiedOrderResult(id=str(ticket), status="FILLED")

    def close_all(self) -> List[UnifiedOrderResult]:
        results = self.exec_client.close_all_positions()
        unified_results = []
        for res in results:
            # Map raw result to UnifiedOrderResult
            ticket = str(res.get("order", ""))
            retcode = res.get("retcode")
            if retcode == 10009:
                unified_results.append(UnifiedOrderResult(id=ticket, status="FILLED"))
            else:
                unified_results.append(UnifiedOrderResult(id=ticket, status="REJECTED", error=res.get("comment")))
        return unified_results
