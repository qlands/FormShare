# Installation instructions
## Prepare the Os
### Ubuntu server 16 required packages  
    sudo apt-get update
    sudo apt-get install  postgresql-9.5-postgis-2.2 binutils libproj-dev gdal-bin memcached libmemcached-dev build-essential python-pip python-virtualenv python-dev git libssl-dev libpq-dev gfortran libatlas-base-dev libjpeg-dev libxml2-dev libxslt-dev zlib1g-dev python-software-properties ghostscript python-celery python-sphinx openjdk-8-jdk openjdk-8-jre  postgresql-9.5-postgis-scripts rabbitmq-server librabbitmq-dev mongodb-server npm
    
### Ubuntu server 14.04 required packages  
    sudo apt-get update
    sudo apt-get install postgresql-9.3-postgis-2.1 binutils libproj-dev gdal-bin memcached libmemcached-dev build-essential python-pip python-virtualenv python-dev git libssl-dev libpq-dev gfortran libatlas-base-dev libjpeg-dev libxml2-dev libxslt-dev zlib1g-dev python-software-properties ghostscript python-celery python-sphinx openjdk-7-jdk openjdk-7-jre  postgresql-9.3-postgis-2.1-scripts rabbitmq-server librabbitmq-dev mongodb-server npm

## Database setup
Replace username and db name accordingly. Later on you will need to indicate this parameters in the configuration file.

    sudo su postgres -c "psql -c \"CREATE USER formshare WITH PASSWORD 'formshare';\""
    sudo su postgres -c "psql -c \"CREATE DATABASE formshare OWNER formshare;\""
    sudo su postgres -c "psql -d formshare -c \"CREATE EXTENSION IF NOT EXISTS postgis;\""
    sudo su postgres -c "psql -d formshare -c \"CREATE EXTENSION IF NOT EXISTS postgis_topology;\""

## Create python virtual environment and activate it
Note: This instructions assume that FormShare will be installed in /opt and the user installing it is not root. The non-root-user will own the FormShare directory.

    cd /opt
    sudo virtualenv formshare
    sudo chown -R [non-root-user] formshare
    source /opt/formshare/bin/activate
    mkdir /opt/formshare/src

## Get the code
    cd /opt/formshare/src
    git clone https://github.com/qlands/FormShare.git formshare
    cd /opt/formshare/src/formshare/

## Install required python packages
    pip install -r requirements/base.pip    


## Edit the configuration scripts
### Edit /opt/formshare/src/formshare/formshare/settings/default_settings.py
Find the section below and edit NAME,USER,PASSWORD with the setting you used in the database setup. If you used a different host edit HOST

     DATABASES = {
    'default': {
    'ENGINE': 'django.contrib.gis.db.backends.postgis',
    'NAME': 'formshare',
    'USER': 'formshare',
    'PASSWORD': '',
    'HOST': '127.0.0.1',
    'OPTIONS': {
        # note: this option obsolete starting with django 1.6
        'autocommit': True,
    }}}

### Edit /opt/formshare/src/formshare/formshare/settings/common.py
Find the section below and edit HOST, PORST, NAME, USER and PASSWORD if necessary. The Installation of Mongo does not set an user or password for the database.  

    MONGO_DATABASE = {
    'HOST': 'localhost',
    'PORT': 27017,
    'NAME': 'formshare',
    'USER': '',
    'PASSWORD': ''
    }

## Test the Installation

    cd /opt/formshare/src/formshare/
    export PYTHONPATH=$PYTHONPATH:/opt/formshare/src/formshare
    export DJANGO_SETTINGS_MODULE=formshare.settings.default_settings
    python manage.py validate

The validate should return 0 errors.

In certain Linux distributions and/or versions of PostGis DJango cannot read the version of PostGIS leading to the following error:

    Cannot determine PostGIS version for database. GeoDjango requires at least PostGIS version 1.3. Was the database created from a spatial database template?

To bypass this error add the following line to /opt/formshare/src/formshare/formshare/settings/common.py  and update the version with the one you installed.

    POSTGIS_VERSION = ( 2, 1 )

## Initial db setup
    python manage.py syncdb --noinput
    python manage.py migrate

## Setup celery service

Celery is used by FormShare to run time-consuming processes like the data exports as distributed tasks.
### Edit the /opt/formshare/src/formshare/extras/celeryd/etc/default/celeryd file

Change the following lines to look like the below:

      CELERYD_CHDIR="/opt/formshare/src/formshare/"
      ENV_PYTHON="/opt/formshare/bin/python"
      CELERYD_USER="www-data"
      CELERYD_GROUP="www-data"
      export DJANGO_SETTINGS_MODULE="formshare.settings.default_settings"

### Set the celeryd as a service

Create a symbolic link to the celery file from de init.d directory. Note /etc/default must exists.

      sudo ln -s /opt/formshare/src/formshare/extras/celeryd/etc/default/celeryd /etc/default/celeryd
      sudo ln -s /opt/formshare/src/formshare/extras/celeryd/etc/init.d/celeryd /etc/init.d/celeryd
      sudo /etc/init.d/celeryd start

The startup of celery should return something like the below:

      celery multi v3.1.15 (Cipater)
      > Starting nodes...
      Your environment is:"formshare.settings.default_settings"
      > w1@SlackFormshare: OK

## Create a super user
      python manage.py createsuperuser

## Install Bower and download the necessary JavaScripts
      sudo npm install -g bower
      cd /opt/formshare/src/formshare
      bower install

If you get "command not found" when running "bower install" do:

      sudo ln -s /usr/bin/nodejs /usr/bin/node

## Copy all files from your static folders into the STATIC_ROOT directory
      cd /opt/formshare/src/formshare
      python manage.py collectstatic --noinput

## Run FormShare for testing

    cd /opt/formshare/src/formshare
    python manage.py runserver

Running the server should return something like the below:

      Your environment is:"formshare.settings.default_settings"
      Your environment is:"formshare.settings.default_settings"
      Validating models...
      0 errors found
      April 21, 2016 - 08:26:37
      Django version 1.6.11, using settings 'formshare.settings.default_settings'
      Starting development server at http://127.0.0.1:8000/
      Quit the server with CONTROL-C.

Using the Internet browser go to http://127.0.0.1:8000/  You will see the FormShare front page. Test the long in page with the super user.

You can also start the server with a different IP address by running:

    python manage.py runserver x.x.x.x:[port]

## Make Apache web server to load FormShare
### Install required packages

    sudo apt-get install apache2 libapache2-mod-wsgi

### Set the group owner of the directory /opt/formshare to be Apache and allow it write access

    sudo chown -R www-data /opt/formshare/
    sudo chmod -R g+w /opt/formshare/

### Add the following lines to /etc/apache2/sites-enabled/000-default.conf after "DocumentRoot"

    WSGIPassAuthorization On
    # Deploy as a daemon (avoids conflicts between other python apps).
    WSGIDaemonProcess formshare python-path=/opt/formshare display-name=formshare processes=2 threads=15
    WSGIScriptAlias /formshare /opt/formshare/src/formshare/extras/wsgi/formshare.wsgi process-group=formshare application-group=%{GLOBAL}
    <Location "/formshare">
            WSGIProcessGroup formshare
    </Location>

### Edit the APP_ROOT directory in formshare/settings/common.py line 81"
In the WSGIScriptAlias above you declared the root as /formshare so reflect this in common.py

    APP_ROOT = '/formshare/'
    
### Restart the Apache service    
    sudo service apache2 restart

Go to http://[ip_address_of_the_server]/formshare .FormShare should be running from there. If you get a "Forbidden" message set the section "Directory" of the file /etc/apache2/apache2.conf to look like this:

    <Directory />
          Options FollowSymLinks
          AllowOverride None
          #Require all denied
          Order Deny,Allow
    </Directory>
