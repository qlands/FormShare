from formshare.views.classes import profileView
from pyramid.httpexceptions import HTTPNotFound,HTTPFound
from formshare.processes import update_profile

class profile_view(profileView):
    def __init__(self, request):
        profileView.__init__(self, request)
        self.privateOnly = True
    def processView(self):
        userID = self.request.matchdict['userid']
        if userID != self.user.login:
            raise HTTPNotFound()
        return {}

class profile_edit_view(profileView):
    def __init__(self, request):
        profileView.__init__(self, request)
        self.privateOnly = True
    def processView(self):
        userID = self.request.matchdict['userid']
        if userID != self.user.login:
            raise HTTPNotFound()
        if self.request.method == 'POST':
            data = self.getPostDict()
            if data["user_name"] != "":
                if self.request.registry.settings['auth.allow_edit_profile_name'] == 'false':
                    data["user_name"] = self.user.name
                res,message = update_profile(self.request,userID,data)
                if res == True:
                    self.reloadUserDetails()
                    self.request.session.flash(self._('The profile has been updated'))
                    self.returnRawViewResult = True
                    return  HTTPFound(location=self.request.route_url('profile_edit',userid=userID))
                else:
                    self.errors.append(message)
            else:
                self.errors.append(self._("The name cannot be empty"))
        return {}