import sys
import os
import configparser
from jinja2 import Environment, FileSystemLoader
import logging
log = logging.getLogger("formshare")


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <path_to_formshare> <path_to_ini_file>\n'
          "(example: %s . ./development.ini )" % (cmd, cmd))
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
    if os.path.exists(argv[2]):
        print("Ini file already exists")
        sys.exit(1)
    if not os.path.exists(os.path.abspath(argv[1])):
        print("Path to FormShare does not exits")
        sys.exit(1)

    formshare_path = os.path.abspath(argv[1])

    template_environment = Environment(autoescape=False,
                                       loader=FileSystemLoader(os.path.join(formshare_path, 'templates')),
                                       trim_blocks=False)
    sqlalchemy_url = get_ini_value(os.path.abspath(argv[1]), 'sqlalchemy.url', 'empty')
    context = {'sqlalchemy_url': sqlalchemy_url}

    rendered_template = template_environment.get_template('formshare.jinja2').render(context)

    with open(argv[2], 'w') as f:
        f.write(rendered_template)

    print("FormShare INI file created at {}".format(argv[2]))
