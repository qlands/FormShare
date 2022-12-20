from jinja2.ext import babel_extract


jinja_extensions = """
                    jinja2.ext.do,jinja2.ext.i18n,                    
                    formshare.config.jinja_extensions:JSResourceExtension,
                    formshare.config.jinja_extensions:CSSResourceExtension,
                    formshare.config.jinja_extensions:ExtendThis,
                   """


def extract_formshare(fileobj, *args, **kw):
    """This code is based on CKAN
    :Copyright (c) 2006-2018 Open Knowledge Foundation and contributors
    :license: AGPL V3, see LICENSE for more details."""
    if "options" not in kw:
        kw["options"] = {}
    if "trimmed" not in kw["options"]:
        kw["options"]["trimmed"] = "True"
    if "silent" not in kw["options"]:
        kw["options"]["silent"] = "False"
    if "extensions" not in kw["options"]:
        kw["options"]["extensions"] = jinja_extensions

    return babel_extract(fileobj, *args, **kw)
