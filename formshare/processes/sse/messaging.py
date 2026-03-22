import logging
from formshare.processes.logging.loggerclass import SecretLogger

import redis as redis_lib

logging.setLoggerClass(SecretLogger)
log = logging.getLogger("formshare")


def send_task_status_to_form(settings, task_id, status):
    redis_url = settings.get("celery.broker", "redis://localhost:6379/0")
    try:
        r = redis_lib.from_url(redis_url, socket_connect_timeout=2)
        r.publish("formshare:tasks:{}".format(task_id), status)
        r.close()
    except Exception as e:
        log.error("Unable to publish task status. Error: {}".format(str(e)))
