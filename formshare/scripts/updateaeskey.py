import argparse
import configparser
import logging
from formshare.processes.logging.loggerclass import SecretLogger
import os
import shutil
import uuid

import transaction
from formshare.config.encdecdata import encode_data_with_key, decode_data_with_key
from formshare.models import User, Collaborator, Partner
from formshare.models import get_engine, get_session_factory, get_tm_session
from formshare.models.meta import Base
from pyramid.paster import get_appsettings


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
        logging.error("Ini file does not exists")
        return 1

    if len(args.new_key) != 32:
        logging.error("The AES key must be 32 characters")
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
                        "Empty password for user {} with encrypted password '{}'".format(
                            a_user.user_id, a_user.user_password
                        )
                    )
                new_password = encode_data_with_key(
                    current_password, args.new_key.encode()
                )
                dbsession.query(User).filter(User.user_id == a_user.user_id).update(
                    {"user_password": new_password}
                )
            # Update Assistants password
            assistants = dbsession.query(Collaborator).all()
            for an_assistant in assistants:
                current_password = decode_data_with_key(
                    an_assistant.coll_password.encode(), settings["aes.key"].encode()
                )
                if current_password == "":
                    raise EmptyPassword(
                        "Empty password for assistant {} with encrypted password '{}'".format(
                            an_assistant.coll_id, an_assistant.coll_password
                        )
                    )
                new_password = encode_data_with_key(
                    current_password, args.new_key.encode()
                )
                dbsession.query(Collaborator).filter(
                    Collaborator.coll_id == an_assistant.coll_id
                ).filter(Collaborator.project_id == an_assistant.project_id).update(
                    {"coll_password": new_password}
                )

            # Update partners password
            partners = dbsession.query(Partner).all()
            for a_partner in partners:
                current_password = decode_data_with_key(
                    a_partner.partner_password.encode(), settings["aes.key"].encode()
                )
                if current_password == "":
                    raise EmptyPassword(
                        "Empty password for partner {} with encrypted password '{}'".format(
                            an_assistant.coll_id, a_partner.partner_password
                        )
                    )
                new_password = encode_data_with_key(
                    current_password, args.new_key.encode()
                )
                dbsession.query(Partner).filter(
                    Partner.partner_id == a_partner.partner_id
                ).update({"partner_password": new_password})
        except Exception as e:
            logging.error(str(e))
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
