from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest
from homeconnect_websocket.task_manager import TaskManager


@pytest.mark.asyncio
async def test_shutdown_cancels_stuck_task_without_blocking_the_loop() -> None:
    """A stuck task is cancelled and the event loop keeps running."""
    manager = TaskManager()
    ticks = 0

    async def stuck() -> None:
        await asyncio.sleep(3600)

    async def ticker() -> None:
        nonlocal ticks
        while True:
            await asyncio.sleep(0.01)
            ticks += 1

    stuck_task = manager.create_background_task(stuck())
    ticker_task = asyncio.ensure_future(ticker())

    with patch("homeconnect_websocket.task_manager.BLOCK_TIMEOUT", 0.2):
        await asyncio.wait_for(manager.shutdown(), timeout=5)

    ticker_task.cancel()
    assert stuck_task.cancelled()
    assert ticks > 5
