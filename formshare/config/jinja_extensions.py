import logging
from formshare.processes.logging.loggerclass import SecretLogger
import os

import formshare.resources as r
from jinja2 import Environment
from jinja2 import FileSystemLoader
from jinja2 import ext, nodes
from webhelpers2.html import literal

jinjaEnv = Environment(autoescape=True)
logging.setLoggerClass(SecretLogger)
log = logging.getLogger("formshare")


def initialize(path_to_templates):
    jinjaEnv.loader = FileSystemLoader(path_to_templates)
    jinjaEnv.add_extension(ext.i18n)
    jinjaEnv.add_extension(JSResourceExtension)
    jinjaEnv.add_extension(CSSResourceExtension)
    jinjaEnv.add_extension(ExtendThis)


def render_resource(
    request, library_name, resource_type, resource_id
):  # pragma: no cover
    """
    This function will inject a resource from Jinja2 using the jsresource or cssresource tags. Not in Coverage
    because Coverage cannot track them from Jinja2
    :param request:
    :param library_name:
    :param resource_type:
    :param resource_id:
    :return:
    """
    if resource_type == "JS" or resource_type == "CSS":
        if resource_type == "CSS":
            html = '<link href="{{ file }}" rel="stylesheet">'
        else:
            html = '<script src="{{ file }}"></script>'
        resources = r.need(library_name, resource_id, resource_type)
        resources_to_include = []
        for resource in resources:
            if not request.activeResources.resource_in_request(
                library_name, resource["resourceID"], resource_type
            ):
                request.activeResources.add_resource(
                    library_name, resource["resourceID"], resource_type
                )
                resources_to_include.append(
                    jinjaEnv.from_string(html).render(
                        file=request.application_url + "/" + resource["filePath"]
                    )
                )
        return literal("\n".join(resources_to_include))
    else:
        return ""


class ExtendThis(ext.Extension):  # pragma: no cover
    """
    This class implements the extend_me tag. Not include in Coverage because Coverage cannot detect its call
    """

    tags = ["extend_me"]

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
        if not hasattr(self, "searchpath"):
            return node

        # First we remove the templates path from the file
        # so to have the just the template file or a template file in a subdirectory of templates
        for searchpath in self.searchpath:
            template_file = template_file.replace(searchpath, "")

        # Here we get the template path of the file
        template_path = template_path.replace(template_file, "")

        # Find the position of the template's path in the list of paths
        index = -1
        try:
            index = self.searchpath.index(template_path)
        except ValueError:
            pass
        if index == -1:
            return node

        # index is the position of the this template's path
        # so we search down stream for the template in other paths
        file_to_extend = ""
        for pos in range(index + 1, len(self.searchpath)):
            if os.path.exists(self.searchpath[pos] + template_file):
                file_to_extend = self.searchpath[pos] + template_file
                break

        # If the file to extend from exits then set it as a template
        if file_to_extend == "":
            return node
        else:
            node.template = nodes.Const(file_to_extend)

        return node


class BaseExtension(ext.Extension):  # pragma: no cover
    """
    Base class for custom Jinja2 tags.

    Expected tag format:
        {% tag_name arg1, arg2, key=value, ... %}

    Subclasses must implement:
        _call(args_list, kwargs_dict, **context_kwargs) -> str | Markup | ...
    """

    def parse(self, parser):
        stream = parser.stream
        start_token = next(stream)  # the tag token itself

        args_list: list[nodes.Expr] = []
        kw_pairs: list[nodes.Pair] = []

        # Parse zero or more comma-separated items until the end of the block.
        # Each item is either:
        #   - a keyword assignment:  name = expression
        #   - a positional expression
        first = True
        while not stream.current.test("block_end"):
            if not first:
                stream.expect("comma")
            first = False

            if self._looks_like_kwarg(stream):
                name_token = stream.expect("name")
                stream.expect("assign")
                key_node = nodes.Const(name_token.value, lineno=name_token.lineno)
                val_node = parser.parse_expression()
                kw_pairs.append(
                    nodes.Pair(key_node, val_node, lineno=name_token.lineno)
                )
            else:
                args_list.append(parser.parse_expression())

        # Build call: self._call([args...], {kwargs...})
        call = self.call_method(
            "_call",
            args=[
                nodes.List(args_list, lineno=start_token.lineno),
                nodes.Dict(kw_pairs, lineno=start_token.lineno),
            ],
        )

        return nodes.Output([call]).set_lineno(start_token.lineno)

    @staticmethod
    def _looks_like_kwarg(stream) -> bool:
        """
        Detect pattern: <name> '='
        """
        return stream.current.test("name") and stream.look().test("assign")


class JSResourceExtension(BaseExtension):  # pragma: no cover
    tags = ["jsresource"]

    @classmethod
    def _call(cls, args, kwargs):
        assert len(args) == 3
        assert len(kwargs) == 0
        return render_resource(args[0], args[1], "JS", args[2])


class CSSResourceExtension(BaseExtension):  # pragma: no cover
    tags = ["cssresource"]

    @classmethod
    def _call(cls, args, kwargs):
        assert len(args) == 3
        assert len(kwargs) == 0
        return render_resource(args[0], args[1], "CSS", args[2])
