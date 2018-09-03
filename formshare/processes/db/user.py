from ...models import mapToSchema,User
import sys
from sqlalchemy.exc import IntegrityError
import logging
from validate_email import validate_email

__all__ = [
    'register_user','user_exists'
]

log = logging.getLogger(__name__)

def register_user(request,userData):
    userData.pop('user_password2', None)
    mappedData = mapToSchema(User,userData)
    emailValid = validate_email(mappedData["user_email"])
    if emailValid:
        res = request.dbsession.query(User).filter(User.user_email == mappedData["user_email"]).first()
        if res is None:
            newUser = User(**mappedData)
            try:
                request.dbsession.add(newUser)
                request.dbsession.flush()
                return True,""
            except IntegrityError as e:
                log.error("Duplicated user {}".format(mappedData["user_id"]))
                return False,request.translate("Username is already taken")
            except:
                log.error("Error {} when inserting user user {}".format(sys.exc_info()[0],mappedData["user_id"]))
                return False,sys.exc_info()[0]
        else:
            log.error("Duplicated user with email {}".format(mappedData["user_email"]))
            return False, request.translate("Email already taken")
    else:
        log.error("Email {} is not valid".format(mappedData["user_email"]))
        return False, request.translate("Email is invalid")

def user_exists(request,userID):
    res = request.dbsession.query(User).filter(User.user_id == userID).filter(User.user_active == 1).first()
    if res is None:
        return False
    return True


