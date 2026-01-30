import asyncio
import logging
import random

logger = logging.getLogger(__name__)


class AsyncRetryHandler:
    """
    Handles exponential backoff logic for retrying operations in an async context.
    """

    def __init__(self, max_retries: int = 5, initial_delay: float = 1.0, max_delay: float = 60.0, backoff_factor: float = 2.0, jitter: float = 0.1):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """
        Calculates the delay for a given attempt number with jitter.
        """
        delay = self.initial_delay * (self.backoff_factor**attempt)
        # Apply jitter
        if self.jitter:
            delay += delay * self.jitter * random.uniform(-1, 1)

        return max(0, min(delay, self.max_delay))

    async def sleep(self, attempt: int):
        """
        Asynchronously sleeps for the duration calculated for the given attempt.
        """
        delay = self.get_delay(attempt)
        logger.info(f"Retrying in {delay:.2f} seconds (attempt {attempt + 1}/{self.max_retries})...")
        await asyncio.sleep(delay)
