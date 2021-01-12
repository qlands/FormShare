FROM ubuntu:20.04

MAINTAINER QLands Technology Consultants
RUN apt-get update && apt-get -y upgrade
RUN apt-get install -y software-properties-common
RUN add-apt-repository universe && add-apt-repository multiverse
RUN apt-get update

RUN apt-get install -y build-essential qt5-default qtbase5-private-dev qtdeclarative5-dev libqt5sql5-mysql cmake mongodb jq libboost-all-dev unzip zlib1g-dev automake npm redis-server libmysqlclient-dev mysql-client-8.0 openjdk-11-jdk sqlite3 libqt5sql5-sqlite git wget python3-venv

RUN npm install -g diff2html
RUN npm install -g diff2html-cli

WORKDIR /opt
RUN git clone https://github.com/qlands/odktools.git

RUN mkdir odktools-deps
WORKDIR /opt/odktools-deps
RUN wget --user=user https://github.com/mongodb/mongo-c-driver/releases/download/1.6.1/mongo-c-driver-1.6.1.tar.gz
RUN wget --user=user https://github.com/jmcnamara/libxlsxwriter/archive/RELEASE_0.7.6.tar.gz
RUN wget https://downloads.sourceforge.net/project/quazip/quazip/0.7.3/quazip-0.7.3.tar.gz
RUN git clone https://github.com/rgamble/libcsv.git

RUN tar xvfz mongo-c-driver-1.6.1.tar.gz
WORKDIR /opt/odktools-deps/mongo-c-driver-1.6.1
RUN ./configure
RUN make
RUN make install
WORKDIR /opt/odktools-deps

RUN tar xvfz quazip-0.7.3.tar.gz
WORKDIR /opt/odktools-deps/quazip-0.7.3
RUN mkdir build
WORKDIR /opt/odktools-deps/quazip-0.7.3/build
RUN cmake -DCMAKE_C_FLAGS:STRING="-fPIC" -DCMAKE_CXX_FLAGS:STRING="-fPIC" ..
RUN make
RUN make install
WORKDIR /opt/odktools-deps

RUN ln -s /usr/bin/aclocal-1.16 /usr/bin/aclocal-1.14
RUN ln -s /usr/bin/automake-1.16 /usr/bin/automake-1.14

RUN tar xvfz RELEASE_0.7.6.tar.gz
WORKDIR /opt/odktools-deps/libxlsxwriter-RELEASE_0.7.6
RUN mkdir build
WORKDIR /opt/odktools-deps/libxlsxwriter-RELEASE_0.7.6/build
RUN cmake ..
RUN make
RUN make install
WORKDIR /opt/odktools-deps

WORKDIR /opt/odktools-deps/libcsv
RUN ./configure
RUN make
RUN make install

WORKDIR /opt/odktools/dependencies/mongo-cxx-driver-r3.1.1
RUN mkdir build
WORKDIR /opt/odktools/dependencies/mongo-cxx-driver-r3.1.1/build
RUN cmake -DCMAKE_C_FLAGS:STRING="-O2 -fPIC" -DCMAKE_CXX_FLAGS:STRING="-O2 -fPIC" -DBSONCXX_POLY_USE_BOOST=1 -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr/local ..
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