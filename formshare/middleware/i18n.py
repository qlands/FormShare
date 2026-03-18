"""
formshare.middleware.i18n
~~~~~~~~~~~~~~~~~~~~~~~~~~

Babel-based translation that replaces Pyramid's i18n event subscribers.

Pyramid wired translation via BeforeRender / NewRequest events.
Here we build the same translator directly so FormShareRequest can expose:

    self._ = self.request.translate
    _("Some string")

Plugin translations are merged automatically for any plugin that
implements ITranslation.

Locale detection order:
    1. Cookie  "_LOCALE_"   (Pyramid's default locale cookie name)
    2. "Accept-Language" header
    3. Default fallback ("en")
"""

import logging
import os
import sys
from typing import Callable
from formshare.processes.logging.loggerclass import SecretLogger
from babel.support import Translations

logging.setLoggerClass(SecretLogger)
log = logging.getLogger("formshare")

# Module-level cache: (locale_name) -> merged Translations object.
# Rebuilt if invalidated (e.g. during development hot-reload).
_translations_cache: dict = {}


def get_locale_name(request) -> str:
    """Determine the locale for *request*.

    Checks the "_LOCALE_" cookie first (matching Pyramid's behaviour),
    then falls back to the Accept-Language header, then to "en".
    """
    locale = request.cookies.get("_LOCALE_")
    if locale:
        return locale

    accept_language = request.headers.get("Accept-Language", "")
    if accept_language:
        # Take the first language tag and normalise  (e.g. "es-MX,es;q=0.9" -> "es_MX")
        primary = accept_language.split(",")[0].split(";")[0].strip()
        locale = primary.replace("-", "_")
        if locale:
            return locale

    return "en"


def build_translator(locale_name: str) -> Callable[[str], str]:
    """Return a translate(msgid) callable for *locale_name*.

    Loads FormShare's core translations and merges all plugin translations
    (ITranslation) – identical logic to the old add_localizer() event handler.

    Results are cached per locale_name.
    """
    if locale_name in _translations_cache:
        return _make_callable(_translations_cache[locale_name])

    # -- Core FormShare locale directory --
    module = sys.modules.get("formshare")
    if module is None:  # pragma: no cover
        import formshare as module
    formshare_locale_path = os.path.join(os.path.dirname(module.__file__), "locale")

    try:
        translations = Translations.load(
            formshare_locale_path, [locale_name], "formshare"
        )
    except Exception as e:
        log.warning(
            "Could not load FormShare translations for '%s': %s", locale_name, e
        )
        translations = Translations()  # identity translator

    # -- Merge plugin translations --
    try:
        import formshare.plugins as p

        for plugin in p.PluginImplementations(p.ITranslation):
            try:
                plugin_dir = plugin.get_translation_directory()
                plugin_domain = plugin.get_translation_domain()
                plugin_translations = Translations.load(
                    plugin_dir, [locale_name], plugin_domain
                )
                translations.merge(plugin_translations)
            except Exception as e:
                log.warning(
                    "Could not load translations for plugin %s: %s",
                    plugin.__class__.__name__,
                    e,
                )
    except Exception as e:
        log.debug("Plugin translation loading skipped: %s", e)

    _translations_cache[locale_name] = translations
    return _make_callable(translations)


def _make_callable(translations: Translations) -> Callable[[str], str]:
    """Wrap *translations* in a simple callable that matches FormShare's
    usage: _(msgid) -> str."""

    def translate(msgid, **kwargs):
        # Support translationstring-style mapping argument (ignored here –
        # the templates do their own substitution).
        if not msgid:
            return msgid
        result = translations.gettext(str(msgid))
        return result

    return translate


def invalidate_cache():
    """Clear the translations cache.  Call after hot-reloading plugins."""
    _translations_cache.clear()
