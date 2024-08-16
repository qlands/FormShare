FROM cimg/python:3.10.12

MAINTAINER QLands Technology Consultants
RUN sudo apt-get update && sudo apt-get -y upgrade
RUN sudo apt-get install -y software-properties-common
RUN sudo add-apt-repository universe
RUN sudo add-apt-repository multiverse

RUN sudo apt-get install -y wget

RUN sudo add-apt-repository ppa:mosquitto-dev/mosquitto-ppa -y

RUN sudo wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc |  sudo gpg --dearmor | sudo tee /usr/share/keyrings/mongodb.gpg > /dev/null
RUN sudo echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list

WORKDIR /opt
RUN sudo mkdir mysql_config
WORKDIR /opt/mysql_config
RUN sudo wget https://dev.mysql.com/get/mysql-apt-config_0.8.29-1_all.deb
RUN sudo dpkg -i ./mysql-apt-config_0.8.29-1_all.deb
WORKDIR /home/circleci/project

RUN sudo apt-get update

RUN sudo DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC apt-get install -y build-essential qtbase5-dev qtbase5-private-dev qtdeclarative5-dev libqt5sql5-mysql cmake jq libboost-all-dev unzip zlib1g-dev automake npm redis-server libmysqlclient-dev mysql-client sqlite3 libqt5sql5-sqlite git wget python3-venv tidy golang-go mosquitto curl nano mongodb-org mysql-shell openjdk-17-jre-headless

# BEGIN IMAGE CUSTOMIZATIONS

# Install pipenv and poetry
#RUN sudo curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
#RUN sudo python3 get-pip.py
#RUN sudo sudo pip install --no-cache pipenv poetry
#RUN sudo sudo pip uninstall --yes setuptools
#RUN sudo sudo pip install setuptools==57.5.0
# END IMAGE CUSTOMIZATIONS
# -------------------------------

RUN sudo npm install -g diff2html
RUN sudo npm install -g diff2html-cli@5.2.1
RUN sudo npm install -g json2csv@5.0.7

COPY ./docker_files/timezone/mysql_tzinfo_to_sql /usr/bin
COPY ./docker_files/mosquitto/mosquitto.conf /etc/mosquitto/conf.d/
COPY ./docker_files/mosquitto/websocket.conf /etc/mosquitto/conf.d/
COPY ./docker_files/mosquitto/access.acl /etc/mosquitto/conf.d/
COPY ./docker_files/mosquitto/users.mqt /etc/mosquitto/conf.d/

WORKDIR /opt
RUN sudo mkdir other_deps
WORKDIR /opt/other_deps

RUN sudo wget https://github.com/BurntSushi/xsv/releases/download/0.13.0/xsv-0.13.0-x86_64-unknown-linux-musl.tar.gz
RUN sudo tar xvfz xsv-0.13.0-x86_64-unknown-linux-musl.tar.gz
RUN sudo cp xsv /bin

RUN sudo git clone https://github.com/qlands/csv2xlsx.git
WORKDIR csv2xlsx
RUN sudo go build
RUN sudo cp csv2xlsx /bin

WORKDIR /home/circleci/project

WORKDIR /opt
RUN sudo mkdir odktools-deps
RUN sudo git clone https://github.com/qlands/odktools.git -b stable-2.13

WORKDIR /opt/odktools-deps
RUN sudo wget https://github.com/mongodb/mongo-c-driver/releases/download/1.21.1/mongo-c-driver-1.21.1.tar.gz
RUN sudo wget https://github.com/mongodb/mongo-cxx-driver/releases/download/r3.6.7/mongo-cxx-driver-r3.6.7.tar.gz
RUN sudo wget https://github.com/jmcnamara/libxlsxwriter/archive/refs/tags/RELEASE_1.1.4.tar.gz
RUN sudo wget https://github.com/stachenov/quazip/archive/refs/tags/v1.3.tar.gz
RUN sudo git clone https://github.com/rgamble/libcsv.git

RUN sudo tar xvfz mongo-c-driver-1.21.1.tar.gz
WORKDIR /opt/odktools-deps/mongo-c-driver-1.21.1
RUN sudo mkdir build_here
WORKDIR /opt/odktools-deps/mongo-c-driver-1.21.1/build_here
RUN sudo cmake ..
RUN sudo make
RUN sudo make install
WORKDIR /opt/odktools-deps

RUN sudo tar xvfz mongo-cxx-driver-r3.6.7.tar.gz
WORKDIR /opt/odktools-deps/mongo-cxx-driver-r3.6.7
RUN sudo mkdir build_here
WORKDIR /opt/odktools-deps/mongo-cxx-driver-r3.6.7/build_here
RUN sudo cmake -DCMAKE_C_FLAGS:STRING="-O2 -fPIC" -DCMAKE_CXX_FLAGS:STRING="-O2 -fPIC" -DBSONCXX_POLY_USE_BOOST=1 -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr/local ..
RUN sudo make
RUN sudo make install
WORKDIR /opt/odktools-deps

RUN sudo tar xvfz v1.3.tar.gz
WORKDIR /opt/odktools-deps/quazip-1.3
RUN sudo mkdir build
WORKDIR /opt/odktools-deps/quazip-1.3/build
RUN sudo cmake -DCMAKE_C_FLAGS:STRING="-fPIC" -DCMAKE_CXX_FLAGS:STRING="-fPIC" ..
RUN sudo make
RUN sudo make install
WORKDIR /opt/odktools-deps

RUN sudo ln -s /usr/bin/aclocal-1.16 /usr/bin/aclocal-1.14
RUN sudo ln -s /usr/bin/automake-1.16 /usr/bin/automake-1.14

RUN sudo tar xvfz RELEASE_1.1.4.tar.gz
WORKDIR /opt/odktools-deps/libxlsxwriter-RELEASE_1.1.4
RUN sudo mkdir build
WORKDIR /opt/odktools-deps/libxlsxwriter-RELEASE_1.1.4/build
RUN sudo cmake ..
RUN sudo make
RUN sudo make install
WORKDIR /opt/odktools-deps

WORKDIR /opt/odktools-deps/libcsv
RUN sudo ./configure
RUN sudo make
RUN sudo make install

WORKDIR /opt/odktools

RUN sudo qmake
RUN sudo make

RUN sudo apt-get update \
    && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y locales \
    && sudo sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
    && sudo dpkg-reconfigure --frontend=noninteractive locales \
    && sudo update-locale LANG=en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8

WORKDIR /opt
RUN sudo mkdir formshare_repository
RUN sudo mkdir formshare_log
RUN sudo mkdir formshare_celery
RUN sudo mkdir formshare_gunicorn
RUN sudo mkdir formshare_config
RUN sudo mkdir formshare_plugins
COPY ./docker_files/testing_plugin_directories.zip /opt/formshare_plugins
WORKDIR /opt/formshare_plugins
RUN sudo unzip ./testing_plugin_directories.zip

RUN sudo ldconfig

WORKDIR /home/circleci/project

USER circleci
ENV PATH /home/circleci/.local/bin:/home/circleci/bin:${PATH}

CMD ["/bin/bash"]