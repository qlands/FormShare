# -*- coding: utf-8 -*-
"""
    formshare.config.mainresources
    ~~~~~~~~~~~~~~~~~~

    Provides the main JS and CSS resources to FormShare.

    :copyright: (c) 2017 by QLands Technology Consultants.
    :license: AGPL, see LICENSE for more details.
"""

import formshare.resources as r
import os

def createResources(apppath,config):
    # Add core fanstatic library

    r.addLibrary('coreresources', os.path.join(apppath, 'jsandcss'), config)

    # Add core CSS and JS
    r.addCSSResource('coreresources', 'bootstrapcss', 'bootstrap.min.css')
    r.addCSSResource('coreresources', 'theme', 'theme.css')
    r.addJSResource('coreresources', 'jquery', 'jquery.min.js')
    r.addJSResource('coreresources', 'bootstrap', 'bootstrap.min.js')