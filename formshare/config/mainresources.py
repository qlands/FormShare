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