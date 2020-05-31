import os
import sys

from jinja2 import Environment, FileSystemLoader


def usage(argv):
    cmd = os.path.basename(argv[0])
    print(
        "usage: %s <path_to_ini_file> \n"
        "(example: %s ./development.ini )" % (cmd, cmd)
    )
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) != 2:
        usage(argv)
    formshare_path = "."
    formshare_ini_file = os.path.abspath(argv[1])
    if not os.path.exists(formshare_ini_file):
        print("Ini file {} does not exists".format(formshare_ini_file))
        sys.exit(1)
    formshare_celery_app = os.path.join(
        formshare_path, *["formshare", "config", "celery_app.py"]
    )

    template_environment = Environment(
        autoescape=False,
        loader=FileSystemLoader(os.path.join(formshare_path, "templates")),
        trim_blocks=False,
    )

    context = {"FORMSHARE_INI_FILE": formshare_ini_file}

    rendered_template = template_environment.get_template(
        "celery_app_template.jinja2"
    ).render(context)

    with open(formshare_celery_app, "w") as f:
        f.write(rendered_template)


if __name__ == "__main__":
    main()
