from pyramid.security import remember
from pyramid.httpexceptions import HTTPFound
from ..config.auth import getUserData
from .classes import publicView
from pyramid.security import authenticated_userid
from pyramid.security import forget
from pyramid.session import check_csrf_token
from pyramid.httpexceptions import HTTPNotFound
from formencode.variabledecode import variable_decode
import formshare.plugins as p

class home_view(publicView):
    def processView(self):
        return {}

class notfound_view(publicView):
    def processView(self):
        self.request.response.status = 404
        return {}

class login_view(publicView):
    def processView(self):
        #If we logged in then go to dashboard
        next = self.request.params.get('next') or self.request.route_url('dashboard')
        if self.request.method == 'GET':
            login = authenticated_userid(self.request)
            currentUser = getUserData(login, self.request)
            if currentUser is not None:
                return HTTPFound(location=self.request.route_url('dashboard'))
        else:
            safe = check_csrf_token(self.request,raises=False)
            if not safe:
                return HTTPNotFound()
            data = variable_decode(self.request.POST)
            login = data['login']
            passwd = data['passwd']
            user = getUserData(login,self.request)
            loginData = {}
            loginData["login"] = login
            loginData["from"] = "mainApp"
            if user is not None:
                if user.check_password(passwd,self.request):
                    continue_login = True
                    error_message = ""
                    # Load connected plugins and check if they modify the login authorization
                    for plugin in p.PluginImplementations(p.IAuthorize):
                        continue_with_login,error_message = plugin.after_login(self.request,user)
                        if not continue_with_login:
                            self.errors.append(error_message)
                            continue_login = False
                    if continue_login:
                        headers = remember(self.request, loginData)
                        response = HTTPFound(location=next, headers=headers)
                        return response
                else:
                    self.errors.append(self._("Invalid credentials"))
            else:
                self.errors.append(self._("The user account does not exists"))
        return {'next': next}

def logout_view(request):
    headers = forget(request)
    loc = request.route_url('home')
    return HTTPFound(location=loc, headers=headers)

class register_view(publicView):
    def processView(self):
        #If we logged in then go to dashboard
        if self.request.method == 'GET':
            data = {}
        else:
            safe = check_csrf_token(self.request,raises=False)
            if not safe:
                return HTTPNotFound()
            data = variable_decode(self.request.POST)

        return {'next': next, 'data':data}
