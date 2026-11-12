import logging
from formshare.processes.logging.loggerclass import SecretLogger

import redis as redis_lib

logging.setLoggerClass(SecretLogger)
log = logging.getLogger("formshare")

# How long a kept status waits for a page that listens late
KEEP_SECONDS = 3600


def task_channel(task_id):
    """The Redis channel of a task's statuses, which /task_stream forwards."""
    return "formshare:tasks:{}".format(task_id)


def kept_status_key(task_id):
    """The Redis key of the status a task kept for a page that listens late."""
    return "formshare:tasks:{}:kept".format(task_id)


def send_task_status_to_form(settings, task_id, status, keep=False):
    """Publishes a status of a task to the pages listening to it. A status
    sent with keep is also kept for an hour, for a page that starts listening
    after it was sent: Redis delivers a message to the subscribers it has
    then, and a task can end before its page listens. A form deletion ends
    that fast (2026-11-11). It is stored before it is published, so a page
    either hears it or finds it."""
    redis_url = settings.get("celery.broker", "redis://localhost:6379/0")
    try:
        r = redis_lib.from_url(redis_url, socket_connect_timeout=2)
        if keep:
            r.set(kept_status_key(task_id), status, ex=KEEP_SECONDS)
        r.publish(task_channel(task_id), status)
        r.close()
    except Exception as e:
        log.error("Unable to publish task status. Error: {}".format(str(e)))
