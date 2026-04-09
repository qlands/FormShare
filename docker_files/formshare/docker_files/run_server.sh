#! /bin/bash

/wait

mysql -h $MYSQL_HOST_NAME -u $MYSQL_USER_NAME --password=$MYSQL_USER_PASSWORD --execute='CREATE SCHEMA IF NOT EXISTS formshare'

mysql_tzinfo_to_sql /usr/share/zoneinfo | mysql -h $MYSQL_HOST_NAME -u $MYSQL_USER_NAME --password=$MYSQL_USER_PASSWORD mysql
source /opt/formshare_env/bin/activate
cd /opt/formshare || exit

python create_config.py /opt/formshare_config/development.ini

ln -s /opt/formshare_config/development.ini ./development.ini
python configure_celery.py ./development.ini
python configure_flatten.py ./development.ini
chmod +x /opt/formshare/formshare/scripts/flatten_jsons.py
pip install -e .
python setup.py compile_catalog

configure_alembic ./development.ini .
configure_mysql ./development.ini .
configure_tests ./development.ini .

ln -s /opt/formshare/alembic.ini /opt/formshare_config/alembic.ini
ln -s /opt/formshare/mysql.cnf /opt/formshare_config/mysql.cnf

alembic upgrade head
create_superuser ./development.ini

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
rm /opt/formshare_uvicorn/formshare.pid
FORMSHARE_INI=/opt/formshare/development.ini uvicorn formshare.app:create_app --factory --host $FORMSHARE_HOST --port $FORMSHARE_PORT --root-path $FORMSHARE_ROOT_PATH --workers $FORMSHARE_NUM_WORKERS >> /opt/formshare_log/formshare.log 2>&1 &
echo $! > /opt/formshare_uvicorn/formshare.pid