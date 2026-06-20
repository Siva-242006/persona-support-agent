"""Small retry helper for transient Gemini API failures."""

from __future__ import annotations

from collections.abc import Callable
import random
import time
from typing import TypeVar


T = TypeVar("T")


def call_with_backoff(operation: Callable[[], T], max_retries: int = 3) -> T:
    """Run an API operation with short exponential backoff.

    This protects the interactive response from brief rate-limit or network spikes
    without hiding real configuration problems after the final retry.
    """
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            return operation()
        except Exception as exc:
            last_error = exc
            if attempt == max_retries - 1:
                break
            sleep_seconds = (2**attempt) + random.uniform(0.0, 0.4)
            time.sleep(sleep_seconds)
    raise RuntimeError(f"Operation failed after {max_retries} attempt(s): {last_error}") from last_error
