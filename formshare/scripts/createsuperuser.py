import argparse
import datetime
import secrets
import time
import uuid
import os
import logging

import requests
import validators
from formshare.app import load_settings_from_ini
from formshare.config.encdecdata import encode_data_with_key
from formshare.models import User
from formshare.models import get_engine, get_session_factory
from formshare.models.meta import Base
from formshare.processes.elasticsearch.user_index import configure_user_index_manager
from requests.auth import HTTPBasicAuth


def main(raw_args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("ini_path", help="Path to ini file")
    args2 = parser.parse_args(raw_args)

    config_uri = args2.ini_path

    random_login = str(uuid.uuid4())
    random_login = random_login[-12:]

    user_password = os.getenv("FORMSHARE_ADMIN_PASSWORD", "change_me_admin")
    user_email = os.getenv(
        "FORMSHARE_ADMIN_EMAIL", "{}@myserver.com".format(random_login)
    )
    user_id = os.getenv("FORMSHARE_ADMIN_USER", random_login)

    email_valid = validators.email(user_email)
    if not email_valid:
        print("Invalid email")
        return 1

    logging.basicConfig(level=logging.INFO)
    settings = load_settings_from_ini(config_uri)

    es_host = settings.get("elasticsearch.repository.host", "localhost")
    es_port = settings.get("elasticsearch.repository.port", 9200)

    es_user = settings.get("elasticsearch.user.name", "empty")
    es_password = settings.get("elasticsearch.user.password", "empty")
    es_scheme = settings.get("elasticsearch.user.scheme", "http")

    ready = False
    print("Waiting for ES to be ready")
    while not ready:
        resp = requests.get(
            "{}://{}:{}/_cluster/health".format(es_scheme, es_host, es_port),
            auth=HTTPBasicAuth(es_user, es_password),
        )
        data = resp.json()
        if data["status"] == "yellow" or data["status"] == "green":
            ready = True
        else:
            time.sleep(30)
    print("ES is ready")

    enc_pass = encode_data_with_key(user_password, settings["aes.key"].encode())

    engine = get_engine(settings)
    Base.metadata.create_all(engine)

    session_factory = get_session_factory(engine)
    dbsession = session_factory()
    error = 0
    try:
        with dbsession.begin():
            if dbsession.query(User).filter(User.user_id == user_id).first() is None:
                if (
                    dbsession.query(User).filter(User.user_email == user_email).first()
                    is None
                ):
                    api_key = str(uuid.uuid4())
                    api_secret = secrets.token_hex(16)
                    new_user = User(
                        user_id=user_id,
                        user_email=user_email,
                        user_password=enc_pass,
                        user_apikey=api_key,
                        user_apisecret=api_secret,
                        user_super=1,
                        user_active=1,
                        user_tenant="main",
                        user_cdate=datetime.datetime.now(),
                    )
                    dbsession.add(new_user)

                    user_details = {
                        "user_id": user_id,
                        "user_email": user_email,
                        "user_name": "FormShare Administrator",
                        "tenant_id": "main",
                    }

                    # Add the user to the user index
                    user_index = configure_user_index_manager(settings)
                    user_index.add_user(user_details["user_id"], user_details)

                    print(
                        "The super user has been added with the following information:"
                    )
                    print("ID: {}.".format(user_id))
                    print("Email: {}".format(user_email))
                else:
                    print("An user with email '{}' already exists".format(user_email))
                    error = 1
            else:
                print("An user with id '{}' already exists".format(user_id))
                error = 1
    except Exception as e:
        print(str(e))
        error = 1
    finally:
        dbsession.close()
    engine.dispose()
    return error
