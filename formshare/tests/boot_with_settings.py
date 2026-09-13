"""Boot FormShare in a process of its own with some settings changed, and
make a few requests. For the code that reads a setting once, at startup.

    python -m formshare.tests.boot_with_settings \\
        --set formshare.static_no_cache=true --get /=200 --get /join

A second app cannot be created in the suite's process (the resource, product
and plugin registries are module-wide and refuse a second registration), so
the step that needs one runs this module as a subprocess, from the project
directory so that the package is imported from it. Coverage follows it
here through ``patch = subprocess`` in .coveragerc, so what runs here counts.

Each --get is a path, optionally with =status; a wrong status makes the
process exit with 1. Nothing in here runs at import: pytest imports every
module under formshare/tests.
"""

import argparse
import json
import os
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--get", action="append", default=[], metavar="PATH[=STATUS]")
    args = parser.parse_args(argv)
    return _boot_and_get(args)


def _boot_and_get(args):
    from a2wsgi import ASGIMiddleware
    from webtest import TestApp

    from formshare import main as make_app

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "test_config.json")) as config_file:
        settings = json.load(config_file)
    for item in args.set:
        key, _, value = item.partition("=")
        settings[key] = value

    app = TestApp(ASGIMiddleware(make_app(None, **settings)))
    failed = 0
    for item in args.get:
        path, _, expected = item.partition("=")
        res = app.get(path, status="*")
        good = not expected or str(res.status_int) == expected
        print(
            "{} {} {}".format("ok " if good else "BAD", res.status_int, path),
            flush=True,
        )
        if not good:
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
