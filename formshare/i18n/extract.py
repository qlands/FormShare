from jinja2.ext import babel_extract as extract_jinja2

import formshare.config.jinja_extensions as je

jinja_extensions = """
                    jinja2.ext.do,jinja2.ext.i18n,                    
                    formshare.config.jinja_extensions:JSResourceExtension,
                    formshare.config.jinja_extensions:CSSResourceExtension,
                    formshare.config.jinja_extensions:ExtendThis,
                   """


def jinja2_cleaner(fileobj, *args, **kw):  # pragma: no cover
    """
    This function take badly formatted html with strings etc and make it beautiful
    generally remove surlus whitespace and kill \n this will break <code><pre>
    tags but they should not be being translated.

    Not included in Coverage because is used by extract_messages and that is not part of the tests

    This code is based on CKAN
    Copyright (C) 2007 Open Knowledge Foundation
    license: AGPL V3.

    :param fileobj:
    :param args:
    :param kw:
    :return:
    """

    kw["options"]["extensions"] = jinja_extensions

    raw_extract = extract_jinja2(fileobj, *args, **kw)

    for lineno, func, message, finder in raw_extract:

        if isinstance(message, str):
            message = je.regularise_html(message)
        elif message is not None:
            message = (je.regularise_html(message[0]), je.regularise_html(message[1]))

        yield lineno, func, message, finder


def extract_formshare(fileobj, *args, **kw):  # pragma: no cover

    # This custom extractor is to support customs tags in the jinja2 extractions. Otherwise the normal extract fail

    # This code is based on CKAN
    # :Copyright (C) 2007 Open Knowledge Foundation
    # :license: AGPL V3, see LICENSE for more details.

    fileobj.read()
    output = jinja2_cleaner(fileobj, *args, **kw)
    fileobj.seek(0)
    return output
