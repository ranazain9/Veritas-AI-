"""Simple async retry helper for flaky network calls."""

import asyncio
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


async def with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    retries: int = 2,
    delay_seconds: float = 1.5,
) -> T:
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return await fn()
        except Exception as exc:
            last_exc = exc
            if attempt >= retries:
                raise
            await asyncio.sleep(delay_seconds * (attempt + 1))
    raise last_exc  # pragma: no cover
