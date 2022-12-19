#!/bin/bash

rm /var/run/mongod.pid
mongod --fork --pidfilepath /var/run/mongod.pid --logpath /var/log/mongodb/mongod.log --config /etc/mongod.conf
rm /var/run/redis/redis-server.pid
/etc/init.d/redis-server start

set -e

# Apache gets grumpy about PID files pre-existing
rm -f /opt/formshare_gunicorn/formshare.pid
rm -f /opt/formshare_celery/run/worker1.pid
/opt/formshare_gunicorn/run_server.sh
tail -f /dev/null