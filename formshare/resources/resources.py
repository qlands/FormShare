"""
    Provides the declaration and injection of resources into Jinja2.

    :copyright: (c) 2018 by QLands Technology Consultants.
    :license: AGPL, see LICENSE.txt for more details.
"""

import os
from lxml import etree

__all__ = [
    'addLibrary', 'addJSResource',
    'addCSSResource','need'
]

_LIBRARIES = []

def library_found(name):
    for library in _LIBRARIES:
        if library["name"] == name:
            return True
    return False

def library_index(name):
    for pos in range(0,len(_LIBRARIES)):
        if _LIBRARIES[pos]["name"] == name:
            return pos
    return -1

def library_path_exits(path):
    return os.path.exists(path)

def library_path_found(path):
    for library in _LIBRARIES:
        if os.path.normpath(library["path"]) == os.path.normpath(path):
            return True
    return False


def addLibrary(name,path,config):
    if not library_found(name):
        if library_path_exits(path):
            if not library_path_found(path):
                _LIBRARIES.append({'name': name,'path': path,'library': etree.Element("root"),'CSSResources':[],'JSResources':[]})
                config.add_static_view(name, path, cache_max_age=3600)
            else:
                raise Exception("Path {} already in use".format(path))
        else:
            raise Exception("Path {} not found".format(path))
    else:
        raise Exception("Library name {} is already in use".format(name))

def resourceExists(libraryIndex,resourceID,resourceType='JS'):
    if resourceType == 'JS':
        for resource in _LIBRARIES[libraryIndex]["JSResources"]:
            if resource["resourceID"] == resourceID:
                return True
    if resourceType == 'CSS':
        for resource in _LIBRARIES[libraryIndex]["CSSResources"]:
            if resource["resourceID"] == resourceID:
                return True
    return False

def resourceIndex(libraryIndex, resourceID,resourceType='JS'):
    if resourceType == 'JS':
        for index in range(0,len(_LIBRARIES[libraryIndex]["JSResources"])) :
            if _LIBRARIES[libraryIndex]["JSResources"][index]["resourceID"] == resourceID:
                return index
    if resourceType == 'CSS':
        for index in range(0, len(_LIBRARIES[libraryIndex]["CSSResources"])):
            if _LIBRARIES[libraryIndex]["CSSResources"][index]["resourceID"] == resourceID:
                return index
    return -1

def addResourceToLibrary(libraryIndex,resourceType,resourceID,resourceFile,depends = None):
    if depends == None:
        resource = etree.Element(resourceType)
        resource.set("resourceID", resourceID)
        resource.set("resourceFile", resourceFile)
        _LIBRARIES[libraryIndex]["library"].append(resource)
    else:
        toResource = _LIBRARIES[libraryIndex]["library"].findall(".//" + resourceType + "[@resourceID='" + depends + "']")
        if toResource:
            resource = etree.Element(resourceType)
            resource.set("resourceID", resourceID)
            resource.set("resourceFile", resourceFile)
            toResource[0].append(resource)
        else:
            raise Exception("Dependency resource {} does not exists".format(depends))
    if resourceType == "JS":
        _LIBRARIES[libraryIndex]["JSResources"].append({'libraryIndex':libraryIndex,'resourceID':resourceID})
    else:
        _LIBRARIES[libraryIndex]["CSSResources"].append({'libraryIndex': libraryIndex, 'resourceID': resourceID})

def addResource(libraryName,resourceID,resourceFile,resourceType='JS',depends='CHAIN'):
    index = library_index(libraryName)
    if index >= 0:
        libraryPath = _LIBRARIES[index]["path"]
        pathToResource = os.path.join(libraryPath, resourceFile)
        if os.path.exists(pathToResource):
            if not resourceExists(index,resourceID,resourceType):
                if resourceType == 'JS':
                    if len(_LIBRARIES[index]["JSResources"]) == 0:
                        addResourceToLibrary(index, resourceType, resourceID, resourceFile)
                    else:
                        if depends == 'CHAIN':
                            addResourceToLibrary(index, resourceType, resourceID, resourceFile,
                                                 _LIBRARIES[index]["JSResources"][len(_LIBRARIES[index]["JSResources"])-1]["resourceID"])
                        else:
                            if depends is None:
                                addResourceToLibrary(index, resourceType, resourceID, resourceFile)
                            else:
                                depIndex = resourceIndex(index,depends)
                                if depIndex >= 0:
                                    addResourceToLibrary(index, resourceType, resourceID, resourceFile,
                                                         _LIBRARIES[index]["JSResources"][depIndex]["resourceID"])
                                else:
                                    raise Exception("Dependency resource {} does not exists".format(depends))
                else:
                    if len(_LIBRARIES[index]["CSSResources"]) == 0:
                        addResourceToLibrary(index, resourceType, resourceID, resourceFile)
                    else:
                        if depends == 'CHAIN':
                            addResourceToLibrary(index, resourceType, resourceID, resourceFile,
                                                 _LIBRARIES[index]["CSSResources"][len(_LIBRARIES[index]["CSSResources"]) - 1]["resourceID"])
                        else:
                            if depends is None:
                                addResourceToLibrary(index, resourceType, resourceID, resourceFile)
                            else:
                                depIndex = resourceIndex(index,depends,'CSS')
                                if depIndex >= 0:
                                    addResourceToLibrary(index, resourceType, resourceID, resourceFile,
                                                         _LIBRARIES[index]["CSSResources"][depIndex]["resourceID"])
                                else:
                                    raise Exception("Dependency resource {} does not exists".format(depends))
            else:
                raise Exception("Resource id {} already in list".format(resourceID))
        else:
            raise Exception("Resource file {} does not exists".format(resourceFile))
    else:
        raise Exception("Library name {} does not exists".format(libraryName))

def addJSResource(libraryName,resourceID,resourceFile,depends='CHAIN'):
    addResource(libraryName,resourceID,resourceFile,'JS',depends)

def addCSSResource(libraryName,resourceID,resourceFile,depends='CHAIN'):
    addResource(libraryName,resourceID,resourceFile,'CSS',depends)

def need(libraryName, resourceID, resourceType):
    ancestors = []
    index = library_index(libraryName)
    if index >= 0:
        resource = _LIBRARIES[index]["library"].findall(".//" + resourceType + "[@resourceID='" + resourceID + "']")
        if resource:
            libraryPath = _LIBRARIES[index]["name"]
            for ancestor in resource[0].iterancestors():
                if ancestor.tag != "root":
                    ancestorID = ancestor.get("resourceID")
                    ancestorFile = ancestor.get("resourceFile")
                    filePath = os.path.join(libraryPath,ancestorFile)
                    ancestors.insert(0, {'resourceID':ancestorID,'filePath':filePath})
            ancestors.append({'resourceID':resourceID,'filePath':os.path.join(libraryPath,resource[0].get("resourceFile"))})
    return ancestors


