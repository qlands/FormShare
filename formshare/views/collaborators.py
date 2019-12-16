from formshare.views.classes import PrivateView
from formshare.processes.db import (
    get_project_collaborators,
    get_project_id_from_name,
    remove_collaborator_from_project,
    add_collaborator_to_project,
    set_collaborator_role,
    get_project_details,
    is_collaborator,
    get_user_name,
    accept_collaboration,
    decline_collaboration,
    get_user_details,
)
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from formshare.processes.email.send_email import send_collaboration_email


class CollaboratorsListView(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if not self.activeProject:
            self.returnRawViewResult = True
            return HTTPFound(self.request.route_url("dashboard", userid=self.user.id))
        if self.activeProject["project_id"] == project_id:
            self.set_active_menu("collaborators")
        else:
            self.set_active_menu("projects")
        project_details = {}
        if project_id is not None:
            project_found = False
            for project in self.user_projects:
                if project["project_id"] == project_id:
                    project_found = True
                    project_details = project
            if not project_found:
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        if project_details["access_type"] > 2:
            raise HTTPNotFound

        if self.request.method == "POST":
            collaborator_details = self.get_post_dict()
            if "add_collaborator" in collaborator_details.keys():
                if "collaborator" in collaborator_details.keys():
                    added, message = add_collaborator_to_project(
                        self.request, project_id, collaborator_details["collaborator"]
                    )
                    if added:
                        auto_accept_collaboration = self.request.registry.settings.get(
                            "auth.auto_accept_collaboration", "false"
                        )
                        if auto_accept_collaboration == "true":
                            self.request.session.flash(
                                self._("The collaborator was added to this project")
                            )
                        else:
                            user_details = get_user_details(
                                self.request, collaborator_details["collaborator"]
                            )
                            project_details = get_project_details(
                                self.request, project_id
                            )
                            send_collaboration_email(
                                self.request,
                                user_details["user_email"],
                                self.user.email,
                                self.user.name,
                                project_details["project_name"],
                                user_id,
                                project_code,
                            )
                            self.request.session.flash(
                                self._(
                                    "The collaborator was added to this project. "
                                    "However, an email has been sent to him/her to accept "
                                    "the collaboration"
                                )
                            )
                        self.returnRawViewResult = True
                        return HTTPFound(
                            self.request.route_url(
                                "collaborators", userid=user_id, projcode=project_code
                            )
                        )
                    else:
                        self.append_to_errors(message)
                else:
                    self.append_to_errors(self._("You need to specify a collaborator"))
            if "change_role" in collaborator_details.keys():
                changed, message = set_collaborator_role(
                    self.request,
                    project_id,
                    collaborator_details["collaborator_id"],
                    collaborator_details["role_collaborator"],
                )
                if changed:
                    self.request.session.flash(self._("The role was changed"))
                    self.returnRawViewResult = True
                    return HTTPFound(
                        self.request.route_url(
                            "collaborators", userid=user_id, projcode=project_code
                        )
                    )
                else:
                    self.append_to_errors(message)

        collaborators, more = get_project_collaborators(self.request, project_id)
        return {
            "collaborators": collaborators,
            "projectDetails": project_details,
            "userid": user_id,
        }


class RemoveCollaborator(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        project_details = {}
        if project_id is not None:
            project_found = False
            for project in self.user_projects:
                if project["project_id"] == project_id:
                    project_found = True
                    project_details = project
            if not project_found:
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        if project_details["access_type"] > 2:
            raise HTTPNotFound
        if self.request.method == "POST":
            self.returnRawViewResult = True
            collaborator_id = self.request.matchdict["collid"]
            removed, message = remove_collaborator_from_project(
                self.request, project_id, collaborator_id
            )
            next_page = self.request.route_url(
                "collaborators", userid=user_id, projcode=project_code
            )
            if removed:
                self.request.session.flash(
                    self._("The collaborator was removed successfully")
                )
                return HTTPFound(next_page)
            else:
                self.request.session.flash(
                    self._("Unable to remove the collaborator: ") + message
                )
                return HTTPFound(next_page, headers={"FS_error": "true"})

        else:
            raise HTTPNotFound


class AcceptCollaboration(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        project_details = get_project_details(self.request, project_id)
        if not is_collaborator(self.request, self.user.login, project_id, 0):
            raise HTTPNotFound
        if user_id == self.user.id:
            raise HTTPNotFound
        owner = get_user_name(self.request, user_id)
        if self.request.method == "POST":
            accept_details = self.get_post_dict()
            if "accept" in accept_details.keys():
                accepted, message = accept_collaboration(
                    self.request, self.user.login, project_id
                )
                if accepted:
                    self.request.session.flash(self._("You accepted the collaboration"))
                else:
                    self.request.session.flash(
                        self._("Unable to accept the collaboration: ") + message
                    )
            if "decline" in accept_details.keys():
                declined, message = decline_collaboration(
                    self.request, self.user.login, project_id
                )
                if declined:
                    self.request.session.flash(self._("You declined the collaboration"))
                else:
                    self.request.session.flash(
                        self._("Unable to decline the collaboration: ") + message
                    )
            self.returnRawViewResult = True
            next_page = self.request.route_url("dashboard", userid=self.user.login)
            return HTTPFound(next_page)
        else:
            return {"projectDetails": project_details, "owner": owner}
