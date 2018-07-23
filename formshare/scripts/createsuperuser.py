import os
import sys, getpass, datetime
import transaction
from validate_email import validate_email

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )

from pyramid.scripts.common import parse_vars

from formshare.models.meta import Base
from formshare.models import (
    get_engine,
    get_session_factory,
    get_tm_session,
    )
from formshare.models import Org,User,Userorg
from formshare.config.encdecdata import encodeDataWithAESKey


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri> org_id=value org_name=value\n'
          "(example: %s development.ini org_id=myorganization user_email=me@mydomain.com)" % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) != 4:
        usage(argv)
    config_uri = argv[1]
    options = parse_vars(argv[2:])
    if 'org_id' not in options.keys():
        usage(argv)
    if 'user_email' not in options.keys():
        usage(argv)

    pass1 = getpass.getpass("User password:")
    pass2 = getpass.getpass("Confirm the password:")
    if pass1 == '':
        print("The password cannot be empty")
        sys.exit(1)
    if pass1 != pass2:
        print("The password and its confirmation are not the same")
        sys.exit(1)

    emailValid = validate_email(options["user_email"])
    if not emailValid:
        print("Invalid email")
        sys.exit(1)

    setup_logging(config_uri)
    settings = get_appsettings(config_uri)

    encPass = encodeDataWithAESKey(pass1,settings['aes.key'])

    engine = get_engine(settings)
    Base.metadata.create_all(engine)

    session_factory = get_session_factory(engine)

    with transaction.manager:
        dbsession = get_tm_session(session_factory, transaction.manager)
        try:
            org_id = options["org_id"].lower()
            org_id = org_id.replace(' ','')
            if dbsession.query(Org).filter(Org.org_id == org_id).first() is not None:
                if dbsession.query(User).filter(User.user_email == options["user_email"]).first() is None:
                    if dbsession.query(Userorg).filter(Userorg.org_id == org_id).filter(Userorg.user_email == options["user_email"]).first() is None:
                        newUser = User(user_email=options["user_email"], user_password=encPass, user_active=1, user_cdate=datetime.datetime.now())
                        dbsession.add(newUser)
                        newUserinOrg = Userorg(org_id=org_id,user_email=options["user_email"],user_admin=1,user_joined=datetime.datetime.now())
                        dbsession.add(newUserinOrg)
                        print("The super user has been added with the following information:")
                        print("Organization: %s" % (org_id))
                        print("Email: %s" % (options["user_email"]))
                    else:
                        print('An user with email "%s" already exists in "%s" organization' % (options["user_email"],org_id))
                        sys.exit(1)
                else:
                    print('An user with email "%s" already exists' % (options["user_email"]))
                    sys.exit(1)
            else:
                print('The organization ID %s does not exist' % (org_id))
                sys.exit(1)
        except Exception as e:
            print(str(e))
            sys.exit(1)

