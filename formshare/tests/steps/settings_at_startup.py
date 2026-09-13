"""Settings that create_app reads once, which no flip at run time reaches.

The app is booted again in a subprocess with those settings changed (see
formshare/tests/boot_with_settings.py for why a subprocess), and a few pages
are requested from it.
"""

import os
import subprocess
import sys


def t_e_s_t_settings_at_startup(test_object):
    project_root = os.path.dirname(os.path.dirname(test_object.path))
    command = [
        sys.executable,
        "-m",
        "formshare.tests.boot_with_settings",
        # Static files are served with no-cache, revalidated on every request
        "--set",
        "formshare.static_no_cache=true",
        "--get",
        "/=200",
        "--get",
        "/fstatic/ephemeral/no_such_file.js=404",
        "--get",
        "/login=200",
    ]
    done = subprocess.run(
        command, cwd=project_root, capture_output=True, text=True, timeout=900
    )
    assert done.returncode == 0, done.stdout + done.stderr
    assert "ok  200 /" in done.stdout
