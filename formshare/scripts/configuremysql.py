import sys
import os
import configparser
from jinja2 import Environment, FileSystemLoader
import logging
log = logging.getLogger("formshare")


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <path_to_ini_file> <path_to_formshare> \n'
          "(example: %s ./development.ini .)" % (cmd, cmd))
    sys.exit(1)


def get_ini_value(ini_file, key, default=None):
    try:
        config = configparser.ConfigParser()
        config.read(ini_file)
        return config.get('app:formshare', key)
    except Exception as e:
        log.warning("Warning: Unable to find key {}. {} . Default used".format(key, str(e)))
        return default


def main(argv=sys.argv):
    if len(argv) != 3:
        usage(argv)
    if not os.path.exists(os.path.abspath(argv[1])):
        print("Ini file does not exists")
        sys.exit(1)
    if not os.path.exists(os.path.abspath(argv[2])):
        print("Path to FormShare does not exits")
        sys.exit(1)

    formshare_ini_file_path = os.path.dirname(os.path.abspath(argv[1]))
    formshare_path = os.path.abspath(argv[2])

    mysql_cnf_file = os.path.join(formshare_ini_file_path, *['mysql.cnf'])

    template_environment = Environment(autoescape=False,
                                       loader=FileSystemLoader(os.path.join(formshare_path, 'templates')),
                                       trim_blocks=False)
    host = get_ini_value(os.path.abspath(argv[1]), 'mysql.host', 'localhost')
    port = get_ini_value(os.path.abspath(argv[1]), 'mysql.port', '3306')
    user = get_ini_value(os.path.abspath(argv[1]), 'mysql.user', 'empty!')
    password = get_ini_value(os.path.abspath(argv[1]), 'mysql.password', 'empty!')
    context = {'host': host, 'port': port, 'user': user, 'password': password}

    rendered_template = template_environment.get_template('mysql.jinja2').render(context)

    with open(mysql_cnf_file, 'w') as f:
        f.write(rendered_template)
