import sys
import os
from jinja2 import Environment, FileSystemLoader


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri> <path_to_formshare> \n'
          "(example: %s ./development.ini)" % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) != 3:
        usage(argv)
    config_uri = argv[1]
    formshare_path = os.path.abspath(argv[2])
    formshare_ini_file = os.path.join(formshare_path, os.path.basename(config_uri))
    climmob_celery_app = os.path.join(formshare_path, *['formshare', 'config', 'celery_app.py'])

    template_environment = Environment(autoescape=False,
                                       loader=FileSystemLoader(os.path.join(formshare_path, 'templates')),
                                       trim_blocks=False)

    context = {
        'FORMSHARE_INI_FILE': formshare_ini_file
    }

    rendered_template = template_environment.get_template('celery_app_template.py').render(context)

    with open(climmob_celery_app, 'w') as f:
        f.write(rendered_template)
