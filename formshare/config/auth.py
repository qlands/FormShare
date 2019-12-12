from formshare.models import User as userModel
from formshare.models import Collaborator as collaboratorModel
from .encdecdata import decode_data
import urllib
import hashlib
from ..models import map_from_schema
import validators
from formshare.plugins.core import PluginImplementations
from formshare.plugins.interfaces import IAuthorize


class User(object):
    """
    This class represents a user in the system
    """

    def __init__(self, user_data):
        default = "identicon"
        size = 45
        self.id = user_data["user_id"]
        self.email = user_data["user_email"]
        gravatar_url = (
            "https://www.gravatar.com/avatar/"
            + hashlib.md5(self.email.lower().encode("utf8")).hexdigest()
            + "?"
        )
        gravatar_url += urllib.parse.urlencode({"d": default, "s": str(size)})
        self.userData = user_data
        self.login = user_data["user_id"]
        self.name = user_data["user_name"]
        self.super = user_data["user_super"]
        self.gravatarURL = gravatar_url
        if user_data["user_about"] is None:
            self.about = ""
        else:
            self.about = user_data["user_about"]
        self.apikey = user_data["user_apikey"]

    def check_password(self, password, request):
        # Load connected plugins and check if they modify the password authentication
        plugin_result = None
        for plugin in PluginImplementations(IAuthorize):
            plugin_result = plugin.on_authenticate_password(
                request, self.login, password
            )
            break  # Only one plugging will be called to extend authenticate_user
        if plugin_result is None:
            return check_login(self.login, password, request)
        else:
            return plugin_result

    def get_gravatar_url(self, size):
        default = "identicon"
        gravatar_url = (
            "https://www.gravatar.com/avatar/"
            + hashlib.md5(self.email.lower()).hexdigest()
            + "?"
        )
        gravatar_url += urllib.parse.urlencode({"d": default, "s": str(size)})
        return gravatar_url

    def update_gravatar_url(self):
        default = "identicon"
        size = 45
        gravatar_url = (
            "https://www.gravatar.com/avatar/"
            + hashlib.md5(self.email.lower()).hexdigest()
            + "?"
        )
        gravatar_url += urllib.parse.urlencode({"d": default, "s": str(size)})
        self.gravatarURL = gravatar_url


class Assistant(object):
    def __init__(self, assistant_data, project):
        default = "identicon"
        size = 45
        self.email = assistant_data["coll_email"]
        if self.email is not None:
            if validators.email(self.email):
                gravatar_url = (
                    "https://www.gravatar.com/avatar/"
                    + hashlib.md5(self.email.lower().encode("utf8")).hexdigest()
                    + "?"
                )
                gravatar_url += urllib.parse.urlencode({"d": default, "s": str(size)})
                self.gravatarURL = gravatar_url
            else:
                self.gravatarURL = ""
        else:
            self.gravatarURL = ""

        self.assistantData = assistant_data
        self.login = assistant_data["coll_id"]
        self.projectID = project
        self.fullName = assistant_data["coll_name"]
        self.APIKey = assistant_data["coll_apikey"]

    def check_password(self, password, request):
        return check_assistant_login(self.projectID, self.login, password, request)

    def get_gravatar_url(self, size):
        if self.email is not None:
            if validators.email(self.email):
                default = "identicon"
                gravatar_url = (
                    "https://www.gravatar.com/avatar/"
                    + hashlib.md5(self.email.lower()).hexdigest()
                    + "?"
                )
                gravatar_url += urllib.parse.urlencode({"d": default, "s": str(size)})
                return gravatar_url
            else:
                return ""
        else:
            return ""


def get_formshare_user_data(request, user, is_email):
    if is_email:
        return map_from_schema(
            request.dbsession.query(userModel)
            .filter(userModel.user_email == user)
            .filter(userModel.user_active == 1)
            .first()
        )
    else:
        return map_from_schema(
            request.dbsession.query(userModel)
            .filter(userModel.user_id == user)
            .filter(userModel.user_active == 1)
            .first()
        )


def get_user_data(user, request):
    email_valid = validators.email(user)
    # Load connected plugins and check if they modify the user authentication
    plugin_result = None
    plugin_result_dict = {}
    for plugin in PluginImplementations(IAuthorize):
        plugin_result, plugin_result_dict = plugin.on_authenticate_user(
            request, user, email_valid
        )
        break  # Only one plugging will be called to extend authenticate_user
    if plugin_result is not None:
        if plugin_result:
            # The plugin authenticated the user. Check now that such user exists in FormShare.
            internal_user = get_formshare_user_data(request, user, email_valid)
            if internal_user:
                return User(plugin_result_dict)
            else:
                return None
        else:
            return None
    else:
        result = get_formshare_user_data(request, user, email_valid)
        if result:
            result["user_password"] = ""  # Remove the password form the result
            return User(result)
        return None


def get_assistant_data(project, assistant, request):
    result = map_from_schema(
        request.dbsession.query(collaboratorModel)
        .filter(collaboratorModel.project_id == project)
        .filter(collaboratorModel.coll_id == assistant)
        .filter(collaboratorModel.coll_active == 1)
        .first()
    )
    if result:
        result["coll_password"] = ""  # Remove the password form the result
        return Assistant(result, project)
    return None


def check_login(user, password, request):
    result = (
        request.dbsession.query(userModel)
        .filter(userModel.user_id == user)
        .filter(userModel.user_active == 1)
        .first()
    )
    if result is None:
        return False
    else:
        cpass = decode_data(request, result.user_password.encode())
        if cpass == bytearray(password.encode()):
            return True
        else:
            return False


def check_assistant_login(project, assistant, password, request):
    result = (
        request.dbsession.query(collaboratorModel)
        .filter(collaboratorModel.project_id == project)
        .filter(collaboratorModel.coll_id == assistant)
        .filter(collaboratorModel.coll_active == 1)
        .first()
    )
    if result is None:
        return False
    else:
        cpass = decode_data(request, result.coll_password.encode())
        if cpass == bytearray(password.encode()):
            return True
        else:
            return False
