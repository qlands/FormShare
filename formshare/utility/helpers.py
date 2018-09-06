"""
    Provides the different helper functions to a pyramid request.

    :copyright: (c) 2017 by QLands Technology Consultants.
    :license: AGPL, see LICENSE for more details.
"""

from ago import human
import arrow
import inflect
import formshare.plugins as p
import urllib, hashlib
from pyramid.csrf import new_csrf_token

__all__ = [
    'helper'
]

class helper:
    request = None
    def __init__(self, request):
        self.request = request

    #This function will humanize a date using ago
    def humanize_date(self,date):
        return human(date,precision=1)

    def readble_date(self,date):
        ar = arrow.get(date)
        return ar.format('dddd Do of MMMM, YYYY')

    def pluralize(self,noun,size):
        if size == 1:
            return noun
        language = None

        if self.request.locale_name.find('en') >= 0:
            language = "en"
        if self.request.locale_name.find('es') >= 0:
            language = "es"
        if self.request.locale_name.find('de') >= 0:
            language = "de"
        if self.request.locale_name.find('fr') >= 0:
            language = "fr"
        if self.request.locale_name.find('it') >= 0:
            language = "it"
        if self.request.locale_name.find('nl') >= 0:
            language = "nl"

        plural = noun

        if language == "en":
            pl = inflect.engine()
            plural = pl.plural(noun)


        #Call connected plugins to see if they have extended or overwrite formshare pluralize function
        for plugin in p.PluginImplementations(p.IPluralize):
            res = plugin.pluralize(noun,self.request.locale_name)
            if res != "":
                plural = res
        #Will return English pluralization if none of the above happens
        # return pluralize_en(noun)
        return plural

    def getGravatarUrl(self,email,size=45):
        encodedEmail = email.encode('utf-8')
        default = "identicon"
        gravatar_url = "http://www.gravatar.com/avatar/" + hashlib.md5(encodedEmail.lower()).hexdigest() + "?"
        gravatar_url += urllib.parse.urlencode({'d':default, 's':str(size)})
        return gravatar_url

    def get_csrf_token(self,request):
        return new_csrf_token(request)