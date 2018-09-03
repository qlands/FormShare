# -*- coding: utf-8 -*-
"""
    formshare.config.routes
    ~~~~~~~~~~~~~~~~~~

    Provides the basic routes of FormShare.

    :copyright: (c) 2017 by QLands Technology Consultants.
    :license: AGPL, see LICENSE for more details.
"""

from ..plugins.utilities import addRoute
import formshare.plugins as p
from ..views.basic_views import notfound_view,home_view,logout_view,login_view,register_view,collaboratorsLogin_view
from ..views.dashboard import dashboard_view
from ..views.projects import projects_view,projectDetails_view
from ..views.form import formDetails_view
from ..views.profile import profile_view

route_list = []

#This function append or overrides the routes to the main list
def appendToRoutes(routeList):
    for new_route in routeList:
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

def loadRoutes(config):
    # Call connected to plugins to add any routes before FormShare
    for plugin in p.PluginImplementations(p.IRoutes):
        routes = plugin.before_mapping(config)
        appendToRoutes(routes)

    #FormShare routes
    routes = []
    routes.append(addRoute('home', '/', home_view, 'landing/index.jinja2'))
    routes.append(addRoute('login', '/login', login_view, 'generic/login.jinja2'))
    routes.append(addRoute('collaboratorslogin', '/collaborators/{userid}/{pname}/login', collaboratorsLogin_view, 'generic/collablogin.jinja2'))
    routes.append(addRoute('register', '/join', register_view, 'generic/register.jinja2'))
    routes.append(addRoute('logout', '/logout', logout_view, None))

    routes.append(addRoute('dashboard', '/{userid}', dashboard_view, 'dashboard/index.jinja2'))
    routes.append(addRoute('profile', '/{userid}/profile', profile_view, 'dashboard/profile/profile.jinja2'))

    routes.append(addRoute('projects', '/{userid}/projects', projects_view, 'dashboard/projects/project_list.jinja2'))
    routes.append(addRoute('project_details', '/{userid}/project/{projid}', projectDetails_view, 'dashboard/projects/project_details.jinja2'))
    routes.append(addRoute('form_details', '/{userid}/project/{projid}/form/{formid}', formDetails_view, 'dashboard/projects/forms/form_details.jinja2'))

    appendToRoutes(routes)

    #Add the not found route
    config.add_notfound_view(notfound_view, renderer='generic/404.jinja2')

    # Call connected plugins to add any routes after FormShare
    for plugin in p.PluginImplementations(p.IRoutes):
        routes = plugin.after_mapping(config)
        appendToRoutes(routes)

    # Now add the routes and views to the Pyramid config
    for curr_route in route_list:
        config.add_route(curr_route['name'], curr_route['path'])
        config.add_view(curr_route['view'], route_name=curr_route['name'], renderer=curr_route['renderer'])