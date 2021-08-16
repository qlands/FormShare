"""Add partner index params to ini

Revision ID: 22cde76e593c
Revises: f38bbf5ab703
Create Date: 2021-08-15 18:53:50.724368

"""
import configparser
import shutil
import os
from alembic import context

from formshare.scripts.modifyconfig import modify_ini_file


# revision identifiers, used by Alembic.
revision = "22cde76e593c"
down_revision = "f38bbf5ab703"
branch_labels = None
depends_on = None


def upgrade():
    config_uri = context.config.get_main_option("formshare.ini.file", None)
    config_uri = os.path.realpath(config_uri)
    if config_uri is None:
        print(
            "This migration needs parameter 'formshare.ini.file' in the alembic ini file."
        )
        print(
            "The parameter 'formshare.ini.file' must point to the full path of the FormShare ini file"
        )
        exit(1)
    shutil.copyfile(config_uri, config_uri + ".bk.22cde76e593c")
    config = configparser.ConfigParser()
    config.read(config_uri)

    elasticsearch_partner_host = config.get(
        "app:formshare", "elasticsearch.user.host", fallback="localhost"
    )
    elasticsearch_partner_port = config.get(
        "app:formshare", "elasticsearch.user.port", fallback="9200"
    )
    elasticsearch_partner_use_ssl = config.get(
        "app:formshare", "elasticsearch.user.use_ssl", fallback="False"
    )

    modify_ini_file(
        config,
        "ADD",
        "app:formshare",
        "elasticsearch.partner.index_name",
        "formshare_partners",
    )
    modify_ini_file(
        config,
        "ADD",
        "app:formshare",
        "elasticsearch.partner.host",
        elasticsearch_partner_host,
    )
    modify_ini_file(
        config,
        "ADD",
        "app:formshare",
        "elasticsearch.partner.port",
        elasticsearch_partner_port,
    )
    modify_ini_file(
        config,
        "ADD",
        "app:formshare",
        "elasticsearch.partner.use_ssl",
        elasticsearch_partner_use_ssl,
    )
    with open(config_uri, "w") as configfile:
        config.write(configfile)


def downgrade():
    config_uri = context.config.get_main_option("formshare.ini.file", None)
    config = configparser.ConfigParser()
    config.read(config_uri)
    modify_ini_file(
        config, "REMOVE", "app:formshare", "elasticsearch.partner.index_name"
    )
    modify_ini_file(config, "REMOVE", "app:formshare", "elasticsearch.partner.host")
    modify_ini_file(config, "REMOVE", "app:formshare", "elasticsearch.partner.port")
    modify_ini_file(config, "REMOVE", "app:formshare", "elasticsearch.partner.use_ssl")
    with open(config_uri, "w") as configfile:
        config.write(configfile)
