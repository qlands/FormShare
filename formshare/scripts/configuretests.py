import configparser
import os
import argparse

from jinja2 import Environment, FileSystemLoader


def get_ini_value(ini_file, key, default=None):
    try:
        config = configparser.ConfigParser()
        config.read(ini_file)
        return config.get("app:formshare", key)
    except Exception as e:
        print("Warning: Unable to find key {}. {} . Default used".format(key, str(e)))
        return default


def main(raw_args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("ini_path", help="Path to ini file")
    parser.add_argument("formshare_path", help="Path to Formshare")
    parser.add_argument(
        "--mysql_cnf_file",
        default="",
        help="CNF file to create. By default is [FormShare_path/mysql.cnf]",
    )
    args = parser.parse_args(raw_args)

    if not os.path.exists(os.path.abspath(args.ini_path)):
        print("Ini file does not exists")
        return 1
    if not os.path.exists(os.path.abspath(args.formshare_path)):
        print("Path to FormShare does not exits")
        return 1

    formshare_ini_file_path = os.path.dirname(os.path.abspath(args.ini_path))
    formshare_path = os.path.abspath(args.formshare_path)

    if args.mysql_cnf_file == "":
        mysql_cnf_file = os.path.join(formshare_ini_file_path, *["mysql.cnf"])
    else:
        mysql_cnf_file = args.mysql_cnf_file

    template_environment = Environment(
        autoescape=False,
        loader=FileSystemLoader(os.path.join(formshare_path, "templates")),
        trim_blocks=False,
    )
    host = get_ini_value(os.path.abspath(args.ini_path), "mysql.host", "localhost")
    port = get_ini_value(os.path.abspath(args.ini_path), "mysql.port", "3306")
    user = get_ini_value(os.path.abspath(args.ini_path), "mysql.user", "empty!")
    password = get_ini_value(os.path.abspath(args.ini_path), "mysql.password", "empty!")
    context = {"host": host, "port": port, "user": user, "password": password}

    rendered_template = template_environment.get_template("mysql.jinja2").render(
        context
    )

    with open(mysql_cnf_file, "w") as f:
        f.write(rendered_template)
    return 0
