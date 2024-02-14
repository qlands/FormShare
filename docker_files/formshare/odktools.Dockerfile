FROM ubuntu:22.04

MAINTAINER QLands Technology Consultants
RUN apt-get update && apt-get -y upgrade
RUN apt-get install -y software-properties-common
RUN add-apt-repository universe
RUN add-apt-repository multiverse

RUN apt-get install -y wget

RUN add-apt-repository ppa:mosquitto-dev/mosquitto-ppa -y

RUN wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc |  gpg --dearmor | tee /usr/share/keyrings/mongodb.gpg > /dev/null
RUN echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/6.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-6.0.list

RUN wget https://dev.mysql.com/get/mysql-apt-config_0.8.29-1_all.deb
RUN DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC dpkg -i ./mysql-apt-config_0.8.29-1_all.deb

RUN apt-get update

RUN DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC apt-get install -y build-essential qtbase5-dev qtbase5-private-dev qtdeclarative5-dev libqt5sql5-mysql cmake jq libboost-all-dev unzip zlib1g-dev automake npm redis-server libmysqlclient-dev mysql-client sqlite3 libqt5sql5-sqlite git wget python3-venv tidy golang-go mosquitto curl nano mongodb-org mysql-shell openjdk-17-jre-headless

RUN npm install -g diff2html
RUN npm install -g diff2html-cli@5.2.1
RUN npm install -g json2csv@5.0.7

COPY ./docker_files/timezone/mysql_tzinfo_to_sql /usr/bin

RUN wget https://github.com/BurntSushi/xsv/releases/download/0.13.0/xsv-0.13.0-x86_64-unknown-linux-musl.tar.gz
RUN tar xvfz xsv-0.13.0-x86_64-unknown-linux-musl.tar.gz
RUN cp xsv /bin

RUN git clone https://github.com/qlands/csv2xlsx.git
WORKDIR csv2xlsx
RUN go build
RUN cp csv2xlsx /bin

WORKDIR /opt
RUN mkdir odktools-deps
RUN git clone https://github.com/qlands/odktools.git -b stable-2.10

WORKDIR /opt/odktools-deps
RUN wget https://github.com/mongodb/mongo-c-driver/releases/download/1.21.1/mongo-c-driver-1.21.1.tar.gz
RUN wget https://github.com/mongodb/mongo-cxx-driver/releases/download/r3.6.7/mongo-cxx-driver-r3.6.7.tar.gz
RUN wget https://github.com/jmcnamara/libxlsxwriter/archive/refs/tags/RELEASE_1.1.4.tar.gz
RUN wget https://github.com/stachenov/quazip/archive/refs/tags/v1.3.tar.gz
RUN git clone https://github.com/rgamble/libcsv.git

RUN tar xvfz mongo-c-driver-1.21.1.tar.gz
WORKDIR /opt/odktools-deps/mongo-c-driver-1.21.1
RUN mkdir build_here
WORKDIR /opt/odktools-deps/mongo-c-driver-1.21.1/build_here
RUN cmake ..
RUN make
RUN make install
WORKDIR /opt/odktools-deps

RUN tar xvfz mongo-cxx-driver-r3.6.7.tar.gz
WORKDIR /opt/odktools-deps/mongo-cxx-driver-r3.6.7
RUN mkdir build_here
WORKDIR /opt/odktools-deps/mongo-cxx-driver-r3.6.7/build_here
RUN cmake -DCMAKE_C_FLAGS:STRING="-O2 -fPIC" -DCMAKE_CXX_FLAGS:STRING="-O2 -fPIC" -DBSONCXX_POLY_USE_BOOST=1 -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr/local ..
RUN make
RUN make install
WORKDIR /opt/odktools-deps

RUN tar xvfz v1.3.tar.gz
WORKDIR /opt/odktools-deps/quazip-1.3
RUN mkdir build
WORKDIR /opt/odktools-deps/quazip-1.3/build
RUN cmake -DCMAKE_C_FLAGS:STRING="-fPIC" -DCMAKE_CXX_FLAGS:STRING="-fPIC" ..
RUN make
RUN make install
WORKDIR /opt/odktools-deps

RUN ln -s /usr/bin/aclocal-1.16 /usr/bin/aclocal-1.14
RUN ln -s /usr/bin/automake-1.16 /usr/bin/automake-1.14

RUN tar xvfz RELEASE_1.1.4.tar.gz
WORKDIR /opt/odktools-deps/libxlsxwriter-RELEASE_1.1.4
RUN mkdir build
WORKDIR /opt/odktools-deps/libxlsxwriter-RELEASE_1.1.4/build
RUN cmake ..
RUN make
RUN make install
WORKDIR /opt/odktools-deps

WORKDIR /opt/odktools-deps/libcsv
RUN ./configure
RUN make
RUN make install

WORKDIR /opt/odktools

RUN qmake
RUN make

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y locales \
    && sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
    && dpkg-reconfigure --frontend=noninteractive locales \
    && update-locale LANG=en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8