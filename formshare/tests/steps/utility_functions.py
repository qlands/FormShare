def t_e_s_t_utility_functions():
    import formshare.plugins.utilities as u

    u.add_js_resource("test", "test", "test")
    u.add_css_resource("test", "test", "test")
    u.add_route("test", "test", "test", None)
    u.add_field_to_user_schema("test", "test")
    u.add_field_to_project_schema("test", "test")
    u.add_field_to_assistant_schema("test", "test")
    u.add_field_to_assistant_group_schema("test", "test")
    u.add_field_to_form_schema("test", "test")
    u.add_field_to_form_access_schema("test", "test")
    u.add_field_to_form_group_access_schema("test", "test")
