from abc import ABC, abstractmethod
from typing import List, Tuple

from tradingview_scraper.pipelines.selection.base import SelectionContext


class BaseFilter(ABC):
    """
    Abstract interface for candidate veto policies.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Filter identifier (e.g., 'darwinian')."""
        pass

    @abstractmethod
    def apply(self, context: SelectionContext) -> Tuple[SelectionContext, List[str]]:
        """
        Apply filter to context and return vetoed symbols.

        Args:
            context: Current pipeline context.

        Returns:
            Tuple of (modified_context, list_of_vetoed_symbols).
        """
        pass
