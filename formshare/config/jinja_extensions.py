# -*- coding: utf-8 -*-
"""
    formshare.config.jinja_extensions
    ~~~~~~~~~~~~~~~~~~

    Provides a series of extension to jinja2.

    :copyright: (c) 2017 by QLands Technology Consultants.
    :license: AGPL, see LICENSE for more details.
"""

from jinja2 import nodes
from jinja2 import ext
import logging
from jinja2 import Environment
from webhelpers.html import literal
from jinja2 import FileSystemLoader
import os,re
import formshare.resources as r
from pyramid.threadlocal import get_current_request


jinjaEnv = Environment()
log = logging.getLogger(__name__)

def initialize(pathToTemplates):
    jinjaEnv.loader = FileSystemLoader(pathToTemplates)
    jinjaEnv.add_extension(ext.i18n)
    jinjaEnv.add_extension(SnippetExtension)
    jinjaEnv.add_extension(JSResourceExtension)
    jinjaEnv.add_extension(CSSResourceExtension)
    jinjaEnv.add_extension(extendThis)

def render_snippet(template_name, **kw):
    ''' This function will render the snippet.

    This code is based on CKAN 
    :Copyright (C) 2007 Open Knowledge Foundation
    :license: AGPL V3, see LICENSE for more details.

     '''

    request = get_current_request()
    template = jinjaEnv.get_template(template_name)
    output = template.render(kw, renderer='snippet', _=request.translate)
    output = '\n<!-- Snippet %s start -->\n%s\n<!-- Snippet %s end -->\n' % (template_name, output, template_name)
    return literal(output)


def renderResource(request,libraryName,resourceType,resourceID):
    if resourceType == "JS" or resourceType == "CSS":
        if resourceType == "CSS":
            html = '<link href="{{ file }}" rel="stylesheet">'
        else:
            html = '<script src="{{ file }}"></script>'
        resources = r.need(libraryName,resourceID,resourceType)
        resourcesToInclude = []
        for resource in resources:
            if not request.activeResources.resourceInRequest(libraryName,resource["resourceID"],resourceType):
                request.activeResources.addResource(libraryName,resource["resourceID"],resourceType)
                resourcesToInclude.append(jinjaEnv.from_string(html).render(file=request.host_url + '/' + resource["filePath"]))
        return literal("\n".join(resourcesToInclude))
    else:
        return ""

class extendThis(ext.Extension):
    tags = ['extend_me']

    def __init__(self, environment):
        ext.Extension.__init__(self, environment)
        try:
            self.searchpath = jinjaEnv.loader.searchpath[:]
        except AttributeError:
            # this isn't available on message extraction
            pass

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        node = nodes.Extends(lineno)
        template_file = parser.filename
        template_path = parser.filename

        # We need to have a list of template paths to look for
        if not hasattr(self, 'searchpath'):
            return node

        # First we remove the templates path from the file
        # so to have the just the template file or a template file in a subdirectory of templates
        for searchpath in self.searchpath:
            template_file = template_file.replace(searchpath,'')

        # Here we get the template path of the file
        template_path = template_path.replace(template_file,'')

        # Find the position of the template's path in the list of paths
        index = -1
        try:
            index = self.searchpath.index(template_path)
        except:
            pass
        if index == -1:
            return node

        # index is the position of the this template's path
        # so we search down stream for the template in other paths
        file_to_extend = ''
        for pos in range(index+1, len(self.searchpath)):
            if os.path.exists(self.searchpath[pos] + template_file):
                file_to_extend = self.searchpath[pos] + template_file
                break

        # If the file to extend from exits then set it as a template
        if file_to_extend == '':
            return node
        else:
            node.template = nodes.Const(file_to_extend)

        return node

class BaseExtension(ext.Extension):
    ''' Base class for creating custom jinja2 tags.
    parse expects a tag of the format
    {% tag_name args, kw %}
    after parsing it will call _call(args, kw) which must be defined.

    This code is based on CKAN 
    :Copyright (C) 2007 Open Knowledge Foundation
    :license: AGPL V3, see LICENSE for more details.

    '''

    def parse(self, parser):
        stream = parser.stream
        tag = stream.next()
        # get arguments
        args = []
        kwargs = []
        while not stream.current.test_any('block_end'):
            if args or kwargs:
                stream.expect('comma')
            if stream.current.test('name') and stream.look().test('assign'):
                key = nodes.Const(stream.next().value)
                stream.skip()
                value = parser.parse_expression()
                kwargs.append(nodes.Pair(key, value, lineno=key.lineno))
            else:
                args.append(parser.parse_expression())

        def make_call_node(*kw):
            return self.call_method('_call', args=[
                nodes.List(args),
                nodes.Dict(kwargs),
            ], kwargs=kw)

        return nodes.Output([make_call_node()]).set_lineno(tag.lineno)

class JSResourceExtension(BaseExtension):
    tags = ['jsresource']

    @classmethod
    def _call(cls, args, kwargs):
        assert len(args) == 3
        assert len(kwargs) == 0
        return renderResource(args[0],args[1],"JS",args[2])

class CSSResourceExtension(BaseExtension):
    tags = ['cssresource']

    @classmethod
    def _call(cls, args, kwargs):
        assert len(args) == 3
        assert len(kwargs) == 0
        return renderResource(args[0],args[1],"CSS",args[2])


class SnippetExtension(BaseExtension):
    ''' 
    
    This tags inject small portions of reusable code i.e. snippets
    into a jinja2 template

    {% snippet <template_name> [, <keyword>=<value>].. %}

    This code is based on CKAN 
    :Copyright (C) 2007 Open Knowledge Foundation
    :license: AGPL V3, see LICENSE for more details.


    '''

    tags = ['snippet']

    @classmethod
    def _call(cls, args, kwargs):
        assert len(args) == 1
        return render_snippet(args[0], **kwargs)


def regularise_html(html):
    ''' Take badly formatted html with strings


    This code is based on CKAN
    :Copyright (C) 2007 Open Knowledge Foundation
    :license: AGPL V3, see LICENSE for more details.


    '''

    if html is None:
        return
    html = re.sub('\n', ' ', html)
    matches = re.findall('(<[^>]*>|%[^%]\([^)]*\)\w|[^<%]+|%)', html)
    for i in xrange(len(matches)):
        match = matches[i]
        if match.startswith('<') or match.startswith('%'):
            continue
        matches[i] = re.sub('\s{2,}', ' ', match)
    html = ''.join(matches)
    return html