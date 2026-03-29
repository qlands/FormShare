import redis
import time
import uuid
from contextlib import contextmanager

from celery.utils.log import get_task_logger

log = get_task_logger(__name__)

# Maximum simultaneous exports across the whole platform.
# Concurrent full-table scans can compete for I/O and sort buffers.
# Raise this if the server has headroom; lower it on constrained Docker hosts.
MAX_CONCURRENT_EXPORTS = 3

# How long (seconds) a lock is held before it self-expires.
# Should be longer than the worst-case export duration to avoid spurious
# expiry, but short enough that a crashed worker doesn't block others for long.
EXPORT_LOCK_EXPIRE = 150  # 2.5 minutes

# Lua script: atomically evict expired semaphore slots, check capacity,
# and insert a new slot — all in one round-trip, no race conditions.
_SEMAPHORE_ACQUIRE_SCRIPT = """
local key        = KEYS[1]
local token      = ARGV[1]
local score      = tonumber(ARGV[2])
local max_slots  = tonumber(ARGV[3])
local now        = tonumber(ARGV[4])
local ttl        = tonumber(ARGV[5])

redis.call("zremrangebyscore", key, "-inf", now)

if redis.call("zcard", key) >= max_slots then
    return 0
end

redis.call("zadd", key, score, token)
redis.call("expire", key, ttl)
return 1
"""


class LockAcquisitionError(Exception):
    pass


@contextmanager
def export_lock(task_id, redis_client, form_schema, expire=EXPORT_LOCK_EXPIRE):
    """
    Two-level export lock:

      1. Per-form mutex  — only one export per form at a time (prevents the
                           same form being exported twice simultaneously).
      2. Global semaphore — at most MAX_CONCURRENT_EXPORTS platform-wide
                            (protects MySQL from concurrent full-table scans).

    Fails immediately if either level cannot be acquired. The Celery task
    should use self.retry(countdown=N) to re-queue without blocking a worker.

    Both locks self-expire after `expire` seconds so a crashed worker cannot
    permanently block other tasks.
    """
    form_key = "export-lock:form:{}".format(form_schema)
    sem_key = "export-lock:global:slots"
    token = str(uuid.uuid4())
    form_acquired = False
    sem_acquired = False

    try:
        # 1. Per-form mutex — fail fast, no busy-wait
        if not redis_client.set(form_key, token, nx=True, ex=expire):
            raise LockAcquisitionError(
                "Task {}: an export is already running for form {}".format(
                    task_id, form_schema
                )
            )
        form_acquired = True

        # 2. Global semaphore — atomic via Lua to avoid TOCTOU race
        now = time.time()
        acquired = redis_client.eval(
            _SEMAPHORE_ACQUIRE_SCRIPT,
            1,
            sem_key,
            token,
            str(now + expire),  # score = expiry timestamp
            str(MAX_CONCURRENT_EXPORTS),
            str(now),
            str(expire),
        )
        if not acquired:
            raise LockAcquisitionError(
                "Task {}: platform export limit ({}) reached".format(
                    task_id, MAX_CONCURRENT_EXPORTS
                )
            )
        sem_acquired = True

        yield

    finally:
        if form_acquired:
            _release_mutex(redis_client, form_key, token)
        if sem_acquired:
            redis_client.zrem(sem_key, token)


def _release_mutex(redis_client, lock_key, token):
    """Release a mutex only if we still own it (token matches)."""
    release_script = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    else
        return 0
    end
    """
    redis_client.eval(release_script, 1, lock_key, token)


def get_redis_client(settings):
    redis_host = settings.get("redis.sessions.redis_host", "localhost")
    redis_port = int(settings.get("redis.sessions.redis_port", "6379"))
    return redis.StrictRedis(host=redis_host, port=redis_port, db=5)
