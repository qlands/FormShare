"""
formshare.views.task_stream
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Raw async SSE endpoint for streaming Celery task status updates to the
browser.  Bypasses the make_endpoint dispatcher (which is sync-only) and
is registered directly on the FastAPI app.

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
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

log = logging.getLogger("formshare")

_TERMINAL_STATUSES = frozenset({"success", "failure"})


def make_task_stream_endpoint(app_state: dict):
    """Return an async FastAPI endpoint function.

    Parameters
    ----------
    app_state:
        The same app_state dict built in formshare.app.create_app().
        Must contain ``"policies"`` (list of auth policy dicts) and
        ``"settings"`` (the flat settings dict).
    """
    policies = app_state["policies"]
    settings = app_state["settings"]
    redis_url = settings.get("celery.broker", "redis://localhost:6379/0")

    def _get_login(request: Request):
        """Return the authenticated login string, or None."""
        for entry in policies:
            if entry["name"] == "main":
                return entry["policy"].authenticated_userid(request)
        return None

    async def task_stream(request: Request, task_id: str):
        if _get_login(request) is None:
            return Response(status_code=401)

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

    return task_stream
