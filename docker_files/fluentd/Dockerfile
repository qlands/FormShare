FROM fluent/fluentd:v1.14-1

# Use root account to use apk
USER root

# below RUN includes plugin as examples elasticsearch is not required
# you may customize including plugins as you wish
RUN apk add --no-cache --update --virtual .build-deps \
        sudo build-base ruby-dev \
 && sudo gem install fluent-plugin-elasticsearch \
 && sudo gem sources --clear-all \
 && apk del .build-deps \
 && rm -rf /tmp/* /var/tmp/* /usr/lib/ruby/gems/*/cache/*.gem

ADD https://github.com/ufoscout/docker-compose-wait/releases/download/2.6.0/wait /wait
RUN chmod +x /wait

COPY ./docker_files/fluent.conf /fluentd/etc/
COPY ./docker_files/entrypoint.sh /bin/

RUN mkdir /opt/formshare_log
VOLUME /opt/formshare_log

VOLUME /fluentd/etc/

ENV FLUENTD_CONF="fluent.conf"
RUN chmod +x /bin/entrypoint.sh
ENV LD_PRELOAD=""
EXPOSE 24224 5140

USER fluent
ENTRYPOINT ["tini",  "--", "/bin/entrypoint.sh"]
CMD ["fluentd"]