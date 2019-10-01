#! /bin/bash

/wait
mysql -h $MYSQL_HOST_NAME -u $MYSQL_USER_NAME --password=$MYSQL_USER_PASSWORD --execute='CREATE SCHEMA IF NOT EXISTS formshare'
source /opt/formshare_env/bin/activate
cd /opt/formshare
python create_config.py --mysql_host $MYSQL_HOST_NAME --mysql_user_name $MYSQL_USER_NAME --mysql_user_password $MYSQL_USER_PASSWORD --repository_path /opt/formshare_repository --odktools_path /opt/odktools --elastic_search_host $ELASTIC_SEARCH_HOST --elastic_search_port $ELASTIC_SEARCH_PORT --formshare_host $FORMSHARE_HOST --formshare_port $FORMSHARE_PORT /opt/formshare_config/development.ini
ln -s /opt/formshare_config/development.ini ./development.ini
python configure_celery.py ./development.ini
python setup.py develop
python setup.py compile_catalog
configure_alembic ./development.ini .
configure_mysql ./development.ini .
alembic upgrade head
create_superuser --user_id $FORMSHARE_ADMIN_USER --user_email $FORMSHARE_ADMIN_EMAIL --user_password $FORMSHARE_ADMIN_PASSWORD ./development.ini -n
deactivate
rabbitmqctl add_user formshare formshare
rabbitmqctl add_vhost formshare
rabbitmqctl set_permissions -p formshare formshare ".*" ".*" ".*"
/etc/init.d/celery_formshare start
source /opt/formshare_env/bin/activate
gunicorn --capture-output --proxy-protocol --forwarded-allow-ips $FORMSHARE_HOST --pid /opt/formshare_gunicorn/formshare.pid --log-file /opt/formshare_log/error_log --paste /opt/formshare/development.ini
