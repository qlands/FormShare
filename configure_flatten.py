import os
import stat
import sys

from jinja2 import Environment, FileSystemLoader


def main():
    formshare_path = "."
    formshare_flatten_app = os.path.join(
        formshare_path, *["formshare", "scripts", "flatten_jsons.py"]
    )

    template_environment = Environment(
        autoescape=False,
        loader=FileSystemLoader(os.path.join(formshare_path, "templates")),
        trim_blocks=False,
    )

    context = {"path_to_python": sys.executable}

    rendered_template = template_environment.get_template(
        "flatten_jsons_template.jinja2"
    ).render(context)

    with open(formshare_flatten_app, "w") as f:
        f.write(rendered_template)

    st = os.stat(formshare_flatten_app)
    os.chmod(formshare_flatten_app, st.st_mode | stat.S_IEXEC)


if __name__ == "__main__":
    main()
