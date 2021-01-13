import configparser
import os
import argparse

import shutil


def get_ini_value(ini_file, key, default=None):
    try:
        config = configparser.ConfigParser()
        config.read(ini_file)
        return config.get("app:formshare", key)
    except Exception as e:
        print("Warning: Unable to find key {}. {} . Default used".format(key, str(e)))
        return default


def main(raw_args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("ini_path", help="Path to ini file")
    args = parser.parse_args(raw_args)

    if not os.path.exists(os.path.abspath(args.ini_path)):
        print("Ini file does not exists")
        return 1
    config = configparser.ConfigParser()
    config.read(args.ini_path)
    sqlalchemy_url = config.get("app:formshare", "sqlalchemy.url")
    if sqlalchemy_url.find("&ssl_disabled=True") == -1:
        shutil.copyfile(args.ini_path, args.ini_path + ".bk.20210113")
        sqlalchemy_url = sqlalchemy_url + "&ssl_disabled=True"
        config.set("app:formshare", "sqlalchemy.url", sqlalchemy_url)
        with open(args.ini_path, "w") as configfile:
            config.write(configfile)
