"""
OCR Rate Limiter - Azure Computer Vision API Rate Limiting

Prevents quota exhaustion for Azure OCR API by enforcing rate limits
and batch size restrictions based on configuration.

Rate Limits:
- Azure Free Tier: 20 calls per minute (default)
- Azure Paid Tier: Configurable based on subscription

Configuration:
    AZURE_OCR_RATE_LIMIT=20/minute  # Default for free tier
    AZURE_OCR_BATCH_SIZE=1          # Process one image at a time for free tier
"""

import logging
import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from collections import deque
from threading import Lock

from app.core.config import settings

logger = logging.getLogger(__name__)


class AzureOCRRateLimiter:
    """
    Rate limiter for Azure OCR API calls.

    Enforces rate limits and batch size restrictions to prevent quota exhaustion.

    Attributes:
        rate_limit_config (str): Rate limit configuration (e.g., "20/minute", "100/hour")
        batch_size (int): Maximum number of documents to process in parallel
        call_timestamps (deque): Timestamps of recent API calls
        lock (Lock): Thread-safe access to timestamps
    """

    def __init__(self, rate_limit_config: Optional[str] = None, batch_size: Optional[int] = None):
        """
        Initialize Azure OCR rate limiter.

        Args:
            rate_limit_config: Rate limit configuration string (e.g., "20/minute")
                             If None, uses settings.AZURE_OCR_RATE_LIMIT
            batch_size: Maximum number of documents to process in parallel
                       If None, uses settings.AZURE_OCR_BATCH_SIZE
        """
        self.rate_limit_config = rate_limit_config or settings.AZURE_OCR_RATE_LIMIT
        self.batch_size = batch_size or settings.AZURE_OCR_BATCH_SIZE

        # Parse rate limit configuration
        self.max_calls, self.time_window_seconds = self._parse_rate_limit(self.rate_limit_config)

        # Track API call timestamps for rate limiting
        self.call_timestamps: deque = deque(maxlen=self.max_calls)
        self.lock = Lock()

        logger.info(
            f"AzureOCRRateLimiter initialized: "
            f"{self.max_calls} calls per {self.time_window_seconds}s, "
            f"batch_size={self.batch_size}"
        )

    @staticmethod
    def _parse_rate_limit(rate_limit_str: str) -> tuple:
        """
        Parse rate limit configuration string.

        Args:
            rate_limit_str: Configuration string (e.g., "20/minute", "100/hour")

        Returns:
            tuple: (max_calls, time_window_seconds)

        Raises:
            ValueError: If configuration string format is invalid
        """
        try:
            # Split by "/" to separate count and time unit
            parts = rate_limit_str.strip().split("/")
            if len(parts) != 2:
                raise ValueError(f"Invalid rate limit format: {rate_limit_str}")

            max_calls = int(parts[0].strip())

            # Parse time unit
            time_unit = parts[1].strip().lower()
            if time_unit == "second" or time_unit == "seconds":
                time_window_seconds = 1
            elif time_unit == "minute" or time_unit == "minutes":
                time_window_seconds = 60
            elif time_unit == "hour" or time_unit == "hours":
                time_window_seconds = 3600
            elif time_unit == "day" or time_unit == "days":
                time_window_seconds = 86400
            else:
                raise ValueError(f"Unknown time unit: {time_unit}")

            return max_calls, time_window_seconds

        except ValueError as e:
            logger.error(f"Error parsing rate limit '{rate_limit_str}': {e}")
            # Fallback to safe defaults (20 calls per minute)
            return 20, 60

    def is_within_limit(self) -> bool:
        """
        Check if a new API call is within rate limit.

        Returns:
            bool: True if call is allowed, False if rate limit would be exceeded
        """
        with self.lock:
            now = time.time()

            # Remove old timestamps outside the time window
            while self.call_timestamps and self.call_timestamps[0] < now - self.time_window_seconds:
                self.call_timestamps.popleft()

            # Check if we can make another call
            if len(self.call_timestamps) < self.max_calls:
                return True

            return False

    def wait_if_needed(self) -> float:
        """
        Wait if necessary to comply with rate limit.

        Returns:
            float: Time waited in seconds
        """
        with self.lock:
            now = time.time()

            # Remove old timestamps outside the time window
            while self.call_timestamps and self.call_timestamps[0] < now - self.time_window_seconds:
                self.call_timestamps.popleft()

            # If we're at limit, calculate wait time
            if len(self.call_timestamps) >= self.max_calls:
                # Find the oldest timestamp in the window
                oldest_timestamp = self.call_timestamps[0]
                wait_until = oldest_timestamp + self.time_window_seconds
                wait_seconds = max(0, wait_until - now)

                if wait_seconds > 0:
                    logger.info(
                        f"Azure OCR rate limit reached. "
                        f"Waiting {wait_seconds:.2f}s ({len(self.call_timestamps)}/{self.max_calls} calls)"
                    )
                    return wait_seconds

            return 0.0

    def record_call(self):
        """
        Record an API call to track rate limit.

        Should be called after a successful Azure OCR API call.
        """
        with self.lock:
            self.call_timestamps.append(time.time())
            logger.debug(f"Azure OCR call recorded ({len(self.call_timestamps)}/{self.max_calls})")

    async def acquire_slot(self) -> None:
        """
        Wait for and acquire a rate limit slot.

        Asynchronously waits if necessary to comply with rate limit.

        Example:
            >>> limiter = AzureOCRRateLimiter()
            >>> await limiter.acquire_slot()
            >>> # Now safe to call Azure OCR API
        """
        while True:
            wait_seconds = self.wait_if_needed()

            if wait_seconds <= 0:
                # Slot acquired
                self.record_call()
                return

            # Wait before trying again
            await asyncio.sleep(min(wait_seconds, 1.0))

    def get_status(self) -> Dict[str, any]:
        """
        Get current rate limiter status.

        Returns:
            Dictionary with rate limit status information
        """
        with self.lock:
            now = time.time()

            # Remove old timestamps outside the time window
            active_calls = [ts for ts in self.call_timestamps if ts >= now - self.time_window_seconds]

            return {
                "rate_limit_config": self.rate_limit_config,
                "max_calls_per_window": self.max_calls,
                "time_window_seconds": self.time_window_seconds,
                "batch_size": self.batch_size,
                "current_calls_in_window": len(active_calls),
                "remaining_calls": self.max_calls - len(active_calls),
                "is_within_limit": len(active_calls) < self.max_calls,
            }

    def estimate_processing_time(self, num_documents: int) -> float:
        """
        Estimate time to process multiple documents given rate limit.

        Args:
            num_documents: Number of documents to process

        Returns:
            float: Estimated time in seconds
        """
        # Number of batches needed
        num_batches = (num_documents + self.batch_size - 1) // self.batch_size

        # Minimum time per batch is the average time between rate limit slots
        time_per_batch = self.time_window_seconds / self.max_calls

        # Estimated total time
        estimated_time = num_batches * time_per_batch

        return estimated_time


# Global rate limiter instance
_azure_ocr_rate_limiter: Optional[AzureOCRRateLimiter] = None


def get_azure_ocr_rate_limiter() -> AzureOCRRateLimiter:
    """
    Get or create the global Azure OCR rate limiter instance.

    Returns:
        AzureOCRRateLimiter: Global rate limiter instance
    """
    global _azure_ocr_rate_limiter
    if _azure_ocr_rate_limiter is None:
        _azure_ocr_rate_limiter = AzureOCRRateLimiter()
    return _azure_ocr_rate_limiter


__all__ = [
    "AzureOCRRateLimiter",
    "get_azure_ocr_rate_limiter",
]
