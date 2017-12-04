'''
These series of functions help plugin developers 
to manipulate the host behaviour without the trouble if dealing with it

This code is based on CKAN 
:Copyright (C) 2007 Open Knowledge Foundation
:license: AGPL V3, see LICENSE for more details.

'''

import inspect
import os
from formshare.views.classes import publicView,privateView

__all__ = [
    'addTemplatesDirectory','addStaticView','addJSResource','addCSSResource',
    'addLibrary','addRoute','addFieldToUserSchema','addFieldToProjectSchema',
    'addFieldToEnumeratorSchema','addFieldToEnumeratorGroupSchema',
    'addFieldToDataUserSchema','addFieldToDataGroupSchema',
    'addFieldToFormSchema','formSharePublicView','formSharePrivateView'
]

def __returnCurrentPath():
    frame, filename, line_number, function_name, lines, index = \
        inspect.getouterframes(inspect.currentframe())[2]
    return os.path.dirname(filename)

#Utility functions for IConfig
def addTemplatesDirectory(config,relative_path,prepend=True):
    callerPath = __returnCurrentPath()
    templates_path = os.path.join(callerPath, relative_path)
    if os.path.exists(templates_path):
        config.add_jinja2_search_path(searchpath=templates_path,prepend=prepend)
        if prepend == True:
            config.registry.settings['templatesPaths'].insert(0,templates_path)
        else:
            config.registry.settings['templatesPaths'].append(templates_path)
    else:
        raise Exception("Templates path {} does not exists".format(relative_path))


def addStaticView(config,viewName,relative_path,cache_max_age=3600):
    callerPath = __returnCurrentPath()
    static_path = os.path.join(callerPath, relative_path)
    if os.path.exists(static_path):
        introspector = config.introspector
        if introspector.get('static views', viewName,None) is None:
            config.add_static_view(viewName, static_path, cache_max_age=cache_max_age)
    else:
        raise Exception("Static path {} does not exists".format(relative_path))

#Utility functions for IResource
def addJSResource(libraryName,resourceID,resourceFile,depends='CHAIN'):
    return {'libraryname':libraryName,'id':resourceID,'file':resourceFile,'depends':depends}

def addCSSResource(libraryName,resourceID,resourceFile,depends='CHAIN'):
    return {'libraryname': libraryName, 'id': resourceID, 'file': resourceFile, 'depends': depends}

def addLibrary(name,path):
    callerPath = __returnCurrentPath()
    library_path = os.path.join(callerPath, path)
    if os.path.exists(library_path):
        return {'name':name,'path':library_path}
    else:
        raise Exception("Library path {} does not exists".format(path))

#Utility functions for IRoute
def addRoute(name,path,view,renderer):
    return {'name': name, 'path': path, 'view': view, 'renderer': renderer}

# Utility functions for the ISchema
def addFieldToUserSchema(fieldName,fieldDesc):
    return {'schema':'user','fieldname':fieldName,'fielddesc':fieldDesc}

def addFieldToProjectSchema(fieldName,fieldDesc):
    return {'schema': 'project', 'fieldname': fieldName, 'fielddesc': fieldDesc}

def addFieldToEnumeratorSchema(fieldName,fieldDesc):
    return {'schema': 'enumerator', 'fieldname': fieldName, 'fielddesc': fieldDesc}

def addFieldToEnumeratorGroupSchema(fieldName,fieldDesc):
    return {'schema': 'enumgroup', 'fieldname': fieldName, 'fielddesc': fieldDesc}

def addFieldToDataUserSchema(fieldName,fieldDesc):
    return {'schema': 'datauser', 'fieldname': fieldName, 'fielddesc': fieldDesc}

def addFieldToDataGroupSchema(fieldName,fieldDesc):
    return {'schema': 'datagroup', 'fieldname': fieldName, 'fielddesc': fieldDesc}

def addFieldToFormSchema(fieldName,fieldDesc):
    return {'schema': 'form', 'fieldname': fieldName, 'fielddesc': fieldDesc}

#FormShare view classes
class formSharePublicView(publicView):
    '''
        A view class for plugins which require a public (not login required) view.
    '''

class formSharePrivateView(privateView):
    '''
        A view class for plugins which require a private (login required) view.
    '''
