#!/bin/bash

# Make sure that NOBODY can access the server without a password
mysql --password="" -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'circleci';"
# Allow root login from any host
mysql --password="circleci" -e "CREATE USER 'root'@'%' IDENTIFIED BY 'circleci'"
# Allow root grant to all
mysql --password="circleci" -e "GRANT ALL ON *.* TO 'root'@'%'"
# Make our changes take effect
mysql --password="circleci" -e "FLUSH PRIVILEGES"