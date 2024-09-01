import os
import sys

if (
    os.environ.get("FORMSHARE_PYTEST_RUNNING", "false") == "false"
    and os.environ.get("FORMSHARE_RUN_FROM_CELERY", "false") == "false"
):
    if sys.version_info[0] == 3 and sys.version_info[1] >= 6:  # pragma: no cover
        import gevent.monkey

        gevent.monkey.patch_all()


from pyramid.config import Configurator
import os
from configparser import ConfigParser, NoOptionError
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid_authstack import AuthenticationStackPolicy
from formshare.config.environment import load_environment
from formshare.config.config_indexes import configure_indexes


def main(global_config, **settings):
    apppath = os.path.dirname(os.path.abspath(__file__))
    if global_config is not None:  # pragma: no cover
        config = ConfigParser()
        config.read(global_config["__file__"])
        host = config.get("server:main", "host")
        try:
            threads = config.get("app:formshare", "odk.threads")
        except NoOptionError:
            threads = "1"
        port = config.get("server:main", "port")
        composite_section = dict(config.items("composite:main"))
        composite_section.pop("use")
        settings["apppath"] = apppath
        settings["server:threads"] = threads
        settings["server:main:host"] = host
        settings["server:main:port"] = port
        settings["server:main:root"] = list(composite_section.keys())[0]
        settings["global:config:file"] = global_config["__file__"]

    """This function returns a Pyramid WSGI application."""
    auth_policy = AuthenticationStackPolicy()
    policy_array = []

    main_policy = AuthTktAuthenticationPolicy(
        settings["auth.main.secret"],
        timeout=settings.get("auth.main.cookie.timeout", None),
        cookie_name=settings["auth.main.cookie"],
    )
    auth_policy.add_policy("main", main_policy)
    policy_array.append({"name": "main", "policy": main_policy})

    assistant_policy = AuthTktAuthenticationPolicy(
        settings["auth.assistant.secret"],
        timeout=settings.get("auth.assistant.cookie.timeout", None),
        cookie_name=settings["auth.assistant.cookie"],
    )
    auth_policy.add_policy("assistant", assistant_policy)
    policy_array.append({"name": "assistant", "policy": assistant_policy})

    partner_policy = AuthTktAuthenticationPolicy(
        settings["auth.partner.secret"],
        timeout=settings.get("auth.partner.cookie.timeout", None),
        cookie_name=settings["auth.partner.cookie"],
    )
    auth_policy.add_policy("partner", partner_policy)
    policy_array.append({"name": "partner", "policy": partner_policy})

    # authn_policy = AuthTktAuthenticationPolicy(settings['auth.secret'], cookie_name='formshare_auth_tkt')
    authz_policy = ACLAuthorizationPolicy()
    config = Configurator(
        settings=settings,
        authentication_policy=auth_policy,
        authorization_policy=authz_policy,
    )

    config.include(".models")
    # Load and configure the host application
    configure_indexes(settings)
    wsgi_app = load_environment(settings, config, apppath, policy_array)
    return wsgi_app
