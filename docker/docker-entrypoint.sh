#!/bin/bash

/etc/init.d/memcached start
/etc/init.d/mongodb start 
/etc/init.d/postgresql start
/etc/init.d/rabbitmq-server start
/etc/init.d/celeryd start

set -e

# Apache gets grumpy about PID files pre-existing
rm -f /usr/local/apache2/logs/httpd.pid
exec apachectl -DFOREGROUND
