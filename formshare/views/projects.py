from formshare.views.classes import ProjectsView
from formshare.processes import add_project, modify_project, delete_project, is_collaborator
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from formshare.config.elasticfeeds import get_manager
from elasticfeeds.activity import Actor, Object, Activity
from formshare.processes import get_project_id_from_name
import validators
from formshare.processes import store_file, get_stream, response_stream, delete_stream, delete_bucket
from pyramid.response import Response


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
        return {'projectData': project_data, 'userid': user_id}


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

            project_image = project_details['project_image']
            if project_image == "":
                project_image = None
                project_details['project_image'] = None
            try:
                input_file = self.request.POST['filetoupload'].file
            except AttributeError:
                input_file = None
            project_details.pop('filetoupload')

            image_valid = True
            if input_file is None:
                if project_image is not None:
                    if not validators.url(project_image):
                        self.errors.append(self._("The image URL is invalid"))
                        image_valid = False
            if image_valid:
                next_page = self.request.params.get('next') or self.request.route_url('dashboard',
                                                                                      userid=self.user.login)
                added, message = add_project(self.request, self.user.login, project_details)
                if added:
                    # Store the image
                    if input_file is not None:
                        store_file(self.request, message, project_image, self.request.POST['filetoupload'].file)
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
            project_details = {'project_image': None}
        return {'projectDetails': project_details}


class EditProjectView(ProjectsView):
    def __init__(self, request):
        ProjectsView.__init__(self, request)

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

            project_image = project_details['project_image']
            if project_image == "":
                project_image = None
                project_details['project_image'] = None
            try:
                input_file = self.request.POST['filetoupload'].file
            except AttributeError:
                input_file = None
            project_details.pop('filetoupload')

            next_page = self.request.params.get('next') or self.request.url
            modified, message = modify_project(self.request, user_id, project_id, project_details)
            if modified:
                # Modify the storage
                if input_file is None:
                    if project_image is not None:
                        if project_image != current_image_file:
                            if not validators.url(project_image):
                                self.errors.append(self._("The image URL is invalid"))
                            else:
                                if current_image_file is not None:
                                    if not validators.url(current_image_file):
                                        delete_stream(self.request, project_id, current_image_file)
                    else:
                        if project_image != current_image_file:
                            if not validators.url(current_image_file):
                                delete_stream(self.request, project_id, current_image_file)
                else:
                    if current_image_file is not None:
                        if not validators.url(current_image_file):
                            delete_stream(self.request, project_id, current_image_file)
                    store_file(self.request, project_id, project_image, self.request.POST['filetoupload'].file)

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
                self.request.session.flash(self._('Unable to delete the project: ' + message))
                return HTTPFound(location=fail_page)
        else:
            raise HTTPNotFound
