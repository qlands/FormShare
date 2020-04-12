import os
from jinja2 import Environment, FileSystemLoader
import argparse
import random
import string
import uuid


def random_password(size):
    """Generate a random password """
    random_source = string.ascii_letters + string.digits + string.punctuation
    password = random.choice(string.ascii_lowercase)
    password += random.choice(string.ascii_uppercase)
    password += random.choice(string.digits)
    password += random.choice(string.punctuation)
    for i in range(size):
        password += random.choice(random_source)
    password_list = list(password)
    random.SystemRandom().shuffle(password_list)
    password = "".join(password_list)
    return password


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ini_path", help="Path to ini file to create")
    parser.add_argument("--mysql_host", required=True, help="MySQL host server to use")
    parser.add_argument("--forwarded_allow_ip", required=True, help="IP of the proxy server calling FormShare")
    parser.add_argument("--pid_file", required=True, help="File that will store the FormShare process ID")
    parser.add_argument("--error_log_file", required=True, help="File that will store the FormShare logs")
    parser.add_argument(
        "-d", "--daemon", action="store_true", help="Start as FormShare in detached mode"
    )
    parser.add_argument(
        "-c", "--capture_output", action="store_true", help="Start as FormShare in detached mode"
    )
    parser.add_argument(
        "-o", "--overwrite", action="store_true", help="Overwrite if exists"
    )

    parser.add_argument(
        "--repository_path", required=True, help="Path to the FormShare repository"
    )
    parser.add_argument("--odktools_path", required=True, help="Path to ODK Tools")
    parser.add_argument(
        "--mysql_port", default=3306, help="MySQL port to use. Default to 3306"
    )
    parser.add_argument(
        "--mysql_schema",
        default="formshare",
        help="MySQL schema to use. Default to 'formshare'",
    )
    parser.add_argument(
        "--mysql_user_name",
        required=True,
        help="MySQL user name to use to create the schema",
    )
    parser.add_argument(
        "--mysql_user_password", required=True, help="MySQL user name password"
    )
    parser.add_argument(
        "--elastic_search_host", required=True, help="ElasticSearch host name"
    )
    parser.add_argument(
        "--elastic_search_port", required=True, help="ElasticSearch host name"
    )
    parser.add_argument(
        "--formshare_host", required=True, help="Host name for FormShare"
    )
    parser.add_argument("--formshare_port", required=True, help="Port for FormShare")
    parser.add_argument(
        "--elastic_search_ssl", action="store_true", help="ElasticSearch use SSL"
    )
    args = parser.parse_args()
    formshare_path = "."

    main_secret = random_password(13).replace("%", "~")
    assistant_secret = random_password(13).replace("%", "!")
    auth_secret = random_password(13).replace("%", "#")
    aes_key = random_password(28).replace("%", "#")
    auth_opaque = uuid.uuid4().hex

    template_environment = Environment(
        autoescape=False,
        loader=FileSystemLoader(os.path.join(formshare_path, "templates")),
        trim_blocks=False,
    )

    context = {
        "mysql_host": args.mysql_host,
        "mysql_port": args.mysql_port,
        "mysql_schema": args.mysql_schema,
        "mysql_user_name": args.mysql_user_name,
        "mysql_user_password": args.mysql_user_password,
        "main_secret": main_secret,
        "assistant_secret": assistant_secret,
        "auth_secret": auth_secret,
        "aes_key": aes_key,
        "auth_opaque": auth_opaque,
        "repository_path": args.repository_path,
        "odktools_path": args.odktools_path,
        "elastic_search_host": args.elastic_search_host,
        "elastic_search_port": args.elastic_search_port,
        "elastic_search_ssl": args.elastic_search_ssl,
        "formshare_host": args.formshare_host,
        "formshare_port": args.formshare_port,
        "capture_output": args.capture_output,
        "daemon": args.daemon,
        "pid_file": args.pid_file,
        "error_log_file": args.error_log_file,
        "forwarded_allow_ip": args.forwarded_allow_ip,
    }
    rendered_template = template_environment.get_template("formshare.jinja2").render(
        context
    )

    if not os.path.exists(args.ini_path):
        with open(args.ini_path, "w") as f:
            f.write(rendered_template)
        print("FormShare INI file created at {}".format(args.ini_path))
    else:
        if args.overwrite:
            with open(args.ini_path, "w") as f:
                f.write(rendered_template)
            print("FormShare INI file created at {}".format(args.ini_path))
        else:
            print("INI file {} already exists".format(args.ini_path))


if __name__ == "__main__":
    main()
