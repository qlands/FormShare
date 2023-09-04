#!/bin/bash

rm /var/run/mongod.pid
mongod --fork --pidfilepath /var/run/mongod.pid --logpath /var/log/mongodb/mongod.log --config /etc/mongod.conf
rm /var/run/redis/redis-server.pid
chown -R redis /etc/redis
chgrp -R redis /etc/redis
chown -R redis /var/log/redis
chgrp -R redis /var/log/redis
chown -R redis /var/lib/redis
chgrp -R redis /var/lib/redis
/etc/init.d/redis-server start

set -e

# Apache gets grumpy about PID files pre-existing
rm -f /opt/formshare_gunicorn/formshare.pid
rm -f /opt/formshare_celery/run/worker1.pid
/opt/formshare_gunicorn/run_server.sh
tail -f /dev/null