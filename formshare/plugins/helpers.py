"""
Helper functions

Consists of functions to typically be used within templates, but also
available to Controllers. This module is available to templates as 'request.h'.
"""

import timeago
import arrow
import inflect
import formshare.plugins as p
import urllib
import hashlib
import validators


class HelperAttributeDict(dict):
    """
    This code is based on CKAN
    :Copyright (C) 2007 Open Knowledge Foundation
    :license: AGPL V3.
    """
    def __init__(self, *args, **kwargs):
        super(HelperAttributeDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

    def __getitem__(self, key):
        try:
            value = super(HelperAttributeDict, self).__getitem__(key)
        except KeyError:
            raise Exception('Helper function \'{key}\' has not been defined.'.format(key=key))
        return value


# Builtin helper functions.
_builtin_functions = {}
helper_functions = HelperAttributeDict()


def core_helper(f, name=None):
    """
    Register a function as a builtin helper method.

    This code is based on CKAN
        :Copyright (C) 2007 Open Knowledge Foundation
        :license: AGPL V3, see LICENSE for more details.

    """
    def _get_name(func_or_class):
        # Handles both methods and class instances.
        try:
            return func_or_class.__name__
        except AttributeError:
            return func_or_class.__class__.__name__

    _builtin_functions[name or _get_name(f)] = f
    return f


@core_helper
def humanize_date(date, locale='en'):
    """
    This humanize a date.
    :param date: Datetime
    :param locale: Locale code
    :return: A human readble date like "days ago"
    """
    return timeago.format(date, None, locale) #human(date, precision=1)


@core_helper
def readble_date(date, locale='en'):
    """
    Returns a readable date"
    :param date: Datetime
    :param locale: Locale code
    :return: A readable date
    """
    ar = arrow.get(date)
    return ar.format('dddd Do of MMMM, YYYY', locale=locale)


@core_helper
def readble_date_with_time(date, locale='en'):
    """
    Returns a readable date"
    :param date: Datetime
    :param locale: Locale code
    :return: A readable date with time
    """
    ar = arrow.get(date)
    return ar.format('dddd Do of MMMM, YYYY. HH:mm:ss', locale=locale)


@core_helper
def simple_date(date):
    """
    Returns a readable date"
    :param date: Datetime
    :return: A readable date
    """
    ar = arrow.get(date)
    return ar.format('DD/MM/YYYY')


@core_helper
def simple_date_usa(date):
    """
    Returns a readable date"
    :param date: Datetime
    :return: A readable date
    """
    ar = arrow.get(date)
    return ar.format('MM/DD/YYYY')


@core_helper
def pluralize(request, noun, size):
    """
    The function calls connected plugins to expand the pluralize capabilities of FormShare
    :param request: Pyramid request
    :param noun: Noun
    :param size: Size
    :return: the plural of a noun based on the locale and size
    """
    if size == 1:
        return noun

    plural = noun

    language = "en"
    if request.locale_name.find('en') >= 0:
        language = "en"

    if language == "en":
        pl = inflect.engine()
        plural = pl.plural(noun)

    # Call connected plugins to see if they have extended or overwrite FormShare pluralize function
    for plugin in p.PluginImplementations(p.IPluralize):
        res = plugin.pluralize(noun, request.locale_name)
        if res != "":
            plural = res
    # Will return English pluralization if none of the above happens
    # return pluralize_en(noun)
    return plural


@core_helper
def get_gravatar_url(email, size=45):
    """
    Return the gravatar based on a email
    :param email: email address
    :param size: Size of the image
    :return: Gravatar URL
    """
    encoded_email = email.encode('utf-8')
    default = "identicon"
    gravatar_url = "https://www.gravatar.com/avatar/" + hashlib.md5(encoded_email.lower()).hexdigest() + "?"
    gravatar_url += urllib.parse.urlencode({'d': default, 's': str(size)})
    return gravatar_url

@core_helper
def is_valid_email(email):
    """
    Checks whether the email is valid
    :param email: Email to check
    :return: True of valid otherwise False
    """
    return validators.email(email)

@core_helper
def is_valid_url(url):
    """
    Checks whether the url is valid
    :param url: Url to check
    :return: True of valid otherwise False
    """
    return validators.url(url)

@core_helper
def get_icon_from_mime_type(mime_type):
    """
    Returns the proper font-awesome file icon based on mimetype
    :param mime_type: Mime type
    :return: FontAwesome icon as string
    """
    icon = "far fa-file"
    if mime_type.find("image") > 0:
        icon = "far fa-file-image"
    if mime_type.find("video") > 0:
        icon = "far fa-file-video"
    if mime_type.find("audio") > 0:
        icon = "far fa-file-audio"
    if mime_type == "text/csv":
        icon = "fas fa-file-csv"
    if mime_type == "application/zip":
        icon = "far fa-file-archive"

    return icon


def load_plugin_helpers():
    """
    (Re)loads the list of helpers provided by plugins.

    This code is based on CKAN
        :Copyright (C) 2007 Open Knowledge Foundation
        :license: AGPL V3, see LICENSE for more details.
    """
    global helper_functions

    helper_functions.clear()
    helper_functions.update(_builtin_functions)

    for plugin in reversed(list(p.PluginImplementations(p.ITemplateHelpers))):
        helper_functions.update(plugin.get_helpers())
