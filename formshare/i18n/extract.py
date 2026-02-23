from jinja2.ext import babel_extract

# Comma-separated list of enabled Jinja2 extensions for message extraction.
JINJA_EXTENSIONS = ",".join(
    [
        "jinja2.ext.do",
        "jinja2.ext.i18n",
        "formshare.config.jinja_extensions:JSResourceExtension",
        "formshare.config.jinja_extensions:CSSResourceExtension",
        "formshare.config.jinja_extensions:ExtendThis",
    ]
)


def extract_formshare(fileobj, *args, **kwargs):
    """
    Babel extractor wrapper for FormShare templates.

    Ensures consistent extraction options (trim blocks, silence failures, and
    enable FormShare's custom Jinja extensions) before delegating to Jinja2's
    babel_extract.
    """
    options = kwargs.setdefault("options", {})

    # Use explicit defaults only if the caller didn't provide them.
    options.setdefault("trimmed", True)
    options.setdefault("silent", False)
    options.setdefault("extensions", JINJA_EXTENSIONS)

    return babel_extract(fileobj, *args, **kwargs)
