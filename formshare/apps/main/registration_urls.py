"""
URLConf for Django user registration and authentication.

Recommended usage is a call to ``include()`` in your project's root
URLConf to include this URLConf for any URL beginning with
``/accounts/``.

"""


from django.conf.urls import patterns, url, include
from django.contrib.auth.forms import AuthenticationForm
from django.conf import settings



AuthenticationForm.APP_ROOT = settings.APP_ROOT

urlpatterns = patterns(
    '',
    url(r'^accounts/login/$', 'django.contrib.auth.views.login', {'template_name': 'registration/login.html', 'authentication_form': AuthenticationForm }),
    (r'', include('registration.auth_urls')),
)
