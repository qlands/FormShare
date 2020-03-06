#! /bin/bash

/wait
mysql -h $MYSQL_HOST_NAME -u $MYSQL_USER_NAME --password=$MYSQL_USER_PASSWORD --execute='CREATE SCHEMA IF NOT EXISTS formshare'
source /opt/formshare_env/bin/activate
cd /opt/formshare
elastic_search_ssl="${ELASTIC_SEARCH_SSL:=false}"
if [ $elastic_search_ssl = "false" ]; then
  python create_config.py --mysql_host $MYSQL_HOST_NAME --mysql_user_name $MYSQL_USER_NAME --mysql_user_password $MYSQL_USER_PASSWORD --repository_path /opt/formshare_repository --odktools_path /opt/odktools --elastic_search_host $ELASTIC_SEARCH_HOST --elastic_search_port $ELASTIC_SEARCH_PORT --formshare_host $FORMSHARE_HOST --formshare_port $FORMSHARE_PORT /opt/formshare_config/development.ini
else
  python create_config.py --mysql_host $MYSQL_HOST_NAME --mysql_user_name $MYSQL_USER_NAME --mysql_user_password $MYSQL_USER_PASSWORD --repository_path /opt/formshare_repository --odktools_path /opt/odktools --elastic_search_host $ELASTIC_SEARCH_HOST --elastic_search_port $ELASTIC_SEARCH_PORT --elastic_search_ssl --formshare_host $FORMSHARE_HOST --formshare_port $FORMSHARE_PORT /opt/formshare_config/development.ini
fi
ln -s /opt/formshare_config/development.ini ./development.ini
python configure_celery.py ./development.ini
python setup.py develop
python setup.py compile_catalog
configure_alembic /opt/formshare_config/development.ini .
configure_mysql ./development.ini /opt/formshare_config
ln -s /opt/formshare_config/mysql.cnf ./mysql.cnf

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
rabbitmqctl add_user formshare formshare
rabbitmqctl add_vhost formshare
rabbitmqctl set_permissions -p formshare formshare ".*" ".*" ".*"
/etc/init.d/celery_formshare start
source /opt/formshare_env/bin/activate
gunicorn --capture-output --proxy-protocol --forwarded-allow-ips $FORWARDED_ALLOW_IP --pid /opt/formshare_gunicorn/formshare.pid --log-file /opt/formshare_log/error_log --paste /opt/formshare/development.ini
