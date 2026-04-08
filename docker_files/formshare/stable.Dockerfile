FROM qlands/odktools:20260407

LABEL MAINTAINER="QLands Software Inc."

WORKDIR /opt
RUN mkdir formshare_repository
VOLUME /opt/formshare_repository

RUN mkdir formshare_log
VOLUME /opt/formshare_log

RUN mkdir formshare_celery
VOLUME /opt/formshare_celery

RUN mkdir formshare_plugins
VOLUME /opt/formshare_plugins

RUN mkdir formshare_uvicorn
RUN python3.13 -m venv formshare_env

RUN git clone https://github.com/qlands/FormShare.git -b stable-3.0.0 formshare
RUN . ./formshare_env/bin/activate && pip install wheel && pip install -r /opt/formshare/requirements.txt && python /opt/formshare/download_nltk_packages.py

ADD https://github.com/ufoscout/docker-compose-wait/releases/download/2.6.0/wait /wait
RUN chmod +x /wait

WORKDIR /opt
RUN mkdir formshare_config
VOLUME /opt/formshare_config

COPY ./docker_files/etc/default/celery_formshare /etc/default/celery_formshare
COPY ./docker_files/etc/init.d/celery_formshare /etc/init.d/celery_formshare
COPY ./docker_files/run_server.sh /opt/formshare_uvicorn
COPY ./docker_files/stop_server.sh /opt/formshare_uvicorn
COPY ./docker_files/docker-entrypoint.sh /

EXPOSE 5900

RUN chmod +x /docker-entrypoint.sh
RUN chmod +x /etc/init.d/celery_formshare
RUN chmod +x /opt/formshare_uvicorn/run_server.sh
RUN chmod +x /opt/formshare_uvicorn/stop_server.sh
RUN chmod 640 /etc/default/celery_formshare
RUN ldconfig
ENTRYPOINT ["/docker-entrypoint.sh"]