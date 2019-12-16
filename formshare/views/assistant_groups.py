from formshare.views.classes import PrivateView
from formshare.processes.db import (
    get_project_id_from_name,
    get_project_groups,
    add_group,
    get_group_data,
    modify_group,
    delete_group,
    get_members,
    add_assistant_to_group,
    remove_assistant_from_group,
)
from formshare.processes.db import get_all_assistants
from pyramid.httpexceptions import HTTPFound, HTTPNotFound


class GroupListView(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if self.activeProject["project_id"] == project_id:
            self.set_active_menu("groups")
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

        if project_details["access_type"] == 5:
            raise HTTPNotFound

        groups = get_project_groups(self.request, project_id)
        return {"groups": groups, "projectDetails": project_details, "userid": user_id}


class AddGroupView(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if self.activeProject["project_id"] == project_id:
            self.set_active_menu("groups")
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

        if project_details["access_type"] >= 4:
            raise HTTPNotFound

        if self.request.method == "POST":
            group_data = self.get_post_dict()
            if group_data["group_desc"] != "":
                next_page = self.request.params.get("next") or self.request.route_url(
                    "groups", userid=user_id, projcode=project_code
                )
                added, message = add_group(self.request, project_id, group_data)
                if added:
                    self.request.session.flash(
                        self._("The group was added to this project")
                    )
                    self.returnRawViewResult = True
                    return HTTPFound(next_page)
                else:
                    self.append_to_errors(message)
            else:
                self.append_to_errors(self._("You need to specify a name"))
        else:
            group_data = {}
        return {
            "groupData": group_data,
            "projectDetails": project_details,
            "userid": user_id,
        }


class EditGroupView(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        group_id = self.request.matchdict["groupid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if self.activeProject["project_id"] == project_id:
            self.set_active_menu("groups")
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

        if project_details["access_type"] >= 4:
            raise HTTPNotFound

        if self.request.method == "POST":
            group_data = self.get_post_dict()

            if "group_active" in group_data.keys():
                group_data["group_active"] = 1
            else:
                group_data["group_active"] = 0

            next_page = self.request.params.get("next") or self.request.route_url(
                "groups", userid=user_id, projcode=project_code
            )
            if group_data["group_desc"] != "":
                edited, message = modify_group(
                    self.request, project_id, group_id, group_data
                )
                if edited:
                    self.request.session.flash(
                        self._("The group was edited successfully")
                    )
                    self.returnRawViewResult = True
                    return HTTPFound(next_page)
                else:
                    self.append_to_errors(message)
            else:
                self.append_to_errors(self._("You need to specify a name"))
        else:
            group_data = get_group_data(self.request, project_id, group_id)
        return {
            "groupData": group_data,
            "projectDetails": project_details,
            "userid": user_id,
        }


class DeleteGroup(PrivateView):
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

        if project_details["access_type"] >= 4:
            raise HTTPNotFound

        if self.request.method == "POST":
            self.returnRawViewResult = True
            group_id = self.request.matchdict["groupid"]
            removed, message = delete_group(self.request, project_id, group_id)
            next_page = self.request.params.get("next") or self.request.route_url(
                "groups", userid=user_id, projcode=project_code
            )
            if removed:
                self.request.session.flash(self._("The group was deleted successfully"))
                return HTTPFound(next_page)
            else:
                self.request.session.flash(
                    self._("Unable to delete the group: ") + message
                )
                return HTTPFound(next_page, headers={'FS_error': "true"})

        else:
            raise HTTPNotFound


class GroupMembersView(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        group_id = self.request.matchdict["groupid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if self.activeProject["project_id"] == project_id:
            self.set_active_menu("groups")
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

        if project_details["access_type"] == 5:
            raise HTTPNotFound

        members = get_members(self.request, project_id, group_id)
        assistants = get_all_assistants(self.request, project_id, self.user.login)
        group_data = get_group_data(self.request, project_id, group_id)

        if self.request.method == "POST":
            group_data = self.get_post_dict()

            next_page = self.request.params.get("next") or self.request.route_url(
                "group_members", userid=user_id, projcode=project_code, groupid=group_id
            )

            if "add_assistant" in group_data.keys():
                self.returnRawViewResult = True
                if "coll_id" in group_data.keys():
                    if group_data["coll_id"] != "":
                        parts = group_data["coll_id"].split("|")
                        edited, message = add_assistant_to_group(
                            self.request, project_id, group_id, parts[0], parts[1]
                        )
                        if edited:
                            self.request.session.flash(
                                self._("The assistant was added successfully")
                            )
                            self.returnRawViewResult = True
                            return HTTPFound(next_page)
                        else:
                            self.add_error(message)
                            return HTTPFound(next_page, headers={'FS_error': "true"})
                    else:
                        self.add_error(self._("You need to specify an assistant"))
                        return HTTPFound(next_page, headers={'FS_error': "true"})
                else:
                    self.add_error(self._("You need to specify an assistant"))
                    return HTTPFound(next_page, headers={'FS_error': "true"})
        return {
            "groupData": group_data,
            "members": members,
            "assistants": assistants,
            "projectDetails": project_details,
            "userid": user_id,
        }


class RemoveMember(PrivateView):
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

        if project_details["access_type"] >= 4:
            raise HTTPNotFound

        if self.request.method == "POST":
            self.returnRawViewResult = True
            group_id = self.request.matchdict["groupid"]
            member_id = self.request.matchdict["memberid"]
            project_id2 = self.request.matchdict["projectid"]
            removed, message = remove_assistant_from_group(
                self.request, project_id, group_id, project_id2, member_id
            )
            next_page = self.request.params.get("next") or self.request.route_url(
                "group_members", userid=user_id, projcode=project_code, groupid=group_id
            )
            if removed:
                self.request.session.flash(self._("The group was deleted successfully"))
                return HTTPFound(next_page)
            else:
                self.request.session.flash(
                    self._("Unable to delete the group: ") + message
                )
                return HTTPFound(next_page, headers={'FS_error': "true"})

        else:
            raise HTTPNotFound
