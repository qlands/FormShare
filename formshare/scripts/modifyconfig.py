import configparser
import argparse
import os


def modify_ini_file(config, action, section, key, value=None):
    if action == "ADD":
        config.set(section, key, value)
    if action == "REMOVE":
        config.remove_option(section, key)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ini_file", required=True, help="Path to FormShare INI file")
    parser.add_argument(
        "--action", required=True, help="Action to perform. ADD or REMOVE"
    )
    parser.add_argument(
        "--section", required=True, help="Section in the INI file to perform the action"
    )
    parser.add_argument("--key", required=True, help="Key to add or remove")
    parser.add_argument(
        "--value", required=False, help="If adding a key the value of such key"
    )

    args = parser.parse_args()
    if args.action == "ADD" or args.action == "REMOVE":
        if args.action == "ADD" and args.value is not None:
            if os.path.exists(args.ini_file):
                config = configparser.ConfigParser()
                config.read(args.ini_file)
                if args.section in config.sections():
                    modify_ini_file(
                        config, args.action, args.section, args.key, args.value
                    )
                    with open(args.ini_file, "w") as configfile:
                        config.write(configfile)
                else:
                    print("Section {} does not exists in INI file".format(args.section))
            else:
                print("INI file does not exists")
        else:
            print("You need to specify a value with an ADD action")
    else:
        print("Invalid action")
