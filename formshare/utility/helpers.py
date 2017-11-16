# -*- coding: utf-8 -*-
"""
    formshare.resources.resources
    ~~~~~~~~~~~~~~~~~~

    Provides the different helper functions to a pyramid request.

    :copyright: (c) 2017 by QLands Technology Consultants.
    :license: AGPL, see LICENSE for more details.
"""

from ago import human
import arrow
from pattern.text.en import pluralize as pluralize_en
from pattern.text.es import pluralize as pluralize_es
from pattern.text.de import pluralize as pluralize_de
from pattern.text.fr import pluralize as pluralize_fr
from pattern.text.it import pluralize as pluralize_it
from pattern.text.nl import pluralize as pluralize_nl
import formshare.plugins as p

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

        if language == "es":
            return pluralize_es(noun)
        if language == "de":
            return pluralize_de(noun)
        if language == "de":
            return pluralize_de(noun)
        if language == "fr":
            return pluralize_fr(noun)
        if language == "it":
            return pluralize_it(noun)
        if language == "nl":
            return pluralize_nl(noun)

        #Call connected plugins to see if they have extended formshare pluralize function
        for plugin in p.PluginImplementations(p.IPluralize):
            res = plugin.pluralize(noun,self.request.locale_name)
            if res != "":
                return res
        #Will return English pluralization if none of the above happens
        return pluralize_en(noun)


