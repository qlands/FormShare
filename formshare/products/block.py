import redis
from contextlib import contextmanager
import uuid
import time
from celery.utils.log import get_task_logger

log = get_task_logger(__name__)


class LockAcquisitionError(Exception):
    pass


@contextmanager
def global_export_lock(
    task_id, redis_client, lock_key="export-lock", timeout=60, expire=120
):
    token = str(uuid.uuid4())
    acquired = False
    try:
        for _ in range(timeout):
            if redis_client.set(lock_key, token, nx=True, ex=expire):
                acquired = True
                break
            time.sleep(1)
        if not acquired:
            log.error(
                "Could not acquire Excel Export lock for task {} within timeout.".format(
                    task_id
                )
            )
            raise LockAcquisitionError(
                "Could not acquire Excel Export lock for task {} within timeout.".format(
                    task_id
                )
            )
        yield
    finally:
        if acquired:
            _release_lock(redis_client, lock_key, token)


def _release_lock(redis_client, lock_key, token):
    release_script = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    else
        return 0
    end
    """
    redis_client.eval(release_script, 1, lock_key, token)


def get_redis_client(settings):
    redis_host = settings.get("redis.sessions.host", "localhost")
    redis_port = int(settings.get("redis.sessions.port", "6379"))
    redis_client = redis.StrictRedis(host=redis_host, port=redis_port, db=5)
    return redis_client
