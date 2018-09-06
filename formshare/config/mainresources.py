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

    #----------------Landing page--------------------
    # # Add core resource library
    # r.addLibrary('landing', os.path.join(apppath, 'jsandcss/landing'), config)
    # # Add core CSS and JS
    # r.addCSSResource('landing', 'bootstrap', 'css/bootstrap.min.css')
    # r.addCSSResource('landing', 'animate', 'css/animate.min.css')
    # r.addCSSResource('landing', 'font-awesome', 'font-awesome/css/font-awesome.min.css')
    # r.addCSSResource('landing', 'style', 'css/style.css')
    # 
    # r.addJSResource('landing', 'jquery', 'js/jquery-2.1.1.js')
    # r.addJSResource('landing', 'pace', 'js/pace.min.js')
    # r.addJSResource('landing', 'bootstrap', 'js/bootstrap.min.js')
    # r.addJSResource('landing', 'classie', 'js/classie.js')
    # r.addJSResource('landing', 'animate-header', 'js/cbpAnimatedHeader.js')
    # r.addJSResource('landing', 'wow', 'js/wow.min.js')
    # r.addJSResource('landing', 'inspinia', 'js/inspinia.js')

    r.addLibrary('formshare', os.path.join(apppath, 'jsandcss'), config)

    #----------------------------Basic CSS-----------------------
    r.addCSSResource('formshare', 'bootstrap', 'css/bootstrap.min.css')
    r.addCSSResource('formshare', 'font-5', 'font-awesome/css/all.css')
    r.addCSSResource('formshare', 'font-awesome', 'font-awesome/css/v4-shims.css')
    r.addCSSResource('formshare', 'sweetalert', 'css/plugins/sweetalert/sweetalert.css')
    r.addCSSResource('formshare', 'animate', 'css/animate.css')
    r.addCSSResource('formshare', 'style', 'css/style.css')
    r.addCSSResource('formshare', 'rtl', 'css/plugins/bootstrap-rtl/bootstrap-rtl.min.css', 'bootstrap')

    #----------------------------Basic JS----------------------------------------------------
    r.addJSResource('formshare', 'jquery', 'js/jquery-3.1.1.min.js')
    r.addJSResource('formshare', 'popper', 'js/popper.min.js')
    r.addJSResource('formshare', 'bootstrap', 'js/bootstrap.min.js')
    r.addJSResource('formshare', 'metismenu', 'js/plugins/metisMenu/jquery.metisMenu.js')
    r.addJSResource('formshare', 'slimscroll', 'js/plugins/slimscroll/jquery.slimscroll.min.js')
    r.addJSResource('formshare', 'pace', 'js/plugins/pace/pace.min.js')
    r.addJSResource('formshare', 'wow', 'js/plugins/wow/wow.min.js')
    r.addJSResource('formshare', 'sweetalert', 'js/plugins/sweetalert/sweetalert.min.js','pace')
    r.addJSResource('formshare', 'inspinia', 'js/inspinia.js',None)

    #----------------------------Profile----------------------------------
    r.addCSSResource('formshare', 'bsmarkdown', 'css/plugins/bootstrap-markdown/bootstrap-markdown.min.css', 'sweetalert')
    r.addJSResource('formshare', 'bsmarkdown', 'js/plugins/bootstrap-markdown/bootstrap-markdown.js',None)
    r.addJSResource('formshare', 'markdown', 'js/plugins/bootstrap-markdown/markdown.js', 'bsmarkdown')
    r.addJSResource('formshare', 'clipboard', 'js/plugins/clipboard/clipboard.js',None)


