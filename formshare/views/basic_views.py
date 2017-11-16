from pyramid.security import remember
from pyramid.httpexceptions import HTTPFound
from ..config.auth import getUserData
from classes import publicView
from pyramid.security import authenticated_userid
from pyramid.security import forget

class home_view(publicView):
    def processView(self):
        return {'project': self._('Formshare')}

class notfound_view(publicView):
    def processView(self):
        self.request.response.status = 404
        return {}

class login_view(publicView):
    def processView(self):

        # If we logged in then go to dashboard
        login = authenticated_userid(self.request)
        currentUser = getUserData(login, self.request)
        if currentUser is not None:
            return HTTPFound(location=self.request.route_url('dashboard'))

        next = self.request.params.get('next') or self.request.route_url('dashboard')
        login = ''
        did_fail = False
        if 'submit' in self.request.POST:
            login = self.request.POST.get('login', '')
            passwd = self.request.POST.get('passwd', '')
            user = getUserData(login,self.request)
            if not user == None and user.check_password(passwd,self.request):
                headers = remember(self.request, login)
                response = HTTPFound(location=next, headers=headers)
                return response
            did_fail = True

        return {'login': login, 'failed_attempt': did_fail, 'next': next}

def logout_view(request):
    headers = forget(request)
    loc = request.route_url('home')
    return HTTPFound(location=loc, headers=headers)

