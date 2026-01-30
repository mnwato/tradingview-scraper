"""
MT5 Client Module.

This module provides the core singleton client for connecting to the MetaTrader 5 terminal.
It handles strict import guarding for Linux/CI environments and ensures thread safety.
"""

import logging
import threading
from dataclasses import dataclass
from typing import Any, Dict, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Import Guard
try:
    import MetaTrader5 as mt5  # type: ignore

    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    from unittest.mock import MagicMock

    mt5 = MagicMock()
    # Log only once at module level if needed, or rely on Client to warn.


class MT5EnvironmentError(EnvironmentError):
    """Raised when MT5 operations are attempted in an unsupported environment."""

    pass


@dataclass
class MT5Config:
    """Configuration for MT5 connection."""

    login: int
    password: str
    server: str
    path: Optional[str] = None
    timeout: int = 60000


class MT5Client:
    """
    Thread-safe Singleton managing the MetaTrader5 terminal connection.
    """

    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(MT5Client, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Prevent re-initialization if already done
        if getattr(self, "_initialized", False):
            return

        self.connected = False
        self._initialized = True

        if not MT5_AVAILABLE:
            logger.warning("MetaTrader5 library not found. MT5 functionality will be disabled.")

    def initialize(self, config: MT5Config) -> bool:
        """
        Initializes the MT5 terminal connection.

        Args:
            config: MT5Config object with credentials and path.

        Returns:
            bool: True if connection successful, False otherwise.
        """
        if not MT5_AVAILABLE:
            logger.error("Cannot initialize MT5: Library not installed.")
            return False

        with self._lock:
            if self.connected:
                logger.debug("MT5 Client already connected.")
                return True

            # Initialize options
            init_params = {"login": config.login, "password": config.password, "server": config.server, "timeout": config.timeout}
            if config.path:
                init_params["path"] = config.path

            # Attempt initialization
            if not mt5.initialize(**init_params):
                error_code = mt5.last_error()
                logger.error(f"MT5 initialization failed, error code: {error_code}")
                self.connected = False
                return False

            logger.info(f"MT5 Client connected to {config.server} as {config.login}")
            self.connected = True
            return True

    def shutdown(self):
        """Shuts down the connection."""
        with self._lock:
            if MT5_AVAILABLE and self.connected:
                mt5.shutdown()
                self.connected = False
                logger.info("MT5 Client disconnected.")

    def get_terminal_info(self) -> Optional[Dict[str, Any]]:
        """Returns terminal info if connected."""
        if not self.check_connected():
            return None

        info = mt5.terminal_info()
        return info._asdict() if info else None

    def check_connected(self) -> bool:
        """Checks if connected to MT5, safely."""
        if not MT5_AVAILABLE:
            return False
        return self.connected

    @property
    def lib(self):
        """Access the underlying mt5 library (or mock)."""
        return mt5
