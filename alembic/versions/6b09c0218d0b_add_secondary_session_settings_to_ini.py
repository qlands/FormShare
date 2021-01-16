"""Add secondary session settings to ini

Revision ID: 6b09c0218d0b
Revises: b0d6a2d89fc7
Create Date: 2021-01-16 07:54:33.688670

"""
import configparser
import random
import shutil
import string

from alembic import context
from formshare.scripts.modifyconfig import modify_ini_file


# revision identifiers, used by Alembic.
revision = "6b09c0218d0b"
down_revision = "b0d6a2d89fc7"
branch_labels = None
depends_on = None


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


def upgrade():
    config_uri = context.config.get_main_option("formshare.ini.file", None)
    if config_uri is None:
        print(
            "This migration needs parameter 'formshare.ini.file' in the alembic ini file."
        )
        print(
            "The parameter 'formshare.ini.file' must point to the full path of the FormShare ini file"
        )
        exit(1)
    shutil.copyfile(config_uri, config_uri + ".bk.6b09c0218d0b")
    config = configparser.ConfigParser()
    config.read(config_uri)

    secondary_sessions_secret = random_password(17).replace("%", "~")
    modify_ini_file(
        config,
        "ADD",
        "app:formshare",
        "auth.secondary.secret",
        secondary_sessions_secret,
    )
    modify_ini_file(
        config,
        "ADD",
        "app:formshare",
        "auth.secondary.cookie",
        "formshare_secondary_tkt",
    )
    with open(config_uri, "w") as configfile:
        config.write(configfile)


def downgrade():
    config_uri = context.config.get_main_option("formshare.ini.file", None)
    config = configparser.ConfigParser()
    config.read(config_uri)
    modify_ini_file(config, "REMOVE", "app:formshare", "auth.secondary.secret")
    modify_ini_file(config, "REMOVE", "app:formshare", "auth.secondary.cookie")
    with open(config_uri, "w") as configfile:
        config.write(configfile)
