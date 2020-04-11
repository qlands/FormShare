"""Move Gunicorn values to ini file

Revision ID: f73906cd769f
Revises: 2348d90c7152
Create Date: 2020-04-11 11:18:19.864006

"""
import configparser
from alembic import context
from formshare.scripts.modifyconfig import modify_ini_file
import os
import shutil

# revision identifiers, used by Alembic.
revision = "f73906cd769f"
down_revision = "2348d90c7152"
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
    shutil.copyfile(config_uri, config_uri + ".bk.f73906cd769f")
    config = configparser.ConfigParser()
    config.read(config_uri)
    modify_ini_file(config, "ADD", "server:main", "capture_output", "True")
    modify_ini_file(config, "ADD", "server:main", "proxy_protocol", "True")
    modify_ini_file(config, "ADD", "server:main", "daemon", "True")
    if "FORMSHARE_HOST" in os.environ:  # Running on Docker
        path_to_pid_file = "/opt/formshare_gunicorn/formshare.pid"
        path_to_log_file = "/opt/formshare_log/error_log"
    else:
        path_to_config = os.path.dirname(config_uri)
        path_to_pid_file = os.path.join(path_to_config, *["formshare.pid"])
        path_to_log_file = os.path.join(path_to_config, *["error_log"])
    modify_ini_file(config, "ADD", "server:main", "pidfile", path_to_pid_file)
    modify_ini_file(config, "ADD", "server:main", "errorlog", path_to_log_file)
    if "FORWARDED_ALLOW_IP" in os.environ:
        forwarded_allow_ip = os.environ.get("FORWARDED_ALLOW_IP")
    else:
        forwarded_allow_ip = config.get("server:main", "host")
    modify_ini_file(
        config, "ADD", "server:main", "forwarded_allow_ips", forwarded_allow_ip
    )
    with open(config_uri, "w") as configfile:
        config.write(configfile)


def downgrade():
    config_uri = context.config.get_main_option("formshare.ini.file", None)
    config = configparser.ConfigParser()
    config.read(config_uri)
    modify_ini_file(config, "REMOVE", "server:main", "capture_output")
    modify_ini_file(config, "REMOVE", "server:main", "proxy_protocol")
    modify_ini_file(config, "REMOVE", "server:main", "daemon")
    modify_ini_file(config, "REMOVE", "server:main", "pidfile")
    modify_ini_file(config, "REMOVE", "server:main", "errorlog")
    modify_ini_file(config, "REMOVE", "server:main", "forwarded_allow_ips")
    with open(config_uri, "w") as configfile:
        config.write(configfile)
