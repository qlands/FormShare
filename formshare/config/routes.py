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
from ..views.basic_views import notfound_view,home_view,logout_view

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
    routes.append(addRoute('home', '/', home_view, 'mytemplate.jinja2'))
    routes.append(addRoute('logout', '/logout', logout_view, None))
    appendToRoutes(routes)

    #Add the not found route
    config.add_notfound_view(notfound_view, renderer='404.jinja2')

    # Call connected plugins to add any routes after FormShare
    for plugin in p.PluginImplementations(p.IRoutes):
        routes = plugin.after_mapping(config)
        appendToRoutes(routes)

    # Now add the routes and views to the Pyramid config
    for curr_route in route_list:
        config.add_route(curr_route['name'], curr_route['path'])
        config.add_view(curr_route['view'], route_name=curr_route['name'], renderer=curr_route['renderer'])