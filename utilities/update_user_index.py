import argparse
from pyramid.paster import get_appsettings, setup_logging
from formshare.models import get_engine, get_session_factory, get_tm_session
from formshare.models.meta import Base
import transaction
from formshare.models import User
import sys
from formshare.processes.elasticsearch.user_index import (
    configure_user_index_manager,
    UserExistError,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ini_path", help="Path to ini file")
    args = parser.parse_args()
    config_uri = args.ini_path
    setup_logging(config_uri)
    settings = get_appsettings(config_uri, "formshare")

    engine = get_engine(settings)
    Base.metadata.create_all(engine)

    session_factory = get_session_factory(engine)

    with transaction.manager:
        dbsession = get_tm_session(session_factory, transaction.manager)
        try:
            users = dbsession.query(User).all()
            user_index = configure_user_index_manager(settings)
            for a_user in users:
                try:
                    # print("****************************99")
                    # print(a_user.user_id)
                    # print(a_user.user_email)
                    # print(a_user.user_name)
                    # print("****************************99")
                    user_index.add_user(
                        a_user.user_id,
                        {
                            "user_id": a_user.user_id,
                            "user_email": a_user.user_email,
                            "user_name": a_user.user_name,
                        },
                    )
                    print("User {} added to the index".format(a_user.user_id))
                except UserExistError:
                    print("User ID {} already in index".format(a_user.user_id))
        except Exception as e:
            print(str(e))
            sys.exit(1)


if __name__ == "__main__":
    main()
