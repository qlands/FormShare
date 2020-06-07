#! /bin/bash

/wait
mysql -h $MYSQL_HOST_NAME -u $MYSQL_USER_NAME --password=$MYSQL_USER_PASSWORD --ssl-mode=DISABLED --execute='CREATE SCHEMA IF NOT EXISTS formshare'
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
python setup.py develop
python setup.py compile_catalog
configure_alembic ./development.ini .
configure_mysql ./development.ini .
configure_fluent="${CONFIGURE_FLUENT:=false}"
if [ $configure_fluent = "true" ]; then
  if [ $elastic_search_ssl = "false" ]; then
    configure_fluent --formshare_path /opt/formshare --formshare_log_file /opt/formshare_log/error_log --elastic_search_host $ELASTIC_SEARCH_HOST --elastic_search_port $ELASTIC_SEARCH_PORT /opt/formshare_fluentd/fluent.conf
  else
    configure_fluent --formshare_path /opt/formshare --formshare_log_file /opt/formshare_log/error_log --elastic_search_host $ELASTIC_SEARCH_HOST --elastic_search_port $ELASTIC_SEARCH_PORT --elastic_search_ssl /opt/formshare_fluentd/fluent.conf
  fi
fi
alembic upgrade head
create_superuser --user_id $FORMSHARE_ADMIN_USER --user_email $FORMSHARE_ADMIN_EMAIL --user_password $FORMSHARE_ADMIN_PASSWORD ./development.ini -n
deactivate
/etc/init.d/celery_formshare start
source /opt/formshare_env/bin/activate
rm /opt/formshare_gunicorn/formshare.pid
pserve /opt/formshare/development.ini
tail -f /dev/null
