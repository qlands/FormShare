"""
formshare.i18n.i18n
~~~~~~~~~~~~~~~~~~~~

Pyramid event handlers kept for backwards compatibility.

FormShare 3.0 uses formshare.middleware.i18n directly via FormShareRequest,
so these handlers are never wired to Pyramid events anymore.  The module is
preserved so any external code that imports it continues to work.
"""

# Translations are now handled by formshare.middleware.i18n.build_translator()
# which is called per-request in FormShareRequest.translate.
