"""Run a few steps of the functional suite, under coverage, without editing
test_00_root.py.

The suite in formshare/tests/test_00_root.py is one test function that runs
77 steps in order and takes over an hour. Filling a coverage gap means running
one step, and the steps depend on the state the earlier ones leave behind, so
the usual way has been to set ``run_whole_suite = False`` and edit the calls
before the gate. This file does the same from outside the tree, where pytest
does not collect it on a normal run.

The six base steps (root, cookie consent, login, dashboard, profile and
projects) always run first. FS_STEPS then names the rest, comma separated::

    export FORMSHARE_PYTEST_RUNNING=true USE_RSTOOLS=True
    FS_STEPS="assistants,assistant_groups,forms,odk,htmx_partials" \\
        ../env_formshare3/bin/pytest -q -p no:cacheprovider -c pytest.ini \\
        --cov=formshare --cov-config=.coveragerc --cov-report= tools/run_steps.py
    ../env_formshare3/bin/coverage report --include=formshare/views/form.py

An entry is a step module under formshare.tests.steps, whose function is then
``t_e_s_t_<name>``; ``module:function`` names any other function (a module
without a dot is looked for under the steps package); and ``sleep:N`` waits
N seconds, as the suite does before importing data. Remember the state a step
needs: the ODK step wants the forms step, the clean interface wants a
repository with data, and the merge steps want form_merge_start.
"""

import importlib
import os
import time

import sys

os.environ.setdefault("FORMSHARE_PYTEST_RUNNING", "true")
# The package is also reachable through a symlink in site-packages; the
# steps locate mysql.cnf from their own __file__, so import it from here
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_root = importlib.import_module("formshare.tests.test_00_root")

BASE = ["root", "cookie_consent", "login", "dashboard", "profile", "projects"]


def _resolve(spec):
    if ":" in spec:
        module_name, function_name = spec.rsplit(":", 1)
        if "." not in module_name:
            module_name = "formshare.tests.steps." + module_name
    else:
        module_name = "formshare.tests.steps." + spec
        function_name = "t_e_s_t_" + spec
    return getattr(importlib.import_module(module_name), function_name)


class SomeSteps(_root.FunctionalTests):
    def test_all(self):
        test_object = self.test_object
        for name in BASE:
            print("Base step", name, flush=True)
            _resolve(name)(test_object)
        for spec in os.environ.get("FS_STEPS", "").split(","):
            spec = spec.strip()
            if not spec:
                continue
            print("Step", spec, flush=True)
            if spec.startswith("sleep:"):
                time.sleep(int(spec.split(":")[1]))
                continue
            step = _resolve(spec)
            try:
                step(test_object)
            except TypeError as e:
                # A few steps take no test object at all
                if "t_e_s_t_" not in str(e):
                    raise
                step()
