"""Add Redis settings to INI

Revision ID: 389ebd4096fc
Revises: f73906cd769f
Create Date: 2020-04-15 07:45:26.850428

"""
import configparser
from alembic import context
from formshare.scripts.modifyconfig import modify_ini_file
import os
import shutil
import random
import string


# revision identifiers, used by Alembic.
revision = '389ebd4096fc'
down_revision = 'f73906cd769f'
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
    shutil.copyfile(config_uri, config_uri + ".bk.389ebd4096fc")
    config = configparser.ConfigParser()
    config.read(config_uri)

    redis_sessions_secret = random_password(17).replace("%", "~")
    modify_ini_file(config, "ADD", "app:formshare", "redis.sessions.secret", redis_sessions_secret)
    modify_ini_file(config, "ADD", "app:formshare", "redis.sessions.timeout", "7200")
    modify_ini_file(config, "ADD", "app:formshare", "redis.sessions.cookie_name", "formshare_session")

    if "FORMSHARE_HOST" in os.environ:  # Running on Docker
        modify_ini_file(config, "ADD", "app:formshare", "redis.sessions.host", "172.28.1.6")
        modify_ini_file(config, "ADD", "app:formshare", "redis.sessions.port", "6379")
    else:
        modify_ini_file(config, "ADD", "app:formshare", "redis.sessions.host", "localhost")
        modify_ini_file(config, "ADD", "app:formshare", "redis.sessions.port", "6379")

    with open(config_uri, "w") as configfile:
        config.write(configfile)


def downgrade():
    config_uri = context.config.get_main_option("formshare.ini.file", None)
    config = configparser.ConfigParser()
    config.read(config_uri)
    modify_ini_file(config, "REMOVE", "app:formshare", "redis.sessions.secret")
    modify_ini_file(config, "REMOVE", "app:formshare", "redis.sessions.timeout")
    modify_ini_file(config, "REMOVE", "app:formshare", "redis.sessions.cookie_name")
    modify_ini_file(config, "REMOVE", "app:formshare", "redis.sessions.host")
    modify_ini_file(config, "REMOVE", "app:formshare", "redis.sessions.port")

    with open(config_uri, "w") as configfile:
        config.write(configfile)