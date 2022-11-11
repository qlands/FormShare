import argparse
import datetime
import getpass
import secrets
import time
import uuid

import requests
import transaction
import validators
from elasticfeeds.activity import Actor, Object, Activity
from formshare.config.elasticfeeds import configure_manager
from formshare.config.encdecdata import encode_data_with_key
from formshare.models import User
from formshare.models import get_engine, get_session_factory, get_tm_session
from formshare.models.meta import Base
from formshare.processes.elasticsearch.user_index import configure_user_index_manager
from pyramid.paster import get_appsettings, setup_logging


def main(raw_args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("ini_path", help="Path to ini file")
    parser.add_argument("--user_id", required=True, help="Superuser ID")
    parser.add_argument("--user_email", required=True, help="Superuser Email")
    parser.add_argument(
        "--user_password", default="", help="Superuser password. Prompt if it is empty"
    )
    args = parser.parse_args(raw_args)

    config_uri = args.ini_path

    if args.user_password == "":
        pass1 = getpass.getpass("User password:")
        pass2 = getpass.getpass("Confirm the password:")
        if pass1 == "":
            print("The password cannot be empty")
            return 1
        if pass1 != pass2:
            print("The password and its confirmation are not the same")
            return 1
    else:
        pass1 = args.user_password

    email_valid = validators.email(args.user_email)
    if not email_valid:
        print("Invalid email")
        return 1

    setup_logging(config_uri)
    settings = get_appsettings(config_uri, "formshare")

    es_host = settings.get("elasticsearch.repository.host", "localhost")
    es_port = settings.get("elasticsearch.repository.port", 9200)
    use_ssl = settings.get("elasticsearch.repository.use_ssl", "False")
    ready = False
    print("Waiting for ES to be ready")
    while not ready:
        if use_ssl == "False":
            resp = requests.get("http://{}:{}/_cluster/health".format(es_host, es_port))
        else:
            resp = requests.get(
                "https://{}:{}/_cluster/health".format(es_host, es_port)
            )
        data = resp.json()
        if data["status"] == "yellow" or data["status"] == "green":
            ready = True
        else:
            time.sleep(30)
    print("ES is ready")

    enc_pass = encode_data_with_key(pass1, settings["aes.key"].encode())

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
                    api_key = str(uuid.uuid4())
                    api_secret = secrets.token_hex(16)
                    new_user = User(
                        user_id=args.user_id,
                        user_email=args.user_email,
                        user_password=enc_pass,
                        user_apikey=api_key,
                        user_apisecret=api_secret,
                        user_super=1,
                        user_active=1,
                        user_cdate=datetime.datetime.now(),
                    )
                    dbsession.add(new_user)

                    feed_manager = configure_manager(settings)
                    # The user follows himself
                    try:
                        feed_manager.follow(args.user_id, args.user_id)
                    except Exception as e:
                        print(
                            "User {} was in FormShare at some point. Error: {}".format(
                                args.user_id, str(e)
                            )
                        )

                    user_details = {
                        "user_id": args.user_id,
                        "user_email": args.user_email,
                        "user_name": "FormShare Administrator",
                    }
                    # The user join FormShare
                    actor = Actor(user_details["user_id"], "person")
                    feed_object = Object("formshare", "platform")
                    activity = Activity("join", actor, feed_object)
                    feed_manager.add_activity_feed(activity)

                    # Add the user to the user index
                    user_index = configure_user_index_manager(settings)
                    user_index.add_user(user_details["user_id"], user_details)

                    print(
                        "The super user has been added with the following information:"
                    )
                    print("ID: {}.".format(args.user_id))
                    print("Email: {}".format(args.user_email))
                    error = 0
                else:
                    print(
                        "An user with email '{}' already exists".format(args.user_email)
                    )
                    error = 1
            else:
                print("An user with id '{}' already exists".format(args.user_id))
                error = 1
        except Exception as e:
            print(str(e))
            error = 1
    engine.dispose()
    return error
