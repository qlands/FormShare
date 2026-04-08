import argparse
import os
import random
import string
import uuid

from jinja2 import Environment, FileSystemLoader


def random_password(size):
    """Generate a random password"""
    random_source = string.ascii_letters + string.digits
    password = random.choice(string.ascii_lowercase)
    password += random.choice(string.ascii_uppercase)
    password += random.choice(string.digits)
    for i in range(size):
        password += random.choice(random_source)
    password_list = list(password)
    random.SystemRandom().shuffle(password_list)
    password = "".join(password_list)
    return password


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ini_path", help="Path to ini file to create")
    args = parser.parse_args()
    formshare_path = "."

    main_secret = random_password(14).replace("%", "~")
    redis_sessions_secret = random_password(14).replace("%", "~")
    assistant_secret = random_password(14).replace("%", "!")
    partner_secret = random_password(14).replace("%", "!")
    auth_secret = random_password(14).replace("%", "#")
    auth_secret2 = random_password(14).replace("%", "#")
    aes_key = random_password(29).replace("%", "#")
    auth_opaque = uuid.uuid4().hex

    template_environment = Environment(
        autoescape=False,
        loader=FileSystemLoader(os.path.join(formshare_path, "templates")),
        trim_blocks=False,
    )

    context = {
        "mysql_host": os.getenv("MYSQL_HOST_NAME", "mysql"),
        "mysql_port": os.getenv("MYSQL_HOST_PORT", "3306"),
        "mysql_schema": "formshare",
        "mysql_user_name": os.getenv("MYSQL_USER_NAME", "root"),
        "mysql_user_password": os.getenv("MYSQL_USER_PASSWORD", "change_me_mysql_root"),
        "main_secret": main_secret,
        "assistant_secret": assistant_secret,
        "partner_secret": partner_secret,
        "auth_secret": auth_secret,
        "auth_secret2": auth_secret2,
        "aes_key": aes_key,
        "auth_opaque": auth_opaque,
        "repository_path": "/opt/formshare_repository",
        "odktools_path": os.getenv("ODKTOOLS_PATH", "/opt/odktools"),
        "elastic_search_host": os.getenv("ELASTIC_SEARCH_HOST", "es01"),
        "elastic_search_port": os.getenv("ELASTIC_SEARCH_PORT", "9200"),
        "formshare_host": os.getenv("FORMSHARE_HOST", "0.0.0.0"),
        "formshare_port": os.getenv("FORMSHARE_PORT", "5900"),
        "forwarded_allow_ip": os.getenv("FORWARDED_ALLOW_IP", "*"),
        "redis_sessions_secret": redis_sessions_secret,
        "elasticsearch_user_name": os.getenv("ELASTIC_USER", "elastic"),
        "elasticsearch_user_password": os.getenv(
            "ELASTIC_PASSWORD", "change_me_elastic"
        ),
    }
    rendered_template = template_environment.get_template("formshare.jinja2").render(
        context
    )

    if not os.path.exists(args.ini_path):
        with open(args.ini_path, "w") as f:
            f.write(rendered_template)
        print("FormShare INI file created at {}".format(args.ini_path))
    else:
        print("INI file {} already exists".format(args.ini_path))


if __name__ == "__main__":
    main()
