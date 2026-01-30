import logging
from typing import Any, List, Optional

from tradingview_scraper.execution.oms import ExecutionEngine, OrderSide, OrderType, UnifiedAccountState, UnifiedOrderRequest, UnifiedOrderResult, UnifiedPosition

# Nautilus Imports (Conditional)
try:
    from nautilus_trader.model.enums import OrderSide as NOrderSide
    from nautilus_trader.model.identifiers import InstrumentId
    from nautilus_trader.model.objects import Price, Quantity

    from tradingview_scraper.portfolio_engines.nautilus_live_strategy import LiveRebalanceStrategy

    HAS_NAUTILUS = True
except ImportError:
    HAS_NAUTILUS = False

logger = logging.getLogger(__name__)


class NautilusOmsAdapter(ExecutionEngine):
    """
    Wraps a running Nautilus Strategy to expose it via Unified OMS.
    Note: Nautilus is event-driven. Accessing state directly from the strategy
    is thread-safe if done carefully, but submitting orders is async.
    """

    def __init__(self, strategy: Any):  # Type 'Any' to avoid import errors if Nautilus missing
        self.strategy = strategy

    def connect(self) -> None:
        # Already connected if strategy is running
        pass

    def disconnect(self) -> None:
        pass

    def get_account_state(self) -> UnifiedAccountState:
        if not HAS_NAUTILUS:
            return UnifiedAccountState(0.0, 0.0)

        # Use strategy's robust NAV logic
        try:
            equity = self.strategy._get_nav()
        except AttributeError:
            # Fallback if _get_nav is missing or fails (though it should be there)
            equity = 0.0

        balance = 0.0
        # Iterate accounts to get cash balance
        # We need to replicate the robust cash access from strategy._get_nav
        # But for now, let's try the simple iteration if strategy._get_nav worked for equity

        # If _get_nav works, it returns TOTAL equity (Cash + Positions)
        # UnifiedAccountState asks for balance (Cash) and equity (Total)

        # We can try to extract cash part separately or reuse strategy logic if we refactor.
        # For now, let's copy the iteration logic from strategy or try accessing accounts.

        # Note: strategy.cache.accounts() returns list of Account objects
        try:
            for acct in self.strategy.cache.accounts():
                for bal in acct.balances():
                    if hasattr(bal, "total"):
                        money = bal.total
                        if hasattr(money, "as_double"):
                            balance += money.as_double()
                        elif hasattr(money, "float_value"):
                            balance += money.float_value()
        except Exception as e:
            logger.error(f"Failed to extract cash balance: {e}")

        return UnifiedAccountState(balance=balance, equity=equity)

    def get_positions(self) -> List[UnifiedPosition]:
        if not HAS_NAUTILUS:
            return []

        unified = []
        # Use strategy.cache.load_positions() instead of portfolio.positions()
        # This returns a dictionary {PositionId: Position}
        try:
            positions_list = self.strategy.cache.positions()
            # Iterate list
            for pos in positions_list:
                # pos is Position object
                inst_id = pos.instrument_id.value
                qty = float(pos.quantity)

                # Check if closed
                if pos.is_closed:
                    continue

                side = OrderSide.BUY if qty > 0 else OrderSide.SELL

                unified.append(
                    UnifiedPosition(
                        symbol=inst_id,  # Or raw symbol? "BTCUSDT.BINANCE"
                        side=side,
                        quantity=abs(qty),
                        avg_price=float(pos.avg_px_open),
                        unrealized_pnl=float(pos.unrealized_pnl),
                        ticket_id=str(pos.id),
                    )
                )
        except Exception as e:
            logger.error(f"Failed to load positions from cache: {e}")

        return unified

    def submit_order(self, order: UnifiedOrderRequest) -> UnifiedOrderResult:
        if not HAS_NAUTILUS:
            return UnifiedOrderResult(id="", status="REJECTED", error="Nautilus missing")

        try:
            instrument_id = InstrumentId.from_str(order.symbol)
            instrument = self.strategy.cache.instrument(instrument_id)

            if not instrument:
                return UnifiedOrderResult(id="", status="REJECTED", error=f"Instrument {order.symbol} not found")

            # Side mapping
            n_side = NOrderSide.BUY if order.side == OrderSide.BUY else NOrderSide.SELL

            # Quantity
            n_qty = Quantity.from_scalar(order.quantity, instrument.size_precision)

            # Create Order
            if order.type == OrderType.MARKET:
                n_order = self.strategy.order_factory.market(instrument_id=instrument.id, order_side=n_side, quantity=n_qty)
            else:
                return UnifiedOrderResult(id="", status="REJECTED", error="Only MARKET supported currently")

            # Submit
            self.strategy.submit_order(n_order)

            return UnifiedOrderResult(id=str(n_order.client_order_id), status="PENDING")

        except Exception as e:
            return UnifiedOrderResult(id="", status="REJECTED", error=str(e))

    def close_position(self, symbol: str, quantity: Optional[float] = None) -> UnifiedOrderResult:
        # Netting logic: Closing means submitting opposing order.
        if not HAS_NAUTILUS:
            return UnifiedOrderResult(id="", status="REJECTED")

        try:
            instrument_id = InstrumentId.from_str(symbol)
            net_pos = self.strategy.portfolio.net_position(instrument_id)

            if net_pos == 0:
                return UnifiedOrderResult(id="", status="REJECTED", error="No position")

            current_qty = float(net_pos)
            close_qty = quantity if quantity else abs(current_qty)

            # Opposing side
            side = OrderSide.SELL if current_qty > 0 else OrderSide.BUY

            return self.submit_order(UnifiedOrderRequest(symbol=symbol, side=side, quantity=close_qty))

        except Exception as e:
            return UnifiedOrderResult(id="", status="REJECTED", error=str(e))

    def close_all(self) -> List[UnifiedOrderResult]:
        if not HAS_NAUTILUS:
            return []
        results = []
        for pos in self.strategy.portfolio.positions():
            res = self.strategy.close_position(pos.instrument_id)
            results.append(UnifiedOrderResult(id="CLOSE_ALL", status="PENDING"))
        return results
