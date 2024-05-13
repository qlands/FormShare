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
    r.add_js_resource(
        "formshare",
        "emoji",
        "js/plugins/emojiarea/emojionearea.js",
        None,
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
        "js/plugins/multiselect/multiselect.min.js",
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
