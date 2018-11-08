from ..plugins.utilities import add_route
import formshare.plugins as p
from ..views.basic_views import NotFoundView, HomeView, log_out_view, LoginView, RegisterView, \
    CollaboratorsLoginView
from ..views.dashboard import UserDashBoardView
from ..views.projects import AddProjectView, ProjectListView, ProjectDetailsView
from ..views.profile import UserProfileView, EditProfileView

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
    for plugin in p.PluginImplementations(p.IRoutes):
        routes = plugin.before_mapping(config)
        append_to_routes(routes)

    # FormShare routes
    routes = []
    routes.append(add_route('home', '/', HomeView, 'landing/index.jinja2'))
    routes.append(add_route('login', '/login', LoginView, 'generic/login.jinja2'))
    routes.append(add_route('collaboratorslogin', '/collaborators/{userid}/{pname}/login', CollaboratorsLoginView,
                            'generic/collablogin.jinja2'))
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
    # routes.append(addRoute('form_details', '/user/{userid}/project/{projid}/form/{formid}', formDetails_view,
    #                        'dashboard/projects/forms/form_details.jinja2'))

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
