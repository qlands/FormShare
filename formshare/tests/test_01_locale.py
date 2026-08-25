#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Regression tests for locale handling.

The "_LOCALE_" cookie and the Accept-Language header are client controlled.
Before these guards, both were passed straight to babel.Locale(), which treats
its argument as a bare language code: Locale("zh_CN") raises UnknownLocaleError
even though zh_CN is a perfectly ordinary browser locale.  Because that call
lives in the view constructors - including the 404 view - every affected
request became a 500 with a full traceback.
"""

from babel import Locale

from formshare.middleware.i18n import (
    DEFAULT_LOCALE,
    get_locale,
    get_locale_name,
    get_supported_locales,
    normalize_locale,
)


class _FakeRequest(object):
    """Minimal stand-in exposing just what get_locale_name() reads."""

    def __init__(self, cookies=None, headers=None):
        self.cookies = cookies or {}
        self.headers = headers or {}


class TestNormalizeLocale(object):
    def test_supported_locales_always_include_default(self):
        assert DEFAULT_LOCALE in get_supported_locales()

    def test_shipped_locales_survive(self):
        for locale in get_supported_locales():
            assert normalize_locale(locale) == locale

    def test_regional_variants_fall_back_to_base_language(self):
        assert normalize_locale("es-MX") == "es"
        assert normalize_locale("es_MX") == "es"
        assert normalize_locale("pt-BR") == "pt"
        assert normalize_locale("PT_br") == "pt"

    def test_untranslated_locale_falls_back_to_default(self):
        # zh_CN produced 55 of the 500s observed in production.
        assert normalize_locale("zh_CN") == DEFAULT_LOCALE
        assert normalize_locale("de") == DEFAULT_LOCALE

    def test_malformed_input_falls_back_to_default(self):
        # "*" is a legal Accept-Language value and produced the other 16.
        for raw in (
            "*",
            "",
            "   ",
            "a",
            "xx",
            "!!!",
            "en" * 40,
            None,
            42,
            [],
            "../../../etc/passwd",
            "en/../secret",
            "en\x00",
        ):
            assert normalize_locale(raw) == DEFAULT_LOCALE

    def test_result_is_always_parsable_by_babel(self):
        for raw in ("zh_CN", "*", "de", "es-MX", None, "../../etc/passwd"):
            Locale.parse(normalize_locale(raw))  # must not raise


class TestGetLocale(object):
    def test_returns_locale_for_valid_identifiers(self):
        assert get_locale("es").language == "es"

    def test_parses_territory_forms_that_locale_ctor_rejects(self):
        # The whole point: Locale("zh_CN") raises, Locale.parse("zh_CN") works.
        assert get_locale("zh_CN").language == "zh"

    def test_never_raises(self):
        for raw in ("*", "", None, 42, "!!!", "xx", "../../etc/passwd"):
            assert get_locale(raw).character_order in (
                "left-to-right",
                "right-to-left",
            )

    def test_falls_back_to_default_on_bad_input(self):
        assert str(get_locale("*")) == DEFAULT_LOCALE


class TestGetLocaleName(object):
    def test_cookie_wins_over_header(self):
        request = _FakeRequest(
            cookies={"_LOCALE_": "fr"}, headers={"Accept-Language": "es"}
        )
        assert get_locale_name(request) == "fr"

    def test_hostile_cookie_is_sanitised(self):
        request = _FakeRequest(cookies={"_LOCALE_": "../../../etc/passwd"})
        assert get_locale_name(request) == DEFAULT_LOCALE

    def test_accept_language_header_is_parsed(self):
        request = _FakeRequest(headers={"Accept-Language": "es-MX,es;q=0.9,en;q=0.8"})
        assert get_locale_name(request) == "es"

    def test_wildcard_accept_language(self):
        request = _FakeRequest(headers={"Accept-Language": "*"})
        assert get_locale_name(request) == DEFAULT_LOCALE

    def test_no_hints_gives_default(self):
        assert get_locale_name(_FakeRequest()) == DEFAULT_LOCALE
