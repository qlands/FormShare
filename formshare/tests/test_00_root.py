import datetime
import json
import os
import unittest
from types import SimpleNamespace
import pkg_resources
from .steps.root import t_e_s_t_root
from .steps.login import t_e_s_t_login
from .steps.dashboard import t_e_s_t_dashboard
from .steps.profile import t_e_s_t_profile
from .steps.projects import t_e_s_t_projects
from .steps.collaborators import t_e_s_t_collaborators
from .steps.assistants import t_e_s_t_assistants
from .steps.assistant_groups import t_e_s_t_assistant_groups
from .steps.forms import t_e_s_t_forms
from .steps.multilanguage_odk import t_e_s_t_multilanguage_odk
from .steps.support_zip_file import t_e_s_t_support_zip_file
from .steps.external_select import t_e_s_t_external_select
from .steps.update_form_missing_files import t_e_s_t_update_form_missing_files
from .steps.odk import t_e_s_t_odk
from .steps.repository import t_e_s_t_repository
from .steps.repository_downloads import t_e_s_t_repository_downloads
from .steps.import_data import t_e_s_t_import_data
from .steps.repository_tasks import t_e_s_t_repository_tasks
from .steps.assistant_access import t_e_s_t_assistant_access
from .steps.json_logs import t_e_s_t_json_logs
from .steps.json_logs_2 import t_e_s_t_json_logs_2
from .steps.json_logs_4 import t_e_s_t_json_logs_4
from .steps.json_logs_3 import t_e_s_t_json_logs_3
from .steps.clean_interface import t_e_s_t_clean_interface
from .steps.clean_interface_unauthorized import t_e_s_t_clean_interface_unauthorized
from .steps.audit import t_e_s_t_audit
from .steps.collaborator_access import t_e_s_t_collaborator_access
from .steps.helpers import t_e_s_t_helpers
from .steps.utility_functions import t_e_s_t_utility_functions
from .steps.avatar_generator import t_e_s_t_avatar_generator
from .steps.color_hash_hex import t_e_s_t_color_hash_hex
from .steps.one_user_assistant import t_e_s_t_one_user_assistant
from .steps.five_collaborators import t_e_s_t_five_collaborators
from .steps.form_merge_start import t_e_s_t_form_merge_start
from .steps.form_merge_check_errors import t_e_s_t_form_merge_check_errors
from .steps.form_merge_delete import t_e_s_t_form_merge_delete
from .steps.form_merge import t_e_s_t_form_merge
from .steps.form_merge_mimic import t_e_s_t_form_merge_mimic
from .steps.form_merge_mimic_2 import t_e_s_t_form_merge_mimic_2
from .steps.form_merge_mimic_3 import t_e_s_t_form_merge_mimic_3
from .steps.form_merge_language_control import t_e_s_t_form_merge_language_control
from .steps.form_merge_language_control_2 import t_e_s_t_form_merge_language_control_2
from .steps.form_merge_language_control_3 import t_e_s_t_form_merge_language_control_3
from .steps.form_merge_language_control_4 import t_e_s_t_form_merge_language_control_4
from .steps.form_merge_language_control_5 import t_e_s_t_form_merge_language_control_5
from .steps.group_assistant import t_e_s_t_group_assistant
from .steps.delete_form_with_repository import t_e_s_t_delete_form_with_repository
from .steps.api import t_e_s_t_api
from .steps.plugin_utility_functions import t_e_s_t_plugin_utility_functions
from .steps.collaborator_projects import t_e_s_t_collaborator_projects
from .steps.collaborator_projects_2 import t_e_s_t_collaborator_projects_2
from .steps.collaborator_projects_3 import t_e_s_t_collaborator_projects_3
from .steps.collaborator_projects_4 import t_e_s_t_collaborator_projects_4
from .steps.delete_active_project import t_e_s_t_delete_active_project
from .steps.form_access import t_e_s_t_form_access
from .steps.create_super_user import t_e_s_t_create_super_user
from .steps.configure_alembic import t_e_s_t_configure_alembic
from .steps.configure_fluent import t_e_s_t_configure_fluent
from .steps.configure_mysql import t_e_s_t_configure_mysql
from .steps.configure_t_e_s_t_s import t_e_s_t_configure_t_e_s_t_s
from .steps.modify_config import t_e_s_t_modify_config
from .steps.disable_ssl import t_e_s_t_disable_ssl
from .steps.update_aes_key import t_e_s_t_update_aes_key
from .steps.unauthorized_access import t_e_s_t_unauthorized_access
from .steps.case_management_start import t_e_s_t_case_management_start
from .steps.case_management import t_e_s_t_case_management
from .steps.partners import t_e_s_t_partners
from .steps.error_pages import t_e_s_t_error_pages


"""
This testing module test all routes. It launch start the server and test all the routes and processes
We allocated all in one massive test because separating them in different test functions load 
the environment processes multiple times and crash FormShare.
   
"""


class FunctionalTests(unittest.TestCase):
    def setUp(self):
        if os.environ.get("FORMSHARE_PYTEST_RUNNING", "false") == "false":
            raise ValueError(
                "Environment variable FORMSHARE_PYTEST_RUNNING must be true. "
                "Do 'export FORMSHARE_PYTEST_RUNNING=true' before running PyTest"
            )
        config_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), *["test_config.json"]
        )
        with open(config_file) as json_file:
            server_config = json.load(json_file)

        from formshare import main

        from pathlib import Path

        home = str(Path.home())

        paths2 = ["formshare_pytest"]
        working_dir = os.path.join(home, *paths2)
        if not os.path.exists(working_dir):
            os.makedirs(working_dir)

        app = main(None, **server_config)
        from webtest import TestApp

        self.testapp = TestApp(app)
        self.randonLogin = ""
        self.randonLoginPartner = ""
        self.randonLoginKey = ""
        self.randonLoginSecret = ""
        self.server_config = server_config
        self.collaboratorLogin = ""
        self.project = ""
        self.projectID = ""
        self.assistantLogin = ""
        self.assistantLogin2 = ""
        self.assistantLoginKey = ""
        self.caseassistantLoginKey = ""
        self.assistantGroupID = ""
        self.formID = ""
        self.formID2 = ""
        self.formMultiLanguageID = ""
        self.path = os.path.dirname(os.path.abspath(__file__))
        self.working_dir = working_dir
        self.partner = ""
        self.case_project_id = ""
        self.product_id = ""

        self.test_object = SimpleNamespace()
        self.test_object.testapp = TestApp(app)
        self.test_object.randonLogin = ""
        self.test_object.randonLoginPartner = ""
        self.test_object.randonLoginKey = ""
        self.test_object.randonLoginSecret = ""
        self.test_object.server_config = server_config
        self.test_object.collaboratorLogin = ""
        self.test_object.project = ""
        self.test_object.projectID = ""
        self.test_object.assistantLogin = ""
        self.test_object.assistantLogin2 = ""
        self.test_object.assistantLoginKey = ""
        self.test_object.caseassistantLoginKey = ""
        self.test_object.assistantGroupID = ""
        self.test_object.formID = ""
        self.test_object.formID2 = ""
        self.test_object.formMultiLanguageID = ""
        self.test_object.path = os.path.dirname(os.path.abspath(__file__))
        self.test_object.working_dir = working_dir
        self.test_object.partner = ""
        self.test_object.case_project_id = ""
        self.test_object.product_id = ""

    def test_all(self):
        pkg_resources.require("formshare")
        print("Testing Root")
        t_e_s_t_root(self.test_object)
        print("Testing login")
        t_e_s_t_login(self.test_object)
        print("Testing dashboard")
        t_e_s_t_dashboard(self.test_object)
        print("Test profile")
        t_e_s_t_profile(self.test_object)
        print("Test projects")
        t_e_s_t_projects(self.test_object)
        print("Test collaborators")
        t_e_s_t_collaborators(self.test_object)
        print("Test assisstants")
        t_e_s_t_assistants(self.test_object)
        print("Test assistants groups")
        t_e_s_t_assistant_groups(self.test_object)
        print("Test Forms")
        t_e_s_t_forms(self.test_object)
        print("Testing multilanguage ODK")
        t_e_s_t_multilanguage_odk(self.test_object)
        print("Testing support zip files")
        t_e_s_t_support_zip_file(self.test_object)
        print("Testing external selects")
        t_e_s_t_external_select(self.test_object)
        print("Testing update form missing files")
        t_e_s_t_update_form_missing_files(self.test_object)
        print("Test ODK")
        t_e_s_t_odk(self.test_object)
        print("Testing repository")
        t_e_s_t_repository(self.test_object)
        print("Test repository downloads")
        t_e_s_t_repository_downloads(self.test_object)
        print("Test import data")
        t_e_s_t_import_data(self.test_object)
        print("Test repository tasks")
        t_e_s_t_repository_tasks(self.test_object)
        print("Test assistant access")
        t_e_s_t_assistant_access(self.test_object)
        print("Test JSON logs")
        t_e_s_t_json_logs(self.test_object)
        print("Test JSON logs 2")
        t_e_s_t_json_logs_2(self.test_object)
        print("Test JSON logs 4")
        t_e_s_t_json_logs_4(self.test_object)
        print("Test JSON logs 3")
        t_e_s_t_json_logs_3(self.test_object)
        print("Test clean interface")
        t_e_s_t_clean_interface(self.test_object)
        print("Test clean interface unauthorized")
        t_e_s_t_clean_interface_unauthorized(self.test_object)
        print("Test audit")
        t_e_s_t_audit(self.test_object)
        print("Test collaborator Access")
        t_e_s_t_collaborator_access(self.test_object)
        print("Test helpers")
        t_e_s_t_helpers()
        print("Test utility functions")
        t_e_s_t_utility_functions()
        print("Test avatar generator")
        t_e_s_t_avatar_generator()
        print("Test color hash hex")
        t_e_s_t_color_hash_hex()
        print("Test one user assistant")
        t_e_s_t_one_user_assistant(self.test_object)
        print("Test five collaborators")
        t_e_s_t_five_collaborators(self.test_object)
        print("Test form_merge_start")
        t_e_s_t_form_merge_start(self.test_object)
        print("Test form merge check errors")
        t_e_s_t_form_merge_check_errors(self.test_object)
        print("Test form merge delete")
        t_e_s_t_form_merge_delete(self.test_object)
        print("Test form merge")
        t_e_s_t_form_merge(self.test_object)
        print("Test Form Merge Mimic")
        t_e_s_t_form_merge_mimic(self.test_object)
        print("Test Form Merge Mimic 2")
        t_e_s_t_form_merge_mimic_2(self.test_object)
        print("Test Form Merge Mimic 3")
        t_e_s_t_form_merge_mimic_3(self.test_object)
        print("Test Form Merge Language Control")
        t_e_s_t_form_merge_language_control(self.test_object)
        print("Test Form Merge Language Control 2")
        t_e_s_t_form_merge_language_control_2(self.test_object)
        print("Test Form Merge Language Control 3")
        t_e_s_t_form_merge_language_control_3(self.test_object)
        print("Test Form Merge Language Control 4")
        t_e_s_t_form_merge_language_control_4(self.test_object)
        print("Test Form Merge Language Control 5")
        t_e_s_t_form_merge_language_control_5(self.test_object)
        print("Test Group Assistant")
        t_e_s_t_group_assistant(self.test_object)
        print("Test Delete Form With Repository")
        t_e_s_t_delete_form_with_repository(self.test_object)
        print("Test API")
        t_e_s_t_api(self.test_object)
        print("Test utility functions")
        t_e_s_t_plugin_utility_functions(self.test_object)
        print("Test collaborator projects")
        t_e_s_t_collaborator_projects(self.test_object)
        print("Test collaborator projects 2")
        t_e_s_t_collaborator_projects_2(self.test_object)
        print("Test collaborator projects 3")
        t_e_s_t_collaborator_projects_3(self.test_object)
        print("Test collaborator projects 4")
        t_e_s_t_collaborator_projects_4(self.test_object)
        print("Test delete active project")
        t_e_s_t_delete_active_project(self.test_object)
        print("Test Form Access")
        t_e_s_t_form_access(self.test_object)
        print("Test Super User")
        t_e_s_t_create_super_user()
        print("Test configure alembic")
        t_e_s_t_configure_alembic()
        print("Test configure fluent")
        t_e_s_t_configure_fluent()
        print("Test configure mysql")
        t_e_s_t_configure_mysql()
        print("Test Configure Tests")
        t_e_s_t_configure_t_e_s_t_s()
        print("Test modify config")
        t_e_s_t_modify_config()
        print("Test disable SSL")
        t_e_s_t_disable_ssl()
        print("Test Update AES Key")
        t_e_s_t_update_aes_key()
        print("Test Unauthorized Access")
        t_e_s_t_unauthorized_access(self.test_object)
        print("Test case management start")
        t_e_s_t_case_management_start(self.test_object)
        print("Test case management")
        t_e_s_t_case_management(self.test_object)
        print("Test partners")
        t_e_s_t_partners(self.test_object)
        print("Test error pages")
        t_e_s_t_error_pages(self.test_object)

        def show_health():
            res = self.testapp.get("/health", status=200)
            print("*****************Final health")
            print(res.body)
            print("*****************Final health")

        start_time = datetime.datetime.now()

        # print("Testing root")
        # test_root()
        # print("Test dashboard")
        # test_dashboard()
        # print("Testing profile")
        # test_profile()
        # print("Testing projects")
        # test_projects()
        # print("Testing collaborators")
        # test_collaborators()
        # print("Testing assistants")
        # test_assistants()
        # print("Testing assistants groups")
        # test_assistant_groups()
        # print("Testing forms")
        # test_forms()
        # print("Testing ODK")
        # test_odk()
        # print("Testing Multilanguage ODK")
        # test_multilanguage_odk()
        # print("Testing Support for ZIP files")
        # test_support_zip_file()
        # print("Testing external selects")
        # test_external_select()
        # print("Testing missing files")
        # test_update_form_missing_files()
        # print("Testing repository")
        # test_repository()
        # print("Testing repository downloads")
        # test_repository_downloads()
        # print("Testing partners")
        # test_partners()
        # time.sleep(60)
        # print("Testing data import")
        # test_import_data()
        # print("Testing assistant access")
        # test_assistant_access()
        # print("Testing logs 1")
        # test_json_logs()
        # print("Testing logs 2")
        # test_json_logs_2()
        # print("Testing logs 3")
        # test_json_logs_3()
        # print("Testing logs 4")
        # test_json_logs_4()
        # print("Testing cleaning interface")
        # test_clean_interface()
        # print("Testing cleaning interface unauthorized")
        # test_clean_interface_unauthorized()
        # print("Testing audit")
        # test_audit()
        # print("Testing repository tasks")
        # test_repository_tasks()
        # print("Testing collaborator access")
        # test_collaborator_access()
        # print("Testing helpers")
        # test_helpers()
        # print("Testing utility functions")
        # test_utility_functions()
        # print("Testing avatar generator")
        # test_avatar_generator()
        # print("Testing colo generator")
        # test_color_hash_hex()
        # print("Testing use assistant")
        # test_one_user_assistant()
        # print("Testing five collaborators")
        # test_five_collaborators()
        # print("Test form merge. Add head")
        # test_form_merge_start()
        # print("Test form merge erros")
        # test_form_merge_check_errors()
        # print("Testing merge then delete")
        # test_form_merge_delete()
        # print("Testing merge")
        # test_form_merge()
        # print("Testing merge code 1")
        # test_form_merge_mimic()
        # print("Testing merge code 2")
        # test_form_merge_mimic2()
        # print("Testing merge code 3")
        # test_form_merge_mimic3()
        # print("Print test merge multi-language")
        # test_form_merge_language_control()
        # print("Print test merge multi-language. Case 2")
        # test_form_merge_language_control_2()
        # print("Print test merge multi-language. Case 3")
        # test_form_merge_language_control_3()
        # print("Print test merge multi-language. Case 4")
        # test_form_merge_language_control_4()
        # print("Print test merge multi-language. Case 5")
        # test_form_merge_language_control_5()
        # print("Testing case management - head")
        # test_case_management_start()
        # print("Testing case management")
        # test_case_management()
        # print("Testing assistant group access")
        # test_group_assistant()
        # print("Testing Delete form with repository")
        # test_delete_form_with_repository()
        # print("Testing API")
        # test_api()
        # print("Testing plugin functions")
        # test_plugin_utility_functions()
        # print("Testing Collaborator access to project 1")
        # test_collaborator_projects()
        # print("Testing Collaborator access to project 2")
        # test_collaborator_projects_2()
        # print("Testing Collaborator access to project 3")
        # test_collaborator_projects_3()
        # print("Testing Collaborator access to project 3")
        # test_collaborator_projects_4()
        # print("Testing delete active project")
        # test_delete_active_project()
        # print("Testing access to form")
        # test_form_access()
        # print("Testing unauthorized access")
        # test_unauthorized_access()
        # print("Testing create super user")
        # test_create_super_user()
        # print("Testing configure alembic")
        # test_configure_alembic()
        # print("Testing configure fluent")
        # test_configure_fluent()
        # print("Testing configire mysql")
        # test_configure_mysql()
        # print("Testing configure tests")
        # test_configure_tests()
        # print("Testing modify config")
        # test_modify_config()
        # print("Testing disable ssl")
        # test_disable_ssl()
        # print("Testing update aes key")
        # test_update_aes_key()
        # print("Testing error pages")
        # test_error_pages()

        show_health()
        end_time = datetime.datetime.now()
        time_delta = end_time - start_time
        total_seconds = time_delta.total_seconds()
        minutes = total_seconds / 60
        print("Finished in {} minutes".format(minutes))
