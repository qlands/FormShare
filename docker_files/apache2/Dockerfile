FROM httpd:2.4

RUN mkdir /usr/local/apache2/conf/sites

STOPSIGNAL WINCH

COPY ./docker_files/httpd-foreground /usr/local/bin/
COPY ./docker_files/httpd.conf /usr/local/apache2/conf/
COPY ./docker_files/000-default.conf /usr/local/apache2/conf/sites/
RUN chmod +x /usr/local/bin/httpd-foreground

EXPOSE 80
CMD ["httpd-foreground"]