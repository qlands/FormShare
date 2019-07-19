import sys
import os
from jinja2 import Environment, FileSystemLoader


def usage(argv):
    cmd = os.path.basename(argv[0])
    print(
        "usage: %s <path_to_ini_file>\n" "(example: %s ./development.ini )" % (cmd, cmd)
    )
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) != 2:
        usage(argv)
    if os.path.exists(argv[1]):
        print("Ini file already exists")
        sys.exit(1)

    formshare_path = "."

    template_environment = Environment(
        autoescape=False,
        loader=FileSystemLoader(os.path.join(formshare_path, "templates")),
        trim_blocks=False,
    )

    context = {}
    rendered_template = template_environment.get_template("formshare.jinja2").render(
        context
    )

    with open(argv[1], "w") as f:
        f.write(rendered_template)

    print("FormShare INI file created at {}".format(argv[1]))


if __name__ == "__main__":
    main()
