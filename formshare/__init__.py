import sys
import os

if os.environ.get("FORMSHARE_PYTEST_RUNNING", "false") == "false":
    if sys.version_info[0] == 3 and sys.version_info[1] >= 6:
        import gevent.monkey

        gevent.monkey.patch_all()


from pyramid.config import Configurator
import os

from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid_authstack import AuthenticationStackPolicy
from formshare.config.environment import load_environment
from formshare.config.config_indexes import configure_indexes


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    auth_policy = AuthenticationStackPolicy()
    policy_array = []

    main_policy = AuthTktAuthenticationPolicy(
        settings["auth.main.secret"],
        timeout=settings.get("auth.main.cookie.timeout", 7200),
        cookie_name=settings["auth.main.cookie"],
    )
    auth_policy.add_policy("main", main_policy)
    policy_array.append({"name": "main", "policy": main_policy})

    assistant_policy = AuthTktAuthenticationPolicy(
        settings["auth.assistant.secret"],
        timeout=settings.get("auth.assistant.cookie.timeout", 7200),
        cookie_name=settings["auth.assistant.cookie"],
    )
    auth_policy.add_policy("assistant", assistant_policy)
    policy_array.append({"name": "assistant", "policy": assistant_policy})

    # authn_policy = AuthTktAuthenticationPolicy(settings['auth.secret'], cookie_name='formshare_auth_tkt')
    authz_policy = ACLAuthorizationPolicy()
    config = Configurator(
        settings=settings,
        authentication_policy=auth_policy,
        authorization_policy=authz_policy,
    )

    apppath = os.path.dirname(os.path.abspath(__file__))

    config.include(".models")
    # Load and configure the host application
    configure_indexes(settings)
    load_environment(settings, config, apppath, policy_array)
    return config.make_wsgi_app()
