"""Configure mosquitto

Revision ID: 4adc5944c025
Revises: d0b3a36c4f7a
Create Date: 2021-07-30 18:14:48.769481

"""
import configparser
from alembic import context
from formshare.scripts.modifyconfig import modify_ini_file
import shutil
import os
import string
import random

# revision identifiers, used by Alembic.
revision = "4adc5944c025"
down_revision = "d0b3a36c4f7a"
branch_labels = None
depends_on = None


def random_password(size):
    """Generate a random password"""
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
    if not os.path.exists("/etc/init.d/mosquitto"):
        print("This migration requires a local mosquito server installed.")
        exit(1)
    config_uri = os.path.realpath(config_uri)
    shutil.copyfile(config_uri, config_uri + ".bk.389ebd4096fc")
    config = configparser.ConfigParser()
    config.read(config_uri)
    mosquitto_password = random_password(17).replace("%", "~").replace(":", "~")

    modify_ini_file(config, "ADD", "app:formshare", "mosquitto.host", "localhost")
    modify_ini_file(config, "ADD", "app:formshare", "mosquitto.port", "1883")
    modify_ini_file(config, "ADD", "app:formshare", "mosquitto.user", "formshare")
    if not os.path.exists("/etc/mosquitto/users.mqt"):
        modify_ini_file(
            config, "ADD", "app:formshare", "mosquitto.password", mosquitto_password
        )
    else:
        modify_ini_file(
            config, "ADD", "app:formshare", "mosquitto.password", "72EkBqCs!"
        )
    with open(config_uri, "w") as configfile:
        config.write(configfile)

    if not os.path.exists("/etc/mosquitto/users.mqt"):
        try:
            with open("/etc/mosquitto/users.mqt", "w") as f:
                f.write("formshare:{}\n".format(mosquitto_password))
                f.write("formshare_client:read_only")
            os.system("mosquitto_passwd -U /etc/mosquitto/users.mqt")
            os.system("/etc/init.d/mosquitto restart")
        except Exception as e:
            print("********************************************")
            print(
                "Unable to configure the local mosquitto server. "
                "The migration passed but MQT might not be configured properly"
            )
            print(
                "You may need to add the following using manually to /etc/mosquitto/users.mqt"
            )
            print("formshare:{}\n".format(mosquitto_password))
            print("formshare_client:read_only")
            print("And restart mosquitto")
            print("--------------------------------------------")
            print("Error: {}".format(str(e)))
            print("********************************************")


def downgrade():
    config_uri = context.config.get_main_option("formshare.ini.file", None)
    config = configparser.ConfigParser()
    config.read(config_uri)
    modify_ini_file(config, "REMOVE", "app:formshare", "mosquitto.host")
    modify_ini_file(config, "REMOVE", "app:formshare", "mosquitto.port")
    modify_ini_file(config, "REMOVE", "app:formshare", "mosquitto.user")
    modify_ini_file(config, "REMOVE", "app:formshare", "mosquitto.password")
    try:
        os.remove("/etc/mosquitto/users.mqt")
    except Exception as e:
        print("Unable to remove mosquito users file. Error: {}".format(str(e)))

    with open(config_uri, "w") as configfile:
        config.write(configfile)
