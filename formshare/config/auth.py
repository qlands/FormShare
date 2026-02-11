import datetime
import formshare.plugins as p
import validators
from dateutil.relativedelta import relativedelta
from formshare.config.encdecdata import decode_data
from formshare.models import Collaborator as collaboratorModel
from formshare.models import Partner as partnerModel
from formshare.models import User as userModel, UserRoles
from formshare.models import map_from_schema
from formshare.plugins.core import PluginImplementations
from formshare.plugins.interfaces import IUserAuthentication, IUserPassword, IRoles
from sqlalchemy import func
import logging
from formshare.processes.logging.loggerclass import SecretLogger

logging.setLoggerClass(SecretLogger)
log = logging.getLogger("formshare")


class User(object):
    """
    This class represents a user in the system
    """

    def __init__(self, user_data, request):
        self.id = user_data["user_id"]
        self.email = user_data["user_email"]
        self.userData = user_data
        self.login = user_data["user_id"]
        self.name = user_data["user_name"]
        self.super = user_data["user_super"]
        self.roles = get_user_roles(request, user_data["user_id"])
        self.tenant = user_data["user_tenant"]
        self.workspace = user_data["user_is_workspace"]
        self.APIKey = user_data["user_apikey"]
        self.gravatarURL = "#"
        if user_data["user_about"] is None:
            self.about = ""
        else:
            self.about = user_data["user_about"]
        self.apikey = user_data["user_apikey"]
        self.metadata = {}
        for plugin in p.PluginImplementations(p.IUserObject):
            self.metadata = plugin.update_metadata(request, user_data, self.metadata)

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
        self.linked_user = assistant_data.get("linked_user", None)
        self.type = assistant_data["coll_type"]
        self.loginUUID = assistant_data["coll_uuid"]
        self.projectID = project
        self.fullName = assistant_data["coll_name"]
        self.APIKey = assistant_data["coll_apikey"]
        self.timezone = assistant_data["coll_timezone"]

    def check_password(self, password, request):
        self.set_gravatar_url(request, self.fullName, 45)
        return check_assistant_login(
            request,
            self.loginUUID,
            password,
        )

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


def get_user_roles(request, user_id):
    # These are the basic roles
    roles = ["can_projects", "can_forms"]
    # Call plugins so they can add new roles

    plugins_roles = []
    for plugin in PluginImplementations(IRoles):
        plugin_roles = plugin.get_roles(request.registry.settings)
        plugins_roles = plugins_roles + plugin_roles

    for a_role in plugins_roles:
        roles.append(a_role["role_id"])

    # Get the roles from the roles table
    res = (
        request.dbsession.query(UserRoles.role_id)
        .filter(UserRoles.user_id == user_id)
        .all()
    )

    final_roles = ["can_projects", "can_forms"]
    # Only add to the final list of roles those that have been defined through plugins
    for a_role in res:
        if a_role.role_id in roles:
            final_roles = final_roles + [a_role.role_id]
    return final_roles


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
    save_point = request.tm.savepoint()
    try:
        request.dbsession.query(userModel).filter(userModel.user_id == user_id).filter(
            userModel.user_password_reset_key.is_(None)
        ).update(
            {
                "user_password_reset_key": reset_key,
                "user_password_reset_token": reset_token,
                "user_password_reset_expires_on": token_expires_on,
            }
        )
        request.dbsession.flush()
    except Exception as e:
        log.error(
            "Unable to set password reset token for user {}. Error: {}".format(
                user_id, str(e)
            )
        )
        save_point.rollback()


def reset_password(request, user_id, reset_key, reset_token, new_password):
    save_point = request.tm.savepoint()
    try:
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
        request.dbsession.flush()
    except Exception as e:
        log.error(
            "Unable to reset password for user {}. Error: {}".format(user_id, str(e))
        )
        save_point.rollback()


def get_formshare_user_data(request, user, is_email):
    if is_email:
        return map_from_schema(
            request.dbsession.query(userModel)
            .filter(func.lower(userModel.user_email) == func.lower(user))
            .filter(userModel.user_active == 1)
            .filter(userModel.user_is_workspace == 0)
            .first()
        )
    else:
        return map_from_schema(
            request.dbsession.query(userModel)
            .filter(userModel.user_id == user)
            .filter(userModel.user_active == 1)
            .filter(userModel.user_is_workspace == 0)
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
                return User(plugin_result_dict, request)
            else:
                return None
        else:
            return None
    else:
        result = get_formshare_user_data(request, user, email_valid)
        if result:
            result["user_password"] = ""  # Remove the password form the result
            return User(result, request)
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


def get_global_assistant_data(request, assistant_uuid, user_id):
    user_data = map_from_schema(
        request.dbsession.query(userModel).filter(userModel.user_id == user_id).first()
    )

    result = map_from_schema(
        request.dbsession.query(collaboratorModel)
        .filter(collaboratorModel.coll_uuid == assistant_uuid)
        .filter(collaboratorModel.coll_active == 1)
        .first()
    )
    if result:
        result["coll_password"] = ""  # Remove the password form the result
        result["coll_id"] = "~global"
        result["project_id"] = "~global"
        result["coll_name"] = user_data["user_name"]
        result["coll_apikey"] = user_data["user_apikey"]
        result["coll_apisecret"] = user_data["user_apisecret"]
        result["coll_apitoken"] = user_data["user_apitoken"]
        result["coll_apitoken_expires_on"] = user_data["user_apitoken_expires_on"]
        return Assistant(result, "~global")
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
        .filter(userModel.user_is_workspace == 0)
        .first()
    )
    if result is None:
        return False
    else:
        for plugin in PluginImplementations(IUserPassword):  # pragma: no cover
            return plugin.validate_user_password(request, user, password)
        cpass = decode_data(request, result.user_password.encode())
        if cpass == bytearray(password.encode()):
            return True
        else:
            return False


def check_assistant_login(request, assistant_uuid, password):
    result = (
        request.dbsession.query(collaboratorModel)
        .filter(collaboratorModel.coll_uuid == assistant_uuid)
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
