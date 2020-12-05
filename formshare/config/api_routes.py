import formshare.plugins as p
from formshare.plugins.utilities import add_route
from formshare.views.api import API1UploadFileToForm
from formshare.views.repository_submissions import API1UpdateRepository

api_route_list = []


def append_to_routes(route_array):
    """
    #This function append or overrides the routes to the main list
    :param route_array: Array of routes
    """
    for new_route in route_array:
        found = False
        pos = 0
        for curr_route in api_route_list:
            if curr_route["path"] == new_route["path"]:
                found = True
                break
            pos = pos + 1
        if not found:
            api_route_list.append(new_route)
        else:
            api_route_list[pos]["name"] = new_route["name"]
            api_route_list[pos]["view"] = new_route["view"]
            api_route_list[pos]["renderer"] = new_route["renderer"]


def load_api_version_1_routes(config):
    """
    Call connected to plugins to add any routes before FormShare
    :param config: Pyramid config
    """
    routes = []
    for plugin in p.PluginImplementations(p.IAPIRoutes):
        routes = plugin.before_mapping(config)
        append_to_routes(routes)

    # FormShare API routes
    routes.append(
        add_route(
            "API1UploadFileToForm",
            "/api/1/upload_file_to_form",
            API1UploadFileToForm,
            "json",
        )
    )

    routes.append(
        add_route(
            "api1_update_repository",
            "/user/{userid}/project/{projcode}/form/{formid}/api_update",
            API1UpdateRepository,
            "json",
        )
    )

    # Overwrite or add the API routes
    append_to_routes(routes)

    # Call connected plugins to add any routes after FormShare
    for plugin in p.PluginImplementations(p.IAPIRoutes):
        routes = plugin.after_mapping(config)
        append_to_routes(routes)

    # Now add the routes and views to the Pyramid config
    for curr_route in api_route_list:
        config.add_route(curr_route["name"], curr_route["path"])
        config.add_view(
            curr_route["view"],
            route_name=curr_route["name"],
            renderer=curr_route["renderer"],
        )
