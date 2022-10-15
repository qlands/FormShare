cd /etc/apache2/mods-enabled
ln -s ../mods-available/cache.load .
ln -s ../mods-available/cache_socache.load .
ln -s ../mods-available/headers.load .
ln -s ../mods-available/lbmethod_byrequests.load .
rm mpm_event.conf
rm mpm_event.load
ln -s ../mods-available/mpm_prefork.conf .
ln -s ../mods-available/mpm_prefork.load .
ln -s ../mods-available/proxy.conf .
ln -s ../mods-available/proxy.load .
ln -s ../mods-available/proxy_http.load .
ln -s ../mods-available/rewrite.load .
ln -s ../mods-available/socache_shmcb.load .
ln -s ../mods-available/ssl.conf .
ln -s ../mods-available/ssl.load .
