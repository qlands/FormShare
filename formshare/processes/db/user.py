from ...models import mapToSchema,User
import datetime,uuid
import sys
from sqlalchemy.exc import IntegrityError
import logging
from ...config.encdecdata import encodeData


__all__ = [
    'register_user'
]

log = logging.getLogger(__name__)

def register_user(request,userData):
    userData.pop('user_password2', None)
    mappedData = mapToSchema(User,userData)
    mappedData["user_cdate"] = datetime.datetime.now()
    mappedData["user_apikey"] = str(uuid.uuid4())
    mappedData["user_password"] = encodeData(request,mappedData["user_password"])
    newUser = User(**mappedData)
    try:
        request.dbsession.add(newUser)
        return True,""
    except IntegrityError as e:
        log.error("Duplicated user {}".format(mappedData["user_id"]))
        return False,request.translate("Duplicated user")
    except:
        log.error("Error {} when inserting user user {}".format(sys.exc_info()[0],mappedData["user_id"]))
        return False,sys.exc_info()[0]


