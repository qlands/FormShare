import argparse
import configparser
import os

from jinja2 import Environment, FileSystemLoader


def get_section(ini_file, section):
    try:
        config = configparser.ConfigParser()
        config.read(ini_file)
        return dict(config.items(section))
    except Exception as e:
        print(
            "Warning: Unable to read section {}. Empty dict was return".format(
                section, str(e)
            )
        )
        return {}


def get_ini_value(ini_file, key, default=None, section="app:formshare"):
    try:
        config = configparser.ConfigParser()
        config.read(ini_file)
        return config.get(section, key)
    except Exception as e:
        print("Warning: Unable to find key {}. {} . Default used".format(key, str(e)))
        return default


def main(raw_args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("ini_path", help="Path to ini file")
    parser.add_argument("formshare_path", help="Path to Formshare")
    parser.add_argument(
        "--json_file",
        default="",
        help="JSON file to create. By default is [FormShare_path/formshare/tests/test_config.json]",
    )
    args = parser.parse_args(raw_args)

    if not os.path.exists(os.path.abspath(args.ini_path)):
        print("Ini file does not exists")
        return 1
    if not os.path.exists(os.path.abspath(args.formshare_path)):
        print("Path to FormShare does not exits")
        return 1

    formshare_path = os.path.abspath(args.formshare_path)

    if args.json_file == "":
        json_file = os.path.join(
            formshare_path, *["formshare", "tests", "test_config.json"]
        )
    else:
        json_file = args.json_file

    mysql_cnf = os.path.join(formshare_path, *["mysql.cnf"])

    template_environment = Environment(
        autoescape=False,
        loader=FileSystemLoader(os.path.join(formshare_path, "templates")),
        trim_blocks=False,
    )
    sqlalchemy_url = get_ini_value(os.path.abspath(args.ini_path), "sqlalchemy.url", "")
    elasticfeeds_host = get_ini_value(
        os.path.abspath(args.ini_path), "elasticfeeds.host", "localhost"
    )

    elasticsearch_user_host = get_ini_value(
        os.path.abspath(args.ini_path), "elasticsearch.user.host", "localhost"
    )
    elasticsearch_repository_host = get_ini_value(
        os.path.abspath(args.ini_path), "elasticsearch.repository.host", "localhost"
    )

    elasticsearch_records_host = get_ini_value(
        os.path.abspath(args.ini_path), "elasticsearch.records.host", "localhost"
    )

    repository_path = get_ini_value(
        os.path.abspath(args.ini_path), "repository.path", ""
    )
    odktools_path = get_ini_value(os.path.abspath(args.ini_path), "odktools.path", "")

    mysql_host = get_ini_value(
        os.path.abspath(args.ini_path), "mysql.host", "localhost"
    )
    mysql_port = get_ini_value(os.path.abspath(args.ini_path), "mysql.port", "3306")
    mysql_user = get_ini_value(os.path.abspath(args.ini_path), "mysql.user", "empty!")
    mysql_password = get_ini_value(
        os.path.abspath(args.ini_path), "mysql.password", "empty!"
    )

    server_main_host = get_ini_value(
        os.path.abspath(args.ini_path), "host", "localhost", "server:main"
    )
    server_main_port = get_ini_value(
        os.path.abspath(args.ini_path), "port", "localhost", "server:main"
    )

    composite_section = get_section(args.ini_path, "composite:main")
    composite_section.pop("use")
    server_main_root = list(composite_section.keys())[0]

    context = {
        "mysql_host": mysql_host,
        "mysql_port": mysql_port,
        "mysql_user": mysql_user,
        "mysql_password": mysql_password,
        "sqlalchemy_url": sqlalchemy_url,
        "elasticfeeds_host": elasticfeeds_host,
        "elasticsearch_user_host": elasticsearch_user_host,
        "elasticsearch_repository_host": elasticsearch_repository_host,
        "elasticsearch_records_host": elasticsearch_records_host,
        "repository_path": repository_path,
        "odktools_path": odktools_path,
        "mysql_cnf": mysql_cnf,
        "formshare_test_directory": os.path.join(
            formshare_path, *["formshare", "tests"]
        ),
        "server_main_host": server_main_host,
        "server_main_port": server_main_port,
        "server_main_root": server_main_root,
    }

    rendered_template = template_environment.get_template("test_config.jinja2").render(
        context
    )

    with open(json_file, "w") as f:
        f.write(rendered_template)
    return 0
