"""
Nautilus Live Execution Configuration (Bridge L6)

This module provides the configuration scaffolding for deploying the
NautilusRebalanceStrategy to live venues (Binance, IBKR).
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, Literal, Optional

try:
    from nautilus_trader.config import (
        LiveRiskEngineConfig,
        LoggingConfig,
        RiskEngineConfig,
        TradingNodeConfig,
    )

    # Execution Clients
    try:
        from nautilus_trader.adapters.binance.config import BinanceDataClientConfig, BinanceExecClientConfig
    except ImportError:
        BinanceExecClientConfig: Any = None
        BinanceDataClientConfig: Any = None

    try:
        from nautilus_trader.adapters.interactive_brokers.config import InteractiveBrokersDataClientConfig, InteractiveBrokersExecClientConfig
    except ImportError:
        InteractiveBrokersExecClientConfig: Any = None
        InteractiveBrokersDataClientConfig: Any = None

    HAS_NAUTILUS = True
except ImportError:
    HAS_NAUTILUS = False
    # Define dummy classes for static analysis / runtime safety when missing
    TradingNodeConfig: Any = None
    LoggingConfig: Any = None
    RiskEngineConfig: Any = None
    LiveRiskEngineConfig: Any = None
    BinanceExecClientConfig: Any = None
    BinanceDataClientConfig: Any = None
    InteractiveBrokersExecClientConfig: Any = None
    InteractiveBrokersDataClientConfig: Any = None

from tradingview_scraper.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class LiveExchangeConfig:
    """
    Holds credentials and connection details for a live venue.
    """

    venue: str
    mode: Literal["LIVE", "SHADOW"] = "SHADOW"
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    account_id: str = ""
    gateway_host: str = "127.0.0.1"
    gateway_port: int = 4001  # IBKR Default

    def __post_init__(self):
        if not self.api_key:
            self.api_key = os.environ.get(f"{self.venue.upper()}_API_KEY")
        if not self.api_secret:
            self.api_secret = os.environ.get(f"{self.venue.upper()}_API_SECRET")

    @property
    def is_valid(self) -> bool:
        if self.mode == "SHADOW":
            return True  # Shadow mode is data-only or simulated
        if self.venue.upper() == "BINANCE":
            return bool(self.api_key and self.api_secret)
        if self.venue.upper() == "IBKR":
            return True  # IBKR relies on Gateway connection
        return False


def build_live_node_config(trader_id: str, exchange: LiveExchangeConfig, log_level: str = "INFO") -> Optional[Any]:
    """
    Constructs a TradingNodeConfig for the specified live venue.
    """
    if not HAS_NAUTILUS or TradingNodeConfig is None:
        logger.warning("NautilusTrader not installed correctly.")
        return None

    if not exchange.is_valid:
        logger.error(f"Invalid credentials for {exchange.venue}")
        return None

    venue_str = exchange.venue.upper()
    exec_client_config = None
    data_client_config = None

    # 1. Configure Venue Clients
    if venue_str == "BINANCE":
        if BinanceDataClientConfig:
            data_client_config = BinanceDataClientConfig(
                api_key=exchange.api_key,
                api_secret=exchange.api_secret,
                us=False,  # Assuming Global
            )

            if exchange.mode == "LIVE" and BinanceExecClientConfig:
                exec_client_config = BinanceExecClientConfig(api_key=exchange.api_key, api_secret=exchange.api_secret, us=False)
        else:
            logger.error("Binance adapter not found")
            return None

    elif venue_str == "IBKR":
        if InteractiveBrokersDataClientConfig:
            # Note: IBKR Config arguments verified via documentation/source would be better
            # Using generic kwargs or assuming standard init
            try:
                data_client_config = InteractiveBrokersDataClientConfig(gateway_host=exchange.gateway_host, gateway_port=exchange.gateway_port, client_id=1, read_only=False)

                if exchange.mode == "LIVE" and InteractiveBrokersExecClientConfig:
                    exec_client_config = InteractiveBrokersExecClientConfig(gateway_host=exchange.gateway_host, gateway_port=exchange.gateway_port, client_id=1, account_id=exchange.account_id or None)
            except Exception as e:
                logger.error(f"Failed to config IBKR: {e}")
                return None
        else:
            logger.error("IBKR adapter not found")
            return None

    else:
        logger.error(f"Unsupported venue: {venue_str}")
        return None

    # 2. Configure Shadow Mode logic (Placeholder)
    if exchange.mode == "SHADOW":
        logger.warning("SHADOW mode requested. Configuring Data-Only node.")
        exec_client_config = None

    # 3. Build Node Config
    settings = get_settings()
    log_dir = settings.artifacts_dir / "logs" / "live"

    node_config = TradingNodeConfig(
        trader_id=trader_id,
        logging=LoggingConfig(log_level=log_level, log_file_format="json", log_directory=str(log_dir), log_component_levels={"Nautilus": log_level}),
        data_clients={venue_str: data_client_config} if data_client_config else {},
        exec_clients={venue_str: exec_client_config} if exec_client_config else {},
        risk_engine=LiveRiskEngineConfig(
            max_order_submit_rate="20/1s",
            max_order_modify_rate="20/1s",
        ),
    )

    return node_config


class NautilusLiveEngine:
    """
    Facade for managing the lifecycle of a Nautilus TradingNode.
    """

    def __init__(self, venue: str, mode: Literal["LIVE", "SHADOW"] = "SHADOW", log_level: str = "INFO"):
        self.venue = venue
        self.mode = mode
        self.log_level = log_level
        self.config = LiveExchangeConfig(venue=venue, mode=mode)
        self.node = None

    def build(self) -> Optional[Any]:
        """Builds the TradingNode instance."""
        if not HAS_NAUTILUS:
            logger.error("Nautilus not installed")
            return None

        node_config = build_live_node_config(trader_id=f"TRADER-{self.venue}-{self.mode}", exchange=self.config, log_level=self.log_level)

        if node_config:
            try:
                from nautilus_trader.live.node import TradingNode

                self.node = TradingNode(config=node_config)
                # Ensure internal components (clients) are built
                self.node.build()

                logger.info(f"Built TradingNode for {self.venue} ({self.mode})")
                return self.node
            except Exception as e:
                logger.error(f"Failed to instantiate TradingNode: {e}")
                return None
        return None

    def run(self):
        """Starts the node (blocking)."""
        if self.node:
            logger.info("Starting TradingNode...")
            self.node.run()
        else:
            logger.error("Node not built. Call build() first.")
