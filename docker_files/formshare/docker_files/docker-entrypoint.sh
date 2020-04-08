#!/bin/bash

/etc/init.d/mongodb start
rm /var/run/rabbitmq/pid
/etc/init.d/rabbitmq-server start

set -e

# Apache gets grumpy about PID files pre-existing
rm -f /opt/formshare_gunicorn/formshare.pid
rm -f /opt/formshare_celery/run/worker1.pid
exec /opt/formshare_gunicorn/run_server.sh