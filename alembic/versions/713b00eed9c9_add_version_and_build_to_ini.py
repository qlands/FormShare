"""Add version and build to ini

Revision ID: 713b00eed9c9
Revises: d9e72a903f87
Create Date: 2020-04-22 14:49:21.947813

"""
import configparser
from alembic import context
from formshare.scripts.modifyconfig import modify_ini_file
import shutil


# revision identifiers, used by Alembic.
revision = "713b00eed9c9"
down_revision = "d9e72a903f87"
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
    shutil.copyfile(config_uri, config_uri + ".bk.713b00eed9c9")
    config = configparser.ConfigParser()
    config.read(config_uri)

    modify_ini_file(config, "ADD", "app:formshare", "formshare.version", "2.6")
    modify_ini_file(config, "ADD", "app:formshare", "formshare.build", "20200420")
    with open(config_uri, "w") as configfile:
        config.write(configfile)


def downgrade():
    config_uri = context.config.get_main_option("formshare.ini.file", None)
    config = configparser.ConfigParser()
    config.read(config_uri)
    modify_ini_file(config, "REMOVE", "app:formshare", "formshare.version")
    modify_ini_file(config, "REMOVE", "app:formshare", "formshare.build")
    with open(config_uri, "w") as configfile:
        config.write(configfile)
