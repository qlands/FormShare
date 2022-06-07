import datetime
import json
import os
import time
import unittest
from types import SimpleNamespace

import pkg_resources

from .steps.api import t_e_s_t_api
from .steps.assistant_access import t_e_s_t_assistant_access
from .steps.assistant_groups import t_e_s_t_assistant_groups
from .steps.assistants import t_e_s_t_assistants
from .steps.audit import t_e_s_t_audit
from .steps.avatar_generator import t_e_s_t_avatar_generator
from .steps.case_management import t_e_s_t_case_management
from .steps.case_management_start import t_e_s_t_case_management_start
from .steps.clean_interface import t_e_s_t_clean_interface
from .steps.clean_interface_unauthorized import t_e_s_t_clean_interface_unauthorized
from .steps.collaborator_access import t_e_s_t_collaborator_access
from .steps.collaborator_projects import t_e_s_t_collaborator_projects
from .steps.collaborator_projects_2 import t_e_s_t_collaborator_projects_2
from .steps.collaborator_projects_3 import t_e_s_t_collaborator_projects_3
from .steps.collaborator_projects_4 import t_e_s_t_collaborator_projects_4
from .steps.collaborators import t_e_s_t_collaborators
from .steps.color_hash_hex import t_e_s_t_color_hash_hex
from .steps.configure_alembic import t_e_s_t_configure_alembic
from .steps.configure_fluent import t_e_s_t_configure_fluent
from .steps.configure_mysql import t_e_s_t_configure_mysql
from .steps.configure_t_e_s_t_s import t_e_s_t_configure_t_e_s_t_s
from .steps.create_super_user import t_e_s_t_create_super_user
from .steps.crowdsourcing import t_e_s_t_crowdsourcing
from .steps.dashboard import t_e_s_t_dashboard
from .steps.delete_active_project import t_e_s_t_delete_active_project
from .steps.delete_form_with_repository import t_e_s_t_delete_form_with_repository
from .steps.disable_ssl import t_e_s_t_disable_ssl
from .steps.error_pages import t_e_s_t_error_pages
from .steps.external_select import t_e_s_t_external_select
from .steps.five_collaborators import t_e_s_t_five_collaborators
from .steps.form_access import t_e_s_t_form_access
from .steps.form_merge import t_e_s_t_form_merge
from .steps.form_merge_check_errors import t_e_s_t_form_merge_check_errors
from .steps.form_merge_delete import t_e_s_t_form_merge_delete
from .steps.form_merge_language_control import t_e_s_t_form_merge_language_control
from .steps.form_merge_language_control_2 import t_e_s_t_form_merge_language_control_2
from .steps.form_merge_language_control_3 import t_e_s_t_form_merge_language_control_3
from .steps.form_merge_language_control_4 import t_e_s_t_form_merge_language_control_4
from .steps.form_merge_language_control_5 import t_e_s_t_form_merge_language_control_5
from .steps.form_merge_mimic import t_e_s_t_form_merge_mimic
from .steps.form_merge_mimic_2 import t_e_s_t_form_merge_mimic_2
from .steps.form_merge_mimic_3 import t_e_s_t_form_merge_mimic_3
from .steps.form_merge_start import t_e_s_t_form_merge_start
from .steps.forms import t_e_s_t_forms
from .steps.group_assistant import t_e_s_t_group_assistant
from .steps.helpers import t_e_s_t_helpers
from .steps.import_data import t_e_s_t_import_data
from .steps.json_logs import t_e_s_t_json_logs
from .steps.json_logs_2 import t_e_s_t_json_logs_2
from .steps.json_logs_3 import t_e_s_t_json_logs_3
from .steps.json_logs_4 import t_e_s_t_json_logs_4
from .steps.login import t_e_s_t_login
from .steps.modify_config import t_e_s_t_modify_config
from .steps.multilanguage_odk import t_e_s_t_multilanguage_odk
from .steps.odk import t_e_s_t_odk
from .steps.one_user_assistant import t_e_s_t_one_user_assistant
from .steps.partners import t_e_s_t_partners
from .steps.plugin_utility_functions import t_e_s_t_plugin_utility_functions
from .steps.profile import t_e_s_t_profile
from .steps.projects import t_e_s_t_projects
from .steps.repository import t_e_s_t_repository
from .steps.repository_downloads import t_e_s_t_repository_downloads
from .steps.repository_tasks import t_e_s_t_repository_tasks
from .steps.root import t_e_s_t_root
from .steps.support_zip_file import t_e_s_t_support_zip_file
from .steps.unauthorized_access import t_e_s_t_unauthorized_access
from .steps.update_aes_key import t_e_s_t_update_aes_key
from .steps.update_form_missing_files import t_e_s_t_update_form_missing_files
from .steps.utility_functions import t_e_s_t_utility_functions

"""
This testing module test all routes. It launch start the server and test all the routes and processes
We allocated all in one testing function because separating them in different test functions load 
the environment processes multiple times and crash FormShare.

Before running this test you need to do:
    'export FORMSHARE_PYTEST_RUNNING=true' before running PyTest
before running pytest or start_local_celery

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

        self.test_object = SimpleNamespace()
        self.test_object.testapp = TestApp(app)
        self.test_object.root = self
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

        def show_health():
            res = self.test_object.testapp.get("/health", status=200)
            print("*****************Final health")
            print(res.body)
            print("*****************Final health")

        start_time = datetime.datetime.now()

        print("Testing root")
        t_e_s_t_root(self.test_object)
        print("Testing login")
        t_e_s_t_login(self.test_object)
        print("Test dashboard")
        t_e_s_t_dashboard(self.test_object)
        print("Testing profile")
        t_e_s_t_profile(self.test_object)
        print("Testing projects")
        t_e_s_t_projects(self.test_object)
        print("Testing collaborators")
        t_e_s_t_collaborators(self.test_object)
        print("Testing assistants")
        t_e_s_t_assistants(self.test_object)
        print("Testing assistants groups")
        t_e_s_t_assistant_groups(self.test_object)
        print("Testing forms")
        t_e_s_t_forms(self.test_object)
        print("Testing ODK")
        t_e_s_t_odk(self.test_object)
        print("Testing Multilanguage ODK")
        t_e_s_t_multilanguage_odk(self.test_object)
        print("Testing Support for ZIP files")
        t_e_s_t_support_zip_file(self.test_object)
        print("Testing external selects")
        t_e_s_t_external_select(self.test_object)
        print("Testing missing files")
        t_e_s_t_update_form_missing_files(self.test_object)
        print("Testing repository")
        t_e_s_t_repository(self.test_object)
        print("Testing repository downloads")
        t_e_s_t_repository_downloads(self.test_object)
        print("Testing partners")
        t_e_s_t_partners(self.test_object)
        time.sleep(60)
        print("Testing data import")
        t_e_s_t_import_data(self.test_object)
        print("Testing assistant access")
        t_e_s_t_assistant_access(self.test_object)
        print("Testing logs 1")
        t_e_s_t_json_logs(self.test_object)
        print("Testing logs 2")
        t_e_s_t_json_logs_2(self.test_object)
        print("Testing logs 3")
        t_e_s_t_json_logs_3(self.test_object)
        print("Testing logs 4")
        t_e_s_t_json_logs_4(self.test_object)
        print("Testing cleaning interface")
        t_e_s_t_clean_interface(self.test_object)
        print("Testing cleaning interface unauthorized")
        t_e_s_t_clean_interface_unauthorized(self.test_object)
        print("Testing audit")
        t_e_s_t_audit(self.test_object)
        print("Testing repository tasks")
        t_e_s_t_repository_tasks(self.test_object)
        print("Testing collaborator access")
        t_e_s_t_collaborator_access(self.test_object)
        print("Testing helpers")
        t_e_s_t_helpers()
        print("Testing utility functions")
        t_e_s_t_utility_functions()
        print("Testing avatar generator")
        t_e_s_t_avatar_generator()
        print("Testing colo generator")
        t_e_s_t_color_hash_hex()
        print("Testing use assistant")
        t_e_s_t_one_user_assistant(self.test_object)
        print("Testing five collaborators")
        t_e_s_t_five_collaborators(self.test_object)
        print("Test form merge. Add head")
        t_e_s_t_form_merge_start(self.test_object)
        print("Test form merge erros")
        t_e_s_t_form_merge_check_errors(self.test_object)
        print("Testing merge then delete")
        t_e_s_t_form_merge_delete(self.test_object)
        print("Testing merge")
        t_e_s_t_form_merge(self.test_object)
        print("Testing merge code 1")
        t_e_s_t_form_merge_mimic(self.test_object)
        print("Testing merge code 2")
        t_e_s_t_form_merge_mimic_2(self.test_object)
        print("Testing merge code 3")
        t_e_s_t_form_merge_mimic_3(self.test_object)
        print("Print test merge multi-language")
        t_e_s_t_form_merge_language_control(self.test_object)
        print("Print test merge multi-language. Case 2")
        t_e_s_t_form_merge_language_control_2(self.test_object)
        print("Print test merge multi-language. Case 3")
        t_e_s_t_form_merge_language_control_3(self.test_object)
        print("Print test merge multi-language. Case 4")
        t_e_s_t_form_merge_language_control_4(self.test_object)
        print("Print test merge multi-language. Case 5")
        t_e_s_t_form_merge_language_control_5(self.test_object)
        print("Testing case management - head")
        t_e_s_t_case_management_start(self.test_object)
        print("Testing case management")
        t_e_s_t_case_management(self.test_object)
        print("Testing assistant group access")
        t_e_s_t_group_assistant(self.test_object)
        print("Testing Delete form with repository")
        t_e_s_t_delete_form_with_repository(self.test_object)
        print("Testing API")
        t_e_s_t_api(self.test_object)
        print("Testing plugin functions")
        t_e_s_t_plugin_utility_functions(self.test_object)
        print("Testing Collaborator access to project 1")
        t_e_s_t_collaborator_projects(self.test_object)
        print("Testing Collaborator access to project 2")
        t_e_s_t_collaborator_projects_2(self.test_object)
        print("Testing Collaborator access to project 3")
        t_e_s_t_collaborator_projects_3(self.test_object)
        print("Testing Collaborator access to project 3")
        t_e_s_t_collaborator_projects_4(self.test_object)
        print("Testing delete active project")
        t_e_s_t_delete_active_project(self.test_object)
        print("Testing access to form")
        t_e_s_t_form_access(self.test_object)
        print("Testing unauthorized access")
        t_e_s_t_unauthorized_access(self.test_object)
        print("Testing create super user")
        t_e_s_t_create_super_user()
        print("Testing configure alembic")
        t_e_s_t_configure_alembic()
        print("Testing configure fluent")
        t_e_s_t_configure_fluent()
        print("Testing configire mysql")
        t_e_s_t_configure_mysql()
        print("Testing configure tests")
        t_e_s_t_configure_t_e_s_t_s()
        print("Testing modify config")
        t_e_s_t_modify_config()
        print("Testing disable ssl")
        t_e_s_t_disable_ssl()
        print("Testing update aes key")
        t_e_s_t_update_aes_key(self.test_object)
        print("Testing error pages")
        t_e_s_t_error_pages(self.test_object)
        print("Testing crowdsourcing")
        t_e_s_t_crowdsourcing(self.test_object)

        show_health()
        end_time = datetime.datetime.now()
        time_delta = end_time - start_time
        total_seconds = time_delta.total_seconds()
        minutes = total_seconds / 60
        print("Finished in {} minutes".format(minutes))
