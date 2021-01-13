"""Disable SSL in INI file

Revision ID: 5750ade545b3
Revises: b0d6a2d89fc7
Create Date: 2021-01-13 13:30:32.518183

"""
import configparser
import shutil

from alembic import context


# revision identifiers, used by Alembic.
revision = '5750ade545b3'
down_revision = 'b0d6a2d89fc7'
branch_labels = None
depends_on = None


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
    config = configparser.ConfigParser()
    config.read(config_uri)

    current_sqlalchemy_url = config.get("app:formshare", "sqlalchemy.url")
    found = current_sqlalchemy_url.find("&ssl_disabled=True")
    if found == -1:
        shutil.copyfile(config_uri, config_uri + ".bk.5750ade545b3")
        current_sqlalchemy_url = current_sqlalchemy_url + "&ssl_disabled=True"
        config.set("app:formshare", "sqlalchemy.url", current_sqlalchemy_url)
        with open(config_uri, "w") as configfile:
            config.write(configfile)


def downgrade():
    config_uri = context.config.get_main_option("formshare.ini.file", None)
    if config_uri is None:
        print(
            "This migration needs parameter 'formshare.ini.file' in the alembic ini file."
        )
        print(
            "The parameter 'formshare.ini.file' must point to the full path of the FormShare ini file"
        )
        exit(1)
    config = configparser.ConfigParser()
    config.read(config_uri)

    current_sqlalchemy_url = config.get("app:formshare", "sqlalchemy.url")
    found = current_sqlalchemy_url.find("&ssl_disabled=True")
    if found >= 0:
        current_sqlalchemy_url = current_sqlalchemy_url.replace("&ssl_disabled=True", "")
        config.set("app:formshare", "sqlalchemy.url", current_sqlalchemy_url)
        with open(config_uri, "w") as configfile:
            config.write(configfile)
