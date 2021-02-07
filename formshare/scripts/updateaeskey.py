import argparse
import transaction
from pyramid.paster import get_appsettings
import configparser
from formshare.config.encdecdata import encode_data_with_key, decode_data_with_key
from formshare.models import User, Collaborator
from formshare.models import get_engine, get_session_factory, get_tm_session
from formshare.models.meta import Base
import os
import shutil
import uuid


class EmptyPassword(Exception):
    """
        Exception raised when there is an empty password
    """


def main(raw_args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--new_key", required=True, help="New AES key")
    parser.add_argument("ini_path", help="Path to ini file")
    args = parser.parse_args(raw_args)

    if not os.path.exists(args.ini_path):
        print("Ini file does not exists")
        return 1

    if len(args.new_key) != 32:
        print("The AES key must be 32 characters")
        return 1

    formshare_ini_file_path = os.path.abspath(args.ini_path)

    settings = get_appsettings(formshare_ini_file_path, "formshare")

    config = configparser.ConfigParser()
    config.read(formshare_ini_file_path)

    engine = get_engine(settings)
    Base.metadata.create_all(engine)

    session_factory = get_session_factory(engine)
    error = 0
    with transaction.manager:
        dbsession = get_tm_session(session_factory, transaction.manager)
        try:
            # Update users password
            users = dbsession.query(User).all()
            for a_user in users:
                current_password = decode_data_with_key(
                    a_user.user_password.encode(), settings["aes.key"].encode()
                )
                if current_password == "":
                    raise EmptyPassword(
                        "Empty password for user {}".format(a_user.user_id)
                    )
                new_password = encode_data_with_key(
                    current_password, args.new_key.encode()
                )
                dbsession.query(User).filter(User.user_id == a_user.user_id).update(
                    {"user_password": new_password}
                )
            assistants = dbsession.query(Collaborator).all()
            # Update Assistants password
            for an_assistant in assistants:
                current_password = decode_data_with_key(
                    an_assistant.coll_password.encode(), settings["aes.key"].encode()
                )
                if current_password == "":
                    raise EmptyPassword(
                        "Empty password for assistant {}".format(an_assistant.coll_id)
                    )
                new_password = encode_data_with_key(
                    current_password, args.new_key.encode()
                )
                dbsession.query(Collaborator).filter(
                    Collaborator.coll_id == an_assistant.coll_id
                ).update({"coll_password": new_password})
        except Exception as e:
            print(str(e))
            error = 1
    engine.dispose()
    if error == 0:
        sequence = str(uuid.uuid4())
        sequence = sequence[-12:]
        shutil.copyfile(
            formshare_ini_file_path, formshare_ini_file_path + ".bk.{}".format(sequence)
        )
        config.set("app:formshare", "aes.key", args.new_key)
        with open(formshare_ini_file_path, "w") as configfile:
            config.write(configfile)

    return error
