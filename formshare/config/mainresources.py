import formshare.resources as r
import os

def createResources(apppath,config):
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

    #------------------------------Add/Edit project--------------------------------------
    r.addCSSResource('formshare', 'switchery', 'css/plugins/switchery/switchery.css',None)
    r.addJSResource('formshare', 'switchery', 'js/plugins/switchery/switchery.js', None)

