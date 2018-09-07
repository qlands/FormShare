'''Helper functions

Consists of functions to typically be used within templates, but also
available to Controllers. This module is available to templates as 'request.h'.

'''

from ago import human
import arrow
import inflect
import formshare.plugins as p
import urllib, hashlib

class HelperAttributeDict(dict):
    '''

    This code is based on CKAN
        :Copyright (C) 2007 Open Knowledge Foundation
        :license: AGPL V3, see LICENSE for more details.

    '''
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
def humanize_date(date):
    '''This humanize a date. For example it returns "days ago"

        '''
    return human(date,precision=1)

@core_helper
def readble_date(date):
    '''Returns a readable date"

        '''
    ar = arrow.get(date)
    return ar.format('dddd Do of MMMM, YYYY')

@core_helper
def pluralize(request,noun,size):
    '''Returns the plural of a noun based on the locale and size."

        The function calls connected plugins to expand the pluralize capabilities of FormShare

        '''
    if size == 1:
        return noun

    plural = noun

    language = "en"
    if request.locale_name.find('en') >= 0:
        language = "en"

    if language == "en":
        pl = inflect.engine()
        plural = pl.plural(noun)

    #Call connected plugins to see if they have extended or overwrite formshare pluralize function
    for plugin in p.PluginImplementations(p.IPluralize):
        res = plugin.pluralize(noun,request.locale_name)
        if res != "":
            plural = res
    #Will return English pluralization if none of the above happens
    # return pluralize_en(noun)
    return plural

@core_helper
def getGravatarUrl(email,size=45):
    '''Return the gravatar based on a URL"


        '''
    encodedEmail = email.encode('utf-8')
    default = "identicon"
    gravatar_url = "http://www.gravatar.com/avatar/" + hashlib.md5(encodedEmail.lower()).hexdigest() + "?"
    gravatar_url += urllib.parse.urlencode({'d':default, 's':str(size)})
    return gravatar_url


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