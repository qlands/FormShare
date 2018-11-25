from formshare.views.classes import ProjectsView
from formshare.processes.db import add_project, modify_project, delete_project, is_collaborator, \
    get_project_id_from_name, get_project_collaborators, get_project_assistants, get_project_groups, \
    add_file_to_project, get_project_files, remove_file_from_project, get_user_details
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from formshare.config.elasticfeeds import get_manager
from elasticfeeds.activity import Actor, Object, Activity
import validators
from formshare.processes.storage import store_file, get_stream, response_stream, delete_stream, delete_bucket
from pyramid.response import Response
import json
import qrcode
import zlib
import base64
import io


class ProjectStoredFileView(ProjectsView):
    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
        file_name = self.request.matchdict['filename']
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if project_id is not None:
            project_found = False
            for project in self.user_projects:
                if project["project_id"] == project_id:
                    project_found = True
            if project_found:
                stream = get_stream(self.request, project_id, file_name)
                if stream is not None:
                    self.returnRawViewResult = True
                    response = Response()
                    return response_stream(stream, file_name, response)
                else:
                    raise HTTPNotFound
            else:
                raise HTTPNotFound
        else:
            raise HTTPNotFound


class ProjectListView(ProjectsView):
    def process_view(self):
        # self.request.h.setActiveMenu("projects")
        return {}


class ProjectDetailsView(ProjectsView):
    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        project_data = {}
        if project_id is not None:
            project_found = False
            for project in self.user_projects:
                if project["project_id"] == project_id:
                    project_found = True
                    project_data = project
                    if self.user is not None:
                        project_data["user_collaborates"] = is_collaborator(self.request, self.user.login, project_id)
                    else:
                        project_data["user_collaborates"] = False
            if not project_found:
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        error = self.request.params.get('error')
        if error is not None:
            self.errors.append(error)

        assistants, more_assistants = get_project_assistants(self.request, project_id, 8)
        if self.user is not None:
            collaborators, more_collaborators = get_project_collaborators(self.request, project_id, self.user.login, 4)
        else:
            collaborators, more_collaborators = get_project_collaborators(self.request, project_id, None, 4)
        user_details = get_user_details(self.request, user_id)
        return {'projectData': project_data, 'userid': user_id, 'collaborators': collaborators,
                'moreCollaborators': more_collaborators, 'assistants': assistants, 'moreAssistants': more_assistants,
                'groups': get_project_groups(self.request, project_id),
                'files': get_project_files(self.request, project_id), 'userDetails': user_details}


class AddProjectView(ProjectsView):
    def __init__(self, request):
        ProjectsView.__init__(self, request)
        self.privateOnly = True

    def process_view(self):
        if self.request.method == 'POST':
            project_details = self.get_post_dict()
            if 'project_public' in project_details.keys():
                project_details['project_public'] = 1
            else:
                project_details['project_public'] = 0

            if project_details['project_abstract'] == "":
                project_details['project_abstract'] = None

            if project_details['project_code'] != "":
                next_page = self.request.params.get('next') or self.request.route_url('dashboard', userid=self.user.login)
                added, message = add_project(self.request, self.user.login, project_details)
                if added:
                    # Generate the QR image
                    url = self.request.route_url('project_details', userid=self.user.login,
                                                 projcode=project_details['project_code'])
                    odk_settings = {'admin': {"change_server": True, "change_form_metadata": False},
                                    'general': {"change_server": True, "navigation": "buttons",
                                                'server_url': url}}
                    qr_json = json.dumps(odk_settings).encode()
                    zip_json = zlib.compress(qr_json)
                    serialization = base64.encodebytes(zip_json)
                    serialization = serialization.decode()
                    serialization = serialization.replace("\n", "")
                    img = qrcode.make(serialization)
                    img_bytes = io.BytesIO()
                    img.save(img_bytes, "PNG")
                    img_bytes.seek(0)
                    store_file(self.request, message, project_details['project_code']+'.png', img_bytes)
                    modify_project(self.request, self.user.login, message,
                                   {'project_code': project_details['project_code'],
                                    'project_image': project_details['project_code'] + '.png'})

                    # Store the notifications
                    feed_manager = get_manager(self.request)
                    # Notify tha the user added a project
                    actor = Actor(self.user.login, 'person')
                    feed_object = Object(message, 'project')
                    activity = Activity('add', actor, feed_object)
                    feed_manager.add_activity_feed(activity)

                    self.request.session.flash(self._('The project has been created'))
                    self.returnRawViewResult = True
                    return HTTPFound(location=next_page)
                else:
                    self.errors.append(message)
            else:
                self.errors.append(self._('The project code cannot be empty'))
        else:
            project_details = {'project_public': 1}
        return {'projectDetails': project_details}


class EditProjectView(ProjectsView):
    def __init__(self, request):
        ProjectsView.__init__(self, request)
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
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

        if project_details["access_type"] == 4:
            raise HTTPNotFound  # Don't edit a public or a project that I am just a member

        current_image_file = project_details["project_image"]

        if self.request.method == 'POST':
            project_details = self.get_post_dict()
            if 'project_public' in project_details.keys():
                project_details['project_public'] = 1
            else:
                project_details['project_public'] = 0

            project_details['project_code'] = project_code

            if project_details['project_abstract'] == "":
                project_details['project_abstract'] = None

            #  TODO: If the project becomes private then we need to unwatched it from consumers

            next_page = self.request.params.get('next') or self.request.url
            modified, message = modify_project(self.request, user_id, project_id, project_details)
            if modified:
                # Store the notifications
                feed_manager = get_manager(self.request)
                # Notify tha the user edited the project
                actor = Actor(self.user.login, 'person')
                feed_object = Object(project_id, 'project')
                activity = Activity('edit', actor, feed_object)
                feed_manager.add_activity_feed(activity)

                self.request.session.flash(self._('The project has been modified'))
                self.returnRawViewResult = True
                return HTTPFound(location=next_page)
            else:
                self.errors.append(message)

        return {'projectDetails': project_details}


class DeleteProjectView(ProjectsView):
    def __init__(self, request):
        ProjectsView.__init__(self, request)
        self.checkCrossPost = False
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
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

        if project_details["access_type"] != 1:
            raise HTTPNotFound  # Don't edit a public or a project that I am just a member

        if self.request.method == 'POST':
            success_page = self.request.params.get('success') or self.request.route_url('projects',
                                                                                        userid=self.user.login)
            fail_page = self.request.params.get('fail') or self.request.route_url('projects', userid=self.user.login)
            self.returnRawViewResult = True
            deleted, message = delete_project(self.request, self.user.login, project_id)
            if deleted:
                # Delete the bucket
                delete_bucket(self.request, project_id)
                # Store the notifications
                feed_manager = get_manager(self.request)
                # Notify tha the user deleted the project
                actor = Actor(self.user.login, 'person')
                feed_object = Object(project_id, 'project')
                activity = Activity('delete', actor, feed_object)
                feed_manager.add_activity_feed(activity)

                self.request.session.flash(self._('The project was deleted successfully'))
                return HTTPFound(location=success_page)
            else:
                self.request.session.flash(self._('Unable to delete the project: ') + message)
                return HTTPFound(location=fail_page)
        else:
            raise HTTPNotFound


class AddFileToProject(ProjectsView):
    def __init__(self, request):
        ProjectsView.__init__(self, request)
        self.checkCrossPost = False
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
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

        if project_details["access_type"] == 4:
            raise HTTPNotFound  # Don't edit a public or a project that I am just a member

        if self.request.method == 'POST':
            self.returnRawViewResult = True
            try:
                input_file = self.request.POST['upload'].file
            except AttributeError:
                input_file = None
            next_page = self.request.route_url('project_details', userid=user_id, projcode=project_code)
            if input_file is not None:
                file_name = self.request.POST['upload'].filename
                added, message = add_file_to_project(self.request, project_id, file_name)
                if added:
                    store_file(self.request, project_id, file_name, self.request.POST['upload'].file)
                    self.request.session.flash(self._('The files was added successfully'))
                else:
                    next_page = self.request.route_url('project_details', userid=user_id, projcode=project_code,
                                                       _query={'error': message})
                    return HTTPFound(location=next_page)
            return HTTPFound(location=next_page)
        else:
            raise HTTPNotFound


class RemoveFileFromProject(ProjectsView):
    def __init__(self, request):
        ProjectsView.__init__(self, request)
        self.checkCrossPost = False
        self.privateOnly = True

    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        file_name = self.request.matchdict['filename']
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

        if project_details["access_type"] == 4:
            raise HTTPNotFound  # Don't edit a public or a project that I am just a member

        if self.request.method == 'POST':
            self.returnRawViewResult = True

            next_page = self.request.route_url('project_details', userid=user_id, projcode=project_code)
            removed, message = remove_file_from_project(self.request, project_id, file_name)
            if removed:
                delete_stream(self.request, project_id, file_name)
                self.request.session.flash(self._('The files was removed successfully'))
            else:
                next_page = self.request.route_url('project_details', userid=user_id, projcode=project_code,
                                                   _query={'error': message})
                return HTTPFound(location=next_page)
            return HTTPFound(location=next_page)
        else:
            raise HTTPNotFound
