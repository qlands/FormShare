from typing import Any
from jinja2.ext import babel_extract
from formshare.config.jinja_extensions import get_extensions


def extract_formshare(fileobj: Any, *args: Any, **kw: Any) -> Any:
    """This code is based on CKAN
    :Copyright (c) 2006-2018 Open Knowledge Foundation and contributors
    :license: AGPL V3, see LICENSE for more details."""
    extensions = [
        ":".join([ext.__module__, ext.__name__]) if isinstance(ext, type) else ext
        for ext in get_extensions()
    ]
    if "options" not in kw:
        kw["options"] = {}
    if "trimmed" not in kw["options"]:
        kw["options"]["trimmed"] = "True"
    if "silent" not in kw["options"]:
        kw["options"]["silent"] = "False"
    if "extensions" not in kw["options"]:
        kw["options"]["extensions"] = ",".join(extensions)

    return babel_extract(fileobj, *args, **kw)
