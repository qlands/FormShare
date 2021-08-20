import logging
import os

import formshare.plugins as p
from formshare.plugins.utilities import add_route
from formshare.views.assistant_groups import (
    GroupListView,
    AddGroupView,
    EditGroupView,
    DeleteGroup,
    GroupMembersView,
    RemoveMember,
)
from formshare.views.assistant_views.clean import (
    CleanInterface,
    PerformAction,
    DataRequest,
)
from formshare.views.assistant_views.forms import (
    AssistantForms,
    ChangeMyAssistantPassword,
    GetQRCode,
    ChangeMyAPIKey,
)
from formshare.views.partner_views.forms import (
    PartnerForms,
    PartnerFormDetails,
    PartnerDownloadGPSPoints,
    PartnerGetSubMissionInfo,
    GetPartnerMediaFile,
)
from formshare.views.assistant_views.jsonlogs import (
    JSONList,
    JSONCompare,
    JSONCheckout,
    JSONCancelCheckout,
    JSONGetSubmission,
    JSONCheckin,
    JSONViewRevision,
    JSONCancelRevision,
    JSONPushRevision,
    JSONPushSubmission,
    JSONDisregard,
    JSONCancelDisregard,
    JSONCompareSubmissions,
    JSONGetSubmissionsMedia,
)
from formshare.views.assistants import (
    AssistantsListView,
    AddAssistantsView,
    EditAssistantsView,
    DeleteAssistant,
    ChangeAssistantPassword,
)
from formshare.views.basic_views import (
    NotFoundView,
    HomeView,
    HealthView,
    log_out_view,
    LoginView,
    RegisterView,
    AssistantLoginView,
    PartnerLoginView,
    assistant_log_out_view,
    partner_log_out_view,
    RefreshSessionView,
    RecoverPasswordView,
    ErrorView,
    Gravatar,
)
from formshare.views.collaborators import (
    CollaboratorsListView,
    RemoveCollaborator,
    AcceptCollaboration,
)
from formshare.views.dashboard import UserDashBoardView
from formshare.views.form import (
    FormDetails,
    AddNewForm,
    EditForm,
    DeleteForm,
    AddFileToForm,
    RemoveFileFromForm,
    FormStoredFile,
    AddAssistant,
    EditAssistant,
    RemoveAssistant,
    AddGroupToForm,
    EditFormGroup,
    RemoveGroupForm,
    DownloadCSVData,
    DownloadXLSX,
    DownloadSubmissionFiles,
    DownloadGPSPoints,
    DownloadPublicXLSData,
    UploadNewVersion,
    ActivateForm,
    DeActivateForm,
    ImportData,
    DownloadKML,
    StopTask,
    DownloadPublicCSV,
    DownloadPrivateCSV,
    DownloadPrivateXLSData,
    GetSubMissionInfo,
    GetMediaFile,
    CaseLookUpTable,
    AddPartnerToForm,
    EditPartnerFormOptions,
    RemovePartnerFromForm,
)
from formshare.views.odk import (
    ODKFormList,
    ODKManifest,
    ODKMediaFile,
    ODKPushData,
    ODKSubmission,
    ODKXMLForm,
)
from formshare.views.products import (
    DownloadPrivateProduct,
    DownloadPublicProduct,
    DownloadPrivateProductByAPI,
    PublishProduct,
    UnPublishProduct,
    DeleteProduct,
)
from formshare.views.profile import UserProfileView, EditProfileView
from formshare.views.projects import (
    AddProjectView,
    ProjectListView,
    ProjectDetailsView,
    ProjectStoredFileView,
    EditProjectView,
    DeleteProjectView,
    AddFileToProject,
    RemoveFileFromProject,
    DownloadProjectGPSPoints,
    ActivateProjectView,
    GetProjectQRCode,
    AddPartnerToProject,
    EditPartnerOptions,
    RemovePartnerFromProject,
)
from formshare.views.repository import GenerateRepository
from formshare.views.repository_dictionary import (
    EditDictionaryTables,
    EditDictionaryFields,
)
from formshare.views.repository_merge import RepositoryMergeForm
from formshare.views.repository_submissions import (
    ManageSubmissions,
    GetFormSubmissions,
    DeleteFormSubmission,
    DeleteAllSubmissions,
    GetFormAudit,
    ReviewAudit,
)
from formshare.views.search import APIUserSearchSelect2, APIPartnerSearchSelect2
from formshare.views.testing import (
    TestUserView,
    TestFormView,
    TestRemoveUserView,
    TestErrorView,
)
from formshare.views.users import UsersListView, EditUserView, AddUserView
from formshare.views.partners import (
    PartnersListView,
    AddPartnerView,
    EditPartnerView,
    DeletePartnerView,
)

log = logging.getLogger("formshare")

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
            if curr_route["path"] == new_route["path"]:
                found = True
                break
            pos = pos + 1
        if not found:
            route_list.append(new_route)
        else:
            route_list[pos]["name"] = new_route["name"]
            route_list[pos]["view"] = new_route["view"]
            route_list[pos]["renderer"] = new_route["renderer"]


def load_routes(config, settings):
    """
    Call connected to plugins to add any routes before FormShare
    :param config: Pyramid config
    """
    routes = []
    for plugin in p.PluginImplementations(p.IRoutes):
        routes = plugin.before_mapping(config)
        append_to_routes(routes)

    # FormShare routes
    routes.append(add_route("home", "/", HomeView, "landing/index.jinja2"))
    routes.append(add_route("health", "/health", HealthView, "json"))

    routes.append(
        add_route("refresh", "/refresh", RefreshSessionView, "generic/refresh.jinja2")
    )
    routes.append(add_route("login", "/login", LoginView, "generic/login.jinja2"))

    # TODO: Mimic send emmail celery task
    routes.append(
        add_route(
            "recover_password",
            "/recover",
            RecoverPasswordView,
            "generic/recover_password.jinja2",
        )
    )
    routes.append(
        add_route("register", "/join", RegisterView, "generic/register.jinja2")
    )

    routes.append(add_route("logout", "/logout", log_out_view, None))

    # TODO: Test for merged forms
    routes.append(
        add_route(
            "dashboard", "/user/{userid}", UserDashBoardView, "dashboard/index.jinja2"
        )
    )
    routes.append(
        add_route(
            "manage_users",
            "/user/{userid}/manage_users",
            UsersListView,
            "dashboard/users/user_list.jinja2",
        )
    )
    routes.append(
        add_route(
            "modify_user",
            "/user/{userid}/manage_user/{manageuser}/edit",
            EditUserView,
            "dashboard/users/user_edit.jinja2",
        )
    )
    routes.append(
        add_route(
            "add_user",
            "/user/{userid}/manage_users/add",
            AddUserView,
            "dashboard/users/user_add.jinja2",
        )
    )

    # Profile
    # TODO: Test with merged forms
    routes.append(
        add_route(
            "profile",
            "/user/{userid}/profile",
            UserProfileView,
            "dashboard/profile/profile.jinja2",
        )
    )
    routes.append(
        add_route(
            "profile_edit",
            "/user/{userid}/profile/edit",
            EditProfileView,
            "dashboard/profile/profile_edit.jinja2",
        )
    )
    routes.append(add_route("gravatar", "/gravatar", Gravatar, None))

    # Projects
    routes.append(
        add_route(
            "projects_add",
            "/user/{userid}/projects/add",
            AddProjectView,
            "dashboard/projects/project_add.jinja2",
        )
    )

    routes.append(
        add_route(
            "projects",
            "/user/{userid}/projects",
            ProjectListView,
            "dashboard/projects/project_list.jinja2",
        )
    )

    # TODO: Test with merged forms
    routes.append(
        add_route(
            "project_details",
            "/user/{userid}/project/{projcode}",
            ProjectDetailsView,
            "dashboard/projects/project_details.jinja2",
        )
    )
    routes.append(
        add_route(
            "project_stored_file",
            "/user/{userid}/project/{projcode}/storage/{filename}",
            ProjectStoredFileView,
            None,
        )
    )
    routes.append(
        add_route(
            "project_edit",
            "/user/{userid}/project/{projcode}/edit",
            EditProjectView,
            "dashboard/projects/project_edit.jinja2",
        )
    )

    routes.append(
        add_route(
            "project_case_lookup_table",
            "/user/{userid}/project/{projcode}/caselookuptable",
            CaseLookUpTable,
            "dashboard/projects/forms/case/case_fields.jinja2",
        )
    )

    routes.append(
        add_route(
            "project_delete",
            "/user/{userid}/project/{projcode}/delete",
            DeleteProjectView,
            None,
        )
    )

    routes.append(
        add_route(
            "project_qr", "/user/{userid}/project/{projcode}/qr", GetProjectQRCode, None
        )
    )

    routes.append(
        add_route(
            "project_setactive",
            "/user/{userid}/project/{projcode}/setactive",
            ActivateProjectView,
            None,
        )
    )

    routes.append(
        add_route(
            "project_upload",
            "/user/{userid}/project/{projcode}/upload",
            AddFileToProject,
            None,
        )
    )

    routes.append(
        add_route(
            "project_remove_file",
            "/user/{userid}/project/{projcode}/uploads/{filename}/remove",
            RemoveFileFromProject,
            None,
        )
    )

    # TODO: Test with merged forms
    routes.append(
        add_route(
            "project_download_gpspoints",
            "/user/{userid}/project/{projcode}/download/gpspoints",
            DownloadProjectGPSPoints,
            "json",
        )
    )

    # Collaborators

    routes.append(
        add_route(
            "collaborators",
            "/user/{userid}/project/{projcode}/collaborators",
            CollaboratorsListView,
            "dashboard/projects/collaborators/collaborator_list.jinja2",
        )
    )
    routes.append(
        add_route(
            "collaborator_remove",
            "/user/{userid}/project/{projcode}/collaborator/{collid}/remove",
            RemoveCollaborator,
            None,
        )
    )

    # TODO: Test
    routes.append(
        add_route(
            "accept_collaboration",
            "/user/{userid}/project/{projcode}/accept",
            AcceptCollaboration,
            "dashboard/projects/collaborators/accept_collaboration.jinja2",
        )
    )

    # Assistants
    routes.append(
        add_route(
            "assistants",
            "/user/{userid}/project/{projcode}/assistants",
            AssistantsListView,
            "dashboard/projects/assistants/assistant_list.jinja2",
        )
    )

    routes.append(
        add_route(
            "assistant_add",
            "/user/{userid}/project/{projcode}/assistants/add",
            AddAssistantsView,
            "dashboard/projects/assistants/assistant_add.jinja2",
        )
    )

    routes.append(
        add_route(
            "assistant_edit",
            "/user/{userid}/project/{projcode}/assistant/{assistid}/edit",
            EditAssistantsView,
            "dashboard/projects/assistants/assistant_edit.jinja2",
        )
    )

    routes.append(
        add_route(
            "assistant_delete",
            "/user/{userid}/project/{projcode}/assistant/{assistid}/delete",
            DeleteAssistant,
            None,
        )
    )

    routes.append(
        add_route(
            "assistant_change_pass",
            "/user/{userid}/project/{projcode}/assistant/{assistid}/change",
            ChangeAssistantPassword,
            None,
        )
    )

    # Assistant groups
    routes.append(
        add_route(
            "groups",
            "/user/{userid}/project/{projcode}/groups",
            GroupListView,
            "dashboard/projects/assistant_groups/group_list.jinja2",
        )
    )

    routes.append(
        add_route(
            "group_add",
            "/user/{userid}/project/{projcode}/groups/add",
            AddGroupView,
            "dashboard/projects/assistant_groups/group_add.jinja2",
        )
    )

    routes.append(
        add_route(
            "group_edit",
            "/user/{userid}/project/{projcode}/group/{groupid}/edit",
            EditGroupView,
            "dashboard/projects/assistant_groups/group_edit.jinja2",
        )
    )

    routes.append(
        add_route(
            "group_delete",
            "/user/{userid}/project/{projcode}/group/{groupid}/delete",
            DeleteGroup,
            None,
        )
    )

    routes.append(
        add_route(
            "group_members",
            "/user/{userid}/project/{projcode}/group/{groupid}/members",
            GroupMembersView,
            "dashboard/projects/assistant_groups/members/member_list.jinja2",
        )
    )

    routes.append(
        add_route(
            "remove_member",
            "/user/{userid}/project/{projcode}/group/{groupid}/member/{memberid}/of/{projectid}/remove",
            RemoveMember,
            None,
        )
    )

    # Forms
    routes.append(
        add_route(
            "form_add", "/user/{userid}/project/{projcode}/forms/add", AddNewForm, None
        )
    )

    routes.append(
        add_route(
            "form_merge",
            "/user/{userid}/project/{projcode}/form/{formid}/merge",
            AddNewForm,
            None,
        )
    )

    routes.append(
        add_route(
            "form_details",
            "/user/{userid}/project/{projcode}/form/{formid}",
            FormDetails,
            "dashboard/projects/forms/form_details.jinja2",
        )
    )

    routes.append(
        add_route(
            "update_form",
            "/user/{userid}/project/{projcode}/form/{formid}/updateodk",
            UploadNewVersion,
            None,
        )
    )

    routes.append(
        add_route(
            "form_edit",
            "/user/{userid}/project/{projcode}/form/{formid}/edit",
            EditForm,
            "dashboard/projects/forms/form_edit.jinja2",
        )
    )

    # TODO: Test with merged forms
    routes.append(
        add_route(
            "delete_form",
            "/user/{userid}/project/{projcode}/form/{formid}/delete",
            DeleteForm,
            None,
        )
    )

    routes.append(
        add_route(
            "activate_form",
            "/user/{userid}/project/{projcode}/form/{formid}/activate",
            ActivateForm,
            None,
        )
    )

    # TODO: Test
    routes.append(
        add_route(
            "stop_task",
            "/user/{userid}/project/{projcode}/form/{formid}/task/{taskid}/stop",
            StopTask,
            None,
        )
    )

    routes.append(
        add_route(
            "deactivate_form",
            "/user/{userid}/project/{projcode}/form/{formid}/deactivate",
            DeActivateForm,
            None,
        )
    )

    routes.append(
        add_route(
            "import_data",
            "/user/{userid}/project/{projcode}/form/{formid}/import",
            ImportData,
            "dashboard/projects/forms/import_data/import_form.jinja2",
        )
    )

    # Form files
    routes.append(
        add_route(
            "form_upload",
            "/user/{userid}/project/{projcode}/form/{formid}/upload",
            AddFileToForm,
            None,
        )
    )

    routes.append(
        add_route(
            "form_remove_file",
            "/user/{userid}/project/{projcode}/form/{formid}/uploads/{filename}/remove",
            RemoveFileFromForm,
            None,
        )
    )

    routes.append(
        add_route(
            "form_stored_file",
            "/user/{userid}/project/{projcode}/form/{formid}/uploads/{filename}/retrieve",
            FormStoredFile,
            None,
        )
    )

    # Form assistants
    routes.append(
        add_route(
            "form_add_assistant",
            "/user/{userid}/project/{projcode}/form/{formid}/assistants/add",
            AddAssistant,
            None,
        )
    )

    routes.append(
        add_route(
            "form_edit_assistant",
            "/user/{userid}/project/{projcode}/form/{formid}/assistant/{projectid}/{assistantid}/edit",
            EditAssistant,
            None,
        )
    )

    routes.append(
        add_route(
            "form_remove_assistant",
            "/user/{userid}/project/{projcode}/form/{formid}/assistant/{projectid}/{assistantid}/remove",
            RemoveAssistant,
            None,
        )
    )

    # Form groups
    routes.append(
        add_route(
            "form_add_group",
            "/user/{userid}/project/{projcode}/form/{formid}/groups/add",
            AddGroupToForm,
            None,
        )
    )

    routes.append(
        add_route(
            "form_edit_group",
            "/user/{userid}/project/{projcode}/form/{formid}/group/{groupid}/edit",
            EditFormGroup,
            None,
        )
    )

    routes.append(
        add_route(
            "form_remove_group",
            "/user/{userid}/project/{projcode}/form/{formid}/group/{groupid}/remove",
            RemoveGroupForm,
            None,
        )
    )

    # Form Products

    routes.append(
        add_route(
            "download_private_product",
            "/user/{userid}/project/{projcode}/form/{formid}/private_download/{productid}/output/{outputid}",
            DownloadPrivateProduct,
            None,
        )
    )

    routes.append(
        add_route(
            "download_public_product",
            "/user/{userid}/project/{projcode}/form/{formid}/public_download/{productid}/output/{outputid}",
            DownloadPublicProduct,
            None,
        )
    )

    routes.append(
        add_route(
            "api_download_private_product",
            "/user/{userid}/project/{projcode}/form/{formid}/api_download/{productid}/output/{outputid}",
            DownloadPrivateProductByAPI,
            "json",
        )
    )

    routes.append(
        add_route(
            "publish_product",
            "/user/{userid}/project/{projcode}/form/{formid}/products/{productid}/output/{outputid}/publish",
            PublishProduct,
            None,
        )
    )

    routes.append(
        add_route(
            "unpublish_product",
            "/user/{userid}/project/{projcode}/form/{formid}/products/{productid}/output/{outputid}/unpublish",
            UnPublishProduct,
            None,
        )
    )

    routes.append(
        add_route(
            "delete_product",
            "/user/{userid}/project/{projcode}/form/{formid}/products/{productid}/output/{outputid}/delete",
            DeleteProduct,
            None,
        )
    )

    # Form Downloads

    # TODO: Test with repository and merged forms
    routes.append(
        add_route(
            "form_download_csv",
            "/user/{userid}/project/{projcode}/form/{formid}/generate/csv",
            DownloadCSVData,
            None,
        )
    )

    # TODO: Test and with merged forms
    routes.append(
        add_route(
            "form_download_public_xlsx_data",
            "/user/{userid}/project/{projcode}/form/{formid}/generate/public_xlsx",
            DownloadPublicXLSData,
            None,
        )
    )

    # TODO: Test and with merged forms
    routes.append(
        add_route(
            "form_download_private_xlsx_data",
            "/user/{userid}/project/{projcode}/form/{formid}/generate/private_xlsx",
            DownloadPrivateXLSData,
            None,
        )
    )

    routes.append(
        add_route(
            "form_download_xlsx",
            "/user/{userid}/project/{projcode}/form/{formid}/get/odk",
            DownloadXLSX,
            None,
        )
    )

    # TODO: Test with repository and with merged forms
    routes.append(
        add_route(
            "form_download_media",
            "/user/{userid}/project/{projcode}/form/{formid}/generate/media",
            DownloadSubmissionFiles,
            None,
        )
    )

    # TODO: Test with repository and with merged forms
    routes.append(
        add_route(
            "form_download_gpspoints",
            "/user/{userid}/project/{projcode}/form/{formid}/get/gpspoints",
            DownloadGPSPoints,
            "json",
        )
    )

    # TODO: Test with repository and with merged forms
    routes.append(
        add_route(
            "form_download_kml",
            "/user/{userid}/project/{projcode}/form/{formid}/generate/kml",
            DownloadKML,
            None,
        )
    )

    # TODO: Test with repository and with merged forms
    routes.append(
        add_route(
            "form_download_repo_public_csv",
            "/user/{userid}/project/{projcode}/form/{formid}/generate/repo_public_csv",
            DownloadPublicCSV,
            None,
        )
    )

    # TODO: Test with repository and with merged forms
    routes.append(
        add_route(
            "form_download_repo_private_csv",
            "/user/{userid}/project/{projcode}/form/{formid}/generate/repo_private_csv",
            DownloadPrivateCSV,
            None,
        )
    )

    routes.append(
        add_route(
            "get_submission_info",
            "/user/{userid}/project/{projcode}/form/{formid}/{submissionid}/info",
            GetSubMissionInfo,
            "dashboard/projects/forms/map/marker_info.jinja2",
        )
    )

    routes.append(
        add_route(
            "get_submission_media_file",
            "/user/{userid}/project/{projcode}/form/{formid}/{submissionid}/media/{filename}/get",
            GetMediaFile,
            None,
        )
    )

    # Repository
    # TODO: Test all error cases
    routes.append(
        add_route(
            "createrepository",
            "/user/{userid}/project/{projcode}/form/{formid}/repository/create",
            GenerateRepository,
            "dashboard/projects/repository/create_repository.jinja2",
        )
    )

    # TODO: Test
    routes.append(
        add_route(
            "merge_new_version",
            "/user/{userid}/project/{projcode}/form/{formid}/merge/into/{oldformid}",
            RepositoryMergeForm,
            "dashboard/projects/repository/merge_new_version.jinja2",
        )
    )

    routes.append(
        add_route(
            "editDictTables",
            "/user/{userid}/project/{projcode}/form/{formid}/dictionary/tables",
            EditDictionaryTables,
            "dashboard/projects/forms/dictionary/edit_tables.jinja2",
        )
    )

    routes.append(
        add_route(
            "editDictFields",
            "/user/{userid}/project/{projcode}/form/{formid}/dictionary/table/{tableid}/fields",
            EditDictionaryFields,
            "dashboard/projects/forms/dictionary/edit_fields.jinja2",
        )
    )

    routes.append(
        add_route(
            "manageSubmissions",
            "/user/{userid}/project/{projcode}/form/{formid}/submissions",
            ManageSubmissions,
            "dashboard/projects/forms/submissions/edit_submissions.jinja2",
        )
    )

    routes.append(
        add_route(
            "viewAudit",
            "/user/{userid}/project/{projcode}/form/{formid}/audit",
            ReviewAudit,
            "dashboard/projects/forms/submissions/view_audit.jinja2",
        )
    )

    routes.append(
        add_route(
            "getFormSubmissions",
            "/user/{userid}/project/{projcode}/form/{formid}/submissions/get",
            GetFormSubmissions,
            "string",
        )
    )

    routes.append(
        add_route(
            "getFormAudit",
            "/user/{userid}/project/{projcode}/form/{formid}/audit/get",
            GetFormAudit,
            "string",
        )
    )

    routes.append(
        add_route(
            "deleteFormSubmission",
            "/user/{userid}/project/{projcode}/form/{formid}/submissions/delete",
            DeleteFormSubmission,
            "json",
        )
    )

    # TODO: Test
    routes.append(
        add_route(
            "deleteAllSubmissions",
            "/user/{userid}/project/{projcode}/form/{formid}/submissions/deleteall",
            DeleteAllSubmissions,
            None,
        )
    )

    # Assistant access

    routes.append(
        add_route(
            "assistant_login",
            "/user/{userid}/project/{projcode}/assistantaccess/login",
            AssistantLoginView,
            "generic/assistant_login.jinja2",
        )
    )

    routes.append(
        add_route(
            "assistant_logout",
            "/user/{userid}/project/{projcode}/assistantaccess/logout",
            assistant_log_out_view,
            None,
        )
    )

    routes.append(
        add_route(
            "assistant_forms",
            "/user/{userid}/project/{projcode}/assistantaccess/forms",
            AssistantForms,
            "assistant/index.jinja2",
        )
    )

    routes.append(
        add_route(
            "assistant_change_my_pass",
            "/user/{userid}/project/{projcode}/assistantaccess/changemypassword",
            ChangeMyAssistantPassword,
            None,
        )
    )

    routes.append(
        add_route(
            "assistant_change_my_key",
            "/user/{userid}/project/{projcode}/assistantaccess/changemykey",
            ChangeMyAPIKey,
            None,
        )
    )

    routes.append(
        add_route(
            "assistant_qr_code",
            "/user/{userid}/project/{projcode}/assistantaccess/form/{formid}/qrcode",
            GetQRCode,
            None,
        )
    )

    # JSON logs

    routes.append(
        add_route(
            "errorlist",
            "/user/{userid}/project/{projcode}/assistantaccess/form/{formid}/errors",
            JSONList,
            "assistant/jsonlogs/loglist.jinja2",
        )
    )

    routes.append(
        add_route(
            "comparejsons",
            "/user/{userid}/project/{projcode}/assistantaccess/form/{formid}/{submissionid}/compare",
            JSONCompare,
            "assistant/jsonlogs/compare.jinja2",
        )
    )

    routes.append(
        add_route(
            "checkoutjson",
            "/user/{userid}/project/{projcode}/assistantaccess/form/{formid}/{submissionid}/checkout",
            JSONCheckout,
            None,
        )
    )

    routes.append(
        add_route(
            "cancelcheckout",
            "/user/{userid}/project/{projcode}/assistantaccess/form/{formid}/{submissionid}/cancel",
            JSONCancelCheckout,
            None,
        )
    )

    routes.append(
        add_route(
            "getsubmission",
            "/user/{userid}/project/{projcode}/assistantaccess/form/{formid}/{submissionid}/get",
            JSONGetSubmission,
            None,
        )
    )

    routes.append(
        add_route(
            "checkinjson",
            "/user/{userid}/project/{projcode}/assistantaccess/form/{formid}/{submissionid}/checkin",
            JSONCheckin,
            "assistant/jsonlogs/checkin.jinja2",
        )
    )

    routes.append(
        add_route(
            "viewrevision",
            "/user/{userid}/project/{projcode}/assistantaccess"
            "/form/{formid}/{submissionid}/{revisionid}/view",
            JSONViewRevision,
            "assistant/jsonlogs/review.jinja2",
        )
    )

    routes.append(
        add_route(
            "cancelrevision",
            "/user/{userid}/project/{projcode}/assistantaccess/"
            "form/{formid}/{submissionid}/{revisionid}/cancel",
            JSONCancelRevision,
            None,
        )
    )

    routes.append(
        add_route(
            "pushrevision",
            "/user/{userid}/project/{projcode}/assistantaccess"
            "/form/{formid}/{submissionid}/{revisionid}/push",
            JSONPushRevision,
            None,
        )
    )

    # TODO: Test
    routes.append(
        add_route(
            "push_log_submission",
            "/user/{userid}/project/{projcode}/assistantaccess/form/{formid}/{submissionid}/push",
            JSONPushSubmission,
            None,
        )
    )

    routes.append(
        add_route(
            "disregard",
            "/user/{userid}/project/{projcode}/assistantaccess"
            "/form/{formid}/{submissionid}/disregard",
            JSONDisregard,
            "assistant/jsonlogs/disregard.jinja2",
        )
    )

    routes.append(
        add_route(
            "canceldisregard",
            "/user/{userid}/project/{projcode}/assistantaccess"
            "/form/{formid}/{submissionid}/canceldisregard",
            JSONCancelDisregard,
            "assistant/jsonlogs/cancel_disregard.jinja2",
        )
    )

    routes.append(
        add_route(
            "comparesubmissions",
            "/user/{userid}/project/{projcode}/assistantaccess"
            "/form/{formid}/{submissiona}/{submissionb}/compare",
            JSONCompareSubmissions,
            "assistant/jsonlogs/compare_submissions.jinja2",
        )
    )

    # TODO: Test
    routes.append(
        add_route(
            "get_submissions_media",
            "/user/{userid}/project/{projcode}/assistantaccess"
            "/form/{formid}/{submissiona}/{submissionb}/media",
            JSONGetSubmissionsMedia,
            None,
        )
    )

    # Clean interface

    routes.append(
        add_route(
            "clean",
            "/user/{userid}/project/{projcode}/assistantaccess/form/{formid}/clean",
            CleanInterface,
            "assistant/clean/clean_data.jinja2",
        )
    )

    routes.append(
        add_route(
            "request",
            "/user/{userid}/project/{projcode}/assistantaccess/form/{formid}/{tablename}/request",
            DataRequest,
            "string",
        )
    )

    routes.append(
        add_route(
            "action",
            "/user/{userid}/project/{projcode}/assistantaccess/form/{formid}/{tablename}/action",
            PerformAction,
            "json",
        )
    )

    # Utility API

    routes.append(
        add_route(
            "api_select2_users",
            "/user/{userid}/api/select2_user",
            APIUserSearchSelect2,
            "json",
        )
    )

    # Repository API

    # ODK Forms
    routes.append(
        add_route(
            "odkformlist",
            "/user/{userid}/project/{projcode}/formList",
            ODKFormList,
            None,
        )
    )
    routes.append(
        add_route(
            "odksubmission",
            "/user/{userid}/project/{projcode}/submission",
            ODKSubmission,
            None,
        )
    )
    routes.append(
        add_route(
            "odkpush", "/user/{userid}/project/{projcode}/push", ODKPushData, None
        )
    )
    routes.append(
        add_route(
            "odkxmlform",
            "/user/{userid}/project/{projcode}/{formid}/xmlform",
            ODKXMLForm,
            None,
        )
    )
    routes.append(
        add_route(
            "odkmanifest",
            "/user/{userid}/project/{projcode}/{formid}/manifest",
            ODKManifest,
            None,
        )
    )
    routes.append(
        add_route(
            "odkmediafile",
            "/user/{userid}/project/{projcode}/{formid}/manifest/mediafile/{fileid}",
            ODKMediaFile,
            None,
        )
    )

    # Partner routes

    if settings.get("allow.partner.access", "False") == "True":
        routes.append(
            add_route(
                "partner_login",
                "/partneraccess/login",
                PartnerLoginView,
                "generic/partner_login.jinja2",
            )
        )

        # TODO: To test
        routes.append(
            add_route(
                "partner_forms",
                "/partneraccess/dashboard",
                PartnerForms,
                "partner/index.jinja2",
            )
        )

        routes.append(
            add_route(
                "partner_logout",
                "/partneraccess/logout",
                partner_log_out_view,
                None,
            )
        )

        routes.append(
            add_route(
                "api_select2_partners",
                "/user/{userid}/api/select2_partners",
                APIPartnerSearchSelect2,
                "json",
            )
        )

        routes.append(
            add_route(
                "manage_partners",
                "/user/{userid}/manage_partners",
                PartnersListView,
                "dashboard/partners/partner_list.jinja2",
            )
        )

        routes.append(
            add_route(
                "add_partner",
                "/user/{userid}/manage_partners/add",
                AddPartnerView,
                "dashboard/partners/partner_add.jinja2",
            )
        )

        routes.append(
            add_route(
                "modify_partner",
                "/user/{userid}/manage_partner/{partnerid}/edit",
                EditPartnerView,
                "dashboard/partners/partner_edit.jinja2",
            )
        )
        routes.append(
            add_route(
                "delete_partner",
                "/user/{userid}/manage_partner/{partnerid}/delete",
                DeletePartnerView,
                None,
            )
        )

        routes.append(
            add_route(
                "project_link_partner",
                "/user/{userid}/project/{projcode}/link_partner",
                AddPartnerToProject,
                None,
            )
        )

        routes.append(
            add_route(
                "project_edit_partner",
                "/user/{userid}/project/{projcode}/edit_partner/{partnerid}",
                EditPartnerOptions,
                None,
            )
        )

        routes.append(
            add_route(
                "project_remove_partner",
                "/user/{userid}/project/{projcode}/remove_partner/{partnerid}",
                RemovePartnerFromProject,
                None,
            )
        )

        routes.append(
            add_route(
                "form_add_partner",
                "/user/{userid}/project/{projcode}/form/{formid}/partners/add",
                AddPartnerToForm,
                None,
            )
        )

        routes.append(
            add_route(
                "edit_partner_form_options",
                "/user/{userid}/project/{projcode}/form/{formid}/partner/{partnerid}/edit",
                EditPartnerFormOptions,
                None,
            )
        )

        routes.append(
            add_route(
                "remove_partner_from_form",
                "/user/{userid}/project/{projcode}/form/{formid}/partner/{partnerid}/remove",
                RemovePartnerFromForm,
                None,
            )
        )

        routes.append(
            add_route(
                "partner_form_details",
                "/partneraccess/user/{userid}/project/{projcode}/form/{formid}",
                PartnerFormDetails,
                "partner/form_details.jinja2",
            )
        )

        routes.append(
            add_route(
                "partner_form_download_gpspoints",
                "/partneraccess/user/{userid}/project/{projcode}/form/{formid}/get/gpspoints",
                PartnerDownloadGPSPoints,
                "json",
            )
        )

        routes.append(
            add_route(
                "partner_get_submission_info",
                "/partneraccess/user/{userid}/project/{projcode}/form/{formid}/{submissionid}/info",
                PartnerGetSubMissionInfo,
                "partner/map/marker_info.jinja2",
            )
        )

        routes.append(
            add_route(
                "get_partner_submission_media_file",
                "/partneraccess/user/{userid}/project/{projcode}/form/{formid}/{submissionid}/media/{filename}/get",
                GetPartnerMediaFile,
                None,
            )
        )

    # Testing routes
    if os.environ.get("FORMSHARE_PYTEST_RUNNING", "false") == "true":
        routes.append(
            add_route(
                "TestOwnedProjectView",
                "/test/{userid}",
                TestUserView,
                "generic/testing.jinja2",
            )
        )
        routes.append(
            add_route(
                "TestFormView",
                "/test/{userid}/project/{projcode}/form/{formid}",
                TestFormView,
                "generic/testing.jinja2",
            )
        )
        routes.append(
            add_route(
                "TestRemoveUserView",
                "/test/{userid}/remove",
                TestRemoveUserView,
                "generic/testing.jinja2",
            )
        )

        routes.append(
            add_route(
                "TestErrorView",
                "/test/{userid}/test_error",
                TestErrorView,
                "generic/testing.jinja2",
            )
        )

    append_to_routes(routes)

    # Add the not found route
    config.add_notfound_view(NotFoundView, renderer="generic/404.jinja2")

    if (
        log.level == logging.WARN
        or os.environ.get("FORMSHARE_TEST_ERROR_PAGE", "false") == "true"
    ):
        config.add_view(ErrorView, context=Exception, renderer="generic/500.jinja2")

    # Call connected plugins to add any routes after FormShare
    for plugin in p.PluginImplementations(p.IRoutes):
        routes = plugin.after_mapping(config)
        append_to_routes(routes)

    # Now add the routes and views to the Pyramid config
    for curr_route in route_list:
        config.add_route(curr_route["name"], curr_route["path"])
        config.add_view(
            curr_route["view"],
            route_name=curr_route["name"],
            renderer=curr_route["renderer"],
        )
