/*
 * FormShare's shared page behaviours, declared in the markup with data-*
 * attributes instead of inline event handlers (onclick="..."), which a
 * Content-Security-Policy refuses to run (formshare/config/csp.py).
 *
 * Every listener is on the document, so a behaviour works wherever its
 * element is -- a snippet included by any page, a fragment loaded later --
 * and a template needs no script of its own for it. Plugins may use the same
 * attributes.
 *
 *   data-href="<url>"                 a click goes to the URL
 *   data-invalid-message="<text>"     the message a required field shows when
 *                                     it is left empty, cleared as soon as
 *                                     something is typed or chosen
 *   data-allowed-chars="<class>"      a key is typed only if it matches the
 *                                     character class, as "[0-9a-zA-Z_]"
 */
(function () {
    "use strict";

    document.addEventListener("click", function (event) {
        var element = event.target.closest("[data-href]");
        if (element === null || element.disabled) {
            return;
        }
        event.preventDefault();
        window.location.href = element.getAttribute("data-href");
    });

    // "invalid" does not bubble: it is caught on its way down.
    document.addEventListener(
        "invalid",
        function (event) {
            var element = event.target;
            if (element && element.hasAttribute && element.hasAttribute("data-invalid-message")) {
                element.setCustomValidity(element.getAttribute("data-invalid-message"));
            }
        },
        true
    );

    function clearValidity(event) {
        var element = event.target;
        if (element && element.hasAttribute && element.hasAttribute("data-invalid-message")) {
            element.setCustomValidity("");
        }
    }
    document.addEventListener("input", clearValidity);
    document.addEventListener("change", clearValidity);

    document.addEventListener("keypress", function (event) {
        var element = event.target;
        if (!element || !element.hasAttribute || !element.hasAttribute("data-allowed-chars")) {
            return;
        }
        if (event.key.length !== 1) {
            return; // Enter, arrows and the like are not characters
        }
        var allowed = new RegExp(element.getAttribute("data-allowed-chars"), "i");
        if (!allowed.test(event.key)) {
            event.preventDefault();
        }
    });
})();
