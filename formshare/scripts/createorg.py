import os
import sys
import transaction

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )

from pyramid.scripts.common import parse_vars

from ..models.meta import Base
from ..models import (
    get_engine,
    get_session_factory,
    get_tm_session,
    )
from ..models import Org


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri> org_id=value org_name=value\n'
          "(example: %s development.ini org_id=myorganization org_name org_name='My first organization' )" % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) != 4:
        usage(argv)
    config_uri = argv[1]
    options = parse_vars(argv[2:])
    if 'org_id' not in options.keys():
        usage(argv)
    if 'org_name' not in options.keys():
        usage(argv)

    setup_logging(config_uri)
    settings = get_appsettings(config_uri)

    engine = get_engine(settings)
    Base.metadata.create_all(engine)

    session_factory = get_session_factory(engine)

    with transaction.manager:
        dbsession = get_tm_session(session_factory, transaction.manager)
        try:
            org_id = options["org_id"].lower()
            org_id = org_id.replace(' ','')
            if dbsession.query(Org).filter(Org.org_id == org_id).first() is None:
                newOrganization = Org(org_id=org_id, org_name=options["org_name"], org_active=1)
                dbsession.add(newOrganization)
                print("The organization has been added with the following information:")
                print("ID: %s" % (org_id))
                print("Name: %s" % (options["org_name"]))
            else:
                print('Organization ID "%s" already exists' % (org_id))
        except Exception as e:
            print(str(e))
            sys.exit(1)

