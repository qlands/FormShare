#!/bin/bash

/etc/init.d/mongodb start
rm /var/run/redis/redis-server.pid
/etc/init.d/redis-server start

set -e

# Apache gets grumpy about PID files pre-existing
rm -f /opt/formshare_gunicorn/formshare.pid
rm -f /opt/formshare_celery/run/worker1.pid
exec /opt/formshare_gunicorn/run_server.sh
exec /opt/formshare_gunicorn/stop.sh