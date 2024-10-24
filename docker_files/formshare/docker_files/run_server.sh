#! /bin/bash

/wait

if [ ! -f /etc/mosquitto/conf.d/mosquitto.conf ]; then
    cp /root/mosquitto.conf /etc/mosquitto/conf.d
    cp /root/websocket.conf /etc/mosquitto/conf.d
    cp /root/access.acl /etc/mosquitto/conf.d
fi
/etc/init.d/mosquitto stop
/etc/init.d/mosquitto start
mysql -h $MYSQL_HOST_NAME -u $MYSQL_USER_NAME --ssl-mode=DISABLED --password=$MYSQL_USER_PASSWORD --execute='CREATE SCHEMA IF NOT EXISTS formshare'
mysql_tzinfo_to_sql /usr/share/zoneinfo | mysql -u $MYSQL_USER_NAME --password=$MYSQL_USER_PASSWORD mysql
source /opt/formshare_env/bin/activate
cd /opt/formshare
elastic_search_ssl="${ELASTIC_SEARCH_SSL:=false}"
if [ $elastic_search_ssl = "false" ]; then
  python create_config.py --daemon --capture_output --mysql_host $MYSQL_HOST_NAME --mysql_user_name $MYSQL_USER_NAME --mysql_user_password $MYSQL_USER_PASSWORD --repository_path /opt/formshare_repository --odktools_path /opt/odktools --elastic_search_host $ELASTIC_SEARCH_HOST --elastic_search_port $ELASTIC_SEARCH_PORT --formshare_host $FORMSHARE_HOST --formshare_port $FORMSHARE_PORT --forwarded_allow_ip $FORWARDED_ALLOW_IP --pid_file /opt/formshare_gunicorn/formshare.pid --error_log_file /opt/formshare_log/error_log /opt/formshare_config/development.ini
else
  python create_config.py --daemon --capture_output --mysql_host $MYSQL_HOST_NAME --mysql_user_name $MYSQL_USER_NAME --mysql_user_password $MYSQL_USER_PASSWORD --repository_path /opt/formshare_repository --odktools_path /opt/odktools --elastic_search_host $ELASTIC_SEARCH_HOST --elastic_search_port $ELASTIC_SEARCH_PORT --elastic_search_ssl --formshare_host $FORMSHARE_HOST --formshare_port $FORMSHARE_PORT --forwarded_allow_ip $FORWARDED_ALLOW_IP --pid_file /opt/formshare_gunicorn/formshare.pid --error_log_file /opt/formshare_log/error_log /opt/formshare_config/development.ini
fi
ln -s /opt/formshare_config/development.ini ./development.ini
python configure_celery.py ./development.ini
python configure_flatten.py
chmod +x /opt/formshare/formshare/scripts/flatten_jsons.py
python setup.py develop
python setup.py compile_catalog
disable_ssl ./development.ini
configure_alembic ./development.ini .
configure_mysql ./development.ini .
configure_tests ./development.ini .
configure_fluent="${CONFIGURE_FLUENT:=false}"
if [ $configure_fluent = "true" ]; then
  if [ $elastic_search_ssl = "false" ]; then
    configure_fluent --formshare_path /opt/formshare --formshare_log_file /opt/formshare_log/error_log --elastic_search_host $ELASTIC_SEARCH_HOST --elastic_search_port $ELASTIC_SEARCH_PORT /opt/formshare_fluentd/fluent.conf
  else
    configure_fluent --formshare_path /opt/formshare --formshare_log_file /opt/formshare_log/error_log --elastic_search_host $ELASTIC_SEARCH_HOST --elastic_search_port $ELASTIC_SEARCH_PORT --elastic_search_ssl /opt/formshare_fluentd/fluent.conf
  fi
fi
alembic upgrade head
create_superuser --user_id $FORMSHARE_ADMIN_USER --user_email $FORMSHARE_ADMIN_EMAIL --user_password $FORMSHARE_ADMIN_PASSWORD ./development.ini

if [ -f /opt/formshare_plugins/build_plugins.sh ]; then
  echo "Building plugins"
  /opt/formshare_plugins/build_plugins.sh
fi

deactivate
export FORMSHARE_RUN_FROM_CELERY=true
/etc/init.d/celery_formshare stop
/etc/init.d/celery_formshare start
export FORMSHARE_RUN_FROM_CELERY=false
source /opt/formshare_env/bin/activate
rm /opt/formshare_gunicorn/formshare.pid
pserve /opt/formshare/development.ini