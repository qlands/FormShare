import os
from pyramid.session import SignedCookieSessionFactory
import formshare.plugins as p
import formshare.resources as r
from formshare.models import addColumnToSchema
from formshare.models.meta import Base, metadata
from sqlalchemy.orm import configure_mappers
from .jinja_extensions import initialize, SnippetExtension, extendThis, CSSResourceExtension,JSResourceExtension
from .mainresources import createResources
import formshare.plugins.helpers as helpers
from .routes import loadRoutes
from pyramid.csrf import SessionCSRFStoragePolicy

my_session_factory = SignedCookieSessionFactory('`h6N[wQ8@S"B$bGy;')

# This function return the address of a static URL.
# It substitutes request.static_url because
# static_url does not work for plugins when using
# a full path to the static directory
def __url_for_static(request,static_file,library='fstatic'):
    return request.application_url + '/' + library + "/" + static_file

def __helper(request):
    h = helpers.helper_functions
    return h

#This class handles the injection of resources
class requestResources(object):

    def __init__(self, request):
        self.request = request
        self.curretResources = []

    def addResource(self, libraryName, resourceID, resourceType):
        self.curretResources.append({'libraryName':libraryName,'resourceID':resourceID,'resourceType':resourceType})

    def resourceInRequest(self, libraryName, resourceID, resourceType):
        for resource in self.curretResources:
            if resource["libraryName"] == libraryName and resource["resourceID"] == resourceID and resource["resourceType"] == resourceType:
                return True
        return False

def load_environment(settings,config,apppath):
    # Add the session factory to the confing
    config.set_session_factory(my_session_factory)
    config.set_csrf_storage_policy(SessionCSRFStoragePolicy())
    #config.set_default_csrf_options(require_csrf=True)

    # Add render subscribers for internationalization
    config.add_translation_dirs('formshare:locale')
    config.add_subscriber('formshare.i18n.i18n.add_renderer_globals', 'pyramid.events.BeforeRender')
    config.add_subscriber('formshare.i18n.i18n.add_localizer', 'pyramid.events.NewRequest')

    #Register jinja2
    config.registry.settings['jinja2.extensions'] = ['jinja2.ext.i18n', 'jinja2.ext.do', 'jinja2.ext.with_',SnippetExtension, extendThis, CSSResourceExtension, JSResourceExtension]
    config.include('pyramid_jinja2')

    #Add url_for_static to the request so plugins can use static resources
    config.add_request_method(__url_for_static, 'url_for_static')
    #Add active resources to the request. This control the injection of resources into a request
    config.add_request_method(requestResources, 'activeResources', reify=True)

    # Add core library and resources
    createResources(apppath,config)

    #Add the template directories
    templatesPathArray = []
    templatesPath = os.path.join(apppath, 'templates')
    templatesPathArray.append(templatesPath)
    config.add_settings(templatesPaths=templatesPathArray)

    #Add the static view
    staticPath = os.path.join(apppath, 'static')
    config.add_static_view('fstatic', staticPath, cache_max_age=3600)
    #Add the template directories to jinja2
    config.add_jinja2_search_path(templatesPath)

    # Load all connected plugins
    p.load_all(settings)

    # Add a series of helper functions to the request like pluralize
    helpers.load_plugin_helpers()
    config.add_request_method(__helper, 'h', reify=True)

    # Load any change in the configuration done by connected plugins
    for plugin in p.PluginImplementations(p.IConfig):
        plugin.update_config(config)

    # Call any connected plugins to add their libraries
    for plugin in p.PluginImplementations(p.IResource):
        pluginLibraries = plugin.add_libraries(config)
        for library in pluginLibraries:
            r.addLibrary(library["name"], library["path"],config)

    # Call any connected plugins to add their CSS Resources
    for plugin in p.PluginImplementations(p.IResource):
        cssResources = plugin.add_CSSResources(config)
        for resource in cssResources:
            r.addCSSResource(resource["libraryname"], resource["id"], resource["file"], resource["depends"])


    # Call any connected plugins to add their JS Resources
    for plugin in p.PluginImplementations(p.IResource):
        jsResources = plugin.add_JSResources(config)
        for resource in jsResources:
            r.addJSResource(resource["libraryname"], resource["id"], resource["file"], resource["depends"])

    # Call any connected plugins to add their modifications into the schema
    schemas_allowed = ["user", "project", "enumerator", "enumgroup", "datauser", "datagroup", "form"]
    for plugin in p.PluginImplementations(p.ISchema):
        schemaFields = plugin.update_schema(config)
        for field in schemaFields:
            if field["schema"] in schemas_allowed:
                addColumnToSchema(field["schema"], field["fieldname"], field["fielddesc"])

    #Call any connected plugins to add their tables
    for plugin in p.PluginImplementations(p.IDatabase):
        plugin.update_schema(config,Base)

    # run configure_mappers after calling plugins implementing IDatabase
    # all relationships can be setup
    configure_mappers()

    # print "**********************88"
    # for table in metadata.sorted_tables:
    #     print table.name
    # print "**********************88"


    # jinjaEnv is used by the jinja2 extensions so we get it from the config
    jinjaEnv = config.get_jinja2_environment()

    # setup the jinjaEnv template's paths for the extensions
    initialize(config.registry.settings['templatesPaths'])

    # Finally we load the routes
    loadRoutes(config)


