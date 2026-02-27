from __future__ import annotations

import asyncio
from typing import Awaitable, TypeVar

from app.domain.errors import AdapterTimeoutError

T = TypeVar("T")


async def run_with_timeout(coro: Awaitable[T], timeout_seconds: int) -> T:
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except TimeoutError as exc:
        raise AdapterTimeoutError(f"Timed out after {timeout_seconds}s") from exc
