def t_e_s_t_plugin_utility_functions(test_object):
    test_object.testapp.get(
        "/test/{}".format(test_object.randonLogin),
        status=200,
    )
    test_object.testapp.get(
        "/test/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )
