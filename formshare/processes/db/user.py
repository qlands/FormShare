from ...models import mapToSchema,User
import datetime,uuid
import sys

__all__ = [
    'register_user'
]

def register_user(request,userData):
    mappedData = mapToSchema(User,userData)
    mappedData["user_cdate"] = datetime.datetime.now()
    mappedData["user_apikey"] = str(uuid.uuid4())
    newUser = User(**mappedData)
    try:
        request.dbsession.add(newUser)
        return True,""
    except:
        return False,sys.exc_info()[0]


