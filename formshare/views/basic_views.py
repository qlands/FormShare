from pyramid.security import remember
from pyramid.httpexceptions import HTTPFound
from ..config.auth import get_user_data, get_collaborator_data
from .classes import PublicView
from pyramid.security import authenticated_userid
from pyramid.security import forget
from pyramid.session import check_csrf_token
from pyramid.httpexceptions import HTTPNotFound
from formencode.variabledecode import variable_decode
import formshare.plugins as p
from ..processes import register_user, get_project_id_from_name
from ast import literal_eval
import datetime
import uuid
from formshare.config.encdecdata import encode_data


class HomeView(PublicView):
    def process_view(self):
        return {'activeUser': None}


class NotFoundView(PublicView):
    def process_view(self):
        self.request.response.status = 404
        return {}


class LoginView(PublicView):
    def process_view(self):
        # If we logged in then go to dashboard
        next_page = self.request.params.get('next')
        if self.request.method == 'GET':
            login_data = authenticated_userid(self.request)
            if login_data is not None:
                login_data = literal_eval(login_data)
                if login_data["group"] == "mainApp":
                    current_user = get_user_data(login_data["login"], self.request)
                    if current_user is not None:
                        return HTTPFound(location=self.request.route_url('dashboard', userid=current_user.login))
        else:
            safe = check_csrf_token(self.request, raises=False)
            if not safe:
                raise HTTPNotFound()
            data = variable_decode(self.request.POST)
            login = data['email']
            passwd = data['passwd']
            user = get_user_data(login, self.request)
            login_data = {"login": login, "group": "mainApp"}
            if user is not None:
                if user.check_password(passwd, self.request):
                    continue_login = True
                    # Load connected plugins and check if they modify the login authorization
                    for plugin in p.PluginImplementations(p.IAuthorize):
                        continue_with_login, error_message = plugin.after_login(self.request, user)
                        if not continue_with_login:
                            self.errors.append(error_message)
                            continue_login = False
                        break  # Only one plugging will be called to extend after_login
                    if continue_login:
                        headers = remember(self.request, login_data)
                        next_page = self.request.params.get('next') or self.request.route_url('dashboard',
                                                                                              userid=user.login)
                        return HTTPFound(location=next_page, headers=headers)
                else:
                    self.errors.append(self._("The user account does not exists or the password is invalid"))
            else:
                self.errors.append(self._("The user account does not exists or the password is invalid"))
        return {'next': next_page}


class CollaboratorsLoginView(PublicView):
    def process_view(self):
        # If we logged in then go to dashboard
        project_name = self.request.matchdict['pname']
        user_id = self.request.matchdict['userid']
        project_id = get_project_id_from_name(self.request, user_id, project_name)
        if project_id is None:
            raise HTTPNotFound()
        next_page = self.request.params.get('next') or self.request.route_url('dashboard')
        if self.request.method == 'GET':
            login_data = authenticated_userid(self.request)
            if login_data is not None:
                login_data = literal_eval(login_data)
                if login_data["group"] == "collaborator":
                    current_collaborator = get_collaborator_data(project_id, login_data["login"], self.request)
                    if current_collaborator is not None:
                        return HTTPFound(location=self.request.route_url('dashboard'))
        else:
            safe = check_csrf_token(self.request, raises=False)
            if not safe:
                raise HTTPNotFound()
            data = variable_decode(self.request.POST)
            login = data['login']
            passwd = data['passwd']
            collaborator = get_collaborator_data(project_id, login, self.request)
            login_data = {"login": login, "group": "collaborators"}
            if collaborator is not None:
                if collaborator.check_password(passwd, self.request):
                    continue_login = True
                    # Load connected plugins and check if they modify the login authorization
                    for plugin in p.PluginImplementations(p.IAuthorize):
                        continue_with_login, error_message = plugin.after_collaborator_login(self.request, collaborator)
                        if not continue_with_login:
                            self.errors.append(error_message)
                            continue_login = False
                        break  # Only one plugging will be called to extend after_collaborator_login
                    if continue_login:
                        headers = remember(self.request, login_data)
                        return HTTPFound(location=next_page, headers=headers)
                else:
                    self.errors.append(self._("Invalid credentials"))
            else:
                self.errors.append(self._("The user account does not exists"))
        return {'next': next_page}


def log_out_view(request):
    headers = forget(request)
    loc = request.route_url('home')
    raise HTTPFound(location=loc, headers=headers)


class RegisterView(PublicView):
    def process_view(self):
        if self.request.registry.settings['auth.register_users_via_web'] == 'false':
            raise HTTPNotFound()
        # If we logged in then go to dashboard
        if self.request.method == 'GET':
            data = {}
        else:
            safe = check_csrf_token(self.request, raises=False)
            if not safe:
                raise HTTPNotFound()
            data = variable_decode(self.request.POST)
            if data["user_password"] != "":
                if data["user_password"] == data["user_password2"]:
                    data["user_cdate"] = datetime.datetime.now()
                    data["user_apikey"] = str(uuid.uuid4())
                    data["user_apikey"] = str(uuid.uuid4())
                    data["user_password"] = encode_data(self.request, data["user_password"])
                    data["user_active"] = 1
                    # Load connected plugins and check if they modify the registration of an user
                    continue_registration = True
                    for plugin in p.PluginImplementations(p.IAuthorize):
                        data, continue_with_registration, error_message = plugin.before_register(self.request, data)
                        if not continue_with_registration:
                            self.errors.append(error_message)
                            continue_registration = False
                        break  # Only one plugging will be called to extend before_register
                    if continue_registration:
                        added, error_message = register_user(self.request, data)
                        if not added:
                            self.errors.append(error_message)
                        else:
                            # Load connected plugins so they perform actions after the login is performed
                            next_page = self.request.route_url('dashboard', userid=data["user_id"])
                            plugin_next_page = ''
                            for plugin in p.PluginImplementations(p.IAuthorize):
                                plugin_next_page = plugin.after_register(self.request, data)
                                break  # Only one plugging will be called to extend after_register
                            if plugin_next_page is not None:
                                if plugin_next_page != '':
                                    if plugin_next_page != next_page:
                                        next_page = plugin_next_page
                            if next_page == self.request.route_url('dashboard', userid=data["user_id"]):
                                login_data = {"login": data["user_id"], "group": "mainApp"}
                                headers = remember(self.request, login_data)
                                return HTTPFound(location=self.request.route_url('dashboard', userid=data["user_id"]),
                                                 headers=headers)
                            else:
                                return HTTPFound(next_page)
                else:
                    self.errors.append(self._("The password and its confirmation are not the same"))
            else:
                self.errors.append(self._("The password cannot be empty"))
        return {'next': next, 'userdata': data}
