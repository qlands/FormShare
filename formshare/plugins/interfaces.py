"""
This file declares the PCA interfaces available in FormShare and their methods.
"""


__all__ = [
    "Interface",
    "IRoutes",
    "IConfig",
    "IResource",
    "IPluginObserver",
    "IPluralize",
    "ISchema",
    "IDatabase",
    "IUserAuthentication",
    "ITemplateHelpers",
    "IProduct",
    "IImportExternalData",
    "IRepository",
    "IProject",
    "IForm",
    "ITranslation",
    "IRegistration",
    "IPublicView",
    "IPrivateView",
    "IAssistantView",
    "IPartnerView",
    "ILogOut",
    "IUserAuthorization",
    "IAPIRoutes",
    "IFormGroupAccess",
    "IAssistant",
    "IAssistantGroup",
    "IFormAccess",
    "IUser",
    "IEnvironment",
    "IXMLSubmission",
    "IMediaSubmission",
    "IJSONSubmission",
    "IPartner",
    "IPartnerAuthentication",
    "IExport",
]


from inspect import isclass

from pyutilib.component.core import Interface as _pca_Interface


class Interface(_pca_Interface):  # pragma: no cover
    """
    This code is based on CKAN
    :Copyright (C) 2007 Open Knowledge Foundation
    :license: AGPL V3, see LICENSE for more details.

    """

    @classmethod
    def provided_by(cls, instance):
        return cls.implemented_by(instance.__class__)

    @classmethod
    def implemented_by(cls, other):
        if not isclass(other):
            raise TypeError("Class expected", other)
        try:
            return cls in other._implements
        except AttributeError:
            return False


class IRoutes(Interface):  # pragma: no cover
    """
    Plugin into the creation of routes.

    """

    def before_mapping(self, config):
        """
        Called before the mapping of routes made by FormShare.

        :param config: ``pyramid.config`` object
        :return Returns a dict array [{'name':'myroute','path':'/myroute','view',viewDefinition,
                                       'renderer':'renderere_used'}]
        """
        raise NotImplementedError("before_mapping must be implemented in subclasses")

    def after_mapping(self, config):
        """
        Called after the mapping of routes made by FormShare.

        :param config: ``pyramid.config`` object
        :return Returns a dict array [{'name':'myroute','path':'/myroute','view',viewDefinition,
                                       'renderer':'renderere_used'}]
        """
        raise NotImplementedError("after_mapping must be implemented in subclasses")


class IAPIRoutes(Interface):  # pragma: no cover
    """
    Plugin into the creation of API routes.

    """

    def before_mapping(self, config):
        """
        Called before the mapping of API routes made by FormShare.

        :param config: ``pyramid.config`` object
        :return Returns a dict array [{'name':'myroute','path':'/myroute','view',viewDefinition,
                                       'renderer':'renderere_used'}]
        """
        raise NotImplementedError("before_mapping must be implemented in subclasses")

    def after_mapping(self, config):
        """
        Called after the mapping of API routes made by FormShare.

        :param config: ``pyramid.config`` object
        :return Returns a dict array [{'name':'myroute','path':'/myroute','view',viewDefinition,
                                       'renderer':'renderere_used'}]
        """
        raise NotImplementedError("after_mapping must be implemented in subclasses")


class IConfig(Interface):  # pragma: no cover
    """
    Allows the modification of the Pyramid config. For example to add new templates or static directories
    """

    def update_config(self, config):
        """
        Called by FormShare during the initialization of the environment

        :param config: ``pyramid.config`` object
        """


class IResource(Interface):  # pragma: no cover
    """
    Allows to hook into the creation of JS and CSS libraries or resources
    """

    def add_libraries(self, config):
        """
        Called by FormShare so plugins can add new JS and CSS libraries to FormShare

        :param config: ``pyramid.config`` object
        :return Returns a dict array [{'name':'mylibrary','path':'/path/to/my/resources'}]
        """
        raise NotImplementedError("add_libraries must be implemented in subclasses")

    def add_js_resources(self, config):
        """
        Called by FormShare so plugins can add new JS Resources

        :param config: ``pyramid.config`` object
        :return Returns a dict array [{'libraryname':'mylibrary','id':'myResourceID','file':'/relative/path/to/jsFile',
                                      'depends':'resourceID'}]
        """
        raise NotImplementedError("add_js_resources must be implemented in subclasses")

    def add_css_resources(self, config):
        """
        Called by FormShare so plugins can add new FanStatic CSS Resources

        :param config: ``pyramid.config`` object
        :return Returns a dict array [{'libraryname':'mylibrary','id':'myResourceID','file':'/relative/path/to/jsFile',
                                      'depends':'resourceID'}]
        """
        raise NotImplementedError("add_css_resources must be implemented in subclasses")


class IPluralize(Interface):  # pragma: no cover
    """
    Allows to hook into the pluralization function so plugins can extend the pluralization of FormShare
    """

    def pluralize(self, noun, locale):
        """
        Called the packages are created

        :param noun: ``Noun to be pluralized``
        :param locale: ``The current locate code e.g. en``
        :return the noun in plural form
        """


class ISchema(Interface):  # pragma: no cover
    """
    Allows to hook into the schema layer and add new fields into it.
    The schema is a layer on top of the database schema so plugin developers can
    add new fields to FormShare tables without affecting the structure
    of the database. New fields are stored in extra as JSON keys
    """

    def update_schema(self, config):
        """
        Called by FormShare so plugins can add new fields to table schemata

        :param config: ``pyramid.config`` object
        :return Returns a dict array [{'schema':'schema_to_update','fieldname':'myfield',
                                       'fielddesc':'A good description of myfield'}]

        Plugin writers should use the utility functions:
            - addFieldToUserSchema
            - addFieldToProjectSchema
            - addFieldToEnumeratorSchema
            - addFieldToEnumeratorGroupSchema
            - addFieldToDataUserSchema
            - addFieldToDataGroupSchema
            - addFieldToFormSchema


        Instead of constructing the dict by themselves to ensure API compatibility

        """
        raise NotImplementedError("update_schema must be implemented in subclasses")


class IDatabase(Interface):  # pragma: no cover
    """
    Allows to hook into the database schema so plugins can add new tables
    After calling this
    """

    def update_orm(self, config):
        """
        Called by FormShare so plugins can add new tables to FormShare ORM

        :param metadata: FormShare ORM metadata object

        """

    def update_extendable_tables(self, tables_allowed):
        """
        Allow to add new tables to the list of tables allowed to have a flexible schema using extras
        :param tables_allowed: "Current list of tables allowed"
        :return: Must return a modified version of tables_allowed
        """
        raise NotImplementedError(
            "update_extendable_tables must be implemented in subclasses"
        )

    def update_extendable_modules(self, modules_allowed):
        """
        Allow to add new tables to the list of tables modules for the schema to filter
        :param modules_allowed: "Current list of tables allowed"
        :return: Must return a modified version of modules_allowed
        """
        raise NotImplementedError(
            "update_extendable_modules must be implemented in subclasses"
        )


class IProject(Interface):  # pragma: no cover
    """
    Allows to hook into the processes that create, update and delete projects
    """

    def before_create(self, request, user, project_data):
        """
        Called by FormShare so plugins can perform actions before adding a project
        :param request: ``pyramid.request`` object
        :param user: User owner of the project
        :param project_data: project data
        :return: Return a modified version of project_data, true or false if the project should be added. If False then
        a message should state why. Example: return project_data, False, "My message"
        """
        raise NotImplementedError("before_create must be implemented in subclasses")

    def after_create(self, request, user, project_data):
        """
        Called by FormShare so plugins can perform actions before adding a project
        :param request: ``pyramid.request`` object
        :param user: User owner of the project
        :param project_data: project data
        :return: None
        """
        raise NotImplementedError("after_create must be implemented in subclasses")


class IForm(Interface):  # pragma: no cover
    """
    Allows to hook into the processes that create, update and delete forms
    """

    def after_odk_form_checks(
        self,
        request,
        user,
        project,
        form,
        form_data,
        form_directory,
        survey_file,
        create_file,
        insert_file,
        itemsets_csv,
    ):
        """
        Called by FormShare so plugins can perform actions after FormShare checks a ODK form
        :param request: ``pyramid.request`` object
        :param user: User owner of the project
        :param project: Project id
        :param form: Form ID coming from the ODK XLS Form
        :param form_data: For data coming from the interface
        :param form_directory: Directory where the form will be stored
        :param survey_file: Path to the JSON representation of the form in temporary directory
        :param create_file: Path to the create.xml file of the form generated by JXFormToMySQL in temporary directory
        :param insert_file: Path to the insert.xml file of the form generated by JXFormToMySQL in temporary directory
        :param itemsets_csv: Path to the itemsets_csv file in temporary directory. None if no file
        :return: True, "" or False, Message
        """

    def before_adding_form(
        self, request, form_type, user_id, project_id, form_id, form_data
    ):
        """
        Called by FormShare so plugins can perform actions before FormShare adds the form to the database
        :param request: ``pyramid.request`` object
        :param form_type: Type of form: ODK, CSPRO, etc
        :param user_id: User ID
        :param project_id: Project id
        :param form_id: Form ID
        :param form_data: Form data to be added to the database
        :return: True, "", modified version of data or False, Message, None
        """

    def after_adding_form(
        self, request, form_type, user_id, project_id, form_id, form_data
    ):
        """
        Called by FormShare so plugins can perform actions after FormShare adds the form to the database
        :param request: ``pyramid.request`` object
        :param form_type: Type of form: ODK, CSPRO, etc
        :param user_id: User id
        :param project_id: Project id
        :param form_id: Form ID
        :param form_data: Form data to be added to the database
        :return: None
        """

    def before_updating_form(
        self, request, form_type, user_id, project_id, form_id, form_data
    ):
        """
        Called by FormShare so plugins can perform actions before FormShare updates a form in the database
        :param request: ``pyramid.request`` object
        :param form_type: Type of form: ODK, CSPRO, etc
        :param user_id: User ID
        :param project_id: Project id
        :param form_id: Form ID
        :param form_data: Form data to be added to the database
        :return: True, "", modified version of data or False, Message, None
        """

    def after_updating_form(
        self, request, form_type, user_id, project_id, form_id, form_data
    ):
        """
        Called by FormShare so plugins can perform actions after FormShare adds the form to the database
        :param request: ``pyramid.request`` object
        :param form_type: Type of form: ODK, CSPRO, etc
        :param user_id: User id
        :param project_id: Project id
        :param form_id: Form ID
        :param form_data: Form data to be added to the database
        :return: None
        """

    def before_deleting_form(self, request, form_type, user_id, project_id, form_id):
        """
        Called by FormShare so plugins can perform actions before FormShare deletes a form from the database
        :param request: ``pyramid.request`` object
        :param form_type: Type of form: ODK, CSPRO, etc
        :param user_id: User ID
        :param project_id: Project id
        :param form_id: Form ID
        :return: True, "", or False, Message
        """

    def after_deleting_form(self, request, form_type, user_id, project_id, form_id):
        """
        Called by FormShare so plugins can perform actions after FormShare deletes a form from the database
        :param request: ``pyramid.request`` object
        :param form_type: Type of form: ODK, CSPRO, etc
        :param user_id: User ID
        :param project_id: Project id
        :param form_id: Form ID
        :return: None
        """


class IRegistration(Interface):  # pragma: no cover
    """
    Allows to hook into the user registration
    """

    def before_register(self, request, registrant):
        """
        Called by FormShare so plugins can do something before registering a user

        :param request: ``pyramid.request`` object
        :param registrant: Dictionary containing the details of the registrant
        :return Return a modified version of registrant, true or false if the registrant should be added. If False then
        a message should state why

        """
        raise NotImplementedError("before_register must be implemented in subclasses")

    def after_register(self, request, registrant):
        """
        Called by FormShare so plugins do something after registering a user

        :param request: ``pyramid.request`` object
        :param registrant: Dictionary containing the details of the registrant
        :return Return the next page that will be loaded after the registration. If empty or None the the Formshare
        dashboard will be loaded

        """
        raise NotImplementedError(
            "on_authenticate_user must be implemented in subclasses"
        )


class IUserAuthentication(Interface):  # pragma: no cover
    """
    Allows to hook into the user authentication
    """

    def after_login(self, request, user):
        """
        Called by FormShare so plugins can modify the login of users

        :param request: ``pyramid.request`` object
        :param user: user object
        :return Return true or false if the login should continue. If False then a message should state why

        """
        raise NotImplementedError("after_login must be implemented in subclasses")

    def on_authenticate_user(self, request, user_id, user_is_email):
        """
        Called by FormShare so plugins can modify the way FormShare gather information about the user

        :param request: ``pyramid.request`` object
        :param user_id: The user ID trying to authenticate
        :param user_is_email: Whether the user is an email
        :return Return None and and empty Dict to indicate that Forshare should get this in the normal way.
                False and None if the user must be denied.
                Otherwise true and then the Dict MUST contain at least the following keys:
                user_id : With the same userID authenticating
                user_email : With the email of the userID authenticating
                user_name : With the full name of the userID authenticating
                user_about : With the bio data of the userID authenticating or None
        """
        raise NotImplementedError(
            "on_authenticate_user must be implemented in subclasses"
        )

    def on_authenticate_password(self, request, user_data, password):
        """
        Called by FormShare so plugins can modify the way FormShare gather information about the user

        :param request: ``pyramid.request`` object
        :param user_data: The user data
        :param password: The password as is typed in the FormShare interface
        :return Return None, None to indicate that Forshare should get this in the normal way.
                False,"Message why" if the password is not correct.
                Otherwise True, ""
        """
        raise NotImplementedError(
            "on_authenticate_password must be implemented in subclasses"
        )

    def after_collaborator_login(self, request, collaborator):
        """
        Called by FormShare so plugins can modify the login of assistants
        :param request: ``pyramid.request`` object
        :param collaborator: Assistant ID
        :return: True, "" or False, "Why"
        """
        raise NotImplementedError(
            "after_collaborator_login must be implemented in subclasses"
        )


class IPartnerAuthentication(Interface):  # pragma: no cover
    """
    Allows to hook into the partner authentication
    """

    def after_partner_login(self, request, partner):
        """
        Called by FormShare so plugins can modify the login of assistants
        :param request: ``pyramid.request`` object
        :param partner: Partner email
        :return: True, "" or False, "Why"
        """
        raise NotImplementedError(
            "after_collaborator_login must be implemented in subclasses"
        )


class IUserAuthorization(Interface):  # pragma: no cover
    """
    Allows to hook into the user authorization.
    """

    def before_check_authorization(self, request):
        """
        Called by FormShare so plugins can modify the normal authorization of users

        :param request: ``pyramid.request`` object
        :return Return true or false if FormShare should check the authorization of a user.

        """
        raise NotImplementedError(
            "before_check_authorization must be implemented in subclasses"
        )

    def custom_authorization(self, request):
        """
        Called by FormShare so plugins can perform their own way of authorizing a user.
        :param request:
        :return: True, Authorized user name or False, ""
        """
        raise NotImplementedError(
            "custom_authorization must be implemented in subclasses"
        )


class ITemplateHelpers(Interface):  # pragma: no cover
    """
    Add custom template helper functions.

    By implementing this plugin interface plugins can provide their own
    template helper functions, which custom templates can then access via the
    ``request.h`` variable.
    """

    def get_helpers(self):
        """
        Return a dict mapping names to helper functions.

        The keys of the dict should be the names with which the helper
        functions will be made available to templates, and the values should be
        the functions themselves. For example, a dict like:
        ``{'example_helper': example_helper}`` allows templates to access the
        ``example_helper`` function via ``request.h.example_helper()``.

        Function names should start with the name of the extension providing
        the function, to prevent name clashes between extensions.
        :return:
        """


class IProduct(Interface):  # pragma: no cover
    """
    Allows to hook into FormShare's Celery task manager.
    """

    def register_products(self, config):
        """
        Called by FormShare so plugins can add new products with Celery as task manager

        :param config: ``pyramid.config`` object
        :return Must returns a dict array [{'code':'productCode', 'hidden': False, 'icon':'fas fa-box-open',
        'metadata':{'key':value}}]
        """
        raise NotImplementedError("register_products must be implemented in subclasses")

    def get_product_description(self, request, product_code):
        """
        Called by FormShare to retrieve the description of a product. Connected plugins can use this to produce the
        description of the product in different languages
        :param request: Pyramid request object
        :param product_code: Product code
        :return: String/None. The description of the product otherwise None MUST be returned
        """
        raise NotImplementedError(
            "get_product_description must be implemented in subclasses"
        )

    def before_download_private_product(
        self, request, project, form, product, output, file_name, mime_type
    ):
        """
        Called before the a product gets downloaded. Must return true to indicate that the download should proceed.
        :param request: Pyramid request object
        :param project: Project ID
        :param form: Form ID
        :param product: Product ID
        :param output: Output ID
        :param file_name: File name
        :param mime_type: Mime type of the file name
        :return: True / False
        """
        raise NotImplementedError(
            "before_download_private_product must be implemented in subclasses"
        )

    def before_partner_download_private_product(
        self, request, partner, project, form, product, output, file_name, mime_type
    ):
        """
        Called before the a product gets downloaded. Must return true to indicate that the download should proceed.
        :param request: Pyramid request object
        :param partner: Partner ID
        :param project: Project ID
        :param form: Form ID
        :param product: Product ID
        :param output: Output ID
        :param file_name: File name
        :param mime_type: Mime type of the file name
        :return: True / False
        """
        raise NotImplementedError(
            "before_download_private_product must be implemented in subclasses"
        )

    def before_download_public_product(
        self, request, project, form, product, output, file_name, mime_type
    ):
        """
        Called before the a product gets downloaded. Must return true to indicate that the download should proceed.
        :param request: Pyramid request object
        :param project: Project ID
        :param form: Form ID
        :param product: Product ID
        :param output: Output ID
        :param file_name: File name
        :param mime_type: Mime type of the file name
        :return: True / False
        """
        raise NotImplementedError(
            "before_download_public_product must be implemented in subclasses"
        )

    def before_download_product_by_api(
        self, request, project, form, product, output, file_name, mime_type
    ):
        """
        Called before the a product gets downloaded. Must return true to indicate that the download should proceed.
        :param request: Pyramid request object
        :param project: Project ID
        :param form: Form ID
        :param product: Product ID
        :param output: Output ID
        :param file_name: File name
        :param mime_type: Mime type of the file name
        :return: True / False
        """
        raise NotImplementedError(
            "before_download_public_product must be implemented in subclasses"
        )

    def before_partner_download_product_by_api(
        self, request, partner, project, form, product, output, file_name, mime_type
    ):
        """
        Called before the a product gets downloaded. Must return true to indicate that the download should proceed.
        :param request: Pyramid request object
        :param project: Project ID
        :param partner: Partner ID
        :param form: Form ID
        :param product: Product ID
        :param output: Output ID
        :param file_name: File name
        :param mime_type: Mime type of the file name
        :return: True / False
        """
        raise NotImplementedError(
            "before_download_public_product must be implemented in subclasses"
        )


class IImportExternalData(Interface):  # pragma: no cover
    """
    Allows to create new data imports
    """

    def import_external_data(
        self,
        request,
        user,
        project,
        form,
        odk_dir,
        form_directory,
        schema,
        assistant,
        temp_dir,
        project_code,
        geopoint_variable,
        project_of_assistant,
        import_type,
        post_data,
        ignore_xform,
    ):
        """
        Called by FormShare so plugins can import new types of data into FormShare. You should do this as a
        product and use Celery to not hang a request in case the import process several files
        :param request: Pyramid request object
        :param user: FormShare user account ID
        :param project: FormShare project ID
        :param form: FormShare form ID
        :param odk_dir: Path to the ODK repository directory
        :param form_directory: Path to the directory of the form
        :param schema: Schema holding the data of the form
        :param assistant: Assistant ID importing the data
        :param temp_dir: Path to the files to be imported
        :param project_code: Project code
        :param geopoint_variable: Which variable should be used to pull the geo localtion
        :param project_of_assistant: Project ID of the assistant
        :param import_type: Type of import > 2
        :param post_data: Data from the import page
        :param ignore_xform: Whether to ignore the ignore_xform ID while importing
        :return: Next url formed with request.route_url()
        """
        raise NotImplementedError(
            "import_external_data must be implemented in subclasses"
        )


class IRepository(Interface):  # pragma: no cover
    """
    Allows to hook into FormShare's repository process.
    Please note that there is no "After creating repository", this is because the creation of the repository
    is runs in a background as a Celery task.
    """

    def before_creating_repository(
        self, request, user, project, form, cnf_file, create_file, insert_file, schema
    ):
        """
        Called before creating a repository so plugins can perform extra actions or overwrite the process
        :param request: Pyramid request object
        :param user: User ID
        :param project: Project ID
        :param form: Form ID
        :param cnf_file: MySQL CNF file
        :param create_file: Repository create SQL file
        :param insert_file: Repository insert SQL file
        :param schema: Schema to create
        :return: True if FormShare should continue creating the repository, otherwise return False
        """
        raise NotImplementedError(
            "before_creating_repository must be implemented in subclasses"
        )

    def on_creating_repository(self, request, user, project, form, task_id):
        """
        Called after FormShare tells Celery to create the repository
        :param request: Pyramid request object
        :param user: User ID
        :param project: Project ID
        :param form: Form ID
        :param task_id: Celery task ID creating the repository
        :return: None
        """
        raise NotImplementedError(
            "on_creating_repository must be implemented in subclasses"
        )

    def custom_repository_process(
        self,
        request,
        user,
        project,
        form,
        odk_dir,
        form_directory,
        schema,
        primary_key,
        cnf_file,
        create_file,
        insert_file,
        create_xml_file,
        repository_string,
    ):
        """
        Called after FormShare tells Celery to create the repository if before_creating_repository == True. You can
        use this to create your own version of the repository. You MUST use Celery to not block the request. The
        returned Celery task ID will be passed to on_creating_repository
        :param request: Pyramid request object
        :param user: User ID
        :param project: Project ID
        :param form: Form ID
        :param odk_dir: Path to the ODK dir in the repository
        :param form_directory: Directory of the form
        :param cnf_file: MySQL CNF file
        :param create_file: Repository create SQL file
        :param insert_file: Repository insert SQL file
        :param create_xml_file: Path to the create xml file
        :param schema: Schema to create
        :param primary_key: Primary key that should be used
        :param repository_string: Command executed by JXFomToMysql for traceability
        :return: Celery task ID
        """
        raise NotImplementedError(
            "custom_repository_process must be implemented in subclasses"
        )


class IPublicView(Interface):  # pragma: no cover
    """
    Allows to hook into FormShare's view public class.
    """

    def before_processing(self, request):
        """
        Called by FormShare's PublicView class before processing a public view
        :param request: Pyramid request object
        :return: None
        """
        raise NotImplementedError(
            "IPublicView before_processing must be implemented in subclasses"
        )

    def after_processing(self, request, context):
        """
        Called by FormShare's PublicView class after processing a public view but just before returning the context
        :param request: Pyramid request object
        :param context: Context of the view
        :return: A modified version of context
        """
        raise NotImplementedError(
            "IPublicView after_processing must be implemented in subclasses"
        )


class IPrivateView(Interface):  # pragma: no cover
    """
    Allows to hook into FormShare's private class.
    """

    def before_processing(self, route_name, request, class_data):
        """
        Called by FormShare's PrivateView class before processing a private view
        :param route_name: The name of the route
        :param request: Pyramid request object
        :param class_data: Class parameters as dict
        :return: None
        """
        raise NotImplementedError(
            "IPrivateView before_processing must be implemented in subclasses"
        )

    def after_processing(self, route_name, request, class_data, context):
        """
        Called by FormShare's PrivateView class after processing the dashboard view but just before returning the
        context
        :param route_name: The name of the route
        :param request: Pyramid request object
        :param class_data: Class parameters as dict
        :param context: Context of the view that will be returned to jinja2
        :return: A modified version of context
        """
        raise NotImplementedError(
            "IPrivateView after_processing must be implemented in subclasses"
        )


class IAssistantView(Interface):  # pragma: no cover
    """
    Allows to hook into FormShare's assistant class.
    """

    def before_processing_assistant_view(self, route_name, request, context):
        """
        Called by FormShare's AssistantView class before processing an assistant view
        :param route_name: The name of the route
        :param request: Pyramid request object
        :param context: Class context before processing the view
        :return: None
        """
        raise NotImplementedError(
            "IAssistantView before_processing_assistant_view must be implemented in subclasses"
        )

    def after_processing_assistant_view(self, route_name, request, context):
        """
        Called by FormShare's AssistantView class after processing the view but just before returning the
        context
        :param route_name: The name of the route
        :param request: Pyramid request object
        :param context: Context of the view that will be returned to jinja2
        :return: A modified version of context
        """
        raise NotImplementedError(
            "IAssistantView after_processing_assistant_view must be implemented in subclasses"
        )


class IPartnerView(Interface):  # pragma: no cover
    """
    Allows to hook into FormShare's partner class.
    """

    def before_processing_partner_view(self, route_name, request, context):
        """
        Called by FormShare's PartnerView class before processing a partner view
        :param route_name: The name of the route
        :param request: Pyramid request object
        :param context: Class context before processing the view
        :return: None
        """
        raise NotImplementedError(
            "IPrivateView before_processing_partner_view must be implemented in subclasses"
        )

    def after_processing_partner_view(self, route_name, request, context):
        """
        Called by FormShare's PartnerView class after processing the view but just before returning the
        context
        :param route_name: The name of the route
        :param request: Pyramid request object
        :param context: Context of the view that will be returned to jinja2
        :return: A modified version of context
        """
        raise NotImplementedError(
            "IPrivateView after_processing_partner_view must be implemented in subclasses"
        )


class ITranslation(Interface):  # pragma: no cover
    """
    Allows extensions to provide their own translation strings.
    """

    def get_translation_directory(self):
        """
        Called by FormShare so plugins can add a translation directory
        :return: String path to the translation directory
        """
        raise NotImplementedError(
            "translation_directory must be implemented in subclasses"
        )

    def get_translation_domain(self):
        """
        Called by FormShare so plugins can add a translation domain
        :return: String domain name
        """
        raise NotImplementedError(
            "translation_domain must be implemented in subclasses"
        )


class ILogOut(Interface):  # pragma: no cover
    """
    Allow extensions to hook to the FormShare logout process
    """

    def before_log_out(self, request, user, continue_logout):
        """
        Called by FormShare so plugins can perform actions before FormShare logs out an user
        :param request: Pyramid request object
        :param user: User disconnecting
        :param continue_logout: If FormShare or other plugin has indicated to logout or not
        :return: True if the logout should proceed. Or false to halt the logout
        """

    def after_log_out(self, request, user, redirect_url, logout_headers):
        """
        Called by FormShare so plugins can perform actions after FormShare logs out an user
        :param request: Pyramid request object
        :param user: User that disconnected
        :param redirect_url: Where FormShare is going after logout
        :param logout_headers: FormShare logout headers
        :return: target_location, headers
        """


class IAssistant(Interface):  # pragma: no cover
    """
    Allows to hook into the processes that create, update and delete assistants
    """

    def before_create(self, request, user, project, assistant_data):
        """
        Called by FormShare so plugins can perform actions before adding an assistant
        :param request: ``pyramid.request`` object
        :param user: User owner of the project
        :param project: Project ID
        :param assistant_data: Assistant information to be added
        :return: Return a modified version of assistant_data, true or false if the assistant should be added.
        If False then a message should state why. Example: return assistant_data, False, "My message"
        """
        raise NotImplementedError("before_create must be implemented in subclasses")

    def after_create(self, request, user, project, assistant_data):
        """
        Called by FormShare so plugins can perform actions before adding an assistant
        :param request: ``pyramid.request`` object
        :param user: User owner of the project
        :param project: project ID
        :param assistant_data: Assistant information
        :return: None
        """
        raise NotImplementedError("after_create must be implemented in subclasses")

    def before_edit(self, request, user, project, assistant, assistant_data):
        """
        Called by FormShare so plugins can perform actions before editing an assistant
        :param request: ``pyramid.request`` object
        :param user: User owner of the project
        :param project: Project ID
        :param assistant: Assistant ID
        :param assistant_data: Assistant information to be added
        :return: Return a modified version of assistant_data, true or false if the assistant should be added.
        If False then a message should state why. Example: return assistant_data, False, "My message"
        """
        raise NotImplementedError("before_create must be implemented in subclasses")

    def after_edit(self, request, user, project, assistant, assistant_data):
        """
        Called by FormShare so plugins can perform actions before editing an assistant
        :param request: ``pyramid.request`` object
        :param user: User owner of the project
        :param project: project ID
        :param assistant: Assistant ID
        :param assistant_data: Assistant information
        :return: None
        """
        raise NotImplementedError("after_create must be implemented in subclasses")

    def before_delete(self, request, user, project, assistant):
        """
        Called by FormShare so plugins can perform actions before deleting an assistant
        :param request: ``pyramid.request`` object
        :param user: User owner of the project
        :param project: Project ID
        :param assistant: Assistant ID
        :return: Return True or false if the project should be deleted. If False then
        a message should state why. Example: return False, "My message"
        """
        raise NotImplementedError("before_create must be implemented in subclasses")

    def after_delete(self, request, user, project, assistant):
        """
        Called by FormShare so plugins can perform actions before deleting an assistant
        :param request: ``pyramid.request`` object
        :param user: User owner of the project
        :param project: project ID
        :param assistant: Assistant ID
        :return: None
        """
        raise NotImplementedError("after_create must be implemented in subclasses")

    def before_password_change(self, request, user, project, assistant, password):
        """
        Called by FormShare so plugins can perform actions changing the password an assistant
        :param request: ``pyramid.request`` object
        :param user: User owner of the project
        :param project: Project ID
        :param assistant: Assistant ID
        :param password: Assistant password
        :return: True or false if the password should be changed. If False then
        a message should state why. Example: return False, "My message"
        """
        raise NotImplementedError("before_create must be implemented in subclasses")

    def after_password_change(self, request, user, project, assistant, password):
        """
        Called by FormShare so plugins can perform actions before changing the password of an assistant
        :param request: ``pyramid.request`` object
        :param user: User owner of the project
        :param project: project ID
        :param assistant: Assistant ID
        :param password: Assistant password
        :return: None
        """
        raise NotImplementedError("after_create must be implemented in subclasses")


class IAssistantGroup(Interface):  # pragma: no cover
    """
    Allows to hook into the processes that create, update and delete assistant groups
    """

    def before_create(self, request, user, project, group_data):
        """
        Called by FormShare so plugins can perform actions before adding an assistant group
        :param request: ``pyramid.request`` object
        :param user: User owner of the project
        :param project: Project ID
        :param group_data: Group information to be added
        :return: Return a modified version of group_data, true or false if the group should be added. If False then
        a message should state why. Example: return group_data, False, "My message"
        """
        raise NotImplementedError("before_create must be implemented in subclasses")

    def after_create(self, request, user, project, group_data):
        """
        Called by FormShare so plugins can perform actions before adding a group
        :param request: ``pyramid.request`` object
        :param user: User owner of the project
        :param project: project ID
        :param group_data: Group information
        :return: None
        """
        raise NotImplementedError("after_create must be implemented in subclasses")

    def before_edit(self, request, user, project, assistant, group_data):
        """
        Called by FormShare so plugins can perform actions before editing a group
        :param request: ``pyramid.request`` object
        :param user: User owner of the project
        :param project: Project ID
        :param assistant: Assistant ID
        :param group_data: Group information to be added
        :return: Return a modified version of group_data, true or false if the group should be edited. If False then
        a message should state why. Example: return project_data, False, "My message"
        """
        raise NotImplementedError("before_edit must be group_data in subclasses")

    def after_edit(self, request, user, project, assistant, group_data):
        """
        Called by FormShare so plugins can perform actions before editing an assistant
        :param request: ``pyramid.request`` object
        :param user: User owner of the project
        :param project: project ID
        :param assistant: Assistant ID
        :param group_data: Group information
        :return: None
        """
        raise NotImplementedError("after_edit must be implemented in subclasses")

    def before_delete(self, request, user, project, group, group_data):
        """
        Called by FormShare so plugins can perform actions before deleting a group
        :param request: ``pyramid.request`` object
        :param user: User owner of the project
        :param project: Project ID
        :param group: Group ID
        :param group_data: Information about the group
        :return: True or false if the group should be deleted. If False then
        a message should state why. Example: return False, "My message"
        """
        raise NotImplementedError("before_delete must be implemented in subclasses")

    def after_delete(self, request, user, project, group, group_data):
        """
        Called by FormShare so plugins can perform actions before deleting a group
        :param request: ``pyramid.request`` object
        :param user: User owner of the project
        :param project: project ID
        :param group: Group ID
        :param group_data: Group data
        :return: None
        """
        raise NotImplementedError("after_delete must be implemented in subclasses")


class IFormAccess(Interface):  # pragma: no cover
    """
    Allows to hook into the processes that gives assistant access to a form
    """

    def before_giving_access(
        self,
        request,
        user,
        project,
        form,
        assistant_project,
        assistant_id,
        privilege_data,
    ):
        """
        Called by FormShare so plugins can perform actions before giving access to an assistant
        :param request: ``pyramid.request`` object
        :param user: User owner of the project
        :param project: Project ID
        :param form: Form ID
        :param assistant_project: The project ID of the assistant
        :param assistant_id: Assistant ID
        :param privilege_data: Privilege data
        :return: A modified version of privilege_data plus True or false if the project should be added. If False then
        a message should state why. Example: return privilege_data, False, "My message"
        or return privilege_data, True, ""
        """
        raise NotImplementedError(
            "before_giving_access must be implemented in subclasses"
        )

    def after_giving_access(
        self,
        request,
        user,
        project,
        form,
        assistant_project,
        assistant_id,
        privilege_data,
    ):
        """
        Called by FormShare so plugins can perform actions after giving access an assistant
        :param request: ``pyramid.request`` object
        :param user: User owner of the project
        :param project: project ID
        :param form: Form ID
        :param assistant_project: The project ID of the assistant
        :param assistant_id: Assistant ID
        :param privilege_data: Privilege data
        :return: None
        """
        raise NotImplementedError(
            "after_giving_access must be implemented in subclasses"
        )

    def before_editing_access(
        self,
        request,
        user,
        project,
        form,
        assistant_project,
        assistant_id,
        privilege_data,
    ):
        """
        Called by FormShare so plugins can perform actions before editing access to an assistant
        :param request: ``pyramid.request`` object
        :param user: User owner of the project
        :param project: Project ID
        :param form: Form ID
        :param assistant_project: The project ID of the assistant
        :param assistant_id: Assistant ID
        :param privilege_data: Privilege data
        :return: A modified version of privilege_data plus True or false if the project should be added. If False then
        a message should state why. Example: return privilege_data, False, "My message"
        or return privilege_data, True, ""
        """
        raise NotImplementedError(
            "before_editing_access must be implemented in subclasses"
        )

    def after_editing_access(
        self,
        request,
        user,
        project,
        form,
        assistant_project,
        assistant_id,
        privilege_data,
    ):
        """
        Called by FormShare so plugins can perform actions after giving access an assistant
        :param request: ``pyramid.request`` object
        :param user: User owner of the project
        :param project: project ID
        :param form: Form ID
        :param assistant_project: The project ID of the assistant
        :param assistant_id: Assistant ID
        :param privilege_data: Privilege data
        :return: None
        """
        raise NotImplementedError(
            "after_editing_access must be implemented in subclasses"
        )

    def before_revoking_access(
        self, request, user, project, form, assistant_project, assistant_id
    ):
        """
        Called by FormShare so plugins can perform actions before revoking access to an assistant
        :param request: ``pyramid.request`` object
        :param user: User owner of the project
        :param project: Project ID
        :param form: Form ID
        :param assistant_project: The project ID of the assistant
        :param assistant_id: Assistant ID
        :return: True or false if the project should be added. If False then
        a message should state why. Example: return False, "My message"
        or return True, ""
        """
        raise NotImplementedError(
            "before_giving_access must be implemented in subclasses"
        )

    def after_revoking_access(
        self, request, user, project, form, assistant_project, assistant_id
    ):
        """
        Called by FormShare so plugins can perform actions after giving access an assistant
        :param request: ``pyramid.request`` object
        :param user: User owner of the project
        :param project: project ID
        :param form: Form ID
        :param assistant_project: The project ID of the assistant
        :param assistant_id: Assistant ID
        :return: None
        """
        raise NotImplementedError(
            "after_giving_access must be implemented in subclasses"
        )


class IFormGroupAccess(Interface):  # pragma: no cover
    """
    Allows to hook into the processes that gives group access to a form
    """

    def before_giving_access(
        self, request, user, project, form, group_project, assistant_group
    ):
        """
        Called by FormShare so plugins can perform actions before giving access to an assistant
        :param request: ``pyramid.request`` object
        :param user: User owner of the project
        :param project: Project ID
        :param form: Form ID
        :param group_project: The project ID of the group
        :param assistant_group: Group ID
        :return: True or false if the project should be added. If False then
        a message should state why. Example: return False, "My message"
        """
        raise NotImplementedError("before_create must be implemented in subclasses")

    def after_giving_access(
        self, request, user, project, form, group_project, group_id
    ):
        """
        Called by FormShare so plugins can perform actions after giving access an assistant
        :param request: ``pyramid.request`` object
        :param user: User owner of the project
        :param project: project ID
        :param form: Form ID
        :param group_project: The project ID of the group
        :param group_id: Group ID
        :return: None
        """
        raise NotImplementedError("after_create must be implemented in subclasses")


class IUser(Interface):  # pragma: no cover
    """
    Allows to hook into the processes that creates and updates users
    """

    def before_create(self, request, user_data):
        """
        Called by FormShare so plugins can perform actions before adding an user
        :param request: ``pyramid.request`` object
        :param user_data: User information to be added
        :return: Return a modified version of user_data, true or false if the assistant should be added.
        If False then a message should state why. Example: return user_data, False, "My message"
        """
        raise NotImplementedError("before_create must be implemented in subclasses")

    def after_create(self, request, user_data):
        """
        Called by FormShare so plugins can perform actions before adding an user
        :param request: ``pyramid.request`` object
        :param user_data: User information
        :return: None
        """
        raise NotImplementedError("after_create must be implemented in subclasses")

    def before_edit(self, request, user, user_data):
        """
        Called by FormShare so plugins can perform actions before editing an assistant
        :param request: ``pyramid.request`` object
        :param user: User owner of the project
        :param user_data: user information to be edited
        :return: Return a modified version of user_data, true or false if the assistant should be edited.
        If False then a message should state why. Example: return user_data, False, "My message"
        """
        raise NotImplementedError("before_edit must be implemented in subclasses")

    def after_edit(self, request, user, user_data):
        """
        Called by FormShare so plugins can perform actions before editing an user
        :param request: ``pyramid.request`` object
        :param user: User owner of the project
        :param user_data: User information
        :return: None
        """
        raise NotImplementedError("after_edit must be implemented in subclasses")


class IPartner(Interface):  # pragma: no cover
    """
    Allows to hook into the processes that creates and updates partners
    """

    def before_create(self, request, partner_data):
        """
        Called by FormShare so plugins can perform actions before adding an partner
        :param request: ``pyramid.request`` object
        :param partner_data: Partner information to be added
        :return: Return a modified version of user_data, true or false if the partner should be added.
        If False then a message should state why. Example: return user_data, False, "My message"
        """
        raise NotImplementedError("before_create must be implemented in subclasses")

    def after_create(self, request, partner_data):
        """
        Called by FormShare so plugins can perform actions after adding an partner
        :param request: ``pyramid.request`` object
        :param partner_data: Partner information
        :return: None
        """
        raise NotImplementedError("after_create must be implemented in subclasses")

    def before_edit(self, request, partner_id, partner_data):
        """
        Called by FormShare so plugins can perform actions before editing a partner
        :param request: ``pyramid.request`` object
        :param partner_id: partner id
        :param partner_data: partner information to be edited
        :return: Return a modified version of partner_data, true or false if the partner should be edited.
        If False then a message should state why. Example: return user_data, False, "My message"
        """
        raise NotImplementedError("before_edit must be implemented in subclasses")

    def after_edit(self, request, partner_id, partner_data):
        """
        Called by FormShare so plugins can perform actions after editing a partner
        :param request: ``pyramid.request`` object
        :param partner_id: partner id
        :param partner_data: Partner information
        :return: None
        """
        raise NotImplementedError("after_edit must be implemented in subclasses")

    def before_delete(self, request, partner_id, partner_data):
        """
        Called by FormShare so plugins can perform actions before deleting a partner
        :param request: ``pyramid.request`` object
        :param partner_id: partner id to be deleted
        :param partner_data: information of the partner to be deleted
        :return: Return true or false if the partner should be edited and a message.
        Example: return False, "My message"
        """
        raise NotImplementedError("before_delete must be implemented in subclasses")

    def after_delete(self, request, partner_id):
        """
        Called by FormShare so plugins can perform actions after deleting a partner
        :param request: ``pyramid.request`` object
        :param partner_id: Partner id that was deleted
        :return: None
        """
        raise NotImplementedError("after_delete must be implemented in subclasses")

    def before_password_change(self, request, partner_id, password):
        """
        Called by FormShare so plugins can perform actions changing the password a partner
        :param request: ``pyramid.request`` object
        :param partner_id: Partner ID
        :param password: Assistant password
        :return: True or false if the password should be changed. If False then
        a message should state why. Example: return False, "My message"
        """
        raise NotImplementedError(
            "before_password_change must be implemented in subclasses"
        )

    def after_password_change(self, request, partner_id, password):
        """
        Called by FormShare so plugins can perform actions after changing the password of a partner
        :param request: ``pyramid.request`` object
        :param partner_id: Partner ID
        :param password: Assistant password
        :return: None
        """
        raise NotImplementedError(
            "after_password_change must be implemented in subclasses"
        )


class IEnvironment(Interface):  # pragma: no cover
    """
    Allows to hook into the process that creates the FormShare environment
    """

    def after_environment_load(self, config):
        """
        Called by FormShare after the environment is configured
        :param config: FormShare config object
        """


class IXMLSubmission(Interface):  # pragma: no cover
    """
    Allows to hook into the process that received and stores the XML submission from ODK Collect
    """

    def before_processing_submission(
        self, request, user, project, form, assistant, xml_file
    ):
        """
        Called by FormShare before FormShare process the XML submission file
        :param request: Pyramid request object
        :param user: User ID
        :param project: Project ID
        :param form: XForm ID
        :param assistant: Assistant ID submitting the XML file
        :param xml_file: XML submission file
        :return True/False, error code: Whether the storage should continue, 0 no error or other error code
        """

    def after_processing_submission(
        self, request, user, project, form, assistant, error, xml_file
    ):
        """
        Called by FormShare after FormShare process the XML submission file
        :param request: Pyramid request object
        :param user: User ID
        :param project: Project ID
        :param form: XForm ID
        :param assistant: Assistant ID submitting the XML file
        :param error: Whether or not FormShare processed the XMK file
        :param xml_file: XML submission file
        :return: None
        """


class IJSONSubmission(Interface):  # pragma: no cover
    """
    Allows to hook into the process that received and stores the XML submission from ODK Collect
    """

    def before_processing_submission(
        self, request, user, project, form, assistant, json_file
    ):
        """
        Called by FormShare before FormShare process the JSON submission file
        :param request: Pyramid request object
        :param user: User ID
        :param project: Project ID
        :param form: XForm ID
        :param assistant: Assistant ID submitting the JSON file
        :param json_file: JSON submission file
        :return Error code, message: 0 or other error code and a message
        """

    def after_processing_submission_in_repository(
        self, request, user, project, form, assistant, submission, error, json_file
    ):
        """
        Called by FormShare after FormShare process the JSON submission file into t
        :param request: Pyramid request object
        :param user: User ID
        :param project: Project ID
        :param form: XForm ID
        :param assistant: Assistant ID submitting the JSON file
        :param submission: Submission ID
        :param error: Whether or not FormShare stored the JSON file. 0 = stored, 2 = in logs
        :param json_file: JSON submission file
        :return: None
        """

    def after_processing_submission_not_in_repository(
        self, request, user, project, form, assistant, submission, json_file
    ):
        """
        Called by FormShare after FormShare process the JSON submission file into t
        :param request: Pyramid request object
        :param user: User ID
        :param project: Project ID
        :param form: XForm ID
        :param assistant: Assistant ID submitting the JSON file
        :param submission: Submission ID
        :param json_file: JSON submission file
        :return: None
        """


class IMediaSubmission(Interface):  # pragma: no cover
    """
    Allows to hook into the process that received and stores media files from ODK Collect
    """

    def after_storing_media_in_repository(
        self, request, user, project, form, assistant, submission, json_file, media_file
    ):
        """
        Called by FormShare after FormShare process the XML submission file
        :param request: Pyramid request object
        :param user: User ID
        :param project: Project ID
        :param form: XForm ID
        :param assistant: Assistant ID submitting the media file
        :param submission: Submission ID
        :param json_file: XML Data file
        :param media_file: Media file
        :return: None
        """

    def after_storing_media_not_in_repository(
        self, request, user, project, form, assistant, submission, json_file, media_file
    ):
        """
        Called by FormShare after FormShare process the XML submission file
        :param request: Pyramid request object
        :param user: User ID
        :param project: Project ID
        :param form: XForm ID
        :param assistant: Assistant ID submitting the media file
        :param submission: Submission ID
        :param json_file: XML Data file
        :param media_file: Media file
        :return: None
        """


class IExport(Interface):  # pragma: no cover
    """
    Allows to hook into the processes that process a data export
    """

    def has_export_for(self, request, export_type):
        """
        Called by FormShare so plugins can indicate if they provide an export for a type
        :param request: ``pyramid.request`` object
        :param export_type: The type of the export requested by the user
        return: True if the plugins export the type or False
        """

    def do_export(self, request, export_type):
        """
        Called by FormShare so plugins can perform other types of exports
        :param request: ``pyramid.request`` object
        :param export_type: The type of the export requested by the user
        :return: Must return a HTTP 302 redirect (A Pyramid HTTPFound)
        """
        raise NotImplementedError("do_export must be implemented in subclasses")


class IPluginObserver(Interface):  # pragma: no cover
    """
    Plugin to the plugin loading mechanism

    This code is based on CKAN
    :Copyright (C) 2007 Open Knowledge Foundation
    :license: AGPL V3, see LICENSE for more details.

    """

    def before_load(self, plugin):
        """
        Called before a plugin is loaded
        This method is passed the plugin class.
        """

    def after_load(self, service):
        """
        Called after a plugin has been loaded.
        This method is passed the instantiated service object.
        """

    def before_unload(self, plugin):
        """
        Called before a plugin is loaded
        This method is passed the plugin class.
        """

    def after_unload(self, service):
        """
        Called after a plugin has been unloaded.
        This method is passed the instantiated service object.
        """
