# Set the base image to use to Ubuntu
FROM ubuntu:14.04

# Set the file maintainer (your name - the file's author)
MAINTAINER Carlos Quiros

# Update the default application repository sources list
RUN apt-get update && apt-get -y upgrade
RUN apt-get install -y postgresql-9.3-postgis-2.1 binutils libproj-dev gdal-bin memcached libmemcached-dev build-essential python-pip python-virtualenv python-dev git libssl-dev libpq-dev gfortran libatlas-base-dev libjpeg-dev libxml2-dev libxslt-dev zlib1g-dev python-software-properties ghostscript python-celery python-sphinx openjdk-7-jdk openjdk-7-jre  postgresql-9.3-postgis-2.1-scripts rabbitmq-server librabbitmq-dev mongodb-server npm apache2 libapache2-mod-wsgi

USER postgres
RUN /etc/init.d/postgresql start && psql -c "CREATE USER formshare WITH PASSWORD 'formshare';" && psql -c "CREATE DATABASE formshare OWNER formshare;" && psql -d formshare -c "CREATE EXTENSION IF NOT EXISTS postgis;" && psql -d formshare -c "CREATE EXTENSION IF NOT EXISTS postgis_topology;"

USER root
RUN /etc/init.d/memcached start


#Create virtualenv
RUN cd /opt
WORKDIR /opt
RUN virtualenv formshare
RUN mkdir /opt/formshare/src
RUN mkdir /opt/formshare/src/formshare
COPY . /opt/formshare/src/formshare

RUN . /opt/formshare/bin/activate && /etc/init.d/mongodb start && /etc/init.d/postgresql start && pip install -r /opt/formshare/src/formshare/requirements/base.pip --allow-all-external && cd /opt/formshare/src/formshare/ && export PYTHONPATH=$PYTHONPATH:/opt/formshare/src/formshare && export DJANGO_SETTINGS_MODULE=formshare.settings.default_settings && python manage.py syncdb --noinput && python manage.py migrate

#Installs celery
RUN ln -s /opt/formshare/src/formshare/extras/celeryd/etc/default/celeryd /etc/default/celeryd
RUN ln -s /opt/formshare/src/formshare/extras/celeryd/etc/init.d/celeryd /etc/init.d/celeryd
RUN /etc/init.d/rabbitmq-server start && /etc/init.d/mongodb start && /etc/init.d/postgresql start && /etc/init.d/celeryd start
RUN update-rc.d celeryd defaults

RUN npm install -g bower
RUN ln -s /usr/bin/nodejs /usr/bin/node

RUN chgrp -R www-data /opt/formshare
RUN chmod -R g+w /opt/formshare
RUN useradd -s /bin/bash -d /opt/formshare formshare
RUN chown -R formshare /opt/formshare

USER formshare
RUN cd /opt/formshare/src/formshare && bower install

USER root
RUN chown -R root /opt/formshare

RUN . /opt/formshare/bin/activate && /etc/init.d/mongodb start && /etc/init.d/postgresql start && cd /opt/formshare/src/formshare/ && export PYTHONPATH=$PYTHONPATH:/opt/formshare/src/formshare && export DJANGO_SETTINGS_MODULE=formshare.settings.default_settings && python manage.py collectstatic --noinput && echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'formshare')" | python manage.py shell && echo "from django.contrib.sites.models import Site; site = Site.objects.get(id=1); site.name = 'FormShare'; site.save()" | python manage.py shell

EXPOSE 80

RUN rm /var/run/celery/w1.pid
COPY ./docker/docker-entrypoint.sh /

COPY ./docker/apache2.conf /etc/apache2/
COPY ./docker/000-default.conf /etc/apache2/sites-available/

RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]
