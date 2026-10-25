import os

import formshare.resources as r


def create_resources(apppath, config):
    r.add_library("formshare", os.path.join(apppath, "jsandcss"), config)

    # ----------------------------Basic CSS-----------------------
    r.add_css_resource("formshare", "bootstrap", "css/bootstrap.min.css")
    r.add_css_resource("formshare", "font-5", "font-awesome/css/all.css")
    r.add_css_resource("formshare", "font-awesome", "font-awesome/css/v4-shims.css")
    r.add_css_resource(
        "formshare", "sweetalert", "css/plugins/sweetalert/sweetalert.css"
    )
    r.add_css_resource("formshare", "animate", "css/animate.css")
    r.add_css_resource("formshare", "style", "css/style.css")
    r.add_css_resource(
        "formshare",
        "rtl",
        "css/plugins/bootstrap-rtl/bootstrap-rtl.min.css",
        "bootstrap",
    )

    # ----------------------------Basic JS----------------------------------------------------
    r.add_js_resource("formshare", "jquery", "js/jquery-3.5.1.min.js")
    r.add_js_resource("formshare", "popper", "js/popper.min.js")
    r.add_js_resource("formshare", "bootstrap", "js/bootstrap.min.js")
    r.add_js_resource(
        "formshare", "metismenu", "js/plugins/metisMenu/jquery.metisMenu.js"
    )
    r.add_js_resource(
        "formshare", "slimscroll", "js/plugins/slimscroll/jquery.slimscroll.min.js"
    )
    r.add_js_resource("formshare", "pace", "js/plugins/pace/pace.min.js")
    r.add_js_resource("formshare", "wow", "js/plugins/wow/wow.min.js")
    r.add_js_resource(
        "formshare", "sweetalert", "js/plugins/sweetalert/sweetalert.min.js", "pace"
    )
    r.add_js_resource("formshare", "inspinia", "js/inspinia.js", None)

    # ----------------------------Profile----------------------------------
    r.add_css_resource(
        "formshare",
        "bsmarkdown",
        "css/plugins/bootstrap-markdown/bootstrap-markdown.min.css",
        "sweetalert",
    )
    r.add_js_resource(
        "formshare",
        "bsmarkdown",
        "js/plugins/bootstrap-markdown/bootstrap-markdown.js",
        None,
    )
    r.add_js_resource(
        "formshare",
        "markdown",
        "js/plugins/bootstrap-markdown/markdown.js",
        "bsmarkdown",
    )
    r.add_js_resource(
        "formshare", "clipboard", "js/plugins/clipboard/clipboard.js", None
    )

    # ------------------------------Add/Edit project--------------------------------------
    r.add_css_resource(
        "formshare", "switchery", "css/plugins/switchery/switchery.css", None
    )
    r.add_js_resource(
        "formshare", "switchery", "js/plugins/switchery/switchery.js", None
    )

    r.add_css_resource(
        "formshare", "datepicker", "css/plugins/datepicker/datepicker3.css", None
    )
    r.add_js_resource(
        "formshare", "datepicker", "js/plugins/datepicker/bootstrap-datepicker.js", None
    )

    r.add_css_resource(
        "formshare",
        "colorpicker",
        "css/plugins/evol-colorpicker/evol-colorpicker.min.css",
        None,
    )
    r.add_js_resource(
        "formshare",
        "colorpicker",
        "js/plugins/evol-colorpicker/evol-colorpicker.min.js",
        None,
    )

    r.add_css_resource(
        "formshare",
        "emoji",
        "js/plugins/emojiarea/emojionearea.css",
        None,
    )
    # EmojioneArea loads emojione from a CDN when the page has none
    # (emojione.min.js, below).
    r.add_js_resource(
        "formshare",
        "emojione",
        "js/plugins/emojiarea/emojione.min.js",
        None,
    )
    r.add_js_resource(
        "formshare",
        "emoji",
        "js/plugins/emojiarea/emojionearea.js",
        "emojione",
    )

    # ------------------------------Project details --------------------------------------
    r.add_js_resource(
        "formshare",
        "element_queries",
        "js/plugins/css-element-queries/ElementQueries.js",
        None,
    )
    r.add_js_resource(
        "formshare",
        "element_sensors",
        "js/plugins/css-element-queries/ResizeSensor.js",
        "element_queries",
    )
    r.add_css_resource("formshare", "leaflet", "js/plugins/leaflet/leaflet.css", None)
    r.add_js_resource(
        "formshare", "leaflet", "js/plugins/leaflet/leaflet.js", "element_sensors"
    )

    r.add_js_resource("formshare", "taphold", "js/plugins/taphold/taphold.js", None)

    r.add_css_resource(
        "formshare",
        "leaflet_beautify_marker_icon",
        "js/plugins/leaflet/plugins/leaflet-beautify-marker-icon.css",
        "leaflet",
    )
    r.add_js_resource(
        "formshare",
        "leaflet_beautify_marker_icon",
        "js/plugins/leaflet/plugins/leaflet-beautify-marker-icon.js",
        "leaflet",
    )
    r.add_js_resource(
        "formshare",
        "bs-custom-file-input",
        "js/plugins/bs-custom-file-input/bs-custom-file-input.min.js",
        "jquery",
    )
    r.add_js_resource("formshare", "sse", "js/plugins/sse/jquery.sse.js", "jquery")
    r.add_js_resource(
        "formshare", "codemirror", "js/plugins/codemirror/codemirror.js", None
    )
    r.add_js_resource(
        "formshare",
        "codemirror-shell",
        "js/plugins/codemirror/mode/shell/shell.js",
        "codemirror",
    )
    r.add_js_resource(
        "formshare",
        "codemirror-r",
        "js/plugins/codemirror/mode/r/r.js",
        "codemirror",
    )
    r.add_css_resource(
        "formshare", "codemirror", "css/plugins/codemirror/codemirror.css", None
    )
    r.add_css_resource(
        "formshare",
        "codemirror-ambiance",
        "css/plugins/codemirror/ambiance.css",
        "codemirror",
    )

    r.add_js_resource("formshare", "shuffle", "js/plugins/shuffle/shuffle.js", None)

    r.add_css_resource("formshare", "shuffle", "css/plugins/shuffle/test.css", None)

    r.add_js_resource(
        "formshare",
        "jqgrid_locale_en",
        "js/plugins/jqGrid/js/trirand/i18n/grid.locale-en.js",
        None,
    )
    r.add_js_resource(
        "formshare",
        "jqgrid",
        "js/plugins/jqGrid/js/trirand/jquery.jqGrid.min.js",
        "jqgrid_locale_en",
    )

    r.add_css_resource(
        "formshare",
        "jqgrid_bootstrap",
        "js/plugins/jqGrid/css/trirand/ui.jqgrid-bootstrap4.css",
        None,
    )

    r.add_js_resource(
        "formshare",
        "tippy",
        "js/plugins/tippy/tippy-bundle.iife.min.js",
        "popper",
    )

    r.add_js_resource(
        "formshare",
        "multiselect",
        "js/plugins/multiselect/multiselect.js",
        None,
    )

    # ------------------------------Collaborators, assistants and groups --------------------------------------
    r.add_css_resource(
        "formshare", "select2", "css/plugins/select2/select2.min.css", "bootstrap"
    )
    r.add_js_resource(
        "formshare", "select2", "js/plugins/select2/select2.full.min.js", None
    )
    r.add_js_resource("formshare", "md5", "js/plugins/md5/jquery.md5.js", None)

    r.add_js_resource(
        "formshare", "submenu", "js/plugins/submenu/bootstrap-submenu.min.js", None
    )
    r.add_css_resource(
        "formshare", "submenu", "css/plugins/submenu/bootstrap-submenu.min.css", None
    )

    # --------------------------------------JSON---------------------------
    r.add_css_resource(
        "formshare", "simplemde", "js/plugins/simplemde/simplemde.min.css", "bootstrap"
    )
    r.add_js_resource(
        "formshare", "simplemde", "js/plugins/simplemde/simplemde.min.js", None
    )
    r.add_js_resource("formshare", "showdown", "js/plugins/showdown/showdown.js", None)
    r.add_js_resource("formshare", "ias", "js/plugins/ias/jquery-ias.min.js", None)

    # ---------------------------------- Gallery -----------------------------

    r.add_css_resource(
        "formshare", "blueimp", "css/plugins/blueimp/css/blueimp-gallery.min.css", None
    )
    r.add_js_resource(
        "formshare", "blueimp", "js/plugins/blueimp/jquery.blueimp-gallery.min.js", None
    )

    # ------------------------------------ Tour -------------------------------------
    r.add_css_resource(
        "formshare",
        "tour",
        "css/plugins/tour/bootstrap-tour-standalone.min.css",
        "bootstrap",
    )
    r.add_js_resource(
        "formshare",
        "tour",
        "js/plugins/tour/bootstrap-tour-standalone.min.js",
        "bootstrap",
    )

    # ------------------- Libraries that pages loaded from CDNs -------------------
    # Bundled so that no script from another origin runs on a FormShare page:
    # the Encryption plugin's vault opens answers for any page of the origin,
    # so a CDN's script anywhere could read them
    # (docs/formshare_field_encryption/formshare.md 13.4). Each file is the
    # published one, checked against the CDNs' integrity hashes or a second
    # CDN (2026-10-13): htmx 2.0.4 (npm htmx.org), highlight.js 9.9.0 with its
    # scala language and github style, jQuery UI 1.12.1 (jqGrid carries its
    # own 1.11.2), jQuery QueryBuilder 3.0.0 standalone, jsPlumb 2.15.6.
    # emojione 3.1.2 (MIT code, js/plugins/emojiarea) was a CDN script that
    # EmojioneArea fetched at runtime, which the policy's 'strict-dynamic'
    # lets through: the npm tarball's, which jsDelivr's npm mirror and cdnjs
    # serve identically (2026-10-14). Its artwork stays on jsDelivr as
    # images (sprite: false where the picker is made).
    r.add_js_resource("formshare", "htmx", "js/plugins/htmx/htmx.min.js", None)
    r.add_js_resource(
        "formshare", "highlightjs", "js/plugins/highlightjs/highlight.min.js", None
    )
    r.add_js_resource(
        "formshare",
        "highlightjs_scala",
        "js/plugins/highlightjs/languages/scala.min.js",
        "highlightjs",
    )
    r.add_css_resource(
        "formshare", "highlightjs", "js/plugins/highlightjs/github.min.css", None
    )
    r.add_js_resource(
        "formshare", "jqueryui", "js/plugins/jquery-ui-1.12.1/jquery-ui.min.js", None
    )
    r.add_js_resource(
        "formshare",
        "querybuilder",
        "js/plugins/querybuilder/js/query-builder.standalone.min.js",
        None,
    )
    r.add_css_resource(
        "formshare",
        "querybuilder_default",
        "js/plugins/querybuilder/css/query-builder.default.min.css",
        None,
    )
    # FormShare's look for it, after the library's (the file says why): a
    # page that needs "querybuilder" gets both, in that order
    r.add_css_resource(
        "formshare",
        "querybuilder",
        "js/plugins/querybuilder/css/query-builder.formshare.css",
        "querybuilder_default",
    )
    r.add_js_resource("formshare", "jsplumb", "js/plugins/jsplumb/jsplumb.min.js", None)

    # The code editor of a form's actions in expert mode: CodeMirror 6 with
    # the actions API, one script built from frontend/actions-editor (its
    # README; THIRD_PARTY_LICENSES.txt beside the bundle). The page runs this
    # file, never the source: rebuild it with the source change.
    r.add_js_resource(
        "formshare",
        "actions_editor",
        "js/plugins/codemirror6/actions_editor.min.js",
        None,
    )

    # The page behaviours declared with data-* attributes instead of inline
    # event handlers, which the Content-Security-Policy refuses
    # (formshare/config/csp.py). base.jinja2 loads it on every page.
    r.add_js_resource("formshare", "behaviours", "js/formshare-behaviours.js", None)
