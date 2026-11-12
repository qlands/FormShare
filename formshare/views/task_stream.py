"""
formshare.views.task_stream
~~~~~~~~~~~~~~~~~~~~~~~~~~~

SSE endpoint for streaming Celery task status updates to the browser.

Usage
-----
The browser opens:

    EventSource("/task_stream/<task_id>")

The server subscribes to the Redis pub/sub channel
``formshare:tasks:<task_id>`` and forwards every message as an SSE data
frame.  When the message payload is ``"success"`` or ``"failure"`` the
stream is closed server-side; the browser can then reload or refresh the
relevant UI fragment.

A task that can end before its page listens keeps its last status
(``send_task_status_to_form(..., keep=True)``, a form deletion since
2026-11-11). A stream opened after it was sent gets it at once, and ends.
The kept status is read after the subscription, so a status sent in between
is heard either way.

Authentication
--------------
The endpoint validates the "main" auth cookie (itsdangerous-signed) that
PrivateView uses.  Unauthenticated requests receive a 401 response before
any Redis connection is made.
"""

import asyncio
import logging

import redis.asyncio as aioredis
from starlette.responses import StreamingResponse

from formshare.processes.sse.messaging import kept_status_key, task_channel
from formshare.views.classes import AsyncView

log = logging.getLogger("formshare")

_TERMINAL_STATUSES = frozenset({"success", "failure"})


class TaskStreamView(AsyncView):
    methods = ["GET"]
    requireAuth = True

    # The stream stays open until the task ends, which the synchronous test
    # client cannot wait for. One that finds a kept status ends at once:
    # tests/steps/form_deletion_task.py reads one
    async def process_view(self, request):  # pragma: no cover
        task_id = request.path_params["task_id"]
        redis_url = self.settings.get("celery.broker", "redis://localhost:6379/0")
        channel = task_channel(task_id)

        async def event_generator():
            r = aioredis.from_url(redis_url, decode_responses=True)
            pubsub = r.pubsub()
            await pubsub.subscribe(channel)
            try:
                # Redis confirms the subscription before anything published
                # after it, so what is kept is read once it is in place
                await pubsub.get_message(timeout=2.0)

                # Initial comment keeps the connection alive and confirms
                # the subscription before the first real message.
                yield ": connected\n\n"

                # A task that ended before this page listened
                kept = await r.get(kept_status_key(task_id))
                if kept is not None:
                    yield "data: {}\n\n".format(kept)
                    return

                while True:
                    if await request.is_disconnected():
                        break

                    message = await pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=1.0
                    )

                    if message is not None and message["type"] == "message":
                        data = message["data"]
                        yield "data: {}\n\n".format(data)
                        if data in _TERMINAL_STATUSES:
                            break
                    else:
                        # Heartbeat comment — keeps the HTTP connection alive
                        # through proxies and load balancers.  Browsers ignore
                        # SSE comment lines.
                        yield ": heartbeat\n\n"

            except asyncio.CancelledError:
                pass
            finally:
                await pubsub.unsubscribe(channel)
                await r.aclose()

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",  # disable nginx buffering
            },
        )
