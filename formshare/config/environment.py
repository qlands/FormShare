import os

import pyramid_session_multi
from pyramid.csrf import SessionCSRFStoragePolicy
from pyramid.session import SignedCookieSessionFactory
from pyramid_session_redis import session_factory_from_settings

import formshare.plugins as p
import formshare.plugins.helpers as helpers
import formshare.resources as r
from formshare.config.api_routes import load_api_version_1_routes
from formshare.config.jinja_extensions import (
    initialize,
    ExtendThis,
    CSSResourceExtension,
    JSResourceExtension,
)
from formshare.config.mainresources import create_resources
from formshare.config.routes import load_routes
from formshare.models import add_column_to_schema, add_modules_to_schema
from formshare.products import add_product
from formshare.products.formshare_products import register_products

main_policy_array = []


def __url_for_static(request, static_file, library="fstatic"):
    """
    This function return the address of a static URL. It substitutes request.static_url because static_url does not
    work for plugins when using a full path to the static directory
    :param request: Current request object
    :param static_file: Static file being requested
    :param library: Library where the static file is located
    :return: URL to the static resource
    """
    return request.application_url + "/" + library + "/" + static_file


def get_policy_array(request):
    return main_policy_array


def __helper(request):
    h = helpers.helper_functions
    return h


class RequestResources(object):
    """
    This class handles the injection of resources in templates
    """

    def __init__(self, request):
        self.request = request
        self.current_resources = []

    def add_resource(self, library_name, resource_id, resource_type):
        self.current_resources.append(
            {
                "libraryName": library_name,
                "resourceID": resource_id,
                "resourceType": resource_type,
            }
        )

    def resource_in_request(self, library_name, resource_id, resource_type):
        for resource in self.current_resources:
            if (
                resource["libraryName"] == library_name
                and resource["resourceID"] == resource_id
                and resource["resourceType"] == resource_type
            ):
                return True
        return False


def load_environment(settings, config, apppath, policy_array):
    for policy in policy_array:
        main_policy_array.append(policy)

    # Add the session factory to the config
    session_factory = session_factory_from_settings(settings)
    config.set_session_factory(session_factory)

    # Adds a secondary session for not critical cookies that will not expire
    config.include("pyramid_session_multi")
    secondary_session_factory = SignedCookieSessionFactory(
        settings["auth.secondary.secret"],
        cookie_name=settings["auth.secondary.cookie"],
        timeout=None,
    )
    pyramid_session_multi.register_session_factory(
        config, "secondary_session", secondary_session_factory
    )

    config.set_csrf_storage_policy(SessionCSRFStoragePolicy())
    # config.set_default_csrf_options(require_csrf=True)

    # Add render subscribers for internationalization
    # config.add_translation_dirs("formshare:locale")
    config.add_subscriber(
        "formshare.i18n.i18n.add_renderer_globals", "pyramid.events.BeforeRender"
    )
    config.add_subscriber(
        "formshare.i18n.i18n.add_localizer", "pyramid.events.NewRequest"
    )

    # Register Jinja2
    config.registry.settings["jinja2.extensions"] = [
        "jinja2.ext.i18n",
        "jinja2.ext.do",
        "jinja2.ext.with_",
        ExtendThis,
        CSSResourceExtension,
        JSResourceExtension,
    ]
    config.include("pyramid_jinja2")

    # Add url_for_static to the request so plugins can use static resources
    config.add_request_method(__url_for_static, "url_for_static")
    # Add active resources to the request. This control the injection of resources into a request
    config.add_request_method(RequestResources, "activeResources", reify=True)

    # Add core library and resources
    create_resources(apppath, config)

    # Add the template directories
    templates_path_array = []
    templates_path = os.path.join(apppath, "templates")
    templates_path_array.append(templates_path)
    config.add_settings(templatesPaths=templates_path_array)

    # Add the static view
    static_path = os.path.join(apppath, "static")
    config.add_static_view("fstatic", static_path, cache_max_age=3600)
    # Add the template directories to jinja2
    config.add_jinja2_search_path(templates_path)

    # Load all connected plugins
    p.load_all(settings)

    # Add a series of helper functions to the request like pluralize
    helpers.load_plugin_helpers()
    config.add_request_method(__helper, "h", reify=True)

    config.add_request_method(get_policy_array, "policies", reify=False)

    # Load any change in the configuration done by connected plugins
    for plugin in p.PluginImplementations(p.IConfig):
        plugin.update_config(config)

    # Call any connected plugins to add their libraries
    for plugin in p.PluginImplementations(p.IResource):
        plugin_libraries = plugin.add_libraries(config)
        for library in plugin_libraries:
            r.add_library(library["name"], library["path"], config)

    # Call any connected plugins to add their CSS Resources
    for plugin in p.PluginImplementations(p.IResource):
        css_resources = plugin.add_css_resources(config)
        for resource in css_resources:
            r.add_css_resource(
                resource["libraryname"],
                resource["id"],
                resource["file"],
                resource["depends"],
            )

    # Call any connected plugins to add their JS Resources
    for plugin in p.PluginImplementations(p.IResource):
        js_resources = plugin.add_js_resources(config)
        for resource in js_resources:
            r.add_js_resource(
                resource["libraryname"],
                resource["id"],
                resource["file"],
                resource["depends"],
            )

    # Register FormShare build-in products
    for product in register_products():
        add_product(product)

    # Call any connected plugins to add their products
    for plugin in p.PluginImplementations(p.IProduct):
        products = plugin.register_products(config)
        for product in products:
            add_product(product, True)

    # Call any connected plugins to add their modifications into the schema. Not all tables has extras so only
    # certain tables are allowed
    schemas_allowed = [
        "fsuser",
        "project",
        "collaborator",
        "collgroup",
        "odkform",
        "formaccess",
        "formgrpaccess",
        "partner",
        "partnerproject",
        "partnerform",
    ]

    modules_allowed = ["formshare.models.formshare"]

    for plugin in p.PluginImplementations(p.IDatabase):
        schemas_allowed = plugin.update_extendable_tables(schemas_allowed)

    for plugin in p.PluginImplementations(p.IDatabase):
        modules_allowed = plugin.update_extendable_modules(modules_allowed)

    add_modules_to_schema(modules_allowed)

    # Call any connected plugins to update FormShare ORM. For example: Add new tables
    for plugin in p.PluginImplementations(p.IDatabase):
        plugin.update_orm(config)

    for plugin in p.PluginImplementations(p.ISchema):
        schema_fields = plugin.update_schema(config)
        for field in schema_fields:
            if field["schema"] in schemas_allowed:
                add_column_to_schema(
                    field["schema"], field["fieldname"], field["fielddesc"]
                )

    # jinjaEnv is used by the jinja2 extensions so we get it from the config
    config.get_jinja2_environment()

    # setup the jinjaEnv template's paths for the extensions
    initialize(config.registry.settings["templatesPaths"])

    # We load the routes
    load_routes(config, settings)
    load_api_version_1_routes(config)

    wsgi_app = config.make_wsgi_app()
    # Finally called connected plugins to IEnvironment
    for plugin in p.PluginImplementations(p.IEnvironment):
        plugin.after_environment_load(config)

    return wsgi_app
