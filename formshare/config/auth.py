import datetime

import validators
from dateutil.relativedelta import relativedelta
from sqlalchemy import func

from formshare.config.encdecdata import decode_data
from formshare.models import Collaborator as collaboratorModel
from formshare.models import Partner as partnerModel
from formshare.models import User as userModel
from formshare.models import map_from_schema
from formshare.plugins.core import PluginImplementations
from formshare.plugins.interfaces import IUserAuthentication


class User(object):
    """
    This class represents a user in the system
    """

    def __init__(self, user_data):
        self.id = user_data["user_id"]
        self.email = user_data["user_email"]
        self.userData = user_data
        self.login = user_data["user_id"]
        self.name = user_data["user_name"]
        self.super = user_data["user_super"]
        self.APIKey = user_data["user_apikey"]
        self.gravatarURL = "#"
        if user_data["user_about"] is None:
            self.about = ""
        else:
            self.about = user_data["user_about"]
        self.apikey = user_data["user_apikey"]

    def check_password(self, password, request):
        self.set_gravatar_url(request, self.name, 45)
        # Load connected plugins and check if they modify the password authentication
        plugin_result = None
        plugin_message = ""
        for plugin in PluginImplementations(IUserAuthentication):
            plugin_result, plugin_message = plugin.on_authenticate_password(
                request, self.userData, password
            )
            break  # Only one plugging will be called to extend authenticate_user
        if plugin_result is None:
            if check_login(self.login, password, request):
                return True, ""
            else:
                _ = request.translate
                return (
                    False,
                    _("The user account does not exist or the password is invalid"),
                )
        else:
            return plugin_result, plugin_message

    def set_gravatar_url(self, request, name, size):
        self.gravatarURL = request.route_url(
            "gravatar", _query={"name": name, "size": size}
        )


class Assistant(object):
    def __init__(self, assistant_data, project):
        self.email = assistant_data["coll_email"]
        self.gravatarURL = "#"
        self.assistantData = assistant_data
        self.login = assistant_data["coll_id"]
        self.projectID = project
        self.fullName = assistant_data["coll_name"]
        self.APIKey = assistant_data["coll_apikey"]
        self.APISecret = assistant_data["coll_apisecret"]
        self.timezone = assistant_data["coll_timezone"]

    def check_password(self, password, request):
        self.set_gravatar_url(request, self.fullName, 45)
        return check_assistant_login(self.projectID, self.login, password, request)

    def set_gravatar_url(self, request, name, size):
        self.gravatarURL = request.route_url(
            "gravatar", _query={"name": name, "size": size}
        )


class Partner(object):
    def __init__(self, partner_data):
        self.email = partner_data["partner_email"]
        self.gravatarURL = "#"
        self.partnerData = partner_data
        self.id = partner_data["partner_id"]
        self.login = partner_data["partner_email"]
        self.fullName = partner_data["partner_name"]
        self.create_by = partner_data["created_by"]
        self.organization = partner_data["partner_organization"]
        self.timezone = partner_data["partner_timezone"]
        self.APIKey = partner_data["partner_apikey"]

    def check_password(self, password, request):
        self.set_gravatar_url(request, self.fullName, 45)
        return check_partner_login(request, self.email, password)

    def set_gravatar_url(self, request, name, size):
        self.gravatarURL = request.route_url(
            "gravatar", _query={"name": name, "size": size}
        )

    # def get_partner_id(self):
    #     return self.id


def reset_key_exists(request, reset_key):
    res = (
        request.dbsession.query(userModel)
        .filter(userModel.user_password_reset_key == reset_key)
        .first()
    )
    if res is not None:
        return True
    return False


def set_password_reset_token(request, user_id, reset_key, reset_token):
    token_expires_on = datetime.datetime.now() + relativedelta(hours=+24)
    request.dbsession.query(userModel).filter(userModel.user_id == user_id).update(
        {
            "user_password_reset_key": reset_key,
            "user_password_reset_token": reset_token,
            "user_password_reset_expires_on": token_expires_on,
        }
    )


def reset_password(request, user_id, reset_key, reset_token, new_password):
    request.dbsession.query(userModel).filter(userModel.user_id == user_id).filter(
        userModel.user_password_reset_key == reset_key
    ).filter(userModel.user_password_reset_token == reset_token).update(
        {
            "user_password_reset_key": None,
            "user_password_reset_token": None,
            "user_password_reset_expires_on": None,
            "user_password": new_password,
        }
    )


def get_formshare_user_data(request, user, is_email):
    if is_email:
        return map_from_schema(
            request.dbsession.query(userModel)
            .filter(func.lower(userModel.user_email) == func.lower(user))
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
    for plugin in PluginImplementations(IUserAuthentication):
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


def get_partner_data(request, partner_email):
    result = map_from_schema(
        request.dbsession.query(partnerModel)
        .filter(partnerModel.partner_email == partner_email)
        .first()
    )
    if result:
        result["partner_password"] = ""  # Remove the password form the result
        return Partner(result)
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


def check_partner_login(request, partner_email, password):
    result = (
        request.dbsession.query(partnerModel)
        .filter(partnerModel.partner_email == partner_email.lower())
        .first()
    )
    cpass = decode_data(request, result.partner_password.encode())
    if cpass == bytearray(password.encode()):
        return True
    else:
        return False
