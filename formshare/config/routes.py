from ..plugins.utilities import add_route
import formshare.plugins as p
from ..views.basic_views import NotFoundView, HomeView, log_out_view, LoginView, RegisterView, \
    AssistantLoginView, assistant_log_out_view, RefreshSessionView
from ..views.dashboard import UserDashBoardView
from ..views.projects import AddProjectView, ProjectListView, ProjectDetailsView, ProjectStoredFileView, \
    EditProjectView, DeleteProjectView, AddFileToProject, RemoveFileFromProject, DownloadProjectGPSPoints, \
    ActivateProjectView
from ..views.profile import UserProfileView, EditProfileView
from ..views.collaborators import CollaboratorsListView, RemoveCollaborator
from ..views.assistants import AssistantsListView, AddAssistantsView, EditAssistantsView, DeleteAssistant, \
    ChangeAssistantPassword
from ..views.api import APIUserSearchSelect2
from ..views.assistant_groups import GroupListView, AddGroupView, EditGroupView, DeleteGroup, GroupMembersView, \
    RemoveMember
from ..views.form import FormDetails, AddNewForm, EditForm, DeleteForm, AddFileToForm, RemoveFileFromForm, \
    FormStoredFile, AddAssistant, EditAssistant, RemoveAssistant, AddGroupToForm, EditFormGroup, RemoveGroupForm, \
    DownloadCSVData, DownloadXLSX, DownloadSubmissionFiles, DownloadGPSPoints, DownloadXLSData, UploadNewVersion, \
    ActivateForm, DeActivateForm, ImportData, DownloadKML
from ..views.odk import ODKFormList, ODKManifest, ODKMediaFile, ODKPushData, ODKSubmission, ODKXMLForm
from ..views.repository import GenerateRepository, SeparateTable, NewSeparationGroup, EditSeparationGroup, \
    DeleteSeparationGroup, RepositoryExist
from ..views.assistant_views.forms import AssistantForms, ChangeMyAssistantPassword, GetQRCode
from ..views.assistant_views.jsonlogs import JSONList, JSONCompare, JSONCheckout, JSONCancelCheckout, \
    JSONGetSubmission, JSONCheckin, JSONViewRevision, JSONCancelRevision, JSONPushRevision, JSONDisregard, \
    JSONCancelDisregard, JSONCompareSubmissions
from ..views.assistant_views.clean import CleanInterface, PerformAction, DataRequest

route_list = []


def append_to_routes(route_array):
    """
    #This function append or overrides the routes to the main list
    :param route_array: Array of routes
    """
    for new_route in route_array:
        found = False
        pos = 0
        for curr_route in route_list:
            if curr_route['path'] == new_route['path']:
                found = True
        pos += 1
        if not found:
            route_list.append(new_route)
        else:
            route_list[pos]['name'] = new_route['name']
            route_list[pos]['view'] = new_route['view']
            route_list[pos]['renderer'] = new_route['renderer']


def load_routes(config):
    """
    Call connected to plugins to add any routes before FormShare
    :param config: Pyramid config
    """
    routes = []
    for plugin in p.PluginImplementations(p.IRoutes):
        routes = plugin.before_mapping(config)
        append_to_routes(routes)

    # FormShare routes
    routes.append(add_route('home', '/', HomeView, 'landing/index.jinja2'))
    routes.append(add_route('refresh', '/refresh', RefreshSessionView, 'generic/refresh.jinja2'))
    routes.append(add_route('login', '/login', LoginView, 'generic/login.jinja2'))
    routes.append(add_route('register', '/join', RegisterView, 'generic/register.jinja2'))
    routes.append(add_route('logout', '/logout', log_out_view, None))

    routes.append(add_route('dashboard', '/user/{userid}', UserDashBoardView, 'dashboard/index.jinja2'))
    routes.append(add_route('profile', '/user/{userid}/profile', UserProfileView, 'dashboard/profile/profile.jinja2'))
    routes.append(add_route('profile_edit', '/user/{userid}/profile/edit', EditProfileView,
                            'dashboard/profile/profile_edit.jinja2'))

    # Projects
    routes.append(add_route('projects_add', '/user/{userid}/projects/add', AddProjectView,
                            'dashboard/projects/project_add.jinja2'))

    routes.append(
        add_route('projects', '/user/{userid}/projects', ProjectListView, 'dashboard/projects/project_list.jinja2'))
    routes.append(add_route('project_details', '/user/{userid}/project/{projcode}', ProjectDetailsView,
                            'dashboard/projects/project_details.jinja2'))
    routes.append(
        add_route('project_stored_file', '/user/{userid}/project/{projcode}/storage/{filename}', ProjectStoredFileView,
                  None))
    routes.append(add_route('project_edit', '/user/{userid}/project/{projcode}/edit', EditProjectView,
                            'dashboard/projects/project_edit.jinja2'))

    routes.append(add_route('project_delete', '/user/{userid}/project/{projcode}/delete', DeleteProjectView, None))

    routes.append(
        add_route('project_setactive', '/user/{userid}/project/{projcode}/setactive', ActivateProjectView, None))

    routes.append(add_route('project_upload', '/user/{userid}/project/{projcode}/upload', AddFileToProject, None))

    routes.append(add_route('project_remove_file', '/user/{userid}/project/{projcode}/uploads/{filename}/remove',
                            RemoveFileFromProject, None))

    routes.append(add_route('project_download_gpspoints', '/user/{userid}/project/{projcode}/download/gpspoints',
                            DownloadProjectGPSPoints, 'json'))

    # Collaborators

    routes.append(add_route('collaborators', '/user/{userid}/project/{projcode}/collaborators', CollaboratorsListView,
                            'dashboard/projects/collaborators/collaborator_list.jinja2'))
    routes.append(add_route('collaborator_remove', '/user/{userid}/project/{projcode}/collaborator/{collid}/remove',
                            RemoveCollaborator, None))

    # Assistants
    routes.append(add_route('assistants', '/user/{userid}/project/{projcode}/assistants', AssistantsListView,
                            'dashboard/projects/assistants/assistant_list.jinja2'))

    routes.append(add_route('assistant_add', '/user/{userid}/project/{projcode}/assistants/add', AddAssistantsView,
                            'dashboard/projects/assistants/assistant_add.jinja2'))

    routes.append(
        add_route('assistant_edit', '/user/{userid}/project/{projcode}/assistant/{assistid}/edit', EditAssistantsView,
                  'dashboard/projects/assistants/assistant_edit.jinja2'))

    routes.append(
        add_route('assistant_delete', '/user/{userid}/project/{projcode}/assistant/{assistid}/delete', DeleteAssistant,
                  None))

    routes.append(add_route('assistant_change_pass', '/user/{userid}/project/{projcode}/assistant/{assistid}/change',
                            ChangeAssistantPassword, None))

    # Assistant groups
    routes.append(add_route('groups', '/user/{userid}/project/{projcode}/groups', GroupListView,
                            'dashboard/projects/assistant_groups/group_list.jinja2'))

    routes.append(add_route('group_add', '/user/{userid}/project/{projcode}/groups/add', AddGroupView,
                            'dashboard/projects/assistant_groups/group_add.jinja2'))

    routes.append(add_route('group_edit', '/user/{userid}/project/{projcode}/group/{groupid}/edit', EditGroupView,
                            'dashboard/projects/assistant_groups/group_edit.jinja2'))

    routes.append(add_route('group_delete', '/user/{userid}/project/{projcode}/group/{groupid}/delete', DeleteGroup,
                            None))

    routes.append(
        add_route('group_members', '/user/{userid}/project/{projcode}/group/{groupid}/members', GroupMembersView,
                  'dashboard/projects/assistant_groups/members/member_list.jinja2'))

    routes.append(add_route('remove_member',
                            '/user/{userid}/project/{projcode}/group/{groupid}/member/{memberid}/of/{projectid}/remove',
                            RemoveMember, None))

    # Forms
    routes.append(add_route('form_add', '/user/{userid}/project/{projcode}/forms/add', AddNewForm, None))

    routes.append(add_route('form_details', '/user/{userid}/project/{projcode}/form/{formid}', FormDetails,
                            'dashboard/projects/forms/form_details.jinja2'))

    routes.append(
        add_route('update_form', '/user/{userid}/project/{projcode}/form/{formid}/updateodk', UploadNewVersion, None))

    routes.append(add_route('form_edit', '/user/{userid}/project/{projcode}/form/{formid}/edit', EditForm,
                            'dashboard/projects/forms/form_edit.jinja2'))

    routes.append(add_route('delete_form', '/user/{userid}/project/{projcode}/form/{formid}/delete', DeleteForm,
                            None))

    routes.append(add_route('activate_form', '/user/{userid}/project/{projcode}/form/{formid}/activate', ActivateForm,
                            None))

    routes.append(
        add_route('deactivate_form', '/user/{userid}/project/{projcode}/form/{formid}/deactivate', DeActivateForm,
                  None))

    routes.append(
        add_route('import_data', '/user/{userid}/project/{projcode}/form/{formid}/import', ImportData,
                  'dashboard/projects/forms/import_data/import_form.jinja2'))

    # Form files
    routes.append(
        add_route('form_upload', '/user/{userid}/project/{projcode}/form/{formid}/upload', AddFileToForm, None))

    routes.append(
        add_route('form_remove_file', '/user/{userid}/project/{projcode}/form/{formid}/uploads/{filename}/remove',
                  RemoveFileFromForm, None))

    routes.append(
        add_route('form_stored_file', '/user/{userid}/project/{projcode}/form/{formid}/uploads/{filename}/retrieve',
                  FormStoredFile, None))

    # Form assistants
    routes.append(
        add_route('form_add_assistant', '/user/{userid}/project/{projcode}/form/{formid}/assistants/add',
                  AddAssistant, None))

    routes.append(add_route('form_edit_assistant',
                            '/user/{userid}/project/{projcode}/form/{formid}/assistant/{projectid}/{assistantid}/edit',
                            EditAssistant, None))

    routes.append(
        add_route(
            'form_remove_assistant',
            '/user/{userid}/project/{projcode}/form/{formid}/assistant/{projectid}/{assistantid}/remove',
            RemoveAssistant, None))

    # Form groups
    routes.append(
        add_route('form_add_group', '/user/{userid}/project/{projcode}/form/{formid}/groups/add',
                  AddGroupToForm, None))

    routes.append(add_route('form_edit_group',
                            '/user/{userid}/project/{projcode}/form/{formid}/group/{groupid}/edit',
                            EditFormGroup, None))

    routes.append(
        add_route(
            'form_remove_group',
            '/user/{userid}/project/{projcode}/form/{formid}/group/{groupid}/remove',
            RemoveGroupForm, None))

    # Form actions
    routes.append(
        add_route(
            'form_download_csv',
            '/user/{userid}/project/{projcode}/form/{formid}/download/csv',
            DownloadCSVData, None))

    routes.append(
        add_route(
            'form_download_xlsx_data',
            '/user/{userid}/project/{projcode}/form/{formid}/download/xlsx',
            DownloadXLSData, None))

    routes.append(
        add_route(
            'form_download_xlsx',
            '/user/{userid}/project/{projcode}/form/{formid}/download/odk',
            DownloadXLSX, None))

    routes.append(
        add_route(
            'form_download_media',
            '/user/{userid}/project/{projcode}/form/{formid}/download/media',
            DownloadSubmissionFiles, None))

    routes.append(
        add_route(
            'form_download_gpspoints',
            '/user/{userid}/project/{projcode}/form/{formid}/download/gpspoints',
            DownloadGPSPoints, 'json'))

    routes.append(
        add_route(
            'form_download_kml',
            '/user/{userid}/project/{projcode}/form/{formid}/download/kml',
            DownloadKML, None))

    # Repository

    routes.append(
        add_route('createrepository', '/user/{userid}/project/{projcode}/form/{formid}/repository/create',
                  GenerateRepository, 'dashboard/projects/repository/create_repository.jinja2'))

    routes.append(
        add_route('repository_exists', '/user/{userid}/project/{projcode}/form/{formid}/repository/exists',
                  RepositoryExist, 'dashboard/projects/repository/repository_exist.jinja2'))

    routes.append(add_route('separatetable', '/user/{userid}/project/{projcode}/form/{formid}/separate/{tablename}',
                            SeparateTable, 'dashboard/projects/repository/separate_table.jinja2'))

    routes.append(
        add_route('addgroup', '/user/{userid}/project/{projcode}/form/{formid}/separate/{tablename}/group/new',
                  NewSeparationGroup, 'dashboard/projects/repository/create_group.jinja2'))

    routes.append(add_route('editgroup',
                            '/user/{userid}/project/{projcode}/form/{formid}/separate/{tablename}/group/{groupid}/edit',
                            EditSeparationGroup, 'dashboard/projects/repository/edit_group.jinja2'))

    routes.append(add_route('deletegroup',
                            '/user/{userid}/project/{projcode}/form/{formid}/separate'
                            '/{tablename}/group/{groupid}/delete',
                            DeleteSeparationGroup, None))

    # Assistant access

    routes.append(
        add_route('assistant_login', '/user/{userid}/project/{projcode}/assistantaccess/login', AssistantLoginView,
                  'generic/assistant_login.jinja2'))

    routes.append(add_route('assistant_logout', '/user/{userid}/project/{projcode}/assistantaccess/logout',
                            assistant_log_out_view, None))

    routes.append(
        add_route('assistant_forms', '/user/{userid}/project/{projcode}/assistantaccess/forms', AssistantForms,
                  'assistant/index.jinja2'))

    routes.append(
        add_route('assistant_change_my_pass', '/user/{userid}/project/{projcode}/assistantaccess/changemypassword',
                  ChangeMyAssistantPassword, None))

    routes.append(
        add_route('assistant_qr_code', '/user/{userid}/project/{projcode}/assistantaccess/form/{formid}/qrcode',
                  GetQRCode, None))

    # JSON logs

    routes.append(
        add_route('errorlist', '/user/{userid}/project/{projcode}/assistantaccess/form/{formid}/errors', JSONList,
                  'assistant/jsonlogs/loglist.jinja2'))

    routes.append(add_route('comparejsons',
                            '/user/{userid}/project/{projcode}/assistantaccess/form/{formid}/{submissionid}/compare',
                            JSONCompare, 'assistant/jsonlogs/compare.jinja2'))

    routes.append(add_route('checkoutjson',
                            '/user/{userid}/project/{projcode}/assistantaccess/form/{formid}/{submissionid}/checkout',
                            JSONCheckout, None))

    routes.append(add_route('cancelcheckout',
                            '/user/{userid}/project/{projcode}/assistantaccess/form/{formid}/{submissionid}/cancel',
                            JSONCancelCheckout, None))

    routes.append(
        add_route('getsubmission', '/user/{userid}/project/{projcode}/assistantaccess/form/{formid}/{submissionid}/get',
                  JSONGetSubmission, None))

    routes.append(add_route('checkinjson',
                            '/user/{userid}/project/{projcode}/assistantaccess/form/{formid}/{submissionid}/checkin',
                            JSONCheckin, 'assistant/jsonlogs/checkin.jinja2'))

    routes.append(add_route('viewrevision', '/user/{userid}/project/{projcode}/assistantaccess'
                                            '/form/{formid}/{submissionid}/{revisionid}/view',
                            JSONViewRevision, 'assistant/jsonlogs/review.jinja2'))

    routes.append(add_route('cancelrevision', '/user/{userid}/project/{projcode}/assistantaccess/'
                                              'form/{formid}/{submissionid}/{revisionid}/cancel',
                            JSONCancelRevision, None))

    routes.append(add_route('pushrevision', '/user/{userid}/project/{projcode}/assistantaccess'
                                            '/form/{formid}/{submissionid}/{revisionid}/push', JSONPushRevision, None))

    routes.append(add_route('disregard', '/user/{userid}/project/{projcode}/assistantaccess'
                                         '/form/{formid}/{submissionid}/disregard',
                            JSONDisregard, 'assistant/jsonlogs/disregard.jinja2'))

    routes.append(add_route('canceldisregard', '/user/{userid}/project/{projcode}/assistantaccess'
                                               '/form/{formid}/{submissionid}/canceldisregard',
                            JSONCancelDisregard, 'assistant/jsonlogs/cancel_disregard.jinja2'))

    routes.append(add_route('comparesubmissions', '/user/{userid}/project/{projcode}/assistantaccess'
                                                  '/form/{formid}/{submissiona}/{submissionb}/compare',
                            JSONCompareSubmissions, 'assistant/jsonlogs/compare_submissions.jinja2'))

    # Clean interface

    routes.append(
        add_route('clean', '/user/{userid}/project/{projcode}/assistantaccess/form/{formid}/clean', CleanInterface,
                  'assistant/clean/clean_data.jinja2'))
    routes.append(
        add_route('request', '/user/{userid}/project/{projcode}/assistantaccess/form/{formid}/{tablename}/request',
                  DataRequest, 'json'))
    routes.append(
        add_route('action', '/user/{userid}/project/{projcode}/assistantaccess/form/{formid}/{tablename}/action',
                  PerformAction, 'json'))

    # API
    routes.append(add_route('api_select2_users', '/api/select2_user', APIUserSearchSelect2, 'json'))

    # ODK Forms
    routes.append(add_route('odkformlist', '/user/{userid}/project/{projcode}/formList', ODKFormList, None))
    routes.append(add_route('odksubmission', '/user/{userid}/project/{projcode}/submission', ODKSubmission, None))
    routes.append(add_route('odkpush', '/user/{userid}/project/{projcode}/push', ODKPushData, None))
    routes.append(add_route('odkxmlform', '/user/{userid}/project/{projcode}/{formid}/xmlform', ODKXMLForm, None))
    routes.append(add_route('odkmanifest', '/user/{userid}/project/{projcode}/{formid}/manifest', ODKManifest, None))
    routes.append(add_route('odkmediafile', '/user/{userid}/project/{projcode}/{formid}/manifest/mediafile/{fileid}',
                            ODKMediaFile, None))

    append_to_routes(routes)

    # Add the not found route
    config.add_notfound_view(NotFoundView, renderer='generic/404.jinja2')

    # Call connected plugins to add any routes after FormShare
    for plugin in p.PluginImplementations(p.IRoutes):
        routes = plugin.after_mapping(config)
        append_to_routes(routes)

    # Now add the routes and views to the Pyramid config
    for curr_route in route_list:
        config.add_route(curr_route['name'], curr_route['path'])
        config.add_view(curr_route['view'], route_name=curr_route['name'], renderer=curr_route['renderer'])
