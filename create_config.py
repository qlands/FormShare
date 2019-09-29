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
    }
    rendered_template = template_environment.get_template("formshare.jinja2").render(
        context
    )

    with open(args.ini_path, "w") as f:
        f.write(rendered_template)

    print("FormShare INI file created at {}".format(args.ini_path))


if __name__ == "__main__":
    main()
