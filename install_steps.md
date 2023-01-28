# Installation steps to build FormShare from source for production or development

**Tested with Ubuntu 22.04 (Python 3.10.X)**
**Tested with Ubuntu 20.04 (Python 3.8.X)**

**Minimum memory requirements**
- For production running on Ubuntu Server: 8GB
- For development running on Ubuntu Desktop: 16GB

## Important notes that many forget!
- **Follow the instructions line by line! Do not skip lines!**

- **You need to replace anything that is between [ ] according to your installation INCLUDING the [ ]. For example, replace [ELASTIC_SEARCH_HOST] for localhost**

## Installation steps

### Update the system

```sh
sudo apt-get update
sudo apt-get -y upgrade
```

### Grab this server IP address. 

This IP address will be used later on

```sh
sudo apt install net-tools
ifconfig
```

### Update repositories

```sh
sudo apt-get install -y software-properties-common
sudo add-apt-repository universe
sudo add-apt-repository multiverse
sudo apt-get install -y wget

sudo add-apt-repository ppa:mosquitto-dev/mosquitto-ppa -y

# The following two lines apply if you are using Ubuntu 22.04
sudo wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc |  gpg --dearmor | sudo tee /usr/share/keyrings/mongodb.gpg > /dev/null
sudo echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list

sudo wget https://dev.mysql.com/get/mysql-apt-config_0.8.24-1_all.deb
sudo dpkg -i ./mysql-apt-config_0.8.24-1_all.deb

sudo apt-get update
```

### Elasticsearch 7.X

We strongly recommend to use a Docker image for this:

```sh
sudo apt-get install -y docker-compose curl
sudo sysctl -w vm.max_map_count=262144
echo 'vm.max_map_count=262144' | sudo tee -a /etc/sysctl.d/60-vm-max_map_count.conf
cd /opt
sudo mkdir elasticsearch-docker
cd elasticsearch-docker
sudo mkdir data
sudo mkdir data2
sudo chmod g+w data
sudo chmod g+w data2
sudo wget https://raw.githubusercontent.com/qlands/FormShare/master-2.0/docker_compose_just_elastic/docker-compose.yml
sudo docker-compose up -d
# Give 5 minutes for Elasticsearch to load
```

**Note: Elasticsearch will run in localhost in the port 9200**

Test Elasticsearch

```
curl http://localhost:9200
```

Result:

```json
{
  "name" : "fses01",
  "cluster_name" : "fs-es-cluster",
  "cluster_uuid" : "nw_UT5VBTHOpW2l2Y745DA",
  "version" : {
    "number" : "7.14.2",
    "build_flavor" : "default",
    "build_type" : "docker",
    "build_hash" : "6bc13727ce758c0e943c3c21653b3da82f627f75",
    "build_date" : "2021-09-15T10:18:09.722761972Z",
    "build_snapshot" : false,
    "lucene_version" : "8.9.0",
    "minimum_wire_compatibility_version" : "6.8.0",
    "minimum_index_compatibility_version" : "6.0.0-beta1"
  },
  "tagline" : "You Know, for Search"
}

```

### Install system dependencies

```sh
# if Ubuntu 22.04
sudo apt-get install -y mysql-server build-essential qtbase5-dev qtbase5-private-dev qtdeclarative5-dev libqt5sql5-mysql cmake jq libboost-all-dev unzip zlib1g-dev automake npm redis-server libmysqlclient-dev mysql-client-8.0 sqlite3 libqt5sql5-sqlite git wget python3-venv tidy golang-go mosquitto curl nano mongodb-org mysql-shell openjdk-17-jre-headless mysql-shell
# if Ubuntu 20.04
sudo sudo apt-get install -y mysql-server build-essential qt5-default qtbase5-private-dev qtdeclarative5-dev libqt5sql5-mysql cmake mongodb jq libboost-all-dev unzip zlib1g-dev automake npm redis-server libmysqlclient-dev mysql-client-8.0 sqlite3 libqt5sql5-sqlite git wget python3-venv tidy golang-go mosquitto nano mysql-shell
```

### Update MySQL root password

```sh
sudo mysql -u root -p
```

```mysql
create user 'root'@'%' IDENTIFIED WITH mysql_native_password by '[my_secure_password]';
grant all on *.* to 'root'@'%';
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password by '[my_secure_password]';
flush privileges;
```

### Upgrade Java SDK (Only for Ubuntu 20.04)

```sh
sudo apt install -y libc6-x32 libc6-i386
sudo wget https://download.oracle.com/java/17/latest/jdk-17_linux-x64_bin.deb
sudo dpkg -i jdk-17_linux-x64_bin.deb
sudo update-alternatives --install /usr/bin/java java /usr/lib/jvm/jdk-17/bin/java 1
```

### Install third-party tools

```sh
sudo npm install -g diff2html
sudo npm install -g diff2html-cli@5.2.1
sudo npm install -g json2csv@5.0.7

sudo wget https://github.com/BurntSushi/xsv/releases/download/0.13.0/xsv-0.13.0-x86_64-unknown-linux-musl.tar.gz
sudo tar xvfz xsv-0.13.0-x86_64-unknown-linux-musl.tar.gz
sudo cp xsv /bin

sudo git clone https://github.com/qlands/csv2xlsx.git
cd csv2xlsx
sudo go build
sudo cp csv2xlsx /bin

```

### Install ODK Tools

```sh
cd /opt
sudo mkdir odktools-deps
sudo git clone https://github.com/qlands/odktools.git

cd /opt/odktools-deps
sudo wget https://github.com/mongodb/mongo-c-driver/releases/download/1.21.1/mongo-c-driver-1.21.1.tar.gz
sudo wget https://github.com/mongodb/mongo-cxx-driver/releases/download/r3.6.7/mongo-cxx-driver-r3.6.7.tar.gz
sudo wget https://github.com/jmcnamara/libxlsxwriter/archive/refs/tags/RELEASE_1.1.4.tar.gz
sudo wget https://github.com/stachenov/quazip/archive/refs/tags/v1.3.tar.gz
sudo git clone https://github.com/rgamble/libcsv.git

sudo tar xvfz mongo-c-driver-1.21.1.tar.gz
cd /opt/odktools-deps/mongo-c-driver-1.21.1
sudo mkdir build_here
cd /opt/odktools-deps/mongo-c-driver-1.21.1/build_here
sudo cmake ..
sudo make
sudo make install
cd /opt/odktools-deps

sudo tar xvfz mongo-cxx-driver-r3.6.7.tar.gz
cd /opt/odktools-deps/mongo-cxx-driver-r3.6.7
sudo mkdir build_here
cd /opt/odktools-deps/mongo-cxx-driver-r3.6.7/build_here
sudo cmake -DCMAKE_C_FLAGS:STRING="-O2 -fPIC" -DCMAKE_CXX_FLAGS:STRING="-O2 -fPIC" -DBSONCXX_POLY_USE_BOOST=1 -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr/local ..
sudo make
sudo make install
cd /opt/odktools-deps

sudo tar xvfz v1.3.tar.gz
cd /opt/odktools-deps/quazip-1.3
sudo mkdir build
cd /opt/odktools-deps/quazip-1.3/build
sudo cmake -DCMAKE_C_FLAGS:STRING="-fPIC" -DCMAKE_CXX_FLAGS:STRING="-fPIC" ..
sudo make
sudo make install
cd /opt/odktools-deps

sudo ln -s /usr/bin/aclocal-1.16 /usr/bin/aclocal-1.14
sudo ln -s /usr/bin/automake-1.16 /usr/bin/automake-1.14

sudo tar xvfz RELEASE_1.1.4.tar.gz
cd /opt/odktools-deps/libxlsxwriter-RELEASE_1.1.4
sudo mkdir build
cd /opt/odktools-deps/libxlsxwriter-RELEASE_1.1.4/build
sudo cmake ..
sudo make
sudo make install
cd /opt/odktools-deps

cd /opt/odktools-deps/libcsv
sudo ./configure
sudo make
sudo make install

cd /opt/odktools

sudo qmake
sudo make

sudo ldconfig

sudo apt-get update
sudo apt-get install -y locales 
sudo sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen 
sudo dpkg-reconfigure --frontend=noninteractive locales \
sudo update-locale LANG=en_US.UTF-8
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
```

### Setup FormShare's directory structures

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

### Create a separate Python environment for FormShare
```sh
cd /opt
sudo python3 -m venv formshare_env
sudo chown -R $whoami formshare_env
```

### Grab the FormShare source code

#### **Stable**

```sh
cd /opt
sudo git clone https://github.com/qlands/FormShare.git -b stable-2.25.0 formshare
sudo chown -R $whoami formshare
```

#### **For development**

```sh
cd /opt
sudo git clone https://github.com/qlands/FormShare.git -b master-2.0 formshare
sudo chown -R $whoami formshare
```

### Install and configure FormShare

**You need to replace [parameter] according to your installation**

```sh
cd /opt
source ./formshare_env/bin/activate

pip install wheel
pip install -r /opt/formshare/requirements.txt
python /opt/formshare/download_nltk_packages.py

# The following lines are for running an stable version
sudo cp /opt/formshare/docker_files/formshare/docker_files/etc/default/celery_formshare /etc/default/celery_formshare
sudo cp /opt/formshare/docker_files/formshare/docker_files/etc/init.d/celery_formshare /etc/init.d/celery_formshare
sudo chmod +x /etc/init.d/celery_formshare
sudo chmod 640 /etc/default/celery_formshare
sudo ldconfig
# --end

sudo service redis-server start
sudo mongod --fork --pidfilepath /var/run/mongod.pid --logpath /var/log/mongodb/mongod.log --config /etc/mongod.conf

mysql -h [MYSQL_HOST_NAME] -u [MYSQL_USER_NAME] --password=[MYSQL_USER_PASSWORD] --execute='CREATE SCHEMA IF NOT EXISTS formshare'

cd /opt/formshare

python create_config.py --daemon --capture_output --mysql_host [MYSQL_HOST_NAME] --mysql_user_name [MYSQL_USER_NAME] --mysql_user_password [MYSQL_USER_PASSWORD] --repository_path /opt/formshare_repository --odktools_path /opt/odktools --elastic_search_host [ELASTIC_SEARCH_HOST] --elastic_search_port [ELASTIC_SEARCH_PORT] --formshare_host [THIS_SERVER_IP_ADDRESS] --formshare_port 5900 --forwarded_allow_ip [THIS_SERVER_IP_ADDRESS] --pid_file /opt/formshare_gunicorn/formshare.pid --error_log_file /opt/formshare_log/error_log /opt/formshare_config/development.ini

ln -s /opt/formshare_config/development.ini ./development.ini

# If you are running FormShare for development purposes.
# Edit development.ini
# Comment lines from 162 to 164
# --end

python configure_celery.py ./development.ini
python setup.py develop
python setup.py compile_catalog
configure_alembic ./development.ini .
configure_mysql ./development.ini .

alembic upgrade head

create_superuser --user_id [FORMSHARE_ADMIN_USER] --user_email [FORMSHARE_ADMIN_EMAIL] --user_password [FORMSHARE_ADMIN_PASSWORD] ./development.ini

deactivate
```

### Start the Celery and FormShare (If running a stable version)
```sh
sudo /etc/init.d/celery_formshare start
source /opt/formshare_env/bin/activate
cd /opt/formshare
pserve ./development.ini

# The process ID of FormShare will be in /opt/formshare_gunicorn/formshare.pid
```

### Start the Celery and FormShare (If running for development)

```sh
source /opt/formshare_env/bin/activate
cd /opt/formshare
./start_local_celery_for_testing.sh
# Celery log will be in /opt/formshare/celery.log
# Celery process ID will be in /opt/formshare/celerypid.log
pserve ./development.ini
```

### Access FormShare

```htaccess
http://[THIS_SERVER_IP_ADDRESS]:5900/formshare
```

## If you are developing plug-ins

```sh
cd /opt/formshare_plugins
cookiecutter https://github.com/qlands/formshare-cookiecutter-plugin
# Follow the instructions
cd [my_plugin_directory]
python setup.py develop
cd /opt/formshare
# Edit development.ini
# Add the following line AFTER LINE 77:
formshare.plugins = [my_plugin]
pserve ./development.ini
```

## Access a custom plug-in page in FormShare

```htaccess
http://[THIS_SERVER_IP_ADDRESS]:5900/formshare/mypublicview
```

