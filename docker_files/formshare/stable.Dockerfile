FROM qlands/odktools:20211231

MAINTAINER QLands Technology Consultants

WORKDIR /opt
RUN mkdir formshare_repository
VOLUME /opt/formshare_repository

RUN mkdir formshare_log
VOLUME /opt/formshare_log

RUN mkdir formshare_celery
VOLUME /opt/formshare_celery

RUN mkdir formshare_fluentd
VOLUME /opt/formshare_fluentd

RUN mkdir formshare_plugins
VOLUME /opt/formshare_plugins

RUN mkdir formshare_odata_webapps
VOLUME /opt/formshare_odata_webapps

VOLUME /etc/mosquitto/conf.d/

COPY ./docker_files/mosquitto/mosquitto.conf /root
COPY ./docker_files/mosquitto/websocket.conf /root
COPY ./docker_files/mosquitto/access.acl /root

RUN mkdir formshare_gunicorn
RUN python3 -m venv formshare_env

RUN git clone https://github.com/qlands/FormShare.git -b stable-2.11.0 formshare
RUN . ./formshare_env/bin/activate && pip install wheel && pip install -r /opt/formshare/requirements.txt && python /opt/formshare/download_nltk_packages.py

ADD https://github.com/ufoscout/docker-compose-wait/releases/download/2.6.0/wait /wait
RUN chmod +x /wait

WORKDIR /opt
RUN mkdir formshare_config
VOLUME /opt/formshare_config

COPY ./docker_files/etc/default/celery_formshare /etc/default/celery_formshare
COPY ./docker_files/etc/init.d/celery_formshare /etc/init.d/celery_formshare
COPY ./docker_files/run_server.sh /opt/formshare_gunicorn
COPY ./docker_files/stop_server.sh /opt/formshare_gunicorn
COPY ./docker_files/docker-entrypoint.sh /

EXPOSE 5900

RUN chmod +x /docker-entrypoint.sh
RUN chmod +x /etc/init.d/celery_formshare
RUN chmod +x /opt/formshare_gunicorn/run_server.sh
RUN chmod +x /opt/formshare_gunicorn/stop_server.sh
RUN chmod 640 /etc/default/celery_formshare
RUN ldconfig
ENTRYPOINT ["/docker-entrypoint.sh"]