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

from formshare.views.classes import AsyncView

log = logging.getLogger("formshare")

_TERMINAL_STATUSES = frozenset({"success", "failure"})


class TaskStreamView(AsyncView):
    methods = ["GET"]
    requireAuth = True

    async def process_view(self, request):
        task_id = request.path_params["task_id"]
        redis_url = self.settings.get("celery.broker", "redis://localhost:6379/0")
        channel = "formshare:tasks:{}".format(task_id)

        async def event_generator():
            r = aioredis.from_url(redis_url, decode_responses=True)
            pubsub = r.pubsub()
            await pubsub.subscribe(channel)
            try:
                # Initial comment keeps the connection alive and confirms
                # the subscription before the first real message.
                yield ": connected\n\n"

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
