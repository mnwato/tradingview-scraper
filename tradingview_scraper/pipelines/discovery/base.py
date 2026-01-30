from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CandidateMetadata:
    """Standardized candidate schema for all discovery sources."""

    symbol: str
    exchange: str
    asset_type: str  # "spot", "perp", "equity", "etf"
    identity: str = ""  # Unique ID across all venues (e.g. BINANCE:BTCUSDT)
    market_cap_rank: Optional[int] = None
    volume_24h: Optional[float] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.identity:
            return
        if isinstance(self.symbol, str) and ":" in self.symbol:
            self.identity = self.symbol
        else:
            self.identity = f"{self.exchange}:{self.symbol}"


class BaseDiscoveryScanner(ABC):
    """
    Abstract interface for asset discovery scanners.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Scanner identifier (e.g., 'binance_spot')."""
        pass

    @abstractmethod
    def discover(self, params: Dict[str, Any]) -> List[CandidateMetadata]:
        """
        Execute discovery and return candidate list.

        Args:
            params: Scanner-specific parameters (e.g., min_volume, filters).

        Returns:
            List of standardized candidate metadata.
        """
        pass
