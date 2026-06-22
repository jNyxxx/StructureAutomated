"""Worker loop foundation.

A minimal, stoppable poller: claim → (throttle) → run → mark, one job per tick
via the same ``QueueService`` used everywhere. ``run_once`` is the testable unit
(injected clock); ``run`` loops until ``stop()`` and sleeps when the queue is
idle. No business jobs are implemented here — the handler is injected.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime

from app.services.queue import Handler, ProcessOutcome, QueueService, ThrottleLike


class WorkerLoop:
    def __init__(
        self,
        service: QueueService,
        handler: Handler,
        *,
        throttle: ThrottleLike | None = None,
        poll_interval: float = 1.0,
    ) -> None:
        self._service = service
        self._handler = handler
        self._throttle = throttle
        self._poll_interval = poll_interval
        self._stopped = False

    def stop(self) -> None:
        self._stopped = True

    async def run_once(self, *, now: datetime) -> ProcessOutcome:
        return await self._service.process_next(
            now=now, handler=self._handler, throttle=self._throttle
        )

    async def run(self, *, now_fn: Callable[[], datetime] | None = None) -> None:
        clock = now_fn or (lambda: datetime.now(UTC))
        while not self._stopped:
            outcome = await self.run_once(now=clock())
            if not outcome.claimed:
                await asyncio.sleep(self._poll_interval)
