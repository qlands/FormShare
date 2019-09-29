import sys
import getpass
import datetime
import uuid
import transaction
import validators
import argparse

from pyramid.paster import get_appsettings, setup_logging
from formshare.models.meta import Base
from formshare.models import get_engine, get_session_factory, get_tm_session
from formshare.models import User
from formshare.config.encdecdata import encode_data_with_aes_key


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ini_path", help="Path to ini file")
    parser.add_argument("--user_id", required=True, help="Superuser ID")
    parser.add_argument("--user_email", required=True, help="Superuser Email")
    parser.add_argument(
        "--user_password", default="", help="Superuser password. Prompt if it is empty"
    )
    parser.add_argument(
        "-n", "--not_fail", action="store_false", help="Not fail if Superuser exists"
    )
    args = parser.parse_args()

    config_uri = args.ini_path

    if args.user_password == "":
        pass1 = getpass.getpass("User password:")
        pass2 = getpass.getpass("Confirm the password:")
        if pass1 == "":
            print("The password cannot be empty")
            sys.exit(1)
        if pass1 != pass2:
            print("The password and its confirmation are not the same")
            sys.exit(1)
    else:
        pass1 = args.user_password

    email_valid = validators.email(args.user_email)
    if not email_valid:
        print("Invalid email")
        sys.exit(1)

    setup_logging(config_uri)
    settings = get_appsettings(config_uri, "formshare")

    enc_pass = encode_data_with_aes_key(pass1, settings["aes.key"])

    engine = get_engine(settings)
    Base.metadata.create_all(engine)

    session_factory = get_session_factory(engine)

    with transaction.manager:
        dbsession = get_tm_session(session_factory, transaction.manager)
        try:
            if (
                dbsession.query(User).filter(User.user_id == args.user_id).first()
                is None
            ):
                if (
                    dbsession.query(User)
                    .filter(User.user_email == args.user_email)
                    .first()
                    is None
                ):
                    api_pey = str(uuid.uuid4())
                    new_user = User(
                        user_id=args.user_id,
                        user_email=args.user_email,
                        user_password=enc_pass,
                        user_apikey=api_pey,
                        user_super=1,
                        user_active=1,
                        user_cdate=datetime.datetime.now(),
                    )
                    dbsession.add(new_user)
                    print(
                        "The super user has been added with the following information:"
                    )
                    print("ID: {}.".format(args.user_id))
                    print("Email: {}".format(args.user_email))
                else:
                    if args.not_fail:
                        print(
                            "An user with email '{}' already exists".format(
                                args.user_email
                            )
                        )
                        sys.exit(1)
            else:
                if args.not_fail:
                    print("An user with id '{}' already exists".format(args.user_id))
                    sys.exit(1)
        except Exception as e:
            print(str(e))
            sys.exit(1)
