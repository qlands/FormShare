# Installation steps to build FormShare from source.

**Tested with Ubuntu Server 21.10**

## Grab this server IP address. 

This IP address will be used later on

```sh
ifconfig
```

## Update system and add repositories

```shell
sudo apt-get update
sudo apt-get -y upgrade
sudo apt-get install -y software-properties-common
sudo add-apt-repository universe
sudo add-apt-repository multiverse
sudo apt-get update
```

## Install main servers

FormShare depends on MySQL 8.X and Elasticsearch 7.X . **FormShare does not support MySQL 5.X or any version of Maria DB.**

### MySQL 8.X 

```sh
sudo apt-get install mysql-server
sudo mysql_secure_installation
```

FormShare creates schemas, triggers, users and other structures in MySQL. Therefore, your need root or other users with sufficient permissions. 

Check if the connection works for both localhost and IP: 

```sh
mysql -u [root] -p
mysql -h [IP] -u [root] -p
```

### Elasticsearch 7.X

We strongly recommend to use a Docker image for this:

```sh
sudo apt-get install -y docker-compose
sudo sysctl -w vm.max_map_count=262144
echo 'vm.max_map_count=262144' | sudo tee -a /etc/sysctl.d/60-vm-max_map_count.conf
cd /opt
sudo mkdir elasticsearch-docker
cd elasticsearch-docker
sudo mkdir data
sudo mkdir data2
sudo chmod g+w data
sudo chmod g+w data2
wget https://raw.githubusercontent.com/qlands/FormShare/master-2.0/docker_compose_just_elastic/docker-compose.yml
sudo docker-compose up [-d]
```

## Install dependencies
```sh
wget -qO - https://www.mongodb.org/static/pgp/server-5.0.asc | sudo apt-key add -
sudo add-apt-repository 'deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/5.0 multiverse'
sudo apt-get update

sudo apt-get install -y build-essential qtbase5-dev qtbase5-private-dev qtdeclarative5-dev libqt5sql5-mysql cmake jq libboost-all-dev unzip zlib1g-dev automake npm redis-server libmysqlclient-dev mysql-client-8.0 openjdk-11-jdk sqlite3 libqt5sql5-sqlite git python3-venv tidy golang-go mosquitto curl nano mongodb-org
wget https://dev.mysql.com/get/mysql-apt-config_0.8.22-1_all.deb
sudo dpkg -i ./mysql-apt-config_0.8.22-1_all.deb
sudo apt-get update
sudo apt-get install mysql-shell

sudo npm install -g diff2html
sudo npm install -g diff2html-cli

wget https://github.com/BurntSushi/xsv/releases/download/0.13.0/xsv-0.13.0-x86_64-unknown-linux-musl.tar.gz
tar xvfz xsv-0.13.0-x86_64-unknown-linux-musl.tar.gz
sudo cp xsv /bin

git clone https://github.com/qlands/csv2xlsx.git
cd csv2xlsx
go build
sudo cp csv2xlsx /bin
```

## Install ODK Tools

```sh
cd /opt
sudo git clone https://github.com/qlands/odktools.git

sudo mkdir odktools-deps
cd /opt/odktools-deps
sudo wget --user=user https://github.com/mongodb/mongo-c-driver/releases/download/1.6.1/mongo-c-driver-1.6.1.tar.gz
sudo wget --user=user https://github.com/jmcnamara/libxlsxwriter/archive/RELEASE_0.7.6.tar.gz
sudo wget https://downloads.sourceforge.net/project/quazip/quazip/0.7.3/quazip-0.7.3.tar.gz
sudo git clone https://github.com/rgamble/libcsv.git

sudo tar xvfz mongo-c-driver-1.6.1.tar.gz
cd /opt/odktools-deps/mongo-c-driver-1.6.1
sudo ./configure
sudo make
sudo make install
cd /opt/odktools-deps

sudo tar xvfz quazip-0.7.3.tar.gz
cd /opt/odktools-deps/quazip-0.7.3
sudo mkdir build
cd /opt/odktools-deps/quazip-0.7.3/build
sudo cmake -DCMAKE_C_FLAGS:STRING="-fPIC" -DCMAKE_CXX_FLAGS:STRING="-fPIC" ..
sudo make
sudo make install
cd /opt/odktools-deps

sudo ln -s /usr/bin/aclocal-1.16 /usr/bin/aclocal-1.14
sudo ln -s /usr/bin/automake-1.16 /usr/bin/automake-1.14

sudo tar xvfz RELEASE_0.7.6.tar.gz
cd /opt/odktools-deps/libxlsxwriter-RELEASE_0.7.6
sudo mkdir build
cd /opt/odktools-deps/libxlsxwriter-RELEASE_0.7.6/build
sudo cmake ..
sudo make
sudo make install
cd /opt/odktools-deps

cd /opt/odktools-deps/libcsv
sudo ./configure
sudo make
sudo make install

cd /opt/odktools/dependencies/mongo-cxx-driver-r3.1.1
sudo mkdir build
cd /opt/odktools/dependencies/mongo-cxx-driver-r3.1.1/build
sudo cmake -DCMAKE_C_FLAGS:STRING="-O2 -fPIC" -DCMAKE_CXX_FLAGS:STRING="-O2 -fPIC" -DBSONCXX_POLY_USE_BOOST=1 -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr/local ..
sudo make
sudo make install
cd /opt/odktools

sudo qmake
sudo make
```

## Setup FormShare's directory structures

```sh
cd /opt
sudo mkdir formshare_repository
sudo mkdir formshare_log
sudo mkdir formshare_celery
sudo mkdir formshare_gunicorn
sudo mkdir formshare_config
sudo mkdir formshare_plugins

whoami=$(whoami)
sudo chown $whoami formshare_repository
sudo chown $whoami formshare_log
sudo chown $whoami formshare_celery
sudo chown $whoami formshare_gunicorn
sudo chown $whoami formshare_config
sudo chown $whoami formshare_plugins
```

## Create a separate Python environment for FormShare
```sh
cd /opt
sudo python3 -m venv formshare_env
sudo chown -R $whoami formshare_env
```

## Grab the FormShare source code

```sh
cd /opt
sudo git clone https://github.com/qlands/FormShare.git -b stable-2.17.0 formshare
sudo chown -R $whoami formshare
```

## Install and configure FormShare

**You need to replace [parameter] according to your installation**

```sh
cd /opt
source ./formshare_env/bin/activate

pip install wheel
pip install -r /opt/formshare/requirements.txt
python /opt/formshare/download_nltk_packages.py

sudo cp /opt/formshare/docker_files/formshare/docker_files/etc/default/celery_formshare /etc/default/celery_formshare
sudo cp /opt/formshare/docker_files/formshare/docker_files/etc/init.d/celery_formshare /etc/init.d/celery_formshare

sudo chmod +x /etc/init.d/celery_formshare
sudo chmod 640 /etc/default/celery_formshare
sudo ldconfig

sudo service redis-server start
sudo service mongodb start

mysql -h [MYSQL_HOST_NAME] -u [MYSQL_USER_NAME] --password=[MYSQL_USER_PASSWORD] --execute='CREATE SCHEMA IF NOT EXISTS formshare'

cd /opt/formshare
python create_config.py --daemon --capture_output --mysql_host [MYSQL_HOST_NAME] --mysql_user_name [MYSQL_USER_NAME] --mysql_user_password [MYSQL_USER_PASSWORD] --repository_path /opt/formshare_repository --odktools_path /opt/odktools --elastic_search_host [ELASTIC_SEARCH_HOST] --elastic_search_port [ELASTIC_SEARCH_PORT] --formshare_host [THIS_SERVER_IP_ADDRESS] --formshare_port 5900 --forwarded_allow_ip [THIS_SERVER_IP_ADDRESS] --pid_file /opt/formshare_gunicorn/formshare.pid --error_log_file /opt/formshare_log/error_log /opt/formshare_config/development.ini
ln -s /opt/formshare_config/development.ini ./development.ini

python configure_celery.py ./development.ini
python setup.py develop
python setup.py compile_catalog
configure_alembic ./development.ini .
configure_mysql ./development.ini .

alembic upgrade head

create_superuser --user_id [FORMSHARE_ADMIN_USER] --user_email [FORMSHARE_ADMIN_EMAIL] --user_password [FORMSHARE_ADMIN_PASSWORD] ./development.ini

deactivate
```

## Start the Celery and FormShare 
```sh
sudo /etc/init.d/celery_formshare start
source /opt/formshare_env/bin/activate
cd /opt/formshare
pserve ./development.ini

# The process ID of FormShare will be in /opt/formshare_gunicorn/formshare.pid
```

## Access FormShare

```htaccess
http://[THIS_SERVER_IP_ADDRESS]:5900/formshare
```

