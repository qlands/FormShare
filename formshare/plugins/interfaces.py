'''

This file declares the PCA interfaces and their methods:

This code is based on CKAN 
:Copyright (C) 2007 Open Knowledge Foundation
:license: AGPL V3, see LICENSE for more details.

'''


__all__ = [
    'Interface',
    'IRoutes',
    'IConfig',
    'IResource',
    'IPluginObserver'
]


from inspect import isclass
from pyutilib.component.core import Interface as _pca_Interface

class Interface(_pca_Interface):

    @classmethod
    def provided_by(cls, instance):
        return cls.implemented_by(instance.__class__)

    @classmethod
    def implemented_by(cls, other):
        if not isclass(other):
            raise TypeError("Class expected", other)
        try:
            return cls in other._implements
        except AttributeError:
            return False

class IRoutes(Interface):
    """
    Plugin into the creation of routes of the host program.

    """
    def before_mapping(self,config):
        """
        Called before the mapping of router of the host app.

        :param config: ``pyramid.config`` object that can be used to call add_view
        :return Returns a dict array [{'name':'myroute','path':'/myroute','view',viewDefinition,'renderer':'renderere_used'}]
        """
        return []

    def after_mapping(self,config):
        """
        Called after the mapping of router of the host app

        :param config: ``pyramid.config`` object that can be used to call add_view
        :return Returns a dict array [{'name':'myroute','path':'/myroute','view',viewDefinition,'renderer':'renderere_used'}]
        """
        return []

class IConfig(Interface):
    """
    Allows the modification of the Pyramid config 
    """

    def update_config(self, config):
        """
        Called in the init of the host application.

        :param config: ``pyramid.config`` object
        """

class IResource(Interface):
    """
        Allows to hook into the creation of FanStatic libraries and resources         
    """

    def add_libraries(self,config):
        """
        Called by the host application so plugins can add new FanStatic libraries AFTER the host

        :param config: ``pyramid.config`` object
        :return Returns a dict array [{'name':'mylibrary','path':'/path/to/my/resources'}]
        """
        return []

    def add_JSResources(self,config):
        """
        Called by the host application so plugins can add new FanStatic JS Resources AFTER the host
        
        :param config: ``pyramid.config`` object        
        :return Returns a dict array [{'libraryname':'mylibrary','id':'myResourceID','file':'/relative/path/to/jsFile','depends':'resourceID'}]
        """
        return []

    def add_CSSResources(self, config):
        """
        Called by the host application so plugins can add new FanStatic JS Resources AFTER the host

        :param config: ``pyramid.config`` object        
        :return Returns a dict array [{'libraryname':'mylibrary','id':'myResourceID','file':'/relative/path/to/jsFile','depends':'resourceID'}]
        """
        return []

class IPluralize(Interface):
    """
        Allows to hook into the pluralization function so plugins can extend the pluralization of formshare
    """
    def pluralize(self,noun,locale):
        """
            Called the packages are created

            :param noun: ``Noun to be pluralized``
            :param locale: ``The current locate code e.g. en``
            :return the noun in plural form
        """

class IPluginObserver(Interface):
    """
    Plugin to the plugin loading mechanism
    """

    def before_load(self, plugin):
        """
        Called before a plugin is loaded
        This method is passed the plugin class.
        """

    def after_load(self, service):
        """
        Called after a plugin has been loaded.
        This method is passed the instantiated service object.
        """

    def before_unload(self, plugin):
        """
        Called before a plugin is loaded
        This method is passed the plugin class.
        """

    def after_unload(self, service):
        """
        Called after a plugin has been unloaded.
        This method is passed the instantiated service object.
        """