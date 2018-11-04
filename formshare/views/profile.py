from formshare.views.classes import ProfileView
from pyramid.httpexceptions import HTTPNotFound, HTTPFound
from formshare.processes import update_profile


class MainProfileView(ProfileView):
    def __init__(self, request):
        ProfileView.__init__(self, request)
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict['userid']
        if user_id != self.user.login:
            raise HTTPNotFound()
        return {}


class EditProfileView(ProfileView):
    def __init__(self, request):
        ProfileView.__init__(self, request)
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict['userid']
        if user_id != self.user.login:
            raise HTTPNotFound()
        if self.request.method == 'POST':
            data = self.get_post_dict()
            if data["user_name"] != "":
                if self.request.registry.settings['auth.allow_edit_profile_name'] == 'false':
                    data["user_name"] = self.user.name
                res, message = update_profile(self.request, user_id, data)
                if res:
                    self.reload_user_details()
                    self.request.session.flash(self._('The profile has been updated'))
                    self.returnRawViewResult = True
                    return HTTPFound(location=self.request.url)
                else:
                    self.errors.append(message)
            else:
                self.errors.append(self._("The name cannot be empty"))
        return {}
